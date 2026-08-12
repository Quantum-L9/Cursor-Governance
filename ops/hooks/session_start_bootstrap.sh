#!/usr/bin/env bash
# sessionStart bootstrap — works before repo symlinks exist.
# Foreground-activates GitHub-tip governance (governance_activate_fresh.sh), then
# wires runtime probes + Graphiti hydrate into a sectioned L9 session state report.
# Resume SSOT is Graphiti only (no memory-bank). Exit 0 always.
# Installed as a REAL file at ~/.cursor/hooks/session-start-bootstrap.sh (not a symlink).
set -uo pipefail

REPO="${CURSOR_PROJECT_DIR:-}"

# Prefer native Claude Code (~/.local/bin) over a stale npm-global binary so
# marketplace schema stays compatible with plugin reconcile.
if [ -x "$HOME/.local/bin/claude" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# Slow reconcilers (plugins, IDE, cold venv) are backgrounded during sessionStart.
# Manual `make start` sets L9_BOOTSTRAP_SYNC=1 to run them in the foreground.
BOOTSTRAP_SYNC="${L9_BOOTSTRAP_SYNC:-0}"
run_reconciler() {
  if [ "$BOOTSTRAP_SYNC" = "1" ]; then
    "$@" >&2 || true
  else
    ( "$@" >/dev/null 2>&1 & )
  fi
}

GOVERNANCE_REMOTE="${GOVERNANCE_GITHUB_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOVERNANCE_BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"

# ── Chicken-egg: ensure activator exists, then run foreground BEFORE resolve ──
chicken_egg_minimal_clone() {
  local root="$HOME/.cursor-governance"
  if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
    return 0
  fi
  if [ -e "$root" ] && [ ! -d "$root/.git" ]; then
    return 1
  fi
  if [ ! -d "$root/.git" ]; then
    git clone --depth 1 -b "$GOVERNANCE_BRANCH" "$GOVERNANCE_REMOTE" "$root" >/dev/null 2>&1 || return 1
  fi
  return 0
}

resolve_activator() {
  local a1="$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh"
  local a2="$HOME/.cursor/hooks/governance-activate-fresh.sh"
  if [ -x "$a1" ]; then
    echo "$a1"
    return 0
  fi
  if [ -x "$a2" ]; then
    echo "$a2"
    return 0
  fi
  if chicken_egg_minimal_clone && [ -x "$a1" ]; then
    echo "$a1"
    return 0
  fi
  if [ -f "$a2" ]; then
    chmod +x "$a2" 2>/dev/null || true
    [ -x "$a2" ] && echo "$a2" && return 0
  fi
  return 1
}

ACTIVATE_ACTION="degraded"
ACTIVATE_SHA="unknown"
ACTIVATE_REMOTE_SHA="unknown"
ACTIVATE_DETAIL="activator_missing"

ACTIVATE_BIN="$(resolve_activator || true)"
if [ -n "${ACTIVATE_BIN:-}" ] && [ -x "$ACTIVATE_BIN" ]; then
  ACTIVATE_OUT="$(
    CURSOR_PROJECT_DIR="$REPO" \
    GOVERNANCE_GITHUB_REMOTE="$GOVERNANCE_REMOTE" \
    GOVERNANCE_GITHUB_BRANCH="$GOVERNANCE_BRANCH" \
    bash "$ACTIVATE_BIN" 2>/dev/null || true
  )"
  STATUS_LINE="$(printf '%s\n' "$ACTIVATE_OUT" | grep '^STATUS ' | tail -n 1 || true)"
  if [ -n "$STATUS_LINE" ]; then
    ACTIVATE_ACTION="$(echo "$STATUS_LINE" | sed -n 's/.*action=\([^ ]*\).*/\1/p')"
    ACTIVATE_SHA="$(echo "$STATUS_LINE" | sed -n 's/.*sha=\([^ ]*\).*/\1/p')"
    ACTIVATE_REMOTE_SHA="$(echo "$STATUS_LINE" | sed -n 's/.*remote_sha=\([^ ]*\).*/\1/p')"
    ACTIVATE_DETAIL="$(echo "$STATUS_LINE" | sed -n 's/.*detail=\(.*\)$/\1/p')"
  else
    ACTIVATE_DETAIL="no_status_line"
  fi
