from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

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


def _require_env(*names: str) -> dict[str, str]:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise PolicyViolation(
            "ADAPTER_SESSION_INCOMPLETE: missing required environment "
            f"variables: {', '.join(missing)}"
        )
    return {name: os.environ[name] for name in names}


def pre_tool_use(
    *,
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    orchestrator: AdapterOrchestrator | None = None,
    require_allowed: bool = True,
) -> dict[str, Any]:
    env = _require_env(
        "L9_ADAPTER_SESSION_ID",
        "L9_LEASE_ID",
        "L9_AGENT_ID",
    )
    # Accept legacy env aliases used by older launchers.
    lease_id = env["L9_LEASE_ID"] or os.environ.get("L9_AUTONOMY_LEASE_ID", "")
    agent_id = env["L9_AGENT_ID"] or os.environ.get("L9_AUTONOMY_AGENT_ID", "")
    session_id = env["L9_ADAPTER_SESSION_ID"]
    if not lease_id:
        lease_id = os.environ.get("L9_AUTONOMY_LEASE_ID", "")
    if not agent_id:
        agent_id = os.environ.get("L9_AUTONOMY_AGENT_ID", "")
    if not lease_id or not agent_id:
        raise PolicyViolation(
            "ADAPTER_SESSION_INCOMPLETE: L9_LEASE_ID and L9_AGENT_ID "
            "are required"
        )
    capability = infer_capability(tool_name, arguments)
    resource = infer_resource(tool_name, arguments)
    orch = orchestrator or _default_orchestrator()
    decision = orch.authorize_tool(
        session_id=session_id,
        lease_id=lease_id,
        agent_id=agent_id,
        capability=capability,
        resource=resource,
        metadata={"tool_name": tool_name},
    )
    if require_allowed and not decision.get("allowed"):
        raise PolicyViolation(
            f"{decision.get('code')}: {decision.get('message')}"
        )
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
        "lease_id": os.environ.get("L9_LEASE_ID")
        or os.environ.get("L9_AUTONOMY_LEASE_ID"),
        "agent_id": os.environ.get("L9_AGENT_ID")
        or os.environ.get("L9_AUTONOMY_AGENT_ID"),
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed autonomy tool mediation hook."
    )
    parser.add_argument("phase", choices=("pre", "post"))
    parser.add_argument("--tool-name", required=True)
    parser.add_argument("--arguments-json", default="{}")
    parser.add_argument("--allowed", action="store_true")
    parser.add_argument("--error")
    parser.add_argument("--root", default=os.environ.get("L9_AUTONOMY_ROOT", "."))
    parser.add_argument("--database")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    arguments = json.loads(args.arguments_json)
    if args.phase == "pre":
        runtime = AutonomyRuntime.from_repository(
            repository_root=args.root,
            database_path=args.database,
        )
        orchestrator = AdapterOrchestrator(
            runtime,
            repository_root=Path(args.root),
        )
        try:
            decision = pre_tool_use(
                tool_name=args.tool_name,
                arguments=arguments,
                orchestrator=orchestrator,
                require_allowed=True,
            )
        except PolicyViolation as exc:
            print(json.dumps({"allowed": False, "error": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(decision, sort_keys=True))
        return 0 if decision.get("allowed") else 1
    report = post_tool_use(
        tool_name=args.tool_name,
        allowed=bool(args.allowed),
        error=args.error,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
