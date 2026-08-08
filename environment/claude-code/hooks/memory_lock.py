#!/usr/bin/env python3
"""Acquire / inspect phase-locks via Cursor Graphiti (front door only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


def _current_session_id(contract: dict) -> str | None:
    root = st.state_root(contract) / "receipts"
    if not root.is_dir():
        return None
    newest, best = None, -1.0
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if (
            st.fresh_receipt(contract, str(data.get("session_id", "")))
            and float(data.get("created_at", 0)) > best
        ):
            best, newest = float(data.get("created_at", 0)), str(data.get("session_id"))
    return newest


def command_acquire(args: argparse.Namespace) -> int:
    contract = st.load_contract()
    session_id = _current_session_id(contract)
    if not session_id:
        print(
            "no fresh SessionStart receipt; memory prefetch must run before locking",
            file=sys.stderr,
        )
        return 3
    namespace = args.namespace
    signature = st.task_signature(namespace)
    workspace = st.workspace_root()

    # Optional advisory conflicts print (Graphiti phase-lock also runs conflicts).
    try:
        conflict = gb.conflicts(workspace=workspace, session_id=session_id)
        overlaps = conflict.get("conflicts") or []
        if overlaps:
            print(json.dumps({"namespace": namespace, "conflicts": overlaps}, indent=2))
            if not args.force:
                print(
                    "conflicts reported by Graphiti; re-run with --force to acquire anyway",
                    file=sys.stderr,
                )
                return 4
    except Exception as exc:  # advisory only
        print(f"memory-lock: conflicts check skipped ({exc})", file=sys.stderr)

    granted = gb.phase_lock(workspace=workspace, session_id=session_id)
    if str(granted.get("phase_lock", "")).lower() not in {"granted", "ok", "active"}:
        print(
            f"Graphiti did not grant phase-lock for {namespace!r}; not writing a lock artifact",
            file=sys.stderr,
        )
        return 5

    st.write_lock(contract, namespace, session_id, signature)
    lock_path = st.state_root(contract) / "locks" / f"{namespace.replace('/', '_')}.json"
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        data["transport"] = "cursor-graphiti-phase-lock"
        data["granted"] = True
        lock_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass

    print(
        json.dumps(
            {
                "acquired": True,
                "namespace": namespace,
                "task": args.task,
                "session_id": session_id,
                "transport": "cursor-graphiti-phase-lock",
                "server_granted": True,
                "graphiti": granted,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_status(_args: argparse.Namespace) -> int:
    contract = st.load_contract()
    for namespace in st.resolve_namespaces(contract):
        lock = st.read_lock(contract, namespace)
        print(f"{namespace}: {'held' if lock else 'none'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="memory_lock")
    sub = parser.add_subparsers(dest="command", required=True)
    acq = sub.add_parser("acquire", help="conflict-check and acquire a Graphiti phase-lock")
    acq.add_argument("--namespace", required=True)
    acq.add_argument("--task", required=True)
    acq.add_argument("--force", action="store_true", help="proceed despite reported conflicts")
    acq.set_defaults(func=command_acquire)
    stt = sub.add_parser("status", help="show local lock state")
    stt.set_defaults(func=command_status)
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
