#!/usr/bin/env bash
# code_graph_batch_index.sh — seed/resume index via CLI (never in agent chat)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-${REPO_ROOT:-$(pwd)}}"
BATCH_SIZE="${BATCH_SIZE:-100}"
MAX_ROUNDS="${MAX_ROUNDS:-50}"
export REPO_ROOT

echo "Indexing: $REPO_ROOT (batch_size=$BATCH_SIZE)"
round=0
while (( round < MAX_ROUNDS )); do
  round=$((round + 1))
  OUT="$(python3 "$SCRIPT_DIR/code_graph_cli.py" batch_index "{\"maxFilesPerBatch\": $BATCH_SIZE}" "$REPO_ROOT")"
  PROGRESS="$(echo "$OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
p = d.get('data', {}).get('progress', {})
print(f\"{p.get('done', False)}|{p.get('percent', 0)}|{p.get('cursor', 0)}|{p.get('totalFiles', 0)}\")
")"
  IFS='|' read -r DONE PCT CURSOR TOTAL <<< "$PROGRESS"
  printf "round %2d: %s/%s files (%.1f%%) done=%s\n" "$round" "$CURSOR" "$TOTAL" "$PCT" "$DONE"
  if [[ "$DONE" == "True" || "$DONE" == "true" ]]; then
    echo "Index complete."
    "$SCRIPT_DIR/code_graph_health.sh" "$REPO_ROOT"
    exit 0
  fi
  sleep 0.1
done

echo "ERROR: exceeded MAX_ROUNDS=$MAX_ROUNDS — re-run to resume." >&2
exit 1
