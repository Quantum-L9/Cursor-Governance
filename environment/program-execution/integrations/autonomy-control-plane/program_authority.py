"""Read-only canonical Program parent authority for subordinate root leases.

Program Execution Controller (PEC) is the sole owner of Program state. A root
autonomy lease issued for a Program task is *subordinate*: it exists only while
the Program parent lease that justifies it is live, and it may never outlive it.

This module is the one place that reads that parent state. It is deliberately
read-only:

* every call re-reads the canonical PEC SQLite state, so a caller can never act
  on a cached parent that was revoked a second ago;
* the connection is opened read-only (``mode=ro``, or ``PRAGMA query_only`` when
  the URI form is unavailable), so a defect here cannot create or mutate
  Program truth;
* no Program transition is ever performed, requested, or implied.

A workspace without a canonical PEC state database is reported as *unbound*
rather than silently treated as live: the caller records `bound: false` in its
authority evidence instead of claiming a parent it never read.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Canonical PEC durable state, relative to the Program workspace.
PROGRAM_STATE_RELATIVE = Path("runtime") / "state.sqlite"

#: Task runtime states in which a Program parent may carry live work authority.
#: COMPLETED/FAILED/STALE/CANCELLED are terminal for the attempt and therefore
#: never authorize a subordinate effect.
LIVE_TASK_STATES = frozenset(
    {
        "LEASED",
        "PREPARED",
        "CONTRACTED",
        "EXECUTING",
        "SUBMITTED",
        "VERIFYING",
    }
)


class ProgramAuthorityError(RuntimeError):
    """The canonical Program parent does not authorize this subordinate."""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class ProgramParent:
    """One immutable read of the canonical Program parent for a task."""

    workspace: str
    task_id: str
    bound: bool
    runtime_state: str | None = None
    lease_id: str | None = None
    lease_active: bool = False
    base_sha: str | None = None
    branch: str | None = None
    worktree: str | None = None
    contract_digest: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "task_id": self.task_id,
            "bound": self.bound,
            "runtime_state": self.runtime_state,
            "lease_id": self.lease_id,
            "lease_active": self.lease_active,
            "base_sha": self.base_sha,
            "branch": self.branch,
            "worktree": self.worktree,
            "contract_digest": self.contract_digest,
            "expires_at": self.expires_at,
        }

    def remaining_seconds(self, *, now: datetime | None = None) -> float | None:
        """Seconds of parent authority left, or None when no expiry is bound."""
        expiry = _parse_timestamp(self.expires_at)
        if expiry is None:
            return None
        moment = now or datetime.now(tz=UTC)
        return (expiry - moment).total_seconds()


class ProgramAuthorityVerifier:
    """Read-only resolver for the canonical PEC parent of one Program task."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()

    @property
    def state_path(self) -> Path:
        return self.workspace / PROGRAM_STATE_RELATIVE

    def is_bound(self) -> bool:
        """Whether this workspace carries canonical PEC durable state."""
        return self.state_path.is_file()

    def resolve_parent(self, contract: Mapping[str, Any]) -> ProgramParent:
        """Read the canonical parent for one rendered contract. Never cached."""
        task_id = _text(contract.get("task_id") or contract.get("id")) or "task"
        if not self.is_bound():
            return ProgramParent(
                workspace=str(self.workspace),
                task_id=task_id,
                bound=False,
                base_sha=_text(contract.get("base_sha")),
                branch=_text(contract.get("branch")),
                worktree=_text(contract.get("worktree")),
                contract_digest=_text(contract.get("contract_digest")),
                lease_id=_text(contract.get("lease_id")),
            )
        connection = self._connect()
        try:
            task_row = connection.execute(
                "SELECT runtime_state, base_sha, branch, worktree, lease_id, "
                "rendered_contract_digest FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            lease_row = connection.execute(
                "SELECT lease_id, base_sha, branch, worktree, contract_digest, expires_at, active "
                "FROM leases WHERE task_id = ? AND active = 1",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        if task_row is None:
            raise ProgramAuthorityError(
                f"PROGRAM_PARENT_UNKNOWN: canonical Program state has no task {task_id!r}"
            )
        # The active lease is the live parent binding; the task row is the
        # fallback for a task whose lease has already been released.
        source = lease_row if lease_row is not None else task_row
        return ProgramParent(
            workspace=str(self.workspace),
            task_id=task_id,
            bound=True,
            runtime_state=_text(task_row["runtime_state"]),
            lease_id=_text(lease_row["lease_id"]) if lease_row is not None else None,
            lease_active=lease_row is not None,
            base_sha=_text(source["base_sha"]),
            branch=_text(source["branch"]),
            worktree=_text(source["worktree"]),
            contract_digest=_text(
                (lease_row["contract_digest"] if lease_row is not None else None)
                or task_row["rendered_contract_digest"]
            ),
            expires_at=_text(lease_row["expires_at"]) if lease_row is not None else None,
        )

    def require_live_parent(
        self,
        contract: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> ProgramParent:
        """Resolve the parent and fail closed unless it is live and matching.

        An unbound workspace carries no canonical parent to contradict, so the
        contract's own binding is returned as-is. Every bound parent must be in
        a live runtime state, hold an active unexpired lease, and match the
        contract's lease/base/contract binding where the contract declares one.
        """
        parent = self.resolve_parent(contract)
        if not parent.bound:
            return parent
        if parent.runtime_state not in LIVE_TASK_STATES:
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_NOT_LIVE: task "
                f"{parent.task_id!r} runtime_state={parent.runtime_state!r}"
            )
        if not parent.lease_active or not parent.lease_id:
            raise ProgramAuthorityError(
                f"PROGRAM_PARENT_LEASE_INACTIVE: task {parent.task_id!r} has no active lease"
            )
        declared_lease = _text(contract.get("lease_id"))
        if declared_lease and declared_lease != parent.lease_id:
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_LEASE_DRIFT: contract lease "
                f"{declared_lease!r} != active lease {parent.lease_id!r}"
            )
        declared_base = _text(contract.get("base_sha"))
        if declared_base and parent.base_sha and declared_base != parent.base_sha:
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_BASE_DRIFT: contract base "
                f"{declared_base!r} != parent base {parent.base_sha!r}"
            )
        declared_digest = _text(contract.get("contract_digest"))
        if declared_digest and parent.contract_digest and declared_digest != parent.contract_digest:
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_CONTRACT_DRIFT: contract digest "
                f"{declared_digest!r} != parent digest {parent.contract_digest!r}"
            )
        remaining = parent.remaining_seconds(now=now)
        if remaining is not None and remaining <= 0:
            raise ProgramAuthorityError(
                f"PROGRAM_PARENT_EXPIRED: task {parent.task_id!r} lease expired at "
                f"{parent.expires_at}"
            )
        return parent

    def subordinate_ttl_seconds(
        self,
        parent: ProgramParent,
        *,
        default_ttl_seconds: int,
        now: datetime | None = None,
    ) -> int:
        """Root TTL, capped so the child can never outlive the Program parent."""
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        remaining = parent.remaining_seconds(now=now)
        if remaining is None:
            return int(default_ttl_seconds)
        bounded = int(remaining)
        if bounded <= 0:
            raise ProgramAuthorityError(
                f"PROGRAM_PARENT_EXPIRED: task {parent.task_id!r} has no remaining authority"
            )
        return max(1, min(int(default_ttl_seconds), bounded))

    def _connect(self) -> sqlite3.Connection:
        """A connection that cannot write, whichever SQLite build is present."""
        path = self.state_path
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            # A build without URI filenames still gets a query-only handle: the
            # point is that this module never writes Program truth.
            connection = sqlite3.connect(str(path))
            connection.execute("PRAGMA query_only = ON")
        connection.row_factory = sqlite3.Row
        return connection
