#!/usr/bin/env bash
# Fixture selftest for install_ide_profile.sh.
#
# Runs the installer against throwaway workspaces under $TMPDIR and asserts the
# behaviours the profile contract depends on: classification, formatter
# exclusivity, managed-key merge, user-key preservation, idempotency, adapter
# dispatch, and the generated agent-docs ownership block.
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
printf '# Dry\n' > "$WS/AGENTS.md"
DRY_BEFORE="$(shasum -a 256 "$WS/AGENTS.md" | awk '{print $1}')"
bash "$INSTALLER" --quiet --dry-run "$WS" >/dev/null 2>&1
check "no .vscode created" "no" "$([ -d "$WS/.vscode" ] && echo yes || echo no)"
check "AGENTS.md untouched in dry-run" "$DRY_BEFORE" "$(shasum -a 256 "$WS/AGENTS.md" | awk '{print $1}')"

echo "=== dispatch: every adapter reports a state ==="
WS="$FIXTURE_ROOT/dispatch-repo"
mkdir -p "$WS"
printf '# Dispatch\n' > "$WS/AGENTS.md"
DISPATCH_STATE="$(run_installer "$WS")"
for key in ext settings agentdocs; do
  check "summary reports $key=" "yes" "$(echo "$DISPATCH_STATE" | grep -q "$key=" && echo yes || echo no)"
done
check "no adapter reported failed" "no" "$(echo "$DISPATCH_STATE" | grep -qE '=(failed|missing)' && echo yes || echo no)"

echo "=== dispatch: a missing adapter degrades, never aborts ==="
EMPTY_ADAPTERS="$FIXTURE_ROOT/.no-adapters"
mkdir -p "$EMPTY_ADAPTERS"
# Symlink, not copy: the adapter resolves its own realpath to find the governance
# root, so a copy outside ops/scripts/adapters/ could not load it.
ln -s "$SCRIPT_DIR/adapters/cursor.sh" "$EMPTY_ADAPTERS/cursor.sh"
WS="$FIXTURE_ROOT/degraded-repo"
mkdir -p "$WS"
DEGRADED="$(L9_IDE_ADAPTER_DIR="$EMPTY_ADAPTERS" bash "$INSTALLER" --quiet "$WS" 2>/dev/null)"
check "missing adapter surfaced" "yes" "$(echo "$DEGRADED" | grep -q 'agentdocs=missing' && echo yes || echo no)"
check "cursor adapter still ran" "yes" "$([ -f "$WS/.vscode/settings.json" ] && echo yes || echo no)"

echo "=== agentdocs: ownership block generated in tracked files ==="
WS="$FIXTURE_ROOT/agentdocs-repo"
mkdir -p "$WS"
printf '# Repo rules\n' > "$WS/AGENTS.md"
printf '# Claude\n' > "$WS/CLAUDE.md"
run_installer "$WS" >/dev/null
check "AGENTS.md got the block" "1" "$(grep -c 'BEGIN L9 FORMATTER OWNERSHIP' "$WS/AGENTS.md")"
check "CLAUDE.md got the block" "1" "$(grep -c 'BEGIN L9 FORMATTER OWNERSHIP' "$WS/CLAUDE.md")"
check "block names the owning formatter" "yes" "$(grep -q '\*\*biome\*\*' "$WS/AGENTS.md" && echo yes || echo no)"
check "pre-existing prose preserved" "yes" "$(grep -q '^# Repo rules' "$WS/AGENTS.md" && echo yes || echo no)"
check "agentdocs stamp written" "yes" "$([ -f "$WS/.vscode/.l9-agentdocs-hash" ] && echo yes || echo no)"

echo "=== agentdocs: block is replaced, not appended, on reclassify ==="
echo 'export default [];' > "$WS/eslint.config.js"
run_installer "$WS" >/dev/null
check "still exactly one block" "1" "$(grep -c 'BEGIN L9 FORMATTER OWNERSHIP' "$WS/AGENTS.md")"
check "block now defers to the repo" "yes" "$(grep -q "eslint (this repo's own config)" "$WS/AGENTS.md" && echo yes || echo no)"

echo "=== agentdocs: never creates AGENTS.md where none exists ==="
WS="$FIXTURE_ROOT/no-agentdocs-repo"
mkdir -p "$WS"
NO_DOCS_STATE="$(run_installer "$WS")"
check "reports absent" "yes" "$(echo "$NO_DOCS_STATE" | grep -q 'agentdocs=absent' && echo yes || echo no)"
check "AGENTS.md not created" "no" "$([ -f "$WS/AGENTS.md" ] && echo yes || echo no)"

echo "=== policy.json is the ownership authority for both classes ==="
check "biome_default binds JS/TS from policy" '{"editor.defaultFormatter":"biomejs.biome"}' \
  "$(json_get "$FIXTURE_ROOT/plain-repo/.vscode/settings.json" '[typescript]')"
check "eslint_owned binds nothing for JS/TS" "__missing__" \
  "$(json_get "$FIXTURE_ROOT/Website-Bot/.vscode/settings.json" '[typescript]')"
check "policy declares no extension IDs" "no" \
  "$(grep -q 'biomejs.biome\|charliermarsh.ruff' "${L9_IDE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)/environment/ide}/policy.json" && echo yes || echo no)"

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
