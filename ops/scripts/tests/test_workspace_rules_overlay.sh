#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../workspace_rules_overlay.sh
source "$OPS_DIR/workspace_rules_overlay.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1" >&2; }

ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cursor-rules-overlay.XXXXXX")"
trap 'rm -rf "$ROOT"' EXIT
GLOBAL="$ROOT/global rules"
mkdir -p "$GLOBAL"
printf '%s\n' 'global rule' > "$GLOBAL/00-global.mdc"

case_missing() {
  local ws="$ROOT/missing"
  mkdir -p "$ws"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  [ -d "$ws/.cursor/rules" ] && [ ! -L "$ws/.cursor/rules" ]
}

case_preserve() {
  local ws="$ROOT/preserve"
  mkdir -p "$ws/.cursor/rules"
  printf '%s\n' 'local content' > "$ws/.cursor/rules/local.mdc"
  local before after
  before="$(shasum -a 256 "$ws/.cursor/rules/local.mdc" | awk '{print $1}')"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  after="$(shasum -a 256 "$ws/.cursor/rules/local.mdc" | awk '{print $1}')"
  [ "$before" = "$after" ] && [ ! -L "$ws/.cursor/rules" ]
}

case_legacy_symlink() {
  local ws="$ROOT/legacy"
  mkdir -p "$ws/.cursor"
  ln -s "$GLOBAL" "$ws/.cursor/rules"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  [ -d "$ws/.cursor/rules" ] && [ ! -L "$ws/.cursor/rules" ]
}

case_unexpected_symlink() {
  local ws="$ROOT/unexpected" other="$ROOT/unrelated"
  mkdir -p "$ws/.cursor" "$other"
  ln -s "$other" "$ws/.cursor/rules"
  if ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null 2>&1; then
    return 1
  fi
  [ -L "$ws/.cursor/rules" ] && [ "$(_rules_realpath "$ws/.cursor/rules")" = "$(_rules_realpath "$other")" ]
}

case_regular_file() {
  local ws="$ROOT/file"
  mkdir -p "$ws/.cursor"
  printf '%s\n' 'do not replace' > "$ws/.cursor/rules"
  if ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null 2>&1; then
    return 1
  fi
  [ -f "$ws/.cursor/rules" ] && grep -q 'do not replace' "$ws/.cursor/rules"
}

case_spaces() {
  local ws="$ROOT/Test Cursor Workspace"
  mkdir -p "$ws"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  validate_repo_rules_overlay "$ws"
}

case_idempotent() {
  local ws="$ROOT/idempotent"
  mkdir -p "$ws"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  local before after
  before="$(find "$ws/.cursor" -print | sort | shasum -a 256 | awk '{print $1}')"
  ensure_repo_rules_overlay "$ws" "$GLOBAL" >/dev/null
  after="$(find "$ws/.cursor" -print | sort | shasum -a 256 | awk '{print $1}')"
  [ "$before" = "$after" ]
}

case_setup_contract() {
  local setup="$OPS_DIR/setup_workspace_symlinks.sh"
  grep -q 'ensure_repo_rules_overlay "$WORKSPACE_DIR" "$GLOBAL_COMMANDS/rules"' "$setup" &&
    ! grep -q 'link_or_update "$WORKSPACE_DIR/.cursor/rules"' "$setup"
}

for spec in \
  "missing directory:case_missing" \
  "preserve populated directory:case_preserve" \
  "repair canonical legacy symlink:case_legacy_symlink" \
  "reject unexpected symlink:case_unexpected_symlink" \
  "reject regular file:case_regular_file" \
  "support paths with spaces:case_spaces" \
  "idempotent repair:case_idempotent" \
  "setup script contract:case_setup_contract"; do
  label="${spec%%:*}"
  fn="${spec##*:}"
  if "$fn"; then pass "$label"; else fail "$label"; fi
done

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
