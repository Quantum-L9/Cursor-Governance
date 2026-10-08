#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from paths import safe_cli_path


def _todo_block(todo: dict) -> list[str]:
    files = todo.get("files") or []
    file_field = files[0] if files else f"BLOCKED: {todo.get('blocker') or 'ungrounded'}"
    return [
        f"[TODO {todo.get('id')}]",
        "Phase: 2",
        f"File: {file_field}",
        f"Operation: {todo.get('operation') or 'Replace'}",
        f"Anchor: {todo.get('anchor') or 'UNSPECIFIED'}",
        f"Description: {todo.get('task')}",
        f"Dependencies: {', '.join(todo.get('dependencies') or []) or 'none'}",
        "",
    ]


def emit(plan: dict) -> str:
    lines = ["# GMP Phase 0 — TODO PLAN LOCK (from l9-plan)", ""]
    for todo in plan.get("todos") or []:
        lines.extend(_todo_block(todo))
    handoff = plan.get("gmp_handoff") or {}
    lines += [
        "MODIFICATION LOCK",
        f"may-modify: {', '.join(handoff.get('may_modify') or [])}",
        f"must-not-modify: {', '.join(handoff.get('must_not_modify') or [])}",
        f"preserved_contracts: {', '.join(handoff.get('preserved_contracts') or [])}",
        f"validation_commands: {', '.join(handoff.get('validation_commands') or [])}",
        "",
        "Phase 0 complete. TODO PLAN locked from PLAN_DOCUMENT.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: emit_gmp_phase0.py <plan.json>", file=sys.stderr)
        return 2
    plan = json.loads(safe_cli_path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(emit(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
