#!/usr/bin/env python3
"""
Cursor-facing CLI for Agent UI Control.

Primary: shell (sqlcmd/bcp/echo)
Fallback: sql-studio GUI typing into SSMS / Azure Data Studio
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

_PACK_DIR = Path(__file__).resolve().parent
_TOOLS_DIR = _PACK_DIR.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from l9_agent_ui_control.task_queue import enqueue_task, poll_for_result


def cmd_shell(args: argparse.Namespace) -> int:
    # Always enqueue argv + shell=False in the runner (CWE-78).
    # --bash wraps as ["/bin/bash", "-c", cmd] for pipes/operators.
    if args.bash:
        argv = ["/bin/bash", "-c", args.cmd]
    else:
        argv = shlex.split(args.cmd, posix=True)
    task = {
        "type": "shell",
        "cmd": args.cmd,
        "argv": argv,
        "timeout": args.timeout,
    }
    if args.cwd:
        task["cwd"] = args.cwd
    task_id = enqueue_task(task)
    print(f"enqueued {task_id}", file=sys.stderr)
    if args.no_wait:
        print(json.dumps({"task_id": task_id, "status": "pending"}))
        return 0
    payload = poll_for_result(task_id, timeout_seconds=args.wait)
    if not payload:
        print(json.dumps({"task_id": task_id, "error": "timeout waiting for result"}))
        return 2
    print(json.dumps(payload, indent=2))
    result = payload.get("result") or {}
    return 0 if result.get("status") == "done" else 1


def cmd_sql_studio(args: argparse.Namespace) -> int:
    sql = args.sql
    if args.file:
        sql = Path(args.file).read_text()
    if not sql:
        print("error: provide --sql or --file", file=sys.stderr)
        return 2
    task = {"type": "sql_studio", "sql": sql, "timeout": args.timeout}
    task_id = enqueue_task(task)
    print(f"enqueued {task_id}", file=sys.stderr)
    if args.no_wait:
        print(json.dumps({"task_id": task_id, "status": "pending"}))
        return 0
    payload = poll_for_result(task_id, timeout_seconds=args.wait)
    if not payload:
        print(json.dumps({"task_id": task_id, "error": "timeout waiting for result"}))
        return 2
    print(json.dumps(payload, indent=2))
    result = payload.get("result") or {}
    return 0 if result.get("status") == "done" else 1


def cmd_status(args: argparse.Namespace) -> int:
    completed = Path.home() / ".l9" / "mac_tasks" / "completed" / f"{args.task_id}.json"
    pending = Path.home() / ".l9" / "mac_tasks" / "pending" / f"{args.task_id}.json"
    if completed.exists():
        print(completed.read_text())
        return 0
    if pending.exists():
        print(json.dumps({"task_id": args.task_id, "status": "pending"}))
        return 0
    print(json.dumps({"task_id": args.task_id, "status": "unknown"}))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent UI Control local console")
    sub = parser.add_subparsers(dest="command", required=True)

    p_shell = sub.add_parser("shell", help="Enqueue a shell command (primary path)")
    p_shell.add_argument("--cmd", required=True, help="Command string (tokenized via shlex)")
    p_shell.add_argument(
        "--bash",
        action="store_true",
        help='Wrap as argv ["/bin/bash","-c",cmd] for pipes/operators',
    )
    p_shell.add_argument("--cwd", default=None)
    p_shell.add_argument("--timeout", type=float, default=120.0)
    p_shell.add_argument("--wait", type=int, default=300, help="Seconds to wait for result")
    p_shell.add_argument("--no-wait", action="store_true")
    p_shell.set_defaults(func=cmd_shell)

    p_sql = sub.add_parser("sql-studio", help="GUI fallback: type SQL into SQL client")
    p_sql.add_argument("--sql", default=None)
    p_sql.add_argument("--file", default=None)
    p_sql.add_argument("--timeout", type=float, default=120.0)
    p_sql.add_argument("--wait", type=int, default=300)
    p_sql.add_argument("--no-wait", action="store_true")
    p_sql.set_defaults(func=cmd_sql_studio)

    p_status = sub.add_parser("status", help="Poll completed/pending status")
    p_status.add_argument("--task-id", required=True)
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
