#!/usr/bin/env bash
# sessionStart bootstrap — works before repo symlinks exist.
# Foreground-activates GitHub-tip governance (governance_activate_fresh.sh), then
# wires runtime probes + Graphiti hydrate into a sectioned L9 session state report.
# Resume SSOT is Graphiti only (no memory-bank). Exit 0 always.
# Installed as a REAL file at ~/.cursor/hooks/session-start-bootstrap.sh (not a symlink).
set -uo pipefail

REPO="${CURSOR_PROJECT_DIR:-}"

# Slow reconcilers (plugins, IDE, cold venv) are backgrounded during sessionStart.
# Manual `make start` sets L9_BOOTSTRAP_SYNC=1 to run them in the foreground.
BOOTSTRAP_SYNC="${L9_BOOTSTRAP_SYNC:-0}"

# Reconcilers write into the workspace (.vscode/settings.json, .claude/, the
# AGENTS.md formatter block). Writing while `make pr` runs lands the change
# inside some pre-commit hook's window, and pre-commit then reports "files were
# modified by this hook" against a hook that never wrote anything. Yield to the
# repo-write lock instead; activation reconciles again next session.
_reconciler_guarded() {
  local lib="${GC:-$HOME/.cursor-governance}/ops/scripts/lib/repo_write_lock.sh"
  local ws="${REPO:-$PWD}" rc=0
  if [ ! -f "$lib" ]; then
    "$@"
    return $?
  fi
  # shellcheck source=/dev/null
  . "$lib"
  export L9_REPO_WRITE_LOCK_LABEL="sessionStart-reconciler"
  if repo_write_lock_acquire "$ws" "${L9_RECONCILER_LOCK_WAIT_S:-45}"; then
    "$@"
    rc=$?
    repo_write_lock_release
    return $rc
  fi
  echo "L9: reconciler skipped ($(repo_write_lock_skip_note "$ws")): $*" >&2
  return 0
}

run_reconciler() {
  if [ "$BOOTSTRAP_SYNC" = "1" ]; then
    _reconciler_guarded "$@" >&2 || true
  else
    ( _reconciler_guarded "$@" >/dev/null 2>&1 & )
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
- pipeline audit: skipped (no SSOT)
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

# Generic hydration (uv, scratch_hold, checkers, capabilities, identity) lives
# only in the shared bootstrap. Cursor keeps tip activation, wiring, hydrate,
# plan audit, and the additional_context JSON envelope.
SHARED_BOOTSTRAP="$GC/ops/scripts/bootstrap_agent_environment.sh"
if [ -f "$SHARED_BOOTSTRAP" ]; then
  # F-10: the surface is a runtime fact, not a constant. Hard-coding `cursor`
  # mis-attributed every warning, receipt and identity check on every other
  # surface, and wrote a phantom Cursor readiness receipt during a Claude Code
  # bootstrap. Default stays `cursor` for a genuine Cursor session with no
  # variable set.
  bash "$SHARED_BOOTSTRAP" \
    --surface "${L9_GOVERNANCE_SURFACE:-cursor}" \
    --governance "$GC" \
    --workspace "${REPO:-$PWD}" \
    --quiet || true
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

# Claude projection is Claude Code SessionStart's job
# (session_start_claude_governance.sh). Running it from Cursor SessionStart
# wrote readiness receipts against the wrong workspace and mixed Claude cloud
# scoring into this report. Do not call claude_projection.py here.

# venv: shared bootstrap owns uv sync; report the result only
VENV_NOTE="absent"
if [[ -x "$GC/.venv/bin/python3" ]]; then
  export PATH="$GC/.venv/bin:$PATH"
  VENV_NOTE="locked (uv.lock)"
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

# Pipeline audit: fail-open, budget-capped; never fail sessionStart.
# Heading stays ### Plan audit (bootstrap tests). Store is tracked docs/plans
# via .cursor/plans → ~/.cursor/plans. Also scans WIP + PE campaigns.
# Archives spent root plans and inventory-landed WIP only; mixed harvestable
# donors stay. Never mutates CAMPAIGN_SOURCE.yaml. No auto-Build.
PLAN_AUDIT_MD="pipeline audit: skipped"
AUDIT_PY="$GC/skills/l9-pipeline-audit/scripts/audit_pipeline.py"
if [ ! -f "$AUDIT_PY" ]; then
  _ws_audit="${CURSOR_PROJECT_DIR:-$PWD}/skills/l9-pipeline-audit/scripts/audit_pipeline.py"
  if [ -f "$_ws_audit" ]; then
    AUDIT_PY="$_ws_audit"
  fi
fi
AUDIT_PY_BIN="$GC/.venv/bin/python"
[ -x "$AUDIT_PY_BIN" ] || AUDIT_PY_BIN=python3
# Archive gating lives in audit_pipeline.py (acquires the $GC write lock).
ARCHIVE_ARGS=(--archive-spent)
if [ -f "$AUDIT_PY" ]; then
  if command -v timeout >/dev/null 2>&1; then
    PLAN_AUDIT_MD="$(
      timeout 4 "$AUDIT_PY_BIN" "$AUDIT_PY" \
        --workspace "${CURSOR_PROJECT_DIR:-$PWD}" \
        --gov-root "$GC" \
        --window-days 7 \
        --format session-start \
        --budget-chars 1600 \
        "${ARCHIVE_ARGS[@]}" \
        2>/dev/null || echo "pipeline audit: unavailable"
    )"
  else
    PLAN_AUDIT_MD="$(
      "$AUDIT_PY_BIN" "$AUDIT_PY" \
        --workspace "${CURSOR_PROJECT_DIR:-$PWD}" \
        --gov-root "$GC" \
        --window-days 7 \
        --format session-start \
        --budget-chars 1600 \
        "${ARCHIVE_ARGS[@]}" \
        2>/dev/null || echo "pipeline audit: unavailable"
    )"
  fi
  [ -n "$PLAN_AUDIT_MD" ] || PLAN_AUDIT_MD="pipeline audit: unavailable"
