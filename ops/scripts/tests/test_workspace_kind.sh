#!/usr/bin/env bash
# Workspace kind: ssot | ssot_checkout | consumer. Identity files, not path prefix.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../resolve_governance_paths.sh
source "$OPS_DIR/resolve_governance_paths.sh"

PASS=0
pass() {
  PASS=$((PASS + 1))
  echo "PASS T$PASS: $1"
}

fail_now() {
  echo "FAIL: $1" >&2
  exit 1
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/l9-workspace-kind.XXXXXX")"
SSOT_ALIAS_CREATED=0
cleanup() {
  rm -rf "$TMP" "${ISO:-}"
  if [ "${SSOT_ALIAS_CREATED:-0}" -eq 1 ]; then
    rm -f "$HOME/.cursor-governance/.cursor-commands"
  fi
}
trap cleanup EXIT

seed_identity() {
  local root=$1
  mkdir -p "$root/skills" "$root/rules" "$root/ops/scripts"
  printf 'law\n' >"$root/CANONICAL_LAW.md"
  printf 'x\n' >"$root/skills/AUTONOMY_MANIFEST.yaml"
  printf 'x\n' >"$root/rules/RULES-MANIFEST.yaml"
  printf '#!/bin/sh\n' >"$root/ops/scripts/check_governance_wiring.sh"
}

CHECKOUT="$TMP/second-clone"
CONSUMER="$TMP/consumer"
seed_identity "$CHECKOUT"
mkdir -p "$CONSUMER/skills" "$CONSUMER/rules"
printf 'x\n' >"$CONSUMER/skills/AUTONOMY_MANIFEST.yaml"
printf 'x\n' >"$CONSUMER/rules/RULES-MANIFEST.yaml"

[ "$(classify_workspace_kind "$HOME/.cursor-governance")" = "ssot" ] \
  || fail_now "live SSOT must classify as ssot"
[ "$(classify_workspace_kind "$CHECKOUT")" = "ssot_checkout" ] \
  || fail_now "identity tree outside SSOT path must be ssot_checkout (got $(classify_workspace_kind "$CHECKOUT"))"
[ "$(classify_workspace_kind "$CONSUMER")" = "consumer" ] \
  || fail_now "partial tree must be consumer"
# Path under ~/.l9 without identity files is not ssot_checkout.
ISO="$HOME/.l9/gov-worktrees/_kind-class-test-$$"
mkdir -p "$ISO"
[ "$(classify_workspace_kind "$ISO")" = "consumer" ] \
  || fail_now "empty ~/.l9 isolate without identity files must not be ssot_checkout"
# run_pr_gate.sh overwrites GOV_ROOT to the workspace; that must not flip kind.
GOV_ROOT="$CHECKOUT"
[ "$(classify_workspace_kind "$CHECKOUT")" = "ssot_checkout" ] \
  || fail_now "overwritten GOV_ROOT must not classify a second clone as ssot"
unset GOV_ROOT
pass "classifier ssot / ssot_checkout / consumer"

out="$(bash "$OPS_DIR/check_governance_wiring.sh" --workspace "$CHECKOUT" 2>&1 || true)"
echo "$out" | grep -q 'Workspace kind:  ssot_checkout' \
  || fail_now "checker must print ssot_checkout kind: $out"
echo "$out" | grep -q 'ssot_checkout — consumer .cursor-commands' \
  || fail_now "unwired ssot_checkout must skip consumer links: $out"
if echo "$out" | grep -q '.cursor-commands missing'; then
  fail_now "unwired ssot_checkout must not require .cursor-commands: $out"
fi
if echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring'; then
  fail_now "unwired ssot_checkout must not fail consumer wiring: $out"
fi
echo "$out" | grep -q 'RESULT: PASS — governance wiring' \
  || fail_now "unwired ssot_checkout --workspace must PASS: $out"
if echo "$out" | grep -B2 'RESULT:' | grep -q 'IDE profile not yet applied'; then
  fail_now "IDE profile WARN must not sit immediately before RESULT: $out"
fi
pass "unwired ssot_checkout --workspace PASS"

out="$(bash "$OPS_DIR/check_governance_wiring.sh" --workspace "$CONSUMER" 2>&1 || true)"
echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring' \
  || fail_now "consumer missing .cursor-commands must FAIL: $out"
if echo "$out" | grep -q 'sessionEnd hook incomplete'; then
  fail_now "consumer symlink fail must not be labeled sessionEnd: $out"
fi
pass "consumer missing .cursor-commands FAIL"

# Optional .cursor-commands on ssot_checkout must point at the live SSOT.
ln -sfn /tmp/not-the-ssot "$CHECKOUT/.cursor-commands"
out="$(bash "$OPS_DIR/check_governance_wiring.sh" --workspace "$CHECKOUT" 2>&1 || true)"
echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring' \
  || fail_now "ssot_checkout wrong .cursor-commands target must FAIL: $out"
rm -f "$CHECKOUT/.cursor-commands"
pass "ssot_checkout wrong optional link FAIL"

# Live SSOT self-alias is forbidden. Probe with a temp link only if absent.
SSOT="$HOME/.cursor-governance"
if [ ! -e "$SSOT/.cursor-commands" ] && [ ! -L "$SSOT/.cursor-commands" ]; then
  ln -sfn "$SSOT" "$SSOT/.cursor-commands"
  SSOT_ALIAS_CREATED=1
  out="$(bash "$OPS_DIR/check_governance_wiring.sh" --workspace "$SSOT" 2>&1 || true)"
  rm -f "$SSOT/.cursor-commands"
  SSOT_ALIAS_CREATED=0
  echo "$out" | grep -q 'SSOT self-alias present' \
    || fail_now "SSOT self-alias must FAIL: $out"
  echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring' \
    || fail_now "SSOT self-alias RESULT must be consumer wiring FAIL: $out"
  pass "SSOT self-alias FAIL"
else
  fail_now "live SSOT already has .cursor-commands; refuse to stack another self-alias"
fi

# validate_governance_symlinks: consumer-link section only (machine may still run).
out="$(bash "$OPS_DIR/validate_governance_symlinks.sh" "$CHECKOUT" 2>&1 || true)"
echo "$out" | grep -q 'ssot_checkout/isolate — consumer .cursor-commands' \
  || fail_now "validate_governance_symlinks must skip consumer links on ssot_checkout: $out"
if echo "$out" | grep -q '.cursor-commands: not a symlink'; then
  fail_now "validate_governance_symlinks must not require .cursor-commands on ssot_checkout: $out"
fi
if echo "$out" | grep -q 'sessionEnd hook incomplete'; then
  fail_now "wrapper must not blame sessionEnd: $out"
fi
pass "validate_governance_symlinks ssot_checkout skips consumer links"

echo "RESULT: PASS — workspace kind ($PASS checks)"
