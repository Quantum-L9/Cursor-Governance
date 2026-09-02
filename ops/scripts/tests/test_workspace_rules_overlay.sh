#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../lib/path_contracts.sh
source "$OPS_DIR/lib/path_contracts.sh"
# shellcheck source=../lib/rules_overlay.sh
source "$OPS_DIR/lib/rules_overlay.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cursor-rules-overlay.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0

pass() {
  PASS=$((PASS + 1))
  echo "PASS T$PASS: $1"
}

assert_real_dir() {
  [ -d "$1" ] && [ ! -L "$1" ]
}

# T1: missing rules directory.
ws="$TMP_ROOT/t1"
mkdir -p "$ws"
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
assert_real_dir "$ws/.cursor/rules"
pass "missing rules directory becomes a real directory"

# T2: populated local directory remains byte-identical.
ws="$TMP_ROOT/t2"
mkdir -p "$ws/.cursor/rules"
printf '%s\n' 'local rule sentinel' > "$ws/.cursor/rules/local-rule.mdc"
before="$(sha256sum "$ws/.cursor/rules/local-rule.mdc" | awk '{print $1}')"
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
after="$(sha256sum "$ws/.cursor/rules/local-rule.mdc" | awk '{print $1}')"
[ "$before" = "$after" ]
assert_real_dir "$ws/.cursor/rules"
pass "populated local directory is preserved byte-for-byte"

# T3: legacy canonical symlink is repaired.
ws="$TMP_ROOT/t3"
mkdir -p "$TMP_ROOT/global/rules" "$ws/.cursor"
ln -s "$TMP_ROOT/global/rules" "$ws/.cursor/rules"
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
assert_real_dir "$ws/.cursor/rules"
pass "legacy canonical rules symlink is replaced with a real directory"

# T4: unexpected symlink fails closed without mutation.
ws="$TMP_ROOT/t4"
mkdir -p "$TMP_ROOT/unrelated" "$ws/.cursor"
ln -s "$TMP_ROOT/unrelated" "$ws/.cursor/rules"
if ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null 2>&1; then
  echo "FAIL: unexpected symlink was accepted" >&2
  exit 1
fi
[ -L "$ws/.cursor/rules" ]
[ "$(path_realpath "$ws/.cursor/rules")" = "$(path_realpath "$TMP_ROOT/unrelated")" ]
pass "unexpected symlink fails closed and remains unchanged"

# T5: regular-file collision fails closed.
ws="$TMP_ROOT/t5"
mkdir -p "$ws/.cursor"
printf '%s\n' 'collision' > "$ws/.cursor/rules"
if ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null 2>&1; then
  echo "FAIL: regular-file collision was accepted" >&2
  exit 1
fi
[ -f "$ws/.cursor/rules" ]
grep -qxF 'collision' "$ws/.cursor/rules"
pass "regular-file collision fails closed"

# T6: paths containing spaces.
ws="$TMP_ROOT/Test Cursor Workspace"
mkdir -p "$ws"
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
assert_real_dir "$ws/.cursor/rules"
pass "workspace paths containing spaces are supported"

# T7: idempotence.
ws="$TMP_ROOT/t7"
mkdir -p "$ws/.cursor/rules"
printf '%s\n' 'stable' > "$ws/.cursor/rules/stable.mdc"
first="$(find "$ws/.cursor/rules" -type f -exec sha256sum {} \; | sort)"
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
ensure_repo_rules_overlay "$ws/.cursor/rules" "$TMP_ROOT/global/rules" >/dev/null
second="$(find "$ws/.cursor/rules" -type f -exec sha256sum {} \; | sort)"
[ "$first" = "$second" ]
pass "repeated repair is idempotent"

# T8: full setup preserves local rules while wiring shared entry points.
fixture_home="$TMP_ROOT/t8-home"
gov="$fixture_home/.cursor-governance"
ws="$TMP_ROOT/t8-workspace"
mkdir -p "$gov/ops/scripts/lib" "$gov/ops/hooks" "$gov/skills" "$gov/commands" \
  "$gov/rules" "$ws/.cursor/rules"
