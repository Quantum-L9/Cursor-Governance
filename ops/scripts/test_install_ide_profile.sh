#!/usr/bin/env bash
# Fixture selftest for install_ide_profile.sh.
#
# Runs the installer against throwaway workspaces under $TMPDIR and asserts the
# behaviours the profile contract depends on: classification, formatter
# exclusivity, managed-key merge, user-key preservation, and idempotency.
# Extension installs are neutralised by stripping `cursor` from PATH.
#
# Usage: bash ops/scripts/test_install_ide_profile.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
INSTALLER="$SCRIPT_DIR/install_ide_profile.sh"

FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-ide-profile-test.XXXXXX")"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

PASS=0
FAIL=0

# Neutralise the cursor CLI: settings merge must work without it.
STUB_BIN="$FIXTURE_ROOT/.stubbin"
mkdir -p "$STUB_BIN"
export PATH="$STUB_BIN:/usr/bin:/bin:/usr/sbin:/sbin"

run_installer() {
  bash "$INSTALLER" --quiet "$@" 2>/dev/null
}

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label"
    echo "        expected: $expected"
    echo "        actual:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

json_get() {
  # json_get <file> <key> → value as compact JSON, or __missing__
  python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except (OSError, json.JSONDecodeError):
    print("__missing__"); raise SystemExit
key = sys.argv[2]
print(json.dumps(data[key], sort_keys=True, separators=(",", ":")) if key in data else "__missing__")
' "$1" "$2"
}

echo "=== biome_default: fresh workspace ==="
WS="$FIXTURE_ROOT/plain-repo"
mkdir -p "$WS"
run_installer "$WS" >/dev/null
check "settings.json created" "yes" "$([ -f "$WS/.vscode/settings.json" ] && echo yes || echo no)"
check "stamp created" "yes" "$([ -f "$WS/.vscode/.l9-ide-desired-hash" ] && echo yes || echo no)"
check "biome owns typescript" '{"editor.defaultFormatter":"biomejs.biome"}' "$(json_get "$WS/.vscode/settings.json" '[typescript]')"
check "ruff owns python" 'charliermarsh.ruff' "$(python3 -c '
import json,sys; print(json.load(open(sys.argv[1]))["[python]"]["editor.defaultFormatter"])' "$WS/.vscode/settings.json")"

echo "=== eslint_owned: named exception ==="
WS="$FIXTURE_ROOT/Website-Bot"
mkdir -p "$WS"
run_installer "$WS" >/dev/null
check "no JS formatter key written" "__missing__" "$(json_get "$WS/.vscode/settings.json" '[typescript]')"
check "python settings still applied" "yes" "$([ "$(json_get "$WS/.vscode/settings.json" '[python]')" != "__missing__" ] && echo yes || echo no)"
check "class recorded as eslint_owned" "eslint_owned" "$(json_get "$WS/.vscode/.l9-ide-desired-hash" class | tr -d '"')"

echo "=== eslint_owned: heuristic (eslint config, no biome.json) ==="
WS="$FIXTURE_ROOT/some-node-app"
mkdir -p "$WS"
echo 'export default [];' > "$WS/eslint.config.js"
run_installer "$WS" >/dev/null
check "heuristic classified eslint_owned" "eslint_owned" "$(json_get "$WS/.vscode/.l9-ide-desired-hash" class | tr -d '"')"

echo "=== biome_default: biome.json present alongside eslint config ==="
WS="$FIXTURE_ROOT/dual-config-app"
mkdir -p "$WS"
echo 'export default [];' > "$WS/eslint.config.js"
echo '{}' > "$WS/biome.json"
run_installer "$WS" >/dev/null
check "biome marker wins" "biome_default" "$(json_get "$WS/.vscode/.l9-ide-desired-hash" class | tr -d '"')"

echo "=== managed-key merge: user keys preserved, user overrides respected ==="
WS="$FIXTURE_ROOT/user-settings-repo"
mkdir -p "$WS/.vscode"
cat > "$WS/.vscode/settings.json" <<'JSON'
{
  "editor.formatOnSave": false,
  "my.custom.setting": "keep-me"
}
JSON
run_installer "$WS" >/dev/null
check "pre-existing user key preserved" '"keep-me"' "$(json_get "$WS/.vscode/settings.json" 'my.custom.setting')"
check "pre-existing formatOnSave not clobbered" 'false' "$(json_get "$WS/.vscode/settings.json" 'editor.formatOnSave')"
check "unowned key still adopted" 'true' "$(json_get "$WS/.vscode/settings.json" 'files.insertFinalNewline')"
check "formatOnSave excluded from managed set" "no" "$(python3 -c '
import json,sys
print("yes" if "editor.formatOnSave" in json.load(open(sys.argv[1]))["managed_keys"] else "no")' "$WS/.vscode/.l9-ide-desired-hash")"

echo "=== idempotency: second run is a no-op ==="
WS="$FIXTURE_ROOT/idempotent-repo"
mkdir -p "$WS"
run_installer "$WS" >/dev/null
FIRST="$(shasum -a 256 "$WS/.vscode/settings.json" | awk '{print $1}')"
SECOND_STATE="$(run_installer "$WS")"
SECOND="$(shasum -a 256 "$WS/.vscode/settings.json" | awk '{print $1}')"
check "settings unchanged on rerun" "$FIRST" "$SECOND"
check "rerun reports settings=current" "yes" "$(echo "$SECOND_STATE" | grep -q 'settings=current' && echo yes || echo no)"

echo "=== JSONC safety: commented settings.json left untouched ==="
WS="$FIXTURE_ROOT/jsonc-repo"
mkdir -p "$WS/.vscode"
cat > "$WS/.vscode/settings.json" <<'JSONC'
{
  // hand-written comment the profile must not destroy
  "editor.tabSize": 4
}
JSONC
BEFORE="$(shasum -a 256 "$WS/.vscode/settings.json" | awk '{print $1}')"
run_installer "$WS" >/dev/null
AFTER="$(shasum -a 256 "$WS/.vscode/settings.json" | awk '{print $1}')"
check "JSONC file untouched" "$BEFORE" "$AFTER"

echo "=== dry-run writes nothing ==="
WS="$FIXTURE_ROOT/dry-run-repo"
mkdir -p "$WS"
bash "$INSTALLER" --quiet --dry-run "$WS" >/dev/null 2>&1
check "no .vscode created" "no" "$([ -d "$WS/.vscode" ] && echo yes || echo no)"

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
