#!/usr/bin/env bash
set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONSUMER=""
FULL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --consumer)
      CONSUMER=${2:?missing consumer path}
      shift 2
      ;;
    --full)
      FULL=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

REPORT="$GOV_ROOT/reports/rules-stabilization-validation.md"
mkdir -p "$(dirname "$REPORT")"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/rules-validation.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
FAIL=0

run_gate() {
  local name=$1
  shift
  local log="$TMP/$(printf '%s' "$name" | tr ' /' '__').log"
  if "$@" >"$log" 2>&1; then
    printf '| %s | PASS | `%s` |\n' "$name" "$(tail -1 "$log" | sed 's/`/\\`/g')" >> "$REPORT"
  else
    FAIL=1
    printf '| %s | FAIL | `%s` |\n' "$name" "$(tail -1 "$log" | sed 's/`/\\`/g')" >> "$REPORT"
  fi
}

cat > "$REPORT" <<EOF_REPORT
# Rules stabilization validation

**Scope:** Cursor rule topology, rule ownership, generated manifests, selective delivery tooling, and startup fingerprinting.

| Gate | Result | Evidence |
|---|---|---|
EOF_REPORT

run_gate "Overlay regression suite" bash "$SCRIPT_DIR/tests/test_workspace_rules_overlay.sh"
run_gate "UV fingerprint suite" bash "$SCRIPT_DIR/tests/test_uv_environment_fingerprint.sh"
run_gate "Selective rule delivery suite" bash "$SCRIPT_DIR/tests/test_selected_rules_sync.sh"
run_gate "Python syntax compilation" python3 -c \
  'import pathlib,sys; [compile(pathlib.Path(p).read_text(encoding="utf-8"), p, "exec") for p in sys.argv[1:]]' \
  "$SCRIPT_DIR/generate_rules_manifest.py" \
  "$SCRIPT_DIR/validate_rules_manifest.py" \
  "$SCRIPT_DIR/sync_selected_rules.py" \
  "$SCRIPT_DIR/capture_rules_cleanup_preflight.py" \
  "$SCRIPT_DIR/audit_rules_corpus.py" \
  "$SCRIPT_DIR/inventory_cursor_extensions.py" \
  "$SCRIPT_DIR/inventory_mcp_servers.py"
run_gate "Manifest generation" python3 "$SCRIPT_DIR/generate_rules_manifest.py" --root "$GOV_ROOT"
run_gate "Manifest validation" python3 "$SCRIPT_DIR/validate_rules_manifest.py" --root "$GOV_ROOT"
run_gate "Corpus audit generation" python3 "$SCRIPT_DIR/audit_rules_corpus.py" --root "$GOV_ROOT"

if [ -n "$CONSUMER" ]; then
  run_gate "Consumer overlay object" bash -c 'test -d "$1/.cursor/rules" && test ! -L "$1/.cursor/rules"' _ "$CONSUMER"
  run_gate "Governance symlink validator" bash "$SCRIPT_DIR/validate_governance_symlinks.sh" "$CONSUMER"
  run_gate "Fast wiring validator" bash "$SCRIPT_DIR/check_governance_wiring.sh" "$CONSUMER"
fi

scoped=(
  "$SCRIPT_DIR/generate_rules_manifest.py"
  "$SCRIPT_DIR/validate_rules_manifest.py"
  "$SCRIPT_DIR/sync_selected_rules.py"
  "$SCRIPT_DIR/capture_rules_cleanup_preflight.py"
  "$SCRIPT_DIR/audit_rules_corpus.py"
  "$SCRIPT_DIR/inventory_cursor_extensions.py"
  "$SCRIPT_DIR/inventory_mcp_servers.py"
)
if [ -x "$GOV_ROOT/.venv/bin/ruff" ]; then
  run_gate "Scoped ruff" "$GOV_ROOT/.venv/bin/ruff" check "${scoped[@]}"
elif command -v ruff >/dev/null 2>&1; then
  run_gate "Scoped ruff" ruff check "${scoped[@]}"
else
  printf '| Scoped ruff | NOT RUN | `locked ruff environment unavailable` |\n' >> "$REPORT"
fi

if [ "$FULL" -eq 1 ]; then
  run_gate "Full repository ruff" bash -c 'cd "$1" && uv run ruff check .' _ "$GOV_ROOT"
  run_gate "Full repository pytest" bash -c 'cd "$1" && uv run pytest' _ "$GOV_ROOT"
else
  printf '| Full repository ruff | DEFERRED | `Use --full; known unrelated debt may remain` |\n' >> "$REPORT"
  printf '| Full repository pytest | DEFERRED | `Use --full; known unrelated collection debt may remain` |\n' >> "$REPORT"
fi

cat >> "$REPORT" <<'EOF_REPORT'

## Manual gate

Cursor UI discovery and all four activation modes require an installed Cursor session. They are tracked in the consumer repository's `reports/cursor-rules-activation-baseline.md` and are not represented as automated success.
EOF_REPORT

if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAIL - see $REPORT" >&2
  exit 1
fi

echo "RESULT: PASS - see $REPORT"
