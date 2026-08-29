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
import subprocess
import sys
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

    def parent_from_authority(self, authority: Mapping[str, Any]) -> ProgramParent:
        """The live parent for an authority sidecar, checked against its record.

        The sidecar records the parent the grant was issued beneath. This
        re-reads canonical state and refuses any drift from that record, so an
        effect can never run under an authority whose parent has been replaced,
        re-leased, re-based, or re-rendered since the grant.
        """
        recorded = dict(authority.get("program_parent") or {})
        binding = {
            "task_id": authority.get("task_id") or recorded.get("task_id"),
            "lease_id": recorded.get("lease_id"),
            "base_sha": recorded.get("base_sha"),
            "branch": recorded.get("branch"),
            "contract_digest": recorded.get("contract_digest"),
            "worktree": recorded.get("worktree"),
        }
        recorded_workspace = _text(recorded.get("workspace"))
        if recorded_workspace and recorded_workspace != str(self.workspace):
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_WORKSPACE_DRIFT: authority workspace "
                f"{recorded_workspace!r} != {str(self.workspace)!r}"
            )
        parent = self.require_live_parent(binding)
        if bool(recorded.get("bound")) and not parent.bound:
            raise ProgramAuthorityError(
                "PROGRAM_PARENT_UNBOUND: canonical Program state disappeared for task "
                f"{parent.task_id!r}"
            )
        for field_name in ("branch", "worktree"):
            declared = _text(recorded.get(field_name))
            actual = _text(getattr(parent, field_name))
            if declared and actual and declared != actual:
                raise ProgramAuthorityError(
                    f"PROGRAM_PARENT_{field_name.upper()}_DRIFT: authority "
                    f"{declared!r} != parent {actual!r}"
                )
        return parent

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


# ---------------------------------------------------------------------------
# Effect authorization
#
# Everything above answers "is the Program parent live?". Everything below is
# the single PE-to-root authorizer for one *effect*: the worker is about to run
# a tool, and nothing may reach the filesystem until the root gateway has
# allowed that exact capability on that exact resource under this task's
# subordinate lease.
# ---------------------------------------------------------------------------

#: Tools whose argument is a shell command rather than a path.
SHELL_TOOLS = frozenset({"Bash", "Shell", "run_terminal_cmd"})

#: Capabilities the gateway resolves against a repository-relative path.
PATH_CAPABILITY_PREFIXES = ("repository.", "file.", "git.diff")

# Authorization phases recorded in a gateway decision's metadata. This module
# owns the vocabulary because it is the one loaded standalone by the live
# PreToolUse hook; `grant.py` imports these rather than restating them.
#
# Both phases are genuine gateway decisions under the same subordinate lease,
# so only the caller can tell them apart:
#
# * `effect` -- taken here, immediately before a real tool call.
# * `grant_probe` -- taken by `grant.py` while issuing the lease, to prove it
#   holds the capability it claims. No effect follows it.
#
# Mediation coverage counts only `effect`. Letting a `grant_probe` satisfy it
# would mean one probe on the task's first writable path silently vouching for
# every unmediated write a provider then made to that path.
AUTHORIZATION_PHASE_EFFECT = "effect"
AUTHORIZATION_PHASE_GRANT_PROBE = "grant_probe"


@dataclass(frozen=True)
class EffectDecision:
    """One root authorization verdict for one worker tool call."""

    allowed: bool
    code: str
    message: str
    tool_name: str
    capability: str | None = None
    resource: str | None = None
    lease_id: str | None = None
    parent: ProgramParent | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "code": self.code,
            "message": self.message,
            "tool_name": self.tool_name,
            "capability": self.capability,
            "resource": self.resource,
            "lease_id": self.lease_id,
            "program_parent": self.parent.to_dict() if self.parent is not None else None,
        }


def _ensure_import_paths() -> None:
    """Make root autonomy and Peer Execution importable from any host process.

    The hook that calls this authorizer runs from the governance clone, not
    from a Python package rooted here.
    """
    here = Path(__file__).resolve().parent
    for candidate in (here, here.parents[1], here.parents[3]):
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