cp "$OPS_DIR/setup_workspace_symlinks.sh" "$gov/ops/scripts/"
cp "$OPS_DIR/resolve_governance_paths.sh" "$gov/ops/scripts/"
cp "$OPS_DIR/lib/path_contracts.sh" "$gov/ops/scripts/lib/"
cp "$OPS_DIR/lib/rules_overlay.sh" "$gov/ops/scripts/lib/"
cp "$OPS_DIR/lib/workspace_kind.sh" "$gov/ops/scripts/lib/"
cp "$OPS_DIR/lib/cursor_plans_store.sh" "$gov/ops/scripts/lib/"
cp "$OPS_DIR/lib/retire_leftover_launchagents.sh" "$gov/ops/scripts/lib/"
printf '%s\n' '# law' > "$gov/CANONICAL_LAW.md"
printf '%s\n' '{"version":1,"hooks":{}}' > "$gov/ops/hooks/hooks.json.template"
cat > "$gov/ops/scripts/validate_governance_symlinks.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$gov/ops/scripts/validate_governance_symlinks.sh"
printf '%s\n' 'preserve me' > "$ws/.cursor/rules/local-rule.mdc"
before="$(sha256sum "$ws/.cursor/rules/local-rule.mdc" | awk '{print $1}')"
(
  export HOME="$fixture_home"
  export GRAPHITI_MEMORY_ENABLED=0
  cd "$ws"
  bash "$gov/ops/scripts/setup_workspace_symlinks.sh" >/dev/null
)
after="$(sha256sum "$ws/.cursor/rules/local-rule.mdc" | awk '{print $1}')"
[ "$before" = "$after" ]
assert_real_dir "$ws/.cursor/rules"
[ -L "$ws/.cursor-commands" ]
[ -L "$ws/.cursor/plans" ]
plans_rt="$(python3 -c "import os; print(os.path.realpath('$ws/.cursor/plans'))")"
plans_want="$(python3 -c "import os; print(os.path.realpath('$fixture_home/.cursor/plans'))")"
[ "$plans_rt" = "$plans_want" ]
[ -L "$fixture_home/.cursor/plans" ]
store_rt="$(python3 -c "import os; print(os.path.realpath('$gov/docs/plans'))")"
[ "$plans_rt" = "$store_rt" ]
pass "full setup preserves local rules and wires .cursor-commands + .cursor/plans"

# T9: SSOT setup removes self-alias (do not create .cursor-commands → self).
fixture_home9="$TMP_ROOT/t9-home"
gov9="$fixture_home9/.cursor-governance"
mkdir -p "$gov9/ops/scripts/lib" "$gov9/ops/hooks" "$gov9/skills" "$gov9/commands" "$gov9/rules"
cp "$OPS_DIR/setup_workspace_symlinks.sh" "$gov9/ops/scripts/"
cp "$OPS_DIR/resolve_governance_paths.sh" "$gov9/ops/scripts/"
cp "$OPS_DIR/lib/path_contracts.sh" "$gov9/ops/scripts/lib/"
cp "$OPS_DIR/lib/rules_overlay.sh" "$gov9/ops/scripts/lib/"
cp "$OPS_DIR/lib/workspace_kind.sh" "$gov9/ops/scripts/lib/"
cp "$OPS_DIR/lib/cursor_plans_store.sh" "$gov9/ops/scripts/lib/"
cp "$OPS_DIR/lib/retire_leftover_launchagents.sh" "$gov9/ops/scripts/lib/"
printf '%s\n' '# law' > "$gov9/CANONICAL_LAW.md"
printf '%s\n' '{"version":1,"hooks":{}}' > "$gov9/ops/hooks/hooks.json.template"
# Minimal activator so install_session_end copy is optional
printf '%s\n' '#!/usr/bin/env bash' > "$gov9/ops/scripts/governance_activate_fresh.sh"
chmod +x "$gov9/ops/scripts/governance_activate_fresh.sh"
cat > "$gov9/ops/scripts/validate_governance_symlinks.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$gov9/ops/scripts/validate_governance_symlinks.sh"
# Pre-seed a bad self-alias
ln -sfn "$gov9" "$gov9/.cursor-commands"
(
  export HOME="$fixture_home9"
  export GRAPHITI_MEMORY_ENABLED=0
  cd "$gov9"
  bash "$gov9/ops/scripts/setup_workspace_symlinks.sh" >/dev/null
)
[ ! -e "$gov9/.cursor-commands" ]
[ -L "$gov9/.cursor/plans" ]
[ -L "$fixture_home9/.cursor/plans" ]
t9_rt="$(python3 -c "import os; print(os.path.realpath('$gov9/.cursor/plans'))")"
t9_store="$(python3 -c "import os; print(os.path.realpath('$gov9/docs/plans'))")"
[ "$t9_rt" = "$t9_store" ]
pass "SSOT setup removes .cursor-commands self-alias and wires .cursor/plans"

