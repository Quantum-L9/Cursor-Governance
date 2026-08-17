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
