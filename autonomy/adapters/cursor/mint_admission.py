"""Mint one native-Cursor Task admission token.

The only producer is :meth:`CursorHostBridge.create_admission`. This module
does not create a second store or derive authority from Task prose.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from autonomy.adapters.cursor.host_bridge import CursorHostBridge
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.policy_loader import load_example, load_policy
from autonomy.runtime.engine import AutonomyRuntime


def mint_admission(
    *,
    campaign_id: str,
    agent_id: str,
    repository_root: str | Path,
    database_path: str | Path | None = None,
    session_id: str | None = None,
    action_id: str | None = None,
    requested_role: str | None = None,
    ttl_seconds: int | None = None,
    adapter_config: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Return the ``create_admission`` payload, including ``prompt_marker``."""
    runtime = AutonomyRuntime.from_repository(
        repository_root=repository_root,
        database_path=database_path,
    )
    orchestrator = AdapterOrchestrator(
        runtime,
        repository_root=repository_root,
        requirements=load_policy("adapter-requirements"),
    )
    bridge = CursorHostBridge(runtime, orchestrator)
    config = adapter_config
    if session_id is None and config is None:
        config = load_example("adapters/cursor.json")
    return bridge.create_admission(
        campaign_id=campaign_id,
        agent_id=agent_id,
        session_id=session_id,
        adapter_config=config,
        action_id=action_id,
        requested_role=requested_role,
        ttl_seconds=ttl_seconds,
        workspace=workspace,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mint one Cursor Task admission via create_admission.",
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument(
        "--database",
        default=os.environ.get("L9_AUTONOMY_RUNTIME_DB"),
        help="Root Autonomy SQLite path (default: L9_AUTONOMY_RUNTIME_DB).",
    )
    parser.add_argument("--session-id")
    parser.add_argument("--action-id")
    parser.add_argument("--requested-role")
    parser.add_argument("--ttl-seconds", type=int)
    parser.add_argument(
        "--workspace",
        default=None,
        help="Consumer workspace for the deployment receipt (default: --root).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        admission = mint_admission(
            campaign_id=args.campaign_id,
            agent_id=args.agent_id,
            repository_root=args.root,
            database_path=args.database,
            session_id=args.session_id,
            action_id=args.action_id,
            requested_role=args.requested_role,
            ttl_seconds=args.ttl_seconds,
            workspace=args.workspace,
        )
    except Exception as exc:  # noqa: BLE001 — CLI fail-closed
        json.dump({"ok": False, "error": str(exc)}, sys.stdout)
        print()
        return 2
    json.dump(
        {
            "ok": True,
            "admission_token": admission["admission_token"],
            "prompt_marker": admission["prompt_marker"],
        },
        sys.stdout,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
