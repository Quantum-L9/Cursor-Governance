#!/usr/bin/env bash
# L9-PASTE-BEGIN — the Setup script field starts at the line above (#!/usr/bin/env bash).
# ---------------------------------------------------------------------------
# L9 Claude Code cloud Setup script — startup stub (Web · Mobile · --cloud).
#
# THIS FILE CONTAINS NO BACKTICKS, DELIBERATELY. See tests/test_account_drift_and_platform_blocks.py.
#
# Paste THIS into claude.ai/code -> environment -> Setup script. Clones governance
# @ main, then execs web/setup.sh from that clone. Prefer lib/cloud_account_env.sh
# when the clone carries it; until then a compact legacy fallback runs here.
#
# Companion fields: web/environment.env.example · web/network-policy.md
# Docs: https://code.claude.com/docs/en/cloud-environments
# ---------------------------------------------------------------------------
set -uo pipefail

# --- 0) Paste-integrity guard ----------------------------------------------
_l9_self="${BASH_SOURCE[0]:-$0}"
_l9_fence="$(printf '\140\140\140')"
if [ -r "$_l9_self" ]; then
  if grep -qF "$_l9_fence" "$_l9_self"; then _l9_contaminated=1; else _l9_contaminated=0; fi
else
  if [ "${BASH_SUBSHELL:-0}" -ne 0 ]; then _l9_contaminated=1; else _l9_contaminated=0; fi
fi
unset _l9_self _l9_fence

if [ "$_l9_contaminated" -ne 0 ]; then
  printf '%s\n' \
    'L9 bootstrap FATAL: the Setup script field contains markdown fence lines.' \
    'L9 bootstrap FATAL:   Re-paste ONLY L9-PASTE-BEGIN through L9-PASTE-END — no fences.' >&2
  exit 2
fi
unset _l9_contaminated

L9_STUB_REVISION="2026-08-29.3"
export L9_STUB_REVISION

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Compact fallback until origin/main carries lib/cloud_account_env.sh (chicken-egg
# with a pasted stub ahead of merge). Must not name retired broker env vars here.
_l9_legacy_normalize() {
  export L9_GOVERNANCE_DIR="$GOV_DIR"
  export L9_GOVERNANCE_SURFACE="claude-code"
  : "${GRAPHITI_MCP_URL:=https://memory.quantumaipartners.com/graphiti/mcp}"
  export GRAPHITI_MCP_URL
  local k v
  for k in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
           INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
           GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN \
           L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
    v="${!k:-}"
    [ -n "$v" ] || continue
    [ "$v" = "proxy-injected" ] && continue
    warn "$k is PROHIBITED on this surface; unsetting"
    unset "$k"
  done
}

_l9_legacy_session_env() {
  local f="$HOME/.l9/cloud-session.env"
  mkdir -p "$(dirname "$f")"
  {
    echo "# Written by L9 setup.bootstrap.sh (legacy fallback) — do not edit."
    echo "export L9_STUB_REVISION=$(printf %q "$L9_STUB_REVISION")"
    echo "export L9_GOVERNANCE_DIR=$(printf %q "$GOV_DIR")"
    echo "export L9_GOVERNANCE_SURFACE=claude-code"
    echo "export GRAPHITI_MCP_URL=$(printf %q "${GRAPHITI_MCP_URL:-}")"
    echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
    echo "unset GRAPHITI_MCP_TOKEN INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
    echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
    echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
  } > "$f"
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    cat "$f" >> "$CLAUDE_ENV_FILE"
  else
    for p in "$HOME/.bashrc" "$HOME/.profile"; do
      [ -f "$p" ] || touch "$p"
      grep -qF 'cloud-session.env' "$p" 2>/dev/null \
        || printf '%s\n' '. "$HOME/.l9/cloud-session.env"  # L9 governed session env' >> "$p"
    done
  fi
}

# --- 1) Governance SSOT ----------------------------------------------------
GOV_DIR="$HOME/.cursor-governance"
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"

mkdir -p "$(dirname "$GOV_DIR")"
if [ -d "$GOV_DIR/.git" ]; then
  git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE" 2>/dev/null || true
  if git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" 2>/dev/null; then
    git -C "$GOV_DIR" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" 2>/dev/null \
      || git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" 2>/dev/null \
      || warn "could not reset governance clone to origin/$GOV_BRANCH"
  else
    warn "governance fetch failed — reusing existing clone (may be stale)"
  fi
else
  rm -rf "$GOV_DIR"
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR" || {
    warn "governance clone FAILED — allowlist github.com (see web/network-policy.md)"
    exit 1
  }
fi

L9_CLOUD_ENV_LIB="$GOV_DIR/environment/agents/adapters/claude-code/lib/cloud_account_env.sh"
SETUP="$GOV_DIR/environment/agents/adapters/claude-code/web/setup.sh"
if [ ! -f "$SETUP" ]; then
  warn "governance clone incomplete — missing web/setup.sh at $SETUP"
  warn "  clone HEAD: $(git -C "$GOV_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  exit 1
fi

if [ -f "$L9_CLOUD_ENV_LIB" ]; then
  # shellcheck source=../lib/cloud_account_env.sh
  source "$L9_CLOUD_ENV_LIB"
  l9_normalize_cloud_account_env
else
  warn "lib/cloud_account_env.sh not on clone yet — using bootstrap legacy normalize"
  _l9_legacy_normalize
fi

L9_GOVERNANCE_BOOTSTRAPPED=1 bash "$SETUP"
SETUP_RC=$?

if [ -f "$L9_CLOUD_ENV_LIB" ]; then
  l9_write_cloud_session_env "$SETUP_RC" || true
  l9_report_cloud_memory_posture
else
  _l9_legacy_session_env || true
  note "memory front door: ${GRAPHITI_MCP_URL:-unset} (no bearer)"
  note "capability plane: RETIRED (never shipped)"
fi

if [ "$SETUP_RC" -ne 0 ]; then
  warn "cloud bootstrap FAILED — web/setup.sh exited $SETUP_RC"
  warn "  see ~/.l9/claude/bootstrap-state.json"
  exit "$SETUP_RC"
fi
note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
exit 0
# L9-PASTE-END — the Setup script field ends at the line above (exit 0).
