#!/usr/bin/env python3
"""CLI: ``python -m ops.graphiti.hydration.cli compile|close``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_compile(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.compile_session_packet import compile_and_format

    result = compile_and_format(
        project_dir=args.project_dir,
        conversation_id=args.session_id,
        agent_id=args.agent_id,
    )
    if args.format == "context":
        print(result["additional_context"])
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_close(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.close_session import close_session

    report = close_session(
        project_dir=args.project_dir,
        session_id=args.session_id,
        reason=args.reason,
        transcript_path=args.transcript_path,
        agent_id=args.agent_id,
        is_background_agent=args.background,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") != "failed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Graphiti session hydrate/close")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compile = sub.add_parser("compile", help="Compile SessionHydrationPacket")
    p_compile.add_argument("--project-dir", default=".")
    p_compile.add_argument("--session-id", default="default")
    p_compile.add_argument("--agent-id", default=None)
    p_compile.add_argument("--format", choices=["json", "context"], default="json")
    p_compile.set_defaults(func=_cmd_compile)

    p_close = sub.add_parser("close", help="Phase A/B session close")
    p_close.add_argument("--project-dir", default=".")
    p_close.add_argument("--session-id", default="default")
    p_close.add_argument("--reason", default="completed")
    p_close.add_argument("--transcript-path", default=None)
    p_close.add_argument("--agent-id", default=None)
    p_close.add_argument("--background", action="store_true")
    p_close.add_argument("--dry-run", action="store_true")
    p_close.set_defaults(func=_cmd_close)

    args = parser.parse_args(argv)
    # Ensure repo root on path when invoked as a script.
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
