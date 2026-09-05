"""Native Cursor host admission over the root autonomy control plane.

This is the canonical producer PR #287's fail-closed lifecycle hooks were
waiting for: it binds a host ``tool_use_id`` (preToolUse Task) and a host
``subagent_id`` (subagentStart) to authority that already exists in the root
Autonomy runtime — an adapter session, a READY action, an ACTIVE lease, and a
rendered agent contract.

It is deliberately thin. Authority, scheduling, lease, capability, and
artifact decisions belong to the existing root owners (`AutonomyRuntime`,
`AdapterOrchestrator`); this module only correlates host identifiers to that
state and never derives scope or authority from Task prose. A prompt may carry
the opaque admission token, but the token is a lookup key for persisted
authority, not authority itself.

Correlation state lives in an adapter extension table inside the existing root
Autonomy SQLite database — never a second database or JSON authority store.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any

from autonomy.adapters.cursor.adapter import _cursor_subagent_type
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.runtime.leases import (
    independence_sources,
    producer_agent_ids,
    requires_independence,
)
from autonomy.runtime.timeutil import parse_timestamp, utc_now, utc_now_text

_BINDINGS_REL = Path("environment/agents/PEER_RUNTIME_BINDINGS.yaml")


def _cursor_deployment_readiness_required(repo_root: Path) -> bool:
    path = Path(repo_root) / _BINDINGS_REL
    if not path.is_file():
        return False
    try:
        import yaml
    except ImportError:
        return True
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return True
    if not isinstance(document, dict):
        return True
    peer = (document.get("peers") or {}).get("cursor") or {}
    deployment = (peer.get("subagents") or {}).get("deployment") or {}
    return bool(deployment.get("readiness_required"))


def _require_cursor_deployment_ready(workspace: Path, repo_root: Path) -> None:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from environment.agents.deployment.receipts import (
        DeploymentNotReady,
        require_cursor_deployment_ready,
    )

    try:
        require_cursor_deployment_ready(workspace, repo_root)
    except DeploymentNotReady:
        raise
    except Exception as exc:
        raise DeploymentNotReady(str(exc)) from exc


ADMISSION_SCHEMA = "l9.cursor-host-admission.v1"

_ADMISSION_DDL = """
CREATE TABLE IF NOT EXISTS cursor_host_admissions (
    admission_token TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    session_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    role TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    allowed_paths_json TEXT NOT NULL,
    forbidden_paths_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    tool_use_id TEXT,
    bound_at TEXT,
    subagent_id TEXT,
    parent_conversation_id TEXT,
    model TEXT,
    is_parallel_worker INTEGER,
    git_branch TEXT,
    started_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cursor_host_admissions_tool_use
    ON cursor_host_admissions(tool_use_id) WHERE tool_use_id IS NOT NULL;
"""

# Columns added after the table first shipped. ``CREATE TABLE IF NOT EXISTS``
# never widens an existing table, so they are reconciled per connection.
_ADMISSION_COLUMNS = (
    ("action_allowed_paths_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("subject_agent_id", "TEXT"),
    ("expected_subagent_type", "TEXT"),
)


def _ensure_admission_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_ADMISSION_DDL)
    present = {row[1] for row in connection.execute("PRAGMA table_info(cursor_host_admissions)")}
    for name, declaration in _ADMISSION_COLUMNS:
        if name not in present:
            # SQLite cannot bind identifiers or type declarations as
            # parameters, so an ALTER TABLE ... ADD COLUMN has to be composed.
            # Both halves come from _ADMISSION_COLUMNS, a module-level literal
            # tuple; no caller value reaches this string.
            # nosemgrep: l9.baseline.python.sql-string-format
            connection.execute(
                f"ALTER TABLE cursor_host_admissions ADD COLUMN {name} {declaration}"
            )
    connection.commit()


def _connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    _ensure_admission_schema(connection)
    return connection


def _deny(reason: str) -> dict[str, Any]:
    return {"allowed": False, "reason": reason}


def _admission_dict(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["allowed_paths"] = json.loads(value.pop("allowed_paths_json"))
    value["action_allowed_paths"] = json.loads(value.pop("action_allowed_paths_json") or "[]")
    value["forbidden_paths"] = json.loads(value.pop("forbidden_paths_json"))
    value["is_parallel_worker"] = (
        None if value["is_parallel_worker"] is None else bool(value["is_parallel_worker"])
    )
    value["schema"] = ADMISSION_SCHEMA
    return value


class CursorHostBridge:
    """Thin native-Cursor host integration over :class:`AdapterOrchestrator`."""

    def __init__(
        self,
        runtime: AutonomyRuntime,
        orchestrator: AdapterOrchestrator,
    ) -> None:
        self.runtime = runtime
        self.orchestrator = orchestrator
        with self.runtime.store.connect() as connection:
            _ensure_admission_schema(connection)

    # ------------------------------------------------------------------
    # producer: root authority first, then an opaque single-use token
    # ------------------------------------------------------------------

    def create_admission(
        self,
        *,
        campaign_id: str,
        agent_id: str,
        session_id: str | None = None,
        adapter_config: dict[str, Any] | None = None,
        action_id: str | None = None,
        requested_role: str | None = None,
        ttl_seconds: int | None = None,
        workspace: str | Path | None = None,
    ) -> dict[str, Any]:
        """Create a pending admission for one native Task launch.

        Root authority must already exist (a bootstrapped campaign with a
        READY action); this method requests the specific action through the
        orchestrator — obtaining the root lease and rendered agent contract —
        and returns an opaque single-use admission token to embed in the Task
        prompt. Nothing about the Task text participates in authorization.
        """
        repo_root = self.orchestrator.repository_root
        campaign_workspace = Path(workspace).resolve() if workspace is not None else repo_root
        if _cursor_deployment_readiness_required(repo_root):
            _require_cursor_deployment_ready(campaign_workspace, repo_root)
        if session_id is None:
            if adapter_config is None:
                msg = "create_admission requires session_id or adapter_config"
                raise ValueError(msg)
            registered = self.orchestrator.register(adapter_config)
            if registered["conformance"]["status"] != "PASS":
                msg = "cursor adapter config failed conformance; admission refused"
                raise ValueError(msg)
            session_id = str(registered["session_id"])
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=campaign_id,
            agent_id=agent_id,
            action_id=action_id,
            requested_role=requested_role,
            ttl_seconds=ttl_seconds,
        )
        lease = deployment["lease"]
        selected_action = str(deployment["deployment"]["action_id"])
        action = self.runtime.store.decode_action(campaign_id, selected_action)
        campaign = self.runtime.store.decode_campaign(campaign_id)
        campaign_row = self.runtime.store.get_campaign(campaign_id)
        scope = campaign.get("scope") or {}
        role = str(action["role"])
        # Writable scope is the intersection the capability gateway enforces:
        # a path must satisfy the campaign scope AND, when the action narrows
        # it, the action scope. Forbidden paths are the union of both.
        action_metadata = action.get("metadata") or {}
        allowed_paths = list(scope.get("allowed_paths") or [])
        action_allowed_paths = list(action_metadata.get("allowed_paths") or [])
        forbidden_paths = list(scope.get("forbidden_paths") or [])
        for pattern in action_metadata.get("forbidden_paths") or []:
            if pattern not in forbidden_paths:
                forbidden_paths.append(pattern)
        subject_agent_id: str | None = None
        if requires_independence(action):
            with self.runtime.store.connect() as connection:
                producers = producer_agent_ids(
                    connection,
                    campaign_id=campaign_id,
                    action_ids=independence_sources(action),
                )
            subject_agent_id = producers[0] if producers else None
        try:
            expected_subagent_type: str | None = _cursor_subagent_type(role)
        except ValueError:
            expected_subagent_type = None
        token = f"admission-{uuid.uuid4().hex}"
        now = utc_now_text()
        with self.runtime.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO cursor_host_admissions (
                    admission_token, status, session_id, campaign_id, graph_id,
                    action_id, role, agent_id, lease_id, capability_id,
                    base_sha, allowed_paths_json, forbidden_paths_json,
                    action_allowed_paths_json, subject_agent_id,
                    expected_subagent_type, created_at, expires_at
                ) VALUES (?, 'PENDING', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token,
                    session_id,
                    campaign_id,
                    campaign_row["graph_id"],
                    selected_action,
                    role,
                    agent_id,
                    lease["lease_id"],
                    lease["capability_id"],
                    lease["base_sha"],
                    json.dumps(allowed_paths),
                    json.dumps(forbidden_paths),
                    json.dumps(action_allowed_paths),
                    subject_agent_id,
                    expected_subagent_type,
                    now,
                    lease["expires_at"],
                ),
            )
        return {
            "admission_token": token,
            "session_id": session_id,
            "deployment": deployment["deployment"],
            "lease": lease,
            "required_acknowledgment": deployment["required_acknowledgment"],
            "agent_contract": deployment["agent_contract"],
            "prompt_marker": f"L9_ADMISSION_TOKEN={token}",
        }

    def bind_pre_tool_use(
        self, token: str, tool_use_id: str, *, subagent_type: str | None = None
    ) -> dict[str, Any]:
        return host_bind_pre_tool_use(
            self.runtime.store.database_path,
            token,
            tool_use_id,
            subagent_type=subagent_type,
        )

    def bind_subagent_start(self, **kwargs: Any) -> dict[str, Any]:
        return host_bind_subagent_start(self.runtime.store.database_path, **kwargs)


# ----------------------------------------------------------------------
# hook-side binders: raw SQLite against the same root runtime database,
# cheap enough for a host hook process and free of policy loading.
# ----------------------------------------------------------------------


def lease_status(database: str | Path, lease_id: str) -> str | None:
    """Terminal or live status of a root lease, or None when it does not exist.

    Cheap raw-SQLite read for hook-side callers (the result gateway re-checks
    the lease at stop time); no policy is loaded.
    """
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT status FROM leases WHERE lease_id = ?", (str(lease_id),)
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()
    return None if row is None else str(row["status"])


def _lease_active(connection: sqlite3.Connection, lease_id: str) -> str | None:
    """Return a denial reason unless the root lease is ACTIVE and unexpired."""
    row = connection.execute(
        "SELECT status, expires_at FROM leases WHERE lease_id = ?",
        (lease_id,),
    ).fetchone()
    if row is None:
        return f"root lease missing: {lease_id}"
    if row["status"] != "ACTIVE":
        return f"root lease is {row['status']}, not ACTIVE"
    if utc_now() >= parse_timestamp(row["expires_at"]):
        return "root lease expired"
    return None


def host_bind_pre_tool_use(
    database: str | Path,
    token: str,
    tool_use_id: str,
    *,
    subagent_type: str | None = None,
) -> dict[str, Any]:
    """Bind a host preToolUse(Task) ``tool_use_id`` to a pending admission.

    Denies when the token is missing, unknown, expired, already bound to a
    different tool use (single-use), when the underlying root lease is no
    longer ACTIVE, or when the Task names a managed ``subagent_type`` other
    than the one the admission was minted for. The Task text never
    contributes anything but the opaque token itself.
    """
    token = str(token or "").strip()
    tool_use_id = str(tool_use_id or "").strip()
    subagent_type = str(subagent_type or "").strip() or None
    if not token or not tool_use_id:
        return _deny("admission token and tool_use_id are required")
    connection = _connect(database)
    try:
        row = connection.execute(
            "SELECT * FROM cursor_host_admissions WHERE admission_token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return _deny("unknown admission token")
        expected_type = row["expected_subagent_type"]
        if subagent_type and expected_type and subagent_type != expected_type:
            return _deny(
                f"Task subagent_type {subagent_type!r} does not match the admitted "
                f"managed agent {expected_type!r}"
            )
        if utc_now() >= parse_timestamp(row["expires_at"]):
            connection.execute(
                "UPDATE cursor_host_admissions SET status='EXPIRED' WHERE admission_token=?",
                (token,),
            )
            connection.commit()
            return _deny("admission token expired")
        if row["status"] == "TOOL_BOUND" and row["tool_use_id"] == tool_use_id:
            return {"allowed": True, "admission": _admission_dict(row), "idempotent": True}
        if row["status"] != "PENDING":
            return _deny(f"admission token is single-use and already {row['status']}")
        lease_problem = _lease_active(connection, str(row["lease_id"]))
        if lease_problem is not None:
            return _deny(lease_problem)
        connection.execute(
            """
            UPDATE cursor_host_admissions
            SET status='TOOL_BOUND', tool_use_id=?, bound_at=?
            WHERE admission_token=? AND status='PENDING'
            """,
            (tool_use_id, utc_now_text(), token),
        )
        connection.commit()
        bound = connection.execute(
            "SELECT * FROM cursor_host_admissions WHERE admission_token = ?",
            (token,),
        ).fetchone()
        return {"allowed": True, "admission": _admission_dict(bound)}
    except sqlite3.IntegrityError:
        return _deny("tool_use_id already bound to a different admission")
    finally:
        connection.close()


def host_bind_subagent_start(
    database: str | Path,
    *,
    tool_call_id: str,
    subagent_id: str,
    parent_conversation_id: str | None = None,
    model: str | None = None,
    is_parallel_worker: bool | None = None,
    git_branch: str | None = None,
) -> dict[str, Any]:
    """Correlate a host subagentStart to the admission bound at preToolUse.

    The host ``tool_call_id`` must exactly match the ``tool_use_id`` bound at
    preToolUse; conflicting reuse (a second, different subagent for the same
    admission) is denied.
    """
    tool_call_id = str(tool_call_id or "").strip()
    subagent_id = str(subagent_id or "").strip()
    if not tool_call_id or not subagent_id:
        return _deny("tool_call_id and subagent_id are required")
    connection = _connect(database)
    try:
        row = connection.execute(
            "SELECT * FROM cursor_host_admissions WHERE tool_use_id = ?",
            (tool_call_id,),
        ).fetchone()
        if row is None:
            return _deny("no admission bound to this tool_call_id")
        if row["status"] == "STARTED":
            if row["subagent_id"] == subagent_id:
                return {"allowed": True, "admission": _admission_dict(row), "idempotent": True}
            return _deny("admission already started with a different subagent_id")
        if row["status"] != "TOOL_BOUND":
            return _deny(f"admission is {row['status']}; subagentStart cannot bind")
        lease_problem = _lease_active(connection, str(row["lease_id"]))
        if lease_problem is not None:
            return _deny(lease_problem)
        connection.execute(
            """
            UPDATE cursor_host_admissions
            SET status='STARTED', subagent_id=?, parent_conversation_id=?,
                model=?, is_parallel_worker=?, git_branch=?, started_at=?
            WHERE admission_token=? AND status='TOOL_BOUND'
            """,
            (
                subagent_id,
                parent_conversation_id,
                model,
                None if is_parallel_worker is None else int(bool(is_parallel_worker)),
                git_branch,
                utc_now_text(),
                row["admission_token"],
            ),
        )
        connection.commit()
        started = connection.execute(
            "SELECT * FROM cursor_host_admissions WHERE admission_token = ?",
            (row["admission_token"],),
        ).fetchone()
        return {"allowed": True, "admission": _admission_dict(started)}
    finally:
        connection.close()
