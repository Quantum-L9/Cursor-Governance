#!/usr/bin/env bash
# Isolated: ~/.cursor/plans becomes a symlink to <gov>/docs/plans.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../lib/workspace_kind.sh
source "$OPS_DIR/lib/workspace_kind.sh"
# shellcheck source=../lib/cursor_plans_store.sh
source "$OPS_DIR/lib/cursor_plans_store.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/cursor-plans-store.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
mkdir -p "$HOME/.cursor/plans/BUILT" "$HOME/.cursor-governance/skills"
printf '%s\n' '# law' > "$HOME/.cursor-governance/CANONICAL_LAW.md"
printf '%s\n' 'plan-body' > "$HOME/.cursor/plans/seeded_abcd1234.plan.md"
printf '%s\n' 'built' > "$HOME/.cursor/plans/BUILT/old.md"
printf '%s\n' 'skip' > "$HOME/.cursor/plans/.DS_Store"

ws="$TMP/gov-checkout"
mkdir -p "$ws/skills" "$ws/rules" "$ws/ops/scripts"
printf '%s\n' '# law' > "$ws/CANONICAL_LAW.md"
printf '%s\n' 'skills: {}' > "$ws/skills/AUTONOMY_MANIFEST.yaml"
printf '%s\n' 'rules: {}' > "$ws/rules/RULES-MANIFEST.yaml"
printf '%s\n' '#!/bin/sh' > "$ws/ops/scripts/check_governance_wiring.sh"

export WORKSPACE_DIR="$ws"
# No stamp yet — ssot_checkout should pick $ws/docs/plans
out="$(ensure_machine_cursor_plans_store)"
printf '%s\n' "$out" | grep -q "MIGRATED:"
[ -L "$HOME/.cursor/plans" ]
store="$(python3 -c "import os; print(os.path.realpath('$HOME/.cursor/plans'))")"
want="$(python3 -c "import os; print(os.path.realpath('$ws/docs/plans'))")"
[ "$store" = "$want" ]
grep -qxF 'plan-body' "$ws/docs/plans/seeded_abcd1234.plan.md"
grep -qxF 'built' "$ws/docs/plans/BUILT/old.md"
[ ! -f "$ws/docs/plans/.DS_Store" ]
[ -f "$HOME/.cursor/l9-plans-store" ]
grep -qxF "$ws/docs/plans" "$HOME/.cursor/l9-plans-store"
stamp_bak="$(ls -d "$HOME/.cursor/plans.pre-repo-store."* | head -n 1)"
[ -d "$stamp_bak" ]
grep -qxF 'plan-body' "$stamp_bak/seeded_abcd1234.plan.md"

out2="$(ensure_machine_cursor_plans_store)"
printf '%s\n' "$out2" | grep -q "OK:"
[ -L "$HOME/.cursor/plans" ]

echo "PASS: cursor_plans_store migrate + idempotent"
