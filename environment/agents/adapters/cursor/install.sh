#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Cursor adapter install — THIN. Binds shared ops/ capability; owns none of it.
#
#   1. shared bootstrap        ops/scripts/bootstrap_agent_environment.sh
#   2. Cursor wiring checks    hooks.json registration, l9-governance plugin,
#                              .cursor-commands (consumers only)
#   3. receipt                 ~/.l9/cursor/bootstrap-state.json
#                              (schema l9.cursor-bootstrap.v1; read by
#                              ops/scripts/claude_bootstrap_receipt.py
#                              --surface cursor — one reader, one expiry rule)
#
# --check is a diagnosis: it writes bootstrap-check.json beside the real
# receipt and never overwrites the session's own verdicts (same rule the
# claude-code installer follows).
#
# HARD REFUSAL: --workspace may not be $HOME or a non-git directory. A $HOME
# workspace is exactly how a harness run poisoned the Claude receipt that was
# then reported as session state (tech-debt ledger TD row: receipt poisoning).
#
# Exit codes: 0 ready | 6 usable but degraded | 1 refused / hard failure.
# ---------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
WORKSPACE="$PWD"
CHECK=0
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --governance) GOV_DIR="${2:?--governance needs a path}"; shift 2 ;;
    --workspace)  WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --check)      CHECK=1; shift ;;
    --quiet)      QUIET=1; shift ;;
    -h|--help)    sed -n '2,21p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "cursor-install: unknown argument '$1'" >&2; exit 1 ;;
  esac
done

say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*" >&2; }
fail() { printf 'cursor-install ERROR: %s\n' "$*" >&2; exit 1; }

# --- workspace refusal (before anything writes) -------------------------------
WORKSPACE="$(cd "$WORKSPACE" 2>/dev/null && pwd -P)" || fail "workspace does not exist"
HOME_REAL="$(cd "$HOME" && pwd -P)"
if [ "$WORKSPACE" = "$HOME_REAL" ]; then
  fail "refusing --workspace \$HOME ($WORKSPACE) — a home-directory workspace writes a receipt no session owns; pass a git repository root"
fi
if ! git -C "$WORKSPACE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "refusing --workspace $WORKSPACE — not a git work tree; pass a repository root"
fi
[ -f "$GOV_DIR/CANONICAL_LAW.md" ] || fail "no governance SSOT at $GOV_DIR"

say "cursor-install: workspace=$WORKSPACE governance=$GOV_DIR mode=$([ "$CHECK" = "1" ] && echo check || echo install)"

# --- receipt machinery (before the first fallible stage) ----------------------
if [ "$CHECK" = "1" ] && [ -z "${L9_CURSOR_BOOTSTRAP_RECEIPT:-}" ]; then
  RECEIPT="$HOME/.l9/cursor/bootstrap-check.json"
else
  RECEIPT="${L9_CURSOR_BOOTSTRAP_RECEIPT:-$HOME/.l9/cursor/bootstrap-state.json}"
fi
STAGE="startup"
STATUS_SHARED="UNKNOWN";  REASON_SHARED=""
STATUS_HOOKS="UNKNOWN";   REASON_HOOKS=""
STATUS_PLUGIN="UNKNOWN";  REASON_PLUGIN=""
STATUS_COMMANDS="UNKNOWN"; REASON_COMMANDS=""

json_token() { printf '%s' "$1" | tr -d '\n\r\t"\\' | head -c 200; }

write_receipt() {
  local state="$1" ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')"
  mkdir -p "$(dirname "$RECEIPT")" 2>/dev/null || return 0
  {
    printf '{\n'
    printf '  "schema": "l9.cursor-bootstrap.v1",\n'
    printf '  "surface": "cursor",\n'
    printf '  "mode": "%s",\n' "$([ "$CHECK" = "1" ] && echo check || echo local)"
    printf '  "state": "%s",\n' "$(json_token "$state")"
    printf '  "stage": "%s",\n' "$(json_token "$STAGE")"
    printf '  "remediation": "make cursor-install WS=<repo>",\n'
    printf '  "generated_at": "%s",\n' "$ts"
    printf '  "ttl_seconds": %s,\n' "${L9_CURSOR_BOOTSTRAP_TTL:-86400}"
    printf '  "governance_revision": "%s",\n' \
      "$(json_token "$(git -C "$GOV_DIR" rev-parse HEAD 2>/dev/null || echo unknown)")"
    printf '  "workspace": "%s",\n' "$(json_token "$WORKSPACE")"
    printf '  "shared_bootstrap": "%s",\n' "$(json_token "$STATUS_SHARED")"
    printf '  "hooks": "%s",\n' "$(json_token "$STATUS_HOOKS")"
    printf '  "plugin": "%s",\n' "$(json_token "$STATUS_PLUGIN")"
    printf '  "commands_link": "%s",\n' "$(json_token "$STATUS_COMMANDS")"
    printf '  "reasons": {\n'
    printf '    "shared_bootstrap": "%s",\n' "$(json_token "$REASON_SHARED")"
    printf '    "hooks": "%s",\n' "$(json_token "$REASON_HOOKS")"
    printf '    "plugin": "%s",\n' "$(json_token "$REASON_PLUGIN")"
    printf '    "commands_link": "%s"\n' "$(json_token "$REASON_COMMANDS")"
    printf '  }\n'
    printf '}\n'
  } >"$RECEIPT" 2>/dev/null || true
  say "cursor-install: receipt -> $RECEIPT ($state)"
}