else
  chicken_egg_minimal_clone || true
  ACTIVATE_DETAIL="activator_unavailable"
fi

resolve_global_commands() {
  GLOBAL_COMMANDS=""
  local root="$HOME/.cursor-governance"
  if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
    GLOBAL_COMMANDS="$root"
    return 0
  fi
  return 1
}

short_sha() {
  local s="${1:-unknown}"
  if [ "${#s}" -ge 7 ] && [ "$s" != "unknown" ]; then
    echo "${s:0:7}"
  else
    echo "$s"
  fi
}

if ! resolve_global_commands; then
  COMBINED="$(cat <<EOF
## L9 session state
### Governance
- tip: unknown action=${ACTIVATE_ACTION} detail=${ACTIVATE_DETAIL}
- ssot: ~/.cursor-governance (missing)
- remote: origin/${GOVERNANCE_BRANCH} @ $(short_sha "$ACTIVATE_REMOTE_SHA") (unknown)
- wiring: FAIL | clone Cursor-Governance to \$HOME/.cursor-governance
### Runtime
- graphiti health: unavailable (no SSOT)
### Graphiti hydrate
- Graphiti disabled — no resume memory
### Code-graph
- skipped
### Plan audit
- plan audit: skipped (no SSOT)
EOF
)"
  COMBINED="$COMBINED" python3 - <<'PY'
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
        "GOVERNANCE_BACKUP_SKIP": os.environ.get("GOVERNANCE_BACKUP_SKIP", "0"),
    },
    "additional_context": os.environ.get("COMBINED", ""),
}))
PY
  exit 0
fi

GC="$GLOBAL_COMMANDS"

# Never-lose: restore open/.tmp legacy holds into the active workspace.
if [[ -n "${REPO:-}" && -f "$GC/ops/scripts/scratch_hold.py" ]]; then
  python3 "$GC/ops/scripts/scratch_hold.py" --workspace "$REPO" restore --all >/dev/null 2>&1 || true
fi

# Self-heal installed bootstrap + activator sidecar from tip SSOT
if [ -f "$GC/ops/hooks/session_start_bootstrap.sh" ]; then
  cp -f "$GC/ops/hooks/session_start_bootstrap.sh" "$HOME/.cursor/hooks/session-start-bootstrap.sh" 2>/dev/null || true
  chmod +x "$HOME/.cursor/hooks/session-start-bootstrap.sh" 2>/dev/null || true
fi
if [ -f "$GC/ops/scripts/governance_activate_fresh.sh" ]; then
  mkdir -p "$HOME/.cursor/hooks" 2>/dev/null || true
  cp -f "$GC/ops/scripts/governance_activate_fresh.sh" "$HOME/.cursor/hooks/governance-activate-fresh.sh" 2>/dev/null || true
  chmod +x "$HOME/.cursor/hooks/governance-activate-fresh.sh" 2>/dev/null || true
fi

# Build-in-progress kill switch
if [ -e "$GC/.governance-build-lock" ]; then
  export GOVERNANCE_BACKUP_SKIP=1
  BACKUP_NOTE="SKIPPED — .governance-build-lock present"
else
  BACKUP_NOTE="armed"
fi

SETUP="$GC/ops/scripts/setup_workspace_symlinks.sh"
ORCH="$GC/ops/hooks/session_start_memory_orchestrator.sh"
GRAPHITI_CLI="$GC/ops/graphiti/graphiti_memory_client.py"

# Background plugins only (activate already ran foreground)
PLUGIN_SETUP="$GC/ops/scripts/setup_claude_code_plugins.sh"
if [ -x "$PLUGIN_SETUP" ]; then
  if [ -n "$REPO" ]; then
    run_reconciler bash "$PLUGIN_SETUP" --quiet --workspace "$REPO"
  else
    run_reconciler bash "$PLUGIN_SETUP" --quiet
  fi
