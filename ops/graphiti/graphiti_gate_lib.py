#!/usr/bin/env python3
"""Graphiti write gate logic for Cursor hooks."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_state(conv_id: str) -> dict:
    path = Path.home() / ".cursor" / "graphiti-state" / f"{conv_id or 'default'}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def gates_enabled() -> bool:
    import os

    env_path = Path.home() / ".cursor" / "graphiti.env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GRAPHITI_WRITE_GATES="):
                return line.split("=", 1)[1].strip() == "1"
    return os.environ.get("GRAPHITI_WRITE_GATES", "0") == "1"


def prefetch_fresh(state: dict, ttl_minutes: int = 30) -> bool:
    ts = state.get("prefetch_ts")
    if not ts:
        return False
    try:
        then = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - then).total_seconds() / 60
        return age <= ttl_minutes
    except ValueError:
        return False


def memory_ok(state: dict, task_sig: str | None = None) -> bool:
    sig = task_sig or state.get("task_signature")
    satisfied = state.get("memory_satisfied_for") or []
    if sig and sig in satisfied:
        return True
    return prefetch_fresh(state) and bool(state.get("prefetch_hash"))


def gmp_prompt(text: str) -> bool:
    return bool(re.search(r"GMP|phase\s*[0-6]|modification lock|TODO plan", text, re.I))


def pre_tool_use(payload: str) -> dict:
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    conv = data.get("conversation_id") or data.get("conversationId") or "default"
    state = load_state(str(conv))
    if memory_ok(state):
        return {"permission": "allow"}
    prompt = json.dumps(data)
    if gmp_prompt(prompt) and "gmp:phase_lock" not in (state.get("memory_satisfied_for") or []):
        return {
            "permission": "deny",
            "user_message": "Graphiti gate: GMP requires prefetch + conflicts check (gmp:phase_lock). Run graphiti_memory_client.py inject/search first.",
        }
    return {
        "permission": "deny",
        "user_message": "Graphiti gate: Write blocked until memory prefetch satisfied. Run Graphiti search or satisfy prefetch.",
    }


def shell_gate(payload: str) -> dict:
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    command = data.get("command") or data.get("full_command") or ""
    if not re.search(r"git\s+commit|make\s+push", command):
        return {"permission": "allow"}
    conv = data.get("conversation_id") or "default"
    state = load_state(str(conv))
    if memory_ok(state):
        return {"permission": "allow"}
    return {"permission": "deny", "user_message": "Graphiti gate: commit/push blocked until memory satisfied."}


def subagent_gate(payload: str) -> dict:
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    conv = data.get("conversation_id") or data.get("parent_conversation_id") or "default"
    state = load_state(str(conv))
    if memory_ok(state):
        return {"permission": "allow"}
    return {"permission": "deny", "user_message": "Graphiti gate: subagent blocked — parent memory not satisfied."}


def main() -> int:
    mode = sys.argv[1]
    payload = sys.stdin.read()
    handlers = {
        "pre_tool_use": pre_tool_use,
        "shell": shell_gate,
        "subagent": subagent_gate,
    }
    result = handlers[mode](payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
