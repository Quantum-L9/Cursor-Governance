#!/usr/bin/env bash
# code_graph_gmp_baseline.sh — GMP Phase 0 code-graph evidence (CLI only, zero chat tokens)
# Usage:
#   code_graph_gmp_baseline.sh <repo_root> [--run-id ID] --files path1 [path2 ...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=""
RUN_ID="gmp-$(date +%Y%m%d-%H%M%S)"
FILES=()

usage() {
  echo "Usage: $0 <repo_root> [--run-id ID] --files rel/path1 [rel/path2 ...]" >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --files)
      shift
      while [ $# -gt 0 ] && [ "$1" != "--run-id" ]; do
        FILES+=("$1")
        shift
      done
      ;;
    *)
      if [ -z "$REPO_ROOT" ]; then
        REPO_ROOT="$1"
      else
        echo "Unknown argument: $1" >&2
        usage
      fi
      shift
      ;;
  esac
done

[ -n "$REPO_ROOT" ] || usage
[ "${#FILES[@]}" -gt 0 ] || usage

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
export REPO_ROOT

if [ ! -d "$REPO_ROOT/plasticos_base" ]; then
  echo "ERROR: not a PlasticOS repo: $REPO_ROOT" >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/.cursor"
EVIDENCE_PATH="$REPO_ROOT/.cursor/code-graph-phase0-evidence.json"

if ! HEALTH_JSON="$(bash "$SCRIPT_DIR/code_graph_health.sh" "$REPO_ROOT" 2>/dev/null)"; then
  python3 - <<PY
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

path = Path("$EVIDENCE_PATH")
data = {
    "run_id": "$RUN_ID",
    "status": "blocked",
    "healthy": False,
    "targets": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "${FILES[@]}"),
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "expires_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "message": "Index unhealthy — run code_graph_batch_index.sh in Terminal",
}
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY
  echo "BLOCKED: code-graph index unhealthy." >&2
  exit 1
fi

python3 - "$REPO_ROOT" "$RUN_ID" "$EVIDENCE_PATH" "$SCRIPT_DIR" "${FILES[@]}" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

repo = Path(sys.argv[1])
run_id = sys.argv[2]
evidence_path = Path(sys.argv[3])
script_dir = Path(sys.argv[4])
files = sys.argv[5:]

sys.path.insert(0, str(script_dir))
from code_graph_plasticos_gate import (  # noqa: E402
    entity_hint_for_path,
    is_foundation_path,
    is_high_impact_path,
    normalize_rel_path,
)


def call_cli(tool: str, args: dict) -> dict:
    proc = subprocess.run(
        ["python3", str(script_dir / "code_graph_cli.py"), tool, json.dumps(args), str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"success": False, "error": proc.stderr.strip() or proc.stdout.strip()}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"success": False, "text": proc.stdout}


now = datetime.now(timezone.utc)
expires = now + timedelta(hours=4)

targets = [normalize_rel_path(f) for f in files]
needs_graph = [t for t in targets if is_high_impact_path(t)]
if not needs_graph:
    data = {
        "run_id": run_id,
        "status": "skipped",
        "healthy": True,
        "targets": targets,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "message": "CODE_GRAPH_BASELINE: SKIPPED (grep-only / known path — no high-impact targets)",
    }
    evidence_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2))
    sys.exit(0)

importers: dict[str, object] = {}
impacts: dict[str, object] = {}
modules: set[str] = set()
covered_prefixes: set[str] = set()

for rel in needs_graph:
    module = rel.split("/", 1)[0]
    modules.add(module)
    covered_prefixes.add(f"{module}/")

    if is_foundation_path(rel):
        result = call_cli("list_module_importers", {"moduleSource": module, "limit": 100})
        importers[rel] = result

    entity = entity_hint_for_path(rel)
    if entity:
        result = call_cli(
            "analyze_code_impact",
            {"entityId": entity, "filePath": rel, "depth": 2},
        )
        impacts[rel] = result
    else:
        resolved = call_cli("resolve_entity", {"name": Path(rel).stem, "filePathHint": rel, "limit": 5})
        impacts[rel] = {"resolve_entity": resolved}

data = {
    "run_id": run_id,
    "status": "complete",
    "healthy": True,
    "targets": targets,
    "modules": sorted(modules),
    "covered_prefixes": sorted(covered_prefixes),
    "importers": importers,
    "impact": impacts,
    "created_at": now.isoformat().replace("+00:00", "Z"),
    "expires_at": expires.isoformat().replace("+00:00", "Z"),
    "trigger_matrix": "skills/l9-code-graph-rag-mcp/assets/plasticos-trigger-matrix.md",
    "message": "CODE_GRAPH_BASELINE: COMPLETE",
}
evidence_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY

echo "OK: evidence written to $EVIDENCE_PATH" >&2