fi

# venv: sync warm path sync; cold build backgrounded
VENV_NOTE="absent"
if command -v uv >/dev/null 2>&1 && [[ -f "$GC/uv.lock" ]]; then
  if [[ -x "$GC/.venv/bin/python3" ]]; then
    if ( cd "$GC" && uv sync --locked --extra dev --no-build >/dev/null 2>&1 ); then
      export PATH="$GC/.venv/bin:$PATH"
      VENV_NOTE="locked (uv.lock)"
    else
      VENV_NOTE="uv sync --locked failed — run: cd \"$GC\" && uv sync --extra dev"
    fi
  else
    run_reconciler bash -c "cd \"$GC\" && uv sync --locked --extra dev --no-build"
    VENV_NOTE="not yet built — background sync started; run 'make venv' in $GC for foreground + wait"
  fi
fi

# IDE profile backgrounded
IDE_NOTE="skipped"
IDE_SETUP="$GC/ops/scripts/install_ide_profile.sh"
if [ -x "$IDE_SETUP" ] && [ -n "$REPO" ]; then
  run_reconciler bash "$IDE_SETUP" --quiet "$REPO"
  if [ -f "$REPO/.vscode/.l9-ide-desired-hash" ]; then
    IDE_NOTE="applied ($(basename "$REPO"))"
  else
    IDE_NOTE="reconciling (first run)"
  fi
fi

# Auto-wire consumer (includes .cursor/plans); never require SSOT self-alias
needs_wire=0
if [ -n "$REPO" ]; then
  WS_REAL="$(python3 -c "import os; print(os.path.realpath('$REPO'))" 2>/dev/null || echo "")"
  GC_REAL="$(python3 -c "import os; print(os.path.realpath('$GC'))" 2>/dev/null || echo "")"
  if [ -n "$WS_REAL" ] && [ "$WS_REAL" = "$GC_REAL" ]; then
    # SSOT workspace: heal plans + plugin only; remove self-alias if present
    rm -f "$REPO/.cursor-commands" 2>/dev/null || true
    for check in "$HOME/.cursor/plugins/local/l9-governance" "$REPO/.cursor/plans"; do
      if [ ! -L "$check" ]; then
        needs_wire=1
        break
      fi
    done
  else
    for check in "$REPO/.cursor-commands" "$HOME/.cursor/plugins/local/l9-governance" "$REPO/.cursor/plans"; do
      if [ ! -L "$check" ]; then
        needs_wire=1
        break
      fi
    done
  fi
fi

WIRE_NOTE="symlinks OK"
if [ "$needs_wire" -eq 1 ] && [ -n "$REPO" ] && [ -f "$SETUP" ]; then
  if (cd "$REPO" && bash "$SETUP" >/dev/null 2>&1); then
    WIRE_NOTE="auto-wired symlinks"
  else
    WIRE_NOTE="auto-wire failed — run: bash \"$SETUP\""
  fi
fi

PLUGIN_STAMP="$HOME/.claude/plugins/.l9-plugin-desired-hash"
if command -v claude >/dev/null 2>&1; then
  if [ -f "$PLUGIN_STAMP" ]; then
    PLUGIN_NOTE="desired-state stamped"
  else
    PLUGIN_NOTE="reconciling (background)"
  fi
else
  PLUGIN_NOTE="claude CLI not on PATH"
fi

# Graphiti env + tunnel + health (no memory-bank)
# shellcheck source=/dev/null
[ -f "$GC/ops/hooks/graphiti_common.sh" ] && source "$GC/ops/hooks/graphiti_common.sh"
graphiti_load_env 2>/dev/null || true

TUNNEL_NOTE="skipped"
ENSURE_TUNNEL="$GC/ops/hooks/ensure_graphiti_tunnel.sh"
if [ -f "$ENSURE_TUNNEL" ]; then
  TUNNEL_NOTE="$(bash "$ENSURE_TUNNEL" 2>/dev/null || echo "tunnel: ensure failed")"
fi

