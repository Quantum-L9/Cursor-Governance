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


def _public_close_report(report: dict) -> dict:
    """Stdout-safe close report — ints/bools only (breaks secret taint to logs)."""
    enqueue_ok = report.get("enqueue_ok")
    status = report.get("status")
    allowed = {
        "closed",
        "idempotent_skip",
        "skipped",
        "failed",
        "closed_enqueue_failed",
    }
    return {
        "status": status if status in allowed else "other",
        "phase_a": bool(report.get("phase_a") is True),
        "phase_b": bool(report.get("phase_b") is True),
        "enqueue_ok": True if enqueue_ok is True else (False if enqueue_ok is False else None),
        "enqueue_error_present": bool(report.get("enqueue_error")),
        "write_count": len(report.get("writes") or []),
        "warning_count": len(report.get("warnings") or []),
    }


def _cmd_open(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.session_latches import resolve_session_id, write_open_latch

    sid = resolve_session_id(explicit=args.session_id)
    result = write_open_latch(Path(args.project_dir), sid, background=args.background)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_record_skip(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.session_latches import record_skip_receipt, resolve_session_id

    sid = resolve_session_id(explicit=args.session_id)
    payload = record_skip_receipt(Path(args.project_dir), sid, args.status)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_fallback_write(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.pickup_write import fallback_pickup_write

    report = fallback_pickup_write(
        project_dir=args.project_dir,
        session_id=args.session_id,
        reason=args.reason,
        transcript_path=args.transcript_path,
        agent_id=args.agent_id,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {"status": report.get("status"), "write_count": report.get("write_count")},
            indent=2,
        )
    )
    return 0 if int(report.get("write_count") or 0) > 0 else 1


def _cmd_repair_write(args: argparse.Namespace) -> int:
    from ops.graphiti.hydration.pickup_write import repair_pickup_write

    report = repair_pickup_write(
        project_dir=args.project_dir,
        session_id=args.session_id,
        objective=args.objective,
        next_action=args.next,
        files=args.files,
        blocker=args.blocker,
        agent_id=args.agent_id,
        supersede=args.supersede,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    if report.get("status") == "skipped_already_closed":
        return 0
    return 0 if report.get("written") else 1


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
    print(json.dumps(_public_close_report(report), indent=2, ensure_ascii=False))
    if report.get("status") == "failed":
        return 1
    if report.get("enqueue_ok") is False:
        return 2
    return 0


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

    p_open = sub.add_parser("open", help="Write session open latch (ADR-0028)")
    p_open.add_argument("--project-dir", default=".")
    p_open.add_argument("--session-id", default="default")
    p_open.add_argument("--background", action="store_true")
    p_open.set_defaults(func=_cmd_open)

    p_skip = sub.add_parser("record-skip", help="Write skip/fail close receipt")
    p_skip.add_argument("--project-dir", default=".")
    p_skip.add_argument("--session-id", default="default")
    p_skip.add_argument(
        "--status",
        required=True,
        choices=[
            "close_failed",
            "skipped_no_project",
            "skipped_disabled",
            "skipped_cli_missing",
        ],
    )
    p_skip.set_defaults(func=_cmd_record_skip)

    p_fb = sub.add_parser("fallback-write", help="One Graphiti PICKUP write after empty close")
    p_fb.add_argument("--project-dir", default=".")
    p_fb.add_argument("--session-id", default="default")
    p_fb.add_argument("--reason", default="close_fallback")
    p_fb.add_argument("--transcript-path", default=None)
    p_fb.add_argument("--agent-id", default=None)
    p_fb.add_argument("--dry-run", action="store_true")
    p_fb.set_defaults(func=_cmd_fallback_write)

    p_rp = sub.add_parser("repair-write", help="/end-session primary Graphiti PICKUP write")
    p_rp.add_argument("--project-dir", default=".")
    p_rp.add_argument("--session-id", default="default")
    p_rp.add_argument("--objective", required=True)
    p_rp.add_argument("--next", required=True)
    p_rp.add_argument("--files", default="")
    p_rp.add_argument("--blocker", default="")
    p_rp.add_argument("--agent-id", default=None)
    p_rp.add_argument("--supersede", action="store_true")
    p_rp.add_argument("--dry-run", action="store_true")
    p_rp.set_defaults(func=_cmd_repair_write)

    args = parser.parse_args(argv)
    # Ensure repo root on path when invoked as a script.
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
