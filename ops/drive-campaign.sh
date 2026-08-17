#!/usr/bin/env bash
# Drive pe-kernel-bind to the top of its task stack, materializing each task's
# declared deliverables in its own worktree before re-attempting execute.
set -uo pipefail

ISO="$HOME/.l9/gov-worktrees/pe-kernel-bind"
WS="$HOME/.l9/programs/pe-kernel-bind"
PEC="$ISO/environment/program-execution/core/program-execution-controller-template/scripts/pec.py"
INTENT="$HOME/.cursor/plans/pe-kernel-bind.activate.yaml"

cd "$ISO"

current_task() {
  L9_ALLOW_PEC_DIRECT=1 python3 "$PEC" status --workspace "$WS" 2>/dev/null | python3 -c "
import json, sys
document = json.load(sys.stdin)
for task in document.get('tasks', []):
    if task['runtime_state'] != 'COMPLETED':
        print(task['id'])
        break
"
}

report_failure() {
  local task="$1"
  python3 -c "
import json
from pathlib import Path
receipt = Path('$WS/receipts/verification/$task.json')
if not receipt.is_file():
    raise SystemExit('no verification receipt yet')
document = json.loads(receipt.read_text())
failed = {name: value for name, value in (document.get('gates') or {}).items() if value != 'PASS'}
print('  verdict:', document.get('kernel_verdict'), failed)
for item in document.get('validations') or []:
    print('  ', item['status'], item['command'][:100])
    if item['status'] != 'PASS':
        print('     ', (item.get('stderr') or item.get('stdout') or '')[:600])
"
}

for _ in $(seq 1 20); do
  task="$(current_task)"
  if [ -z "$task" ]; then
    echo "ALL TASKS COMPLETED"
    exit 0
  fi

  if [ -d "$WS/worktrees/$task" ] && [ -f "$WS/contracts/rendered/$task.json" ]; then
    "$ISO/ops/port-task-deliverable.sh" "$task" 2>&1 | sed 's/^/  /' | head -8
    if [ "$task" = "TASK-001" ]; then
      cp /tmp/adrs-keep/canonical/*.md "$WS/worktrees/$task/environment/contracts/execution/adr/"
      cp /tmp/adrs-keep/pointer/*.md "$WS/worktrees/$task/docs/decisions/"
      echo "  restored the ADR bodies for TASK-001"
    fi
  fi

  output="$(L9_CAMPAIGN_UNTIL_DEBUG=1 make campaign INTENT="$INTENT" CAMPAIGN_UNTIL=execute 2>&1)"
  after="$(current_task)"
  echo "[$task] -> ${after:-all complete}"

  if [ "$after" = "$task" ]; then
    if echo "$output" | grep -q "refuse stub"; then
      echo "$output" | grep "refuse stub" | head -1
      continue
    fi
    echo "$output" | grep -E "FAIL|Error" | head -2
    report_failure "$task"
    exit 1
  fi
done
