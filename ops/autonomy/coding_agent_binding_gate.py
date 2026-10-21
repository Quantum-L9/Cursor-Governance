#!/usr/bin/env python3
"""Coding-agent canonical-binding gate (PreToolUse, file mutations).

The ``l9-coding-agent`` skill requires a verified canonical invariant binding
before its first mutation and lets only an explicit user instruction, recorded
verbatim, carry a run past an Unknown (``integrations/L9_RUNTIME_BINDING.yaml``
``unknown_handling``). This gate makes that law mechanical for the file tools
while a coding-agent run is active, so the governance binding can say
``blocks_mutation: true`` truthfully.

State contract (written by the skill at intake, removed at convergence):

``<workspace>/.l9/coding-agent/run.json``  ``l9.coding-agent-run/v1``
    {"schema", "started_at", "binding_record": "binding.json",
     "reauthorized_unknown": null | {"instruction": "<verbatim user text>", "recorded_at"}}
``<workspace>/.l9/coding-agent/binding.json``
    the record ``skills/l9-coding-agent/scripts/verify_canonical_binding.py`` printed.

Decision:

* no ``run.json`` above the mutated path: no coding-agent run is active; allow.
* writes inside ``.l9/coding-agent/`` itself: allow (the run must be able to
  record its state).
* a recorded reauthorization with a non-empty instruction: allow.
* a binding record whose status is BOUND or CURRENT from the coding-agent
  verifier: allow.
* anything else, including a malformed run or record: deny, naming the fix.

Operator breakglass (human/ops only, a reason, never a bare flag):
``L9_CODING_BINDING_AUTHORIZED=<reason>``.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUN_DIR = Path(".l9") / "coding-agent"
RUN_FILE = "run.json"
RECORD_FILE = "binding.json"
RUN_SCHEMA = "l9.coding-agent-run/v1"
VERIFIER_PREFIX = "l9-coding-agent/"
BOUND_STATUSES = frozenset({"BOUND", "CURRENT"})
MUTATING_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
BREAKGLASS_ENV = "L9_CODING_BINDING_AUTHORIZED"
SKILL_LAW = (
    "skills/l9-coding-agent: a verified canonical invariant binding precedes mutation "
    "(RUNBOOK step 4; L9_RUNTIME_BINDING unknown_handling)"
)


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    run: str | None = None


def mutated_path(tool_name: str, tool_input: Any) -> Path | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value)
    return None


def locate_run(start: Path) -> Path | None:
    """The nearest ``.l9/coding-agent/run.json`` at or above *start*."""
    current = start.resolve()
    seen: set[Path] = set()
    while current not in seen:
        seen.add(current)
        candidate = current / RUN_DIR / RUN_FILE
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate(
    tool_name: str,
    tool_input: Any,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> Decision:
    env = os.environ if env is None else env
    if tool_name not in MUTATING_TOOLS:
        return Decision(True, "not a file mutation")
    breakglass = str(env.get(BREAKGLASS_ENV, "")).strip()
    if breakglass and breakglass.lower() not in {"1", "true", "yes"}:
        return Decision(True, f"operator breakglass: {breakglass}")

    target = mutated_path(tool_name, tool_input)
    anchor = target if target is not None else cwd
    if not anchor.is_absolute():
        anchor = cwd / anchor
    run_path = locate_run(anchor.parent if target is not None else anchor)
    if run_path is None:
        return Decision(True, "no active coding-agent run")
    run_dir = run_path.parent
    if target is not None:
        try:
            anchor.resolve().relative_to(run_dir.resolve())
            return Decision(True, "coding-agent run state", run=str(run_path))
        except ValueError:
            pass

    try:
        run = _load(run_path)
    except (OSError, ValueError) as exc:
        return Decision(
            False,
            f"{run_path} is unreadable ({exc}); a coding-agent run is active but its state is "
            f"Unknown. {SKILL_LAW}. Rewrite it from intake or remove it if no run is active.",
            run=str(run_path),
        )
    if not isinstance(run, dict) or run.get("schema") != RUN_SCHEMA:
        return Decision(
            False,
            f"{run_path} is not {RUN_SCHEMA}; the active coding-agent run has no valid state. "
            f"{SKILL_LAW}. Rewrite it from intake or remove it if no run is active.",
            run=str(run_path),
        )
    reauth = run.get("reauthorized_unknown")
    if isinstance(reauth, dict) and str(reauth.get("instruction") or "").strip():
        return Decision(
            True,
            "the user explicitly reauthorized this run with the binding Unknown; the receipt "
            "must carry that instruction verbatim",
            run=str(run_path),
        )

    record_rel = run.get("binding_record") or RECORD_FILE
    record_path = (run_dir / str(record_rel)).resolve()
    try:
        record = _load(record_path)
    except (OSError, ValueError) as exc:
        return Decision(
            False,
            f"no verified canonical binding for the active coding-agent run ({record_path}: "
            f"{exc}). {SKILL_LAW}. Run scripts/verify_canonical_binding.py --bundle "
            "<bundle> --authority-root <.github> --expect-revision <pin>, save its record as "
            f"{record_path}, or record the user's explicit reauthorization in {run_path} "
            '("reauthorized_unknown": {"instruction": "<verbatim>"}).',
            run=str(run_path),
        )
    status = record.get("status") if isinstance(record, dict) else None
    verifier = str(record.get("verifier", "")) if isinstance(record, dict) else ""
    if status in BOUND_STATUSES and verifier.startswith(VERIFIER_PREFIX):
        return Decision(True, f"canonical binding {status}", run=str(run_path))
    reason = record.get("reason") if isinstance(record, dict) else None
    return Decision(
        False,
        f"the active coding-agent run's canonical binding is {status or 'absent'}"
        f"{f' ({reason})' if reason else ''}, not BOUND or CURRENT from {VERIFIER_PREFIX}*. "
        f"{SKILL_LAW}. Re-bind, or record the user's explicit reauthorization in {run_path}.",
        run=str(run_path),
    )


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"coding-agent binding gate: {reason}",
                }
            }
        )
    )


def main(stdin: Any = None) -> int:
    try:
        event = json.load(stdin or sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0
    cwd_raw = str(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    decision = evaluate(
        str(event.get("tool_name", "")),
        event.get("tool_input") or {},
        cwd=Path(cwd_raw),
    )
    if not decision.allow:
        _deny(decision.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
