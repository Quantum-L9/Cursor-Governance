#!/usr/bin/env bash
# code_graph_health.sh — check code-graph index health (exit 0 = healthy)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-${REPO_ROOT:-$(pwd)}}"
export REPO_ROOT

OUT="$(python3 "$SCRIPT_DIR/code_graph_cli.py" get_graph_health "{}" "$REPO_ROOT")"
echo "$OUT"

HEALTHY="$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('true' if d.get('data',{}).get('healthy') else 'false')")"
if [[ "$HEALTHY" != "true" ]]; then
  echo "UNHEALTHY: run code_graph_batch_index.sh to seed the graph." >&2
  exit 1
fi
