#!/usr/bin/env bash
# Materialize one task's declared deliverables in its own worktree from the
# reference implementation, so the task produces the diff its contract declares.
set -euo pipefail

TASK="${1:?usage: port-task-deliverable.sh TASK-00N [REF]}"
REF="${2:-feat/pe-kernel-bind}"
WS="$HOME/.l9/programs/pe-kernel-bind"
TARGET="$HOME/.l9/program-worktrees/pe-kernel-bind"
WORKTREE="$WS/worktrees/$TASK"
CONTRACT="$WS/contracts/rendered/$TASK.json"

[ -d "$WORKTREE" ] || { echo "no worktree for $TASK"; exit 2; }
[ -f "$CONTRACT" ] || { echo "no rendered contract for $TASK"; exit 2; }

python3 - "$CONTRACT" "$WORKTREE" "$TARGET" "$REF" "$TASK" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

contract_path, worktree, target, ref, task_id = (
    Path(sys.argv[1]),
    Path(sys.argv[2]),
    sys.argv[3],
    sys.argv[4],
    sys.argv[5],
)
contract = json.loads(contract_path.read_text(encoding="utf-8"))

# Tasks that share a file must not deliver each other's change, or the later one
# has an empty diff and fails the scope gate. Hold back the functions that belong
# to a task further up the stack.
CONTROLLER = (
    "environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py"
)
HOLD_BACK = {"TASK-005": {CONTROLLER: ("complete_task", "evaluate_gate")}}


def function_span(text: str, name: str) -> tuple[int, int] | None:
    match = re.search(rf"^def {re.escape(name)}\(", text, re.MULTILINE)
    if match is None:
        return None
    following = re.search(r"^(?:def |@)", text[match.end() :], re.MULTILINE)
    end = len(text) if following is None else match.end() + following.start()
    return match.start(), end


def hold_back(rel: str, ported: str, base_text: str, names: tuple[str, ...]) -> str:
    for name in names:
        target_span = function_span(ported, name)
        base_span = function_span(base_text, name)
        if target_span is None or base_span is None:
            continue
        ported = ported[: target_span[0]] + base_text[base_span[0] : base_span[1]] + ported[target_span[1] :]
    return ported

ported, missing = [], []
for rel in contract.get("writable_paths") or []:
    blob = subprocess.run(
        ["git", "-C", target, "show", f"{ref}:{rel}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if blob.returncode != 0:
        missing.append(rel)
        continue
    content = blob.stdout
    names = (HOLD_BACK.get(task_id) or {}).get(rel)
    if names:
        base = subprocess.run(
            ["git", "-C", target, "show", f"HEAD:{rel}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if base.returncode == 0:
            content = hold_back(rel, content, base.stdout, names)
            print(f"  held back for a later task: {', '.join(names)}")

    destination = worktree / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    ported.append(rel)

print(f"ported {len(ported)} file(s) into {worktree.name}")
for rel in ported:
    print("  +", rel)
if missing:
    print(f"absent from {ref} — author by hand:")
    for rel in missing:
        print("  ?", rel)
PY