fi

# T-CI007 / T-CI015 / T-CI021 / T-CI022 — live Cursor SessionStart caller (U2).
GRANT_NOTE="publish-path grant: none"
if [ -f "$GC/ops/autonomy/breakglass_receipt.py" ]; then
  GRANT_NOTE="$("$AUDIT_PY_BIN" "$GC/ops/autonomy/breakglass_receipt.py" --status 2>/dev/null || echo "publish-path grant: unread")"
fi
TWO_CLONE_NOTE=""
WS_ROOT="${CURSOR_PROJECT_DIR:-$PWD}"
if git -C "$WS_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ws_abs=$(cd "$(git -C "$WS_ROOT" rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null && pwd -P)
  gov_abs=$(cd "$GC" 2>/dev/null && pwd -P)
  if [ -n "$ws_abs" ] && [ -n "$gov_abs" ] && [ "$ws_abs" != "$gov_abs" ]; then
    ws_sha=$(git -C "$ws_abs" rev-parse --short HEAD 2>/dev/null || echo "?")
    gov_sha=$(git -C "$GC" rev-parse --short HEAD 2>/dev/null || echo "?")
    if [ -f "$ws_abs/CANONICAL_LAW.md" ] && [ -f "$ws_abs/AGENTS.md" ]; then
      clone_kind="intentional consumer checkout of Cursor-Governance"
    else
      clone_kind="leftover or unknown second checkout"
    fi
    TWO_CLONE_NOTE=$(printf '%s\n' \
      "- two-clone: workspace $ws_abs @$ws_sha ($clone_kind)" \
      "- two-clone: live SSOT $gov_abs @$gov_sha" \
      "- two-clone: rules resolve from live SSOT (not the workspace clone)")
  fi
fi
SKILL_LOG="$HOME/.claude/l9/skill-usage.jsonl"
if [ -f "$SKILL_LOG" ]; then
  SKILL_NOTE="skill-usage: $SKILL_LOG ($(wc -l < "$SKILL_LOG" | tr -d ' ') entries)"
else
  SKILL_NOTE="skill-usage: $SKILL_LOG (absent — logger never wrote)"
fi
ITEST_NOTE="itest: neo4j 127.0.0.1:7687 reachable — service-backed integration tests may run"
if ! "$AUDIT_PY_BIN" -c 'import socket;s=socket.socket();s.settimeout(0.3);s.connect(("127.0.0.1",7687));s.close()' 2>/dev/null; then
  ITEST_NOTE="itest: unavailable — neo4j absent or 127.0.0.1:7687 refused"
fi
BOOTSTRAP_NOTE=""
if [ -f "$GC/ops/scripts/claude_bootstrap_receipt.py" ]; then
  BOOTSTRAP_NOTE="$("$AUDIT_PY_BIN" "$GC/ops/scripts/claude_bootstrap_receipt.py" --read --reprobe 2>/dev/null | head -n 20 || true)"
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
${TWO_CLONE_NOTE}
### Runtime
- venv: ${VENV_NOTE}
- ide-profile: ${IDE_NOTE}
- tunnel: ${TUNNEL_NOTE}
- graphiti health: ${GRAPHITI_HEALTH}
- ${GRANT_NOTE}
- ${SKILL_NOTE}
- ${ITEST_NOTE}
${BOOTSTRAP_NOTE:+- bootstrap:}${BOOTSTRAP_NOTE:+
}${BOOTSTRAP_NOTE}
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
