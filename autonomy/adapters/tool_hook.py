from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime

TOOL_CAPABILITY_MAP: dict[str, str] = {
    "Read": "repository.read",
    "read_file": "repository.read",
    "Grep": "repository.search",
    "rg": "repository.search",
    "Glob": "repository.search",
    "Edit": "repository.write_scoped",
    "Write": "repository.write_scoped",
    "StrReplace": "repository.write_scoped",
    "Delete": "repository.write_scoped",
    "Shell": "test.run",
    "Bash": "test.run",
    "run_terminal_cmd": "test.run",
    "git_diff": "git.diff",
    "git_commit": "git.commit_local",
    "git_push": "git.push_non_force_declared_branch",
    "gh_pr_view": "pr.inspect",
    "gh_pr_merge": "pr.merge",
    "WebFetch": "repository.read",
    "WebSearch": "repository.search",
}


def infer_capability(
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
) -> str:
    arguments = dict(arguments or {})
    explicit = arguments.get("capability")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    mapped = TOOL_CAPABILITY_MAP.get(tool_name)
    if mapped:
        return mapped
    lowered = tool_name.lower()
    if "merge" in lowered:
        return "pr.merge"
    if "commit" in lowered:
        return "git.commit_local"
    if "push" in lowered:
        return "git.push_non_force_declared_branch"
    if "write" in lowered or "edit" in lowered:
        return "repository.write_scoped"
    if "search" in lowered or "grep" in lowered:
        return "repository.search"
    return "repository.read"


def infer_resource(
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
) -> str | None:
    arguments = dict(arguments or {})
    for key in (
        "resource",
        "path",
        "file_path",
        "target_file",
        "filename",
        "cwd",
    ):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _require_env_aliases(*groups: tuple[str, ...]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for group in groups:
        value = _env_first(*group)
        if value is None:
            missing.append(" or ".join(group))
            continue
        resolved[group[0]] = value
    if missing:
        raise PolicyViolation(
            "ADAPTER_SESSION_INCOMPLETE: missing required environment "
            f"variables: {', '.join(missing)}"
        )
    return resolved


#: Tools whose argument is a shell command. A shell tool only reaches
#: ``test.run`` when a caller that validated the command against the canonical
#: Program Execution validation grammar says so explicitly; inferring it here
#: would let any shell string inherit a validation command's authority.
SHELL_TOOL_NAMES = frozenset({"Bash", "Shell", "run_terminal_cmd"})


def pre_tool_use(
    *,
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    orchestrator: AdapterOrchestrator | None = None,
    require_allowed: bool = True,
    session_id: str | None = None,
    lease_id: str | None = None,
    agent_id: str | None = None,
    capability: str | None = None,
    resource: str | None = None,
) -> dict[str, Any]:
    """Authorize one tool call through the root capability gateway.

    A Program Execution worker passes its identity and its already-validated
    capability/resource explicitly, because those were resolved against the live
    Program parent. Every other caller keeps the environment fallback.
    """
    if session_id and lease_id and agent_id:
        resolved_session, resolved_lease, resolved_agent = session_id, lease_id, agent_id
    else:
        env = _require_env_aliases(
            ("L9_ADAPTER_SESSION_ID",),
            ("L9_LEASE_ID", "L9_AUTONOMY_LEASE_ID"),
            ("L9_AGENT_ID", "L9_AUTONOMY_AGENT_ID"),
        )
        resolved_session = session_id or env["L9_ADAPTER_SESSION_ID"]
        resolved_lease = lease_id or env["L9_LEASE_ID"]
        resolved_agent = agent_id or env["L9_AGENT_ID"]
    if capability is None:
        capability = infer_capability(tool_name, arguments)
        if tool_name in SHELL_TOOL_NAMES and capability == "test.run":
            raise PolicyViolation(
                "SHELL_CAPABILITY_NOT_VALIDATED: a shell tool reaches test.run only "
                "through a caller that validated the command grammar"
            )
    if resource is None:
        resource = infer_resource(tool_name, arguments)
    orch = orchestrator or _default_orchestrator()
    decision = orch.authorize_tool(
        session_id=resolved_session,
        lease_id=resolved_lease,
        agent_id=resolved_agent,
        capability=capability,
        resource=resource,
        metadata={"tool_name": tool_name},
    )
    if require_allowed and not decision.get("allowed"):
        raise PolicyViolation(f"{decision.get('code')}: {decision.get('message')}")
    return decision


def post_tool_use(
    *,
    tool_name: str,
    allowed: bool,
    result: Mapping[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "allowed": allowed,
        "session_id": os.environ.get("L9_ADAPTER_SESSION_ID"),
        "lease_id": os.environ.get("L9_LEASE_ID") or os.environ.get("L9_AUTONOMY_LEASE_ID"),
        "agent_id": os.environ.get("L9_AGENT_ID") or os.environ.get("L9_AUTONOMY_AGENT_ID"),
        "result": dict(result or {}),
        "error": error,
    }


def _default_orchestrator() -> AdapterOrchestrator:
    root = os.environ.get("L9_AUTONOMY_ROOT", ".")
    database = os.environ.get("L9_AUTONOMY_DATABASE")
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=database,
    )
    return AdapterOrchestrator(runtime, repository_root=root)


def main(argv: list[str] | None = None) -> int:
    raise SystemExit(
        "tool_hook file-path CLI is disabled; "
        "call pre_tool_use()/post_tool_use() with an in-memory orchestrator"
    )


if __name__ == "__main__":
    raise SystemExit(main())