# --- 1) shared bootstrap (the brain; never reimplement it here) ---------------
STAGE="shared-bootstrap"
SHARED="$GOV_DIR/ops/scripts/bootstrap_agent_environment.sh"
if [ "${L9_CURSOR_SKIP_SHARED_BOOTSTRAP:-0}" = "1" ]; then
  # Receipt-contract tests only. The receipt says UNKNOWN — honesty over green.
  STATUS_SHARED="UNKNOWN"; REASON_SHARED="skipped by L9_CURSOR_SKIP_SHARED_BOOTSTRAP=1"
elif [ -f "$SHARED" ]; then
  SHARED_ARGS=(--surface cursor --governance "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && SHARED_ARGS+=(--check)
  [ "$QUIET" = "1" ] && SHARED_ARGS+=(--quiet)
  bash "$SHARED" "${SHARED_ARGS[@]}"
  shared_rc=$?
  case "$shared_rc" in
    0) STATUS_SHARED="READY" ;;
    6) STATUS_SHARED="DEGRADED"; REASON_SHARED="shared bootstrap exit 6 — usable, component(s) degraded" ;;
    *) STATUS_SHARED="BLOCKED"; REASON_SHARED="shared bootstrap exit $shared_rc" ;;
  esac
else
  STATUS_SHARED="BLOCKED"; REASON_SHARED="missing $SHARED"
fi

# --- 2) Cursor wiring (verify, never rewrite user-owned files) -----------------
STAGE="cursor-wiring"
HOOKS_JSON="$HOME/.cursor/hooks.json"
if [ -f "$HOOKS_JSON" ] && grep -q "session-start-bootstrap" "$HOOKS_JSON" 2>/dev/null; then
  STATUS_HOOKS="READY"
else
  STATUS_HOOKS="DEGRADED"
  REASON_HOOKS="~/.cursor/hooks.json missing or has no session-start-bootstrap registration (AGENTS.md §2.1)"
fi

PLUGIN_LINK="$HOME/.cursor/plugins/local/l9-governance"
if [ -e "$PLUGIN_LINK" ] && [ -f "$PLUGIN_LINK/CANONICAL_LAW.md" ]; then
  STATUS_PLUGIN="READY"
else
  STATUS_PLUGIN="DEGRADED"
  REASON_PLUGIN="$PLUGIN_LINK absent or does not resolve to a governance root"
fi

WS_REAL="$WORKSPACE"
GOV_REAL="$(cd "$GOV_DIR" && pwd -P)"
SSOT_REAL="$(cd "$HOME/.cursor-governance" 2>/dev/null && pwd -P || echo "")"
if [ "$WS_REAL" = "$GOV_REAL" ] || { [ -n "$SSOT_REAL" ] && [ "$WS_REAL" = "$SSOT_REAL" ]; }; then
  STATUS_COMMANDS="READY"; REASON_COMMANDS="ssot workspace — no self-alias (CANONICAL_LAW §1)"
elif [ -L "$WORKSPACE/.cursor-commands" ] && [ -f "$WORKSPACE/.cursor-commands/CANONICAL_LAW.md" ]; then
  STATUS_COMMANDS="READY"
elif [ -f "$WORKSPACE/CANONICAL_LAW.md" ] && [ -f "$WORKSPACE/AGENTS.md" ]; then
  STATUS_COMMANDS="READY"; REASON_COMMANDS="governance checkout — reference plane is the repo itself"
else
  STATUS_COMMANDS="DEGRADED"
  REASON_COMMANDS="no .cursor-commands symlink; run ops/scripts/setup_workspace_symlinks.sh from the workspace"
fi

# --- verdict + receipt ---------------------------------------------------------
STAGE="complete"
STATE="READY"; RC=0
for status in "$STATUS_SHARED" "$STATUS_HOOKS" "$STATUS_PLUGIN" "$STATUS_COMMANDS"; do
  case "$status" in
    BLOCKED) STATE="FAILED"; RC=1 ;;
    DEGRADED|UNKNOWN) [ "$STATE" = "READY" ] && { STATE="DEGRADED"; RC=6; } ;;
  esac
done
write_receipt "$STATE"
say "cursor-install: $STATE (shared=$STATUS_SHARED hooks=$STATUS_HOOKS plugin=$STATUS_PLUGIN commands=$STATUS_COMMANDS)"
exit "$RC"
