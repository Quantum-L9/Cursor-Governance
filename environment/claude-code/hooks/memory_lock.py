#!/usr/bin/env python3
"""Acquire / inspect conflict-checked memory phase-locks.

`acquire` runs memory.conflicts then memory.phase_lock for a namespace and
writes a local lock artifact the PreToolUse gate re-verifies against the server.
The session id is read from the current SessionStart receipt, so a lock cannot
be acquired before memory was prefetched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))

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
    import memory_client as mc
    from errors import MemoryWriteDenied

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
    ttl = int(contract.get("state", {}).get("lock_ttl_seconds", 3600))

    conflict = mc.conflicts(namespace)
    overlaps = conflict.get("conflicts") or conflict.get("overlaps") or []
    if overlaps and not args.force:
        print(json.dumps({"namespace": namespace, "conflicts": overlaps}, indent=2))
        print("conflicts present; resolve or re-run with --force", file=sys.stderr)
        return 4

    try:
        granted = mc.phase_lock(namespace, signature, ttl_seconds=ttl)
    except MemoryWriteDenied as exc:
        print(f"memory-lock: {exc}; not writing a lock artifact", file=sys.stderr)
        return 6
    if not granted.get("granted", False):
        print(
            f"server did not grant the phase-lock for {namespace!r}; not writing a lock artifact",
            file=sys.stderr,
        )
        return 5
    st.write_lock(contract, namespace, session_id, signature)
    print(
        json.dumps(
            {
                "acquired": True,
                "namespace": namespace,
                "task": args.task,
                "session_id": session_id,
                "server_granted": bool(granted.get("granted", False)),
                "lock_id": granted.get("lock_id"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    contract = st.load_contract()
    for namespace in st.resolve_namespaces(contract):
        lock = st.read_lock(contract, namespace)
        print(f"{namespace}: {'held' if lock else 'none'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="memory_lock")
    sub = parser.add_subparsers(dest="command", required=True)
    acq = sub.add_parser("acquire", help="conflict-check and acquire a phase-lock")
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