GRAPHITI_HEALTH="disabled or CLI missing"
if [ "${GRAPHITI_MEMORY_ENABLED:-1}" != "0" ] && [ -f "$GRAPHITI_CLI" ]; then
  if [ -x "$GC/.venv/bin/python3" ]; then
    GPY="$GC/.venv/bin/python3"
  else
    GPY="python3"
  fi
  HEALTH_JSON="$("$GPY" "$GRAPHITI_CLI" health 2>/dev/null || echo '{"healthy":false}')"
  HEALTH_OK="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; print(json.load(sys.stdin).get('healthy',False))" 2>/dev/null || echo False)"
  LIVENESS_OK="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('liveness_ok', False))" 2>/dev/null || echo False)"
  if [ "$HEALTH_OK" = "True" ]; then
    GRAPHITI_HEALTH="healthy"
  elif [ "$LIVENESS_OK" = "True" ]; then
    GRAPHITI_HEALTH="tunnel up (MCP tools degraded — check VPS / graphiti-mcp-token)"
  else
    REASON="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('degraded') or d.get('liveness_error') or d.get('reason') or 'unreachable')" 2>/dev/null || echo unreachable)"
    GRAPHITI_HEALTH="$REASON"
  fi
fi

WIRING_CHECK="skipped"
if [ -n "$REPO" ] && [ -f "$GC/ops/scripts/check_governance_wiring.sh" ]; then
  if bash "$GC/ops/scripts/check_governance_wiring.sh" "$REPO" >/dev/null 2>&1; then
    WIRING_CHECK="PASS"
  else
    WIRING_CHECK="FAIL — run bash \"$GC/ops/scripts/wire_governance_workspace.sh\" \"$REPO\""
  fi
fi

# Self-link status on SSOT
SELF_LINK="absent"
if [ -L "$GC/.cursor-commands" ]; then
  SELF_LINK="PRESENT (should remove)"
elif [ -e "$GC/.cursor-commands" ]; then
  SELF_LINK="PRESENT (non-symlink)"
fi

CC_TARGET="n/a"
if [ -n "$REPO" ] && [ -L "$REPO/.cursor-commands" ]; then
  CC_TARGET="$(python3 -c "import os; print(os.path.realpath('$REPO/.cursor-commands'))" 2>/dev/null || echo "?")"
elif [ -n "$REPO" ]; then
  WS_REAL="$(python3 -c "import os; print(os.path.realpath('$REPO'))" 2>/dev/null || echo "")"
  GC_REAL="$(python3 -c "import os; print(os.path.realpath('$GC'))" 2>/dev/null || echo "")"
  if [ "$WS_REAL" = "$GC_REAL" ]; then
    CC_TARGET="(SSOT — no self-alias)"
  else
    CC_TARGET="missing"
  fi
fi

REMOTE_MATCH="unknown"
if [ -n "$ACTIVATE_SHA" ] && [ -n "$ACTIVATE_REMOTE_SHA" ] \
  && [ "$ACTIVATE_SHA" != "unknown" ] && [ "$ACTIVATE_REMOTE_SHA" != "unknown" ]; then
  if [ "$ACTIVATE_SHA" = "$ACTIVATE_REMOTE_SHA" ]; then
    REMOTE_MATCH="match"
  else
    REMOTE_MATCH="behind_or_diverged"
  fi
fi

# Orchestrator: hydrate + code-graph as structured fields
HYDRATE_MD="Graphiti disabled — no resume memory"
CODEGRAPH_MD="skipped"
if [ -f "$ORCH" ]; then
  ORCH_OUT="$(bash "$ORCH" 2>/dev/null || echo '{}')"
  eval "$(echo "$ORCH_OUT" | python3 -c '
import sys, json, shlex
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
hm = d.get("hydrate_markdown") or d.get("additional_context") or "Graphiti disabled — no resume memory"
cm = d.get("codegraph_markdown") or "skipped"
print("HYDRATE_MD=" + shlex.quote(str(hm)))
print("CODEGRAPH_MD=" + shlex.quote(str(cm)))
' 2>/dev/null || true)"
fi