# T10: ssot_checkout (identity tree, not live SSOT) must not get .cursor-commands.
# Consumer T8 still requires the link; this case is the C1 complement.
fixture_home10="$TMP_ROOT/t10-home"
gov10="$fixture_home10/.cursor-governance"
checkout10="$TMP_ROOT/t10-checkout"
mkdir -p "$gov10/ops/scripts/lib" "$gov10/ops/hooks" "$gov10/skills" "$gov10/commands" \
  "$gov10/rules" "$checkout10/skills" "$checkout10/rules" "$checkout10/ops/scripts"
cp "$OPS_DIR/setup_workspace_symlinks.sh" "$gov10/ops/scripts/"
cp "$OPS_DIR/resolve_governance_paths.sh" "$gov10/ops/scripts/"
cp "$OPS_DIR/lib/path_contracts.sh" "$gov10/ops/scripts/lib/"
cp "$OPS_DIR/lib/rules_overlay.sh" "$gov10/ops/scripts/lib/"
cp "$OPS_DIR/lib/workspace_kind.sh" "$gov10/ops/scripts/lib/"
cp "$OPS_DIR/lib/cursor_plans_store.sh" "$gov10/ops/scripts/lib/"
cp "$OPS_DIR/lib/retire_leftover_launchagents.sh" "$gov10/ops/scripts/lib/"
printf '%s\n' '# law' > "$gov10/CANONICAL_LAW.md"
printf '%s\n' '# law' > "$checkout10/CANONICAL_LAW.md"
printf '%s\n' 'x' > "$gov10/skills/AUTONOMY_MANIFEST.yaml"
printf '%s\n' 'x' > "$checkout10/skills/AUTONOMY_MANIFEST.yaml"
printf '%s\n' 'x' > "$gov10/rules/RULES-MANIFEST.yaml"
printf '%s\n' 'x' > "$checkout10/rules/RULES-MANIFEST.yaml"
printf '%s\n' '#!/bin/sh' > "$checkout10/ops/scripts/check_governance_wiring.sh"
printf '%s\n' '{"version":1,"hooks":{}}' > "$gov10/ops/hooks/hooks.json.template"
printf '%s\n' '#!/usr/bin/env bash' > "$gov10/ops/scripts/governance_activate_fresh.sh"
chmod +x "$gov10/ops/scripts/governance_activate_fresh.sh"
cat > "$gov10/ops/scripts/validate_governance_symlinks.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$gov10/ops/scripts/validate_governance_symlinks.sh"
ln -sfn "$gov10" "$checkout10/.cursor-commands"
(
  export HOME="$fixture_home10"
  export GRAPHITI_MEMORY_ENABLED=0
  cd "$checkout10"
  bash "$gov10/ops/scripts/setup_workspace_symlinks.sh" >/dev/null
)
[ ! -e "$checkout10/.cursor-commands" ]
[ -L "$checkout10/.cursor/plans" ]
pass "ssot_checkout setup removes .cursor-commands and does not recreate it"

echo "RESULT: PASS ($PASS cases)"