def normalize_effect_resource(worktree: str | Path | None, resource: str | None) -> str:
    """One repository-relative resource for the gateway, or fail closed.

    The gateway authorizes repository-relative paths against campaign and action
    scope. A worker hands over whatever its host tool reported — usually an
    absolute path inside the task worktree. Anything that leaves the worktree,
    by absolute path, by traversal, or through a symlink, is not this task's
    resource and is refused here rather than normalized into something the
    gateway would accept.
    """
    raw = (resource or "").strip()
    if not raw:
        raise ProgramAuthorityError("RESOURCE_REQUIRED: this effect has no resource to authorize")
    if "\x00" in raw:
        raise ProgramAuthorityError("RESOURCE_INVALID: resource contains a NUL byte")
    if worktree is None or not str(worktree).strip():
        raise ProgramAuthorityError("WORKTREE_UNBOUND: no worktree to normalize this resource in")
    root = Path(str(worktree)).expanduser()
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        try:
            relative = candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        except ValueError as exc:
            raise ProgramAuthorityError(
                f"RESOURCE_OUTSIDE_WORKTREE: absolute path {raw!r} is outside {str(root)!r}"
            ) from exc
    else:
        if ".." in candidate.parts:
            raise ProgramAuthorityError(
                f"RESOURCE_TRAVERSAL: {raw!r} traverses out of the worktree"
            )
        try:
            relative = (
                (root / candidate).resolve(strict=False).relative_to(root.resolve(strict=False))
            )
        except ValueError as exc:
            raise ProgramAuthorityError(
                f"RESOURCE_OUTSIDE_WORKTREE: {raw!r} resolves outside {str(root)!r}"
            ) from exc
    normalized = relative.as_posix()
    if not normalized or normalized == ".":
        raise ProgramAuthorityError("RESOURCE_INVALID: resource must name a path in the worktree")
    # A symlinked parent or target is an escape the resolved path already hid:
    # `resolve()` followed the link, so the check has to be on the links
    # themselves, walked from the worktree root.
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ProgramAuthorityError(f"RESOURCE_SYMLINK_PARENT: {str(cursor)!r} is a symlink")
    target = root / relative
    if target.is_symlink():
        raise ProgramAuthorityError(f"RESOURCE_SYMLINK: {str(target)!r} is a symlink")
    return normalized


def canonical_shell_capability(command: str) -> str:
    """`test.run`, but only for a command the canonical PE grammar admits.

    Root autonomy maps a shell tool to `test.run`. Without this check any shell
    string at all would inherit the capability a validation command was granted,
    so the existing peer_execution grammar — one operation, no substitution, no
    inline interpreter, read-only git — is what decides.
    """
    _ensure_import_paths()
    from peer_execution.validation_command import (  # noqa: PLC0415
        ValidationCommandError,
        validate_validation_command,
    )

    try:
        validate_validation_command(command)
    except ValidationCommandError as exc:
        raise ProgramAuthorityError(f"SHELL_COMMAND_NOT_CANONICAL: {exc}") from exc
    return "test.run"