GOV_HEAD="$(short_sha "$ACTIVATE_SHA")"
REMOTE_HEAD="$(short_sha "$ACTIVATE_REMOTE_SHA")"

# Plan audit: fail-open, budget-capped; never fail sessionStart.
PLAN_AUDIT_MD="plan audit: skipped"
AUDIT_PY="$GC/skills/l9-plan-audit/scripts/audit_plans.py"
# Prefer SSOT; fall back to open workspace when developing ahead of tip sync.
if [ ! -f "$AUDIT_PY" ]; then
  _ws_audit="${CURSOR_PROJECT_DIR:-$PWD}/skills/l9-plan-audit/scripts/audit_plans.py"
  if [ -f "$_ws_audit" ]; then
    AUDIT_PY="$_ws_audit"
  fi
fi
if [ -f "$AUDIT_PY" ]; then
  if command -v timeout >/dev/null 2>&1; then
    PLAN_AUDIT_MD="$(
      timeout 2 python3 "$AUDIT_PY" \
        --workspace "${CURSOR_PROJECT_DIR:-$PWD}" \
        --window-days 7 \
        --format markdown \
        --budget-chars 1200 \
        --limit 5 \
        --deadline-seconds 1.5 \
        2>/dev/null || echo "plan audit: unavailable"
    )"
  else
    PLAN_AUDIT_MD="$(
      python3 "$AUDIT_PY" \
        --workspace "${CURSOR_PROJECT_DIR:-$PWD}" \
        --window-days 7 \
        --format markdown \
        --budget-chars 1200 \
        --limit 5 \
        --deadline-seconds 1.5 \
        2>/dev/null || echo "plan audit: unavailable"
    )"
  fi
  [ -n "$PLAN_AUDIT_MD" ] || PLAN_AUDIT_MD="plan audit: unavailable"
fi

COMBINED="$(cat <<EOF
## L9 session state
### Governance
- tip: ${GOV_HEAD} action=${ACTIVATE_ACTION} detail=${ACTIVATE_DETAIL}
- ssot: ~/.cursor-governance
- remote: origin/${GOVERNANCE_BRANCH} @ ${REMOTE_HEAD} (${REMOTE_MATCH})
- wiring: ${WIRING_CHECK} | .cursor-commands → ${CC_TARGET}
- self-link: ${SELF_LINK}
- wire: ${WIRE_NOTE}
- backup: ${BACKUP_NOTE}
### Runtime
- venv: ${VENV_NOTE}
- ide-profile: ${IDE_NOTE}
- claude-plugins: ${PLUGIN_NOTE}
- tunnel: ${TUNNEL_NOTE}
- graphiti health: ${GRAPHITI_HEALTH}
### Graphiti hydrate
${HYDRATE_MD}
### Code-graph
${CODEGRAPH_MD}
### Plan audit
${PLAN_AUDIT_MD}
EOF
)"

COMBINED="$COMBINED" python3 - <<'PY'
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
        "GOVERNANCE_BACKUP_SKIP": os.environ.get("GOVERNANCE_BACKUP_SKIP", "0"),
    },
    "additional_context": os.environ.get("COMBINED", ""),
}))
PY

exit 0

l9_session_runtime_probe() {
  local root py
  root="${GOVERNANCE_ROOT:-${GLOBAL_COMMANDS:-$HOME/.cursor-governance}}"
  if [ -x "$root/.venv/bin/python3" ]; then py="$root/.venv/bin/python3"; else py="$(command -v python3)"; fi
  if [ -f "$root/environment/agents/deployment/reconcile.py" ]; then
    "$py" "$root/environment/agents/deployment/reconcile.py" --surface cursor --workspace "${CURSOR_PROJECT_DIR:-$PWD}" >/dev/null 2>&1 || true
  fi
  if [ -f "$root/environment/agents/readiness/probe_runtime.py" ]; then
    "$py" "$root/environment/agents/readiness/probe_runtime.py" >/dev/null 2>&1 || true
  fi
}
if [ "${L9_SESSION_RUNTIME_PROBE:-0}" = "1" ]; then
  l9_session_runtime_probe || true
fi
