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

python3 - "$CONTRACT" "$WORKTREE" "$TARGET" "$REF" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

contract_path, worktree, target, ref = (Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4])
contract = json.loads(contract_path.read_text(encoding="utf-8"))

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
    destination = worktree / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(blob.stdout, encoding="utf-8")
    ported.append(rel)

print(f"ported {len(ported)} file(s) into {worktree.name}")
for rel in ported:
    print("  +", rel)
if missing:
    print(f"absent from {ref} — author by hand:")
    for rel in missing:
        print("  ?", rel)
PY
