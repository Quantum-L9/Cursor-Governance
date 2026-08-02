from __future__ import annotations

import argparse
import json
import os
from typing import Any, Mapping

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime


def send_heartbeat(
    *,
    orchestrator: AdapterOrchestrator | None = None,
    session_id: str | None = None,
    lease_id: str | None = None,
    agent_id: str | None = None,
    base_sha: str | None = None,
    status: str = "running",
    progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_session = session_id or os.environ.get("L9_ADAPTER_SESSION_ID")
    resolved_lease = (
        lease_id
        or os.environ.get("L9_LEASE_ID")
        or os.environ.get("L9_AUTONOMY_LEASE_ID")
    )
    resolved_agent = (
        agent_id
        or os.environ.get("L9_AGENT_ID")
        or os.environ.get("L9_AUTONOMY_AGENT_ID")
    )
    resolved_base = (
        base_sha
        or os.environ.get("L9_BASE_SHA")
        or os.environ.get("L9_AUTONOMY_BASE_SHA")
    )
    if not resolved_session or not resolved_lease or not resolved_agent:
        raise PolicyViolation(
            "ADAPTER_HEARTBEAT_INCOMPLETE: L9_ADAPTER_SESSION_ID, "
            "L9_LEASE_ID, and L9_AGENT_ID are required"
        )
    if not resolved_base:
        raise PolicyViolation(
            "ADAPTER_HEARTBEAT_INCOMPLETE: L9_BASE_SHA is required"
        )
    orch = orchestrator or _default_orchestrator()
    return orch.heartbeat(
        session_id=resolved_session,
        lease_id=resolved_lease,
        agent_id=resolved_agent,
        base_sha=resolved_base,
        status=status,
        progress=progress,
    )


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
        description="Send an autonomy lease heartbeat via AdapterOrchestrator."
    )
    parser.add_argument("--session-id")
    parser.add_argument("--lease-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--base-sha")
    parser.add_argument("--status", default="running")
    parser.add_argument("--progress-json", default="{}")
    parser.add_argument("--root", default=os.environ.get("L9_AUTONOMY_ROOT", "."))
    parser.add_argument("--database")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(runtime, repository_root=args.root)
    progress = json.loads(args.progress_json)
    result = send_heartbeat(
        orchestrator=orchestrator,
        session_id=args.session_id,
        lease_id=args.lease_id,
        agent_id=args.agent_id,
        base_sha=args.base_sha,
        status=args.status,
        progress=progress,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
