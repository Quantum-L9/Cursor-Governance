#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC="$SCRIPT_DIR/../sync_selected_rules.py"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/selected-rules.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
GOV="$TMP_ROOT/governance"
WS="$TMP_ROOT/workspace"
mkdir -p "$GOV/rules" "$WS/.cursor/rules" "$WS/.cursor/governance" "$WS/reports"
printf '%s\n' 'shared A' > "$GOV/rules/00-global.mdc"
printf '%s\n' 'shared B' > "$GOV/rules/01-git.mdc"
cat > "$GOV/rules/RULES-MANIFEST.json" <<'JSON'
{
  "rules": [
    {"file": "00-global.mdc", "id": "l9.rule.global"},
    {"file": "01-git.mdc", "id": "l9.rule.git"}
  ]
}
JSON
cat > "$WS/.cursor/governance/rules.yaml" <<'YAML'
schema: l9.cursor-rules-selection/v1
enabled: true
shared:
  required: [l9.rule.global]
  optional: [01-git]
local:
  preserve_unknown_files: true
delivery:
  mode: individual_symlink
  collision_policy: fail_closed
activation_gate:
  required_report: reports/cursor-rules-activation-baseline.md
  required_status: PASS
YAML
printf '%s\n' '# Activation' '**Status:** PASS' > "$WS/reports/cursor-rules-activation-baseline.md"
printf '%s\n' 'local sentinel' > "$WS/.cursor/rules/local.mdc"

python3 "$SYNC" "$WS" --governance-root "$GOV" --apply >/dev/null
[ -L "$WS/.cursor/rules/00-global.mdc" ]
[ -L "$WS/.cursor/rules/01-git.mdc" ]
grep -qxF 'local sentinel' "$WS/.cursor/rules/local.mdc"
python3 "$SYNC" "$WS" --governance-root "$GOV" --apply >/dev/null

rm "$WS/.cursor/rules/01-git.mdc"
printf '%s\n' 'local collision' > "$WS/.cursor/rules/01-git.mdc"
if python3 "$SYNC" "$WS" --governance-root "$GOV" --apply >/dev/null 2>&1; then
  echo "FAIL: local collision was overwritten" >&2
  exit 1
fi
grep -qxF 'local collision' "$WS/.cursor/rules/01-git.mdc"

echo "RESULT: PASS (individual links, idempotence, collision fail-closed)"
