#!/usr/bin/env bash
# SP-02: ensure_workspace_wired creates consumer .cursor links; second run is no-op.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPER="$OPS_DIR/ensure_workspace_wired.sh"
[ -x "$HELPER" ]

TMP="$(mktemp -d "${TMPDIR:-/tmp}/ensure-wired.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ws="$TMP/consumer"
mkdir -p "$ws"
export L9_WIRE_LINKS_ONLY=1

bash "$HELPER" "$ws"
[ -L "$ws/.cursor-commands" ]
[ -L "$ws/.cursor/plans" ]
[ -L "$ws/.cursor/governance/CANONICAL_LAW.md" ]
gc="$(python3 -c "import os; print(os.path.realpath('$HOME/.cursor-governance'))")"
rt="$(python3 -c "import os; print(os.path.realpath('$ws/.cursor-commands'))")"
[ "$rt" = "$gc" ]

out="$(bash "$HELPER" "$ws")"
printf '%s\n' "$out" | grep -q "already wired"

echo "PASS: ensure_workspace_wired.sh links + idempotent"

# ssot_checkout (identity tree, not live SSOT): do not create .cursor-commands,
# and remove a leftover consumer link. Plans + CANONICAL_LAW still wire.
checkout="$TMP/ssot-checkout"
mkdir -p "$checkout/skills" "$checkout/rules" "$checkout/ops/scripts"
printf '%s\n' '# law' > "$checkout/CANONICAL_LAW.md"
printf '%s\n' 'x' > "$checkout/skills/AUTONOMY_MANIFEST.yaml"
printf '%s\n' 'x' > "$checkout/rules/RULES-MANIFEST.yaml"
printf '%s\n' '#!/bin/sh' > "$checkout/ops/scripts/check_governance_wiring.sh"
ln -sfn "$HOME/.cursor-governance" "$checkout/.cursor-commands"

out="$(bash "$HELPER" "$checkout")"
[ ! -e "$checkout/.cursor-commands" ] \
  || { echo "FAIL: ssot_checkout still has .cursor-commands: $out" >&2; exit 1; }
[ -L "$checkout/.cursor/plans" ]
[ -L "$checkout/.cursor/governance/CANONICAL_LAW.md" ]
printf '%s\n' "$out" | grep -q 'ssot_checkout' \
  || { echo "FAIL: ssot_checkout wire did not name the kind: $out" >&2; exit 1; }

out2="$(bash "$HELPER" "$checkout")"
printf '%s\n' "$out2" | grep -q "already wired" \
  || { echo "FAIL: second ssot_checkout wire not idempotent: $out2" >&2; exit 1; }
[ ! -e "$checkout/.cursor-commands" ]

echo "PASS: ensure_workspace_wired.sh ssot_checkout removes .cursor-commands"
