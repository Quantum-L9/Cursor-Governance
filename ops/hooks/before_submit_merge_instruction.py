#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt adapter → ops/autonomy/operator_merge_instruction.py (§2.1).

Records explicit operator merge instructions from the prompt Cursor is about to
send (CANONICAL_LAW §6.2.13, operator-prompt channel). Cursor fires this hook
on the user's send action, with ``conversation_id`` as the session identity and
``workspace_roots`` as the repository hint.

Contract: stdout is always ``{"continue": true}``; prompt submission is never
blocked; no network; no LLM. The receipt file is the same one the Claude Code
hook writes, so ``authorize_merge.py --operator-instruction`` reads one store
on either host.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

MODULE_REL = Path("ops/autonomy/operator_merge_instruction.py")


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        roots.append(Path(configured).expanduser())
    roots.append(Path.home() / ".cursor-governance")
    roots.extend(Path(__file__).resolve().parents)
    return roots


def load_recorder():
    for root in _candidate_roots():
        path = root / MODULE_REL
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("l9_operator_merge_instruction", path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    raise RuntimeError("ops/autonomy/operator_merge_instruction.py not found (L9_GOVERNANCE_DIR?)")


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        load_recorder().record_from_payload(payload, "cursor")
    except Exception as exc:  # noqa: BLE001 - fail-open: never block a prompt
        print(f"WARN: Cursor operator merge instruction recorder degraded: {exc}", file=sys.stderr)
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