class ProgramBoundEffectAuthorizer:
    """Authorize one worker effect under a live Program parent, or refuse.

    Order matters and is fail-closed at every step:

    1. re-read the canonical Program parent (no cache, no transition);
    2. resolve the capability, admitting `test.run` only for a shell command
       the canonical validation grammar accepts;
    3. normalize the resource inside the bound worktree, refusing escapes;
    4. heartbeat the subordinate lease against the worktree's *actual* HEAD, so
       a drifted base revokes the lease instead of authorizing over it;
    5. ask the root gateway, through the live orchestrator, for this exact
       capability on this exact resource.
    """

    def __init__(
        self,
        authority: Mapping[str, Any],
        *,
        orchestrator: Any = None,
        head_reader: Any = None,
    ) -> None:
        self.authority = dict(authority)
        for field_name in ("task_id", "adapter_session_id", "lease_id", "agent_id"):
            if not _text(self.authority.get(field_name)):
                raise ProgramAuthorityError(
                    f"AUTONOMY_AUTHORITY_INCOMPLETE: missing {field_name!r}"
                )
        self._orchestrator = orchestrator
        self._head_reader = head_reader or _worktree_head
        workspace = _text(self.authority.get("workspace")) or _text(
            (self.authority.get("program_parent") or {}).get("workspace")
        )
        if not workspace:
            raise ProgramAuthorityError("AUTONOMY_AUTHORITY_INCOMPLETE: missing 'workspace'")
        self.verifier = ProgramAuthorityVerifier(workspace)

    @property
    def orchestrator(self) -> Any:
        if self._orchestrator is None:
            self._orchestrator = self._default_orchestrator()
        return self._orchestrator

    def authorize(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> EffectDecision:
        arguments = dict(arguments or {})
        try:
            parent = self.verifier.parent_from_authority(self.authority)
        except ProgramAuthorityError as exc:
            return self._denied(tool_name, exc)
        try:
            capability = self._capability_for(tool_name, arguments)
            resource = self._resource_for(capability, parent, tool_name, arguments)
            self._heartbeat(parent)
        except ProgramAuthorityError as exc:
            return self._denied(tool_name, exc, parent=parent)
        _ensure_import_paths()
        from autonomy.adapters import tool_hook  # noqa: PLC0415
        from autonomy.errors import PolicyViolation  # noqa: PLC0415

        try:
            decision = tool_hook.pre_tool_use(
                tool_name=tool_name,
                arguments=arguments,
                orchestrator=self.orchestrator,
                session_id=str(self.authority["adapter_session_id"]),
                lease_id=str(self.authority["lease_id"]),
                agent_id=str(self.authority["agent_id"]),
                capability=capability,
                resource=resource,
                require_allowed=False,
                metadata=self._effect_metadata(parent),
            )
        except (PolicyViolation, KeyError, ValueError, OSError, RuntimeError) as exc:
            return self._denied(
                tool_name,
                ProgramAuthorityError(f"ROOT_AUTHORIZATION_UNAVAILABLE: {exc}"),
                parent=parent,
                capability=capability,
                resource=resource,
            )
        return EffectDecision(
            allowed=bool(decision.get("allowed")),
            code=str(decision.get("code") or "UNKNOWN"),
            message=str(decision.get("message") or ""),
            tool_name=tool_name,
            capability=capability,
            resource=resource,
            lease_id=str(self.authority["lease_id"]),
            parent=parent,
        )

    def _effect_metadata(self, parent: ProgramParent) -> dict[str, Any]:
        """Annotation proving this decision was taken to authorize an effect.

        Recorded with the decision so campaign reconciliation can ask the one
        question that matters: did *this* change carry a pre-effect
        authorization, or only the probe the grant took on its way in?
        """
        return {
            "authorization_phase": AUTHORIZATION_PHASE_EFFECT,
            "program_task_id": _text(self.authority.get("task_id")),
            "program_lease_id": parent.lease_id,
        }

    def _capability_for(self, tool_name: str, arguments: Mapping[str, Any]) -> str:
        _ensure_import_paths()
        from autonomy.adapters import tool_hook  # noqa: PLC0415

        if tool_name in SHELL_TOOLS:
            command = arguments.get("command") or arguments.get("cmd") or ""
            if not isinstance(command, str) or not command.strip():
                raise ProgramAuthorityError("SHELL_COMMAND_MISSING: no command to validate")
            return canonical_shell_capability(command)
        capability = tool_hook.infer_capability(tool_name, arguments)
        if capability == "test.run":
            # Only the validated shell path above may reach test.run.
            raise ProgramAuthorityError(
                f"SHELL_CAPABILITY_NOT_VALIDATED: {tool_name!r} may not claim test.run"
            )
        return capability

    def _resource_for(
        self,
        capability: str,
        parent: ProgramParent,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> str | None:
        _ensure_import_paths()
        from autonomy.adapters import tool_hook  # noqa: PLC0415

        if not capability.startswith(PATH_CAPABILITY_PREFIXES):
            return None
        worktree = self._worktree(parent)
        return normalize_effect_resource(worktree, tool_hook.infer_resource(tool_name, arguments))

    def _worktree(self, parent: ProgramParent) -> str | None:
        recorded = (self.authority.get("program_parent") or {}).get("worktree")
        return _text(parent.worktree) or _text(recorded)

    def _heartbeat(self, parent: ProgramParent) -> None:
        """Prove the worktree still stands on the authorized base."""
        worktree = self._worktree(parent)
        if not worktree:
            return
        observed = self._head_reader(worktree)
        if observed is None:
            raise ProgramAuthorityError(
                f"WORKTREE_HEAD_UNREADABLE: cannot read the actual HEAD of {worktree!r}"
            )
        _ensure_import_paths()
        from autonomy.errors import PolicyViolation  # noqa: PLC0415

        try:
            self.orchestrator.heartbeat(
                session_id=str(self.authority["adapter_session_id"]),
                lease_id=str(self.authority["lease_id"]),
                agent_id=str(self.authority["agent_id"]),
                base_sha=observed,
                status="RUNNING",
                progress={"task_id": self.authority.get("task_id")},
            )
        except (PolicyViolation, KeyError, ValueError) as exc:
            raise ProgramAuthorityError(f"ROOT_HEARTBEAT_REFUSED: {exc}") from exc

    def _denied(
        self,
        tool_name: str,
        exc: ProgramAuthorityError,
        *,
        parent: ProgramParent | None = None,
        capability: str | None = None,
        resource: str | None = None,
    ) -> EffectDecision:
        message = str(exc)
        code = message.split(":", 1)[0] if ":" in message else "PROGRAM_AUTHORITY_DENIED"
        return EffectDecision(
            allowed=False,
            code=code,
            message=message,
            tool_name=tool_name,
            capability=capability,
            resource=resource,
            lease_id=_text(self.authority.get("lease_id")),
            parent=parent,
        )

    def _default_orchestrator(self) -> Any:
        _ensure_import_paths()
        from autonomy.adapters.orchestrator import AdapterOrchestrator  # noqa: PLC0415
        from autonomy.runtime.engine import AutonomyRuntime  # noqa: PLC0415

        root = _text(self.authority.get("repository_root")) or "."
        database = _text(self.authority.get("runtime_database"))
        if not database:
            raise ProgramAuthorityError("AUTONOMY_AUTHORITY_INCOMPLETE: missing 'runtime_database'")
        runtime = AutonomyRuntime.from_repository(
            repository_root=root,
            database_path=database,
        )
        return AdapterOrchestrator(runtime, repository_root=root)


def _worktree_head(worktree: str | Path) -> str | None:
    """The worktree's actual current HEAD, or None when it cannot be read."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(worktree), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    head = completed.stdout.strip()
    return head or None
