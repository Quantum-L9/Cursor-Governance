#!/usr/bin/env bash
# sessionStart bootstrap — works before repo symlinks exist.
# Resolves GlobalCommands from $HOME/.cursor-governance (GitHub main clone only).
# Dropbox is never consulted. Auto-wires governance, Graphiti health, memory prefetch.
# Also publishes GOVERNANCE_BACKUP_SKIP to the rest of the hook chain when a
# .governance-build-lock marker exists in the governance clone.
# Installed as a REAL file at ~/.cursor/hooks/session-start-bootstrap.sh (not a symlink).
set -uo pipefail

REPO="${CURSOR_PROJECT_DIR:-}"
PARTS=()

# Prefer native Claude Code (~/.local/bin) over a stale npm-global binary so
# marketplace schema stays compatible with plugin reconcile.
if [ -x "$HOME/.local/bin/claude" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# Slow reconcilers (git sync, plugin install, extension install) are backgrounded and
# silenced during a real sessionStart so they can never stall or fail a session. A manual
# run (`make start`) sets L9_BOOTSTRAP_SYNC=1 to run them in the foreground with output on
# stderr, so stdout stays a clean JSON payload either way.
BOOTSTRAP_SYNC="${L9_BOOTSTRAP_SYNC:-0}"
run_reconciler() {
  if [ "$BOOTSTRAP_SYNC" = "1" ]; then
    "$@" >&2 || true
  else
    ( "$@" >/dev/null 2>&1 & )
  fi
}

# Auto-sync the ~/.cursor-governance SSOT clone (guarded: ff-only, never destroys local
# edits, single-flight). Replaces the unsafe reset --hard pattern.
SYNC="$HOME/.cursor-governance/ops/scripts/governance_sync.sh"
[ -x "$SYNC" ] && run_reconciler "$SYNC"

# Keep Claude Code plugins in sync with Cursor-Governance desired state.
# --quiet: fail-open, no `claude update`, fast no-op when stamp matches. --workspace
# is required here because sessionStart's cwd is the hooks dir, not the open
# workspace -- CURSOR_PROJECT_DIR ($REPO) is the only reliable source for the path
# that class-gated project-scope installs (environment/plugins/) need to target.
PLUGIN_SETUP="$HOME/.cursor-governance/ops/scripts/setup_claude_code_plugins.sh"
if [ -x "$PLUGIN_SETUP" ]; then
  if [ -n "$REPO" ]; then
    run_reconciler bash "$PLUGIN_SETUP" --quiet --workspace "$REPO"
  else
    run_reconciler bash "$PLUGIN_SETUP" --quiet
  fi
fi

resolve_global_commands() {
  # SSOT: $HOME/.cursor-governance only — GitHub clone of Quantum-L9/Cursor-Governance.
  # Dropbox / cloud-storage trees are never used (CANONICAL_LAW / resolve_governance_paths).
  GLOBAL_COMMANDS=""
  local root="$HOME/.cursor-governance"
  if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
    GLOBAL_COMMANDS="$root"
    return 0
  fi
  return 1
}

emit_json() {
  local combined="$1"
  python3 - <<PY
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
        "GOVERNANCE_BACKUP_SKIP": os.environ.get("GOVERNANCE_BACKUP_SKIP", "0"),
    },
    "additional_context": """${combined}""",
}))
PY
}

if ! resolve_global_commands; then
  emit_json "session bootstrap: governance root not found — clone Cursor-Governance to \$HOME/.cursor-governance"
  exit 0
fi

GC="$GLOBAL_COMMANDS"

# Build-in-progress kill switch. While the marker file exists, every sessionEnd in
# every window skips its governance backup, so a long build is never snapshotted
# half-written. backup_gate.sh returns exit 10 for this, which leaves the debounce
# stamp untouched — the first sessionEnd after the marker is removed still backs up.
#   touch "$GC/.governance-build-lock"   # arm
#   rm    "$GC/.governance-build-lock"   # disarm
if [ -e "$GC/.governance-build-lock" ]; then
  export GOVERNANCE_BACKUP_SKIP=1
  PARTS+=("backup: SKIPPED — .governance-build-lock present")
fi

SETUP="$GC/ops/scripts/setup_workspace_symlinks.sh"
ORCH="$GC/ops/hooks/session_start_memory_orchestrator.sh"
GRAPHITI_CLI="$GC/ops/graphiti/graphiti_memory_client.py"

# Recreate/refresh the pinned .venv from uv.lock and put it first on PATH for the
# rest of this hook chain. `--locked` fails loudly if pyproject.toml drifts from uv.lock.
# --extra dev keeps ruff/pytest in the SAME locked venv as runtime deps.
#
# Fast path vs. background path: when .venv already exists, a verify-only sync
# against a warm cache is sub-second, so it's safe to run synchronously and keep
# PATH correct for the rest of this hook chain. When .venv does NOT exist yet, the
# first build can take minutes on a cold uv cache (48 locked packages incl. the
# langgraph stack) — that must never block this hook's 30s budget, so it goes
# through the same `run_reconciler` backgrounding every other slow reconciler
# above uses. The next session start hits the fast path once the background sync
# finishes; `make venv` remains the way to force it in the foreground and wait.
# `--no-build` refuses source builds (no setup.py/PEP517 script execution) so a
# compromised or unexpected sdist cannot run installer code during sessionStart.
if command -v uv >/dev/null 2>&1 && [[ -f "$GC/uv.lock" ]]; then
  if [[ -x "$GC/.venv/bin/python3" ]]; then
    if ( cd "$GC" && uv sync --locked --extra dev --no-build >/dev/null 2>&1 ); then
      export PATH="$GC/.venv/bin:$PATH"
      PARTS+=("venv: locked (uv.lock)")
    else
      PARTS+=("venv: uv sync --locked failed — run: cd \"$GC\" && uv sync --extra dev")
    fi
  else
    run_reconciler bash -c "cd \"$GC\" && uv sync --locked --extra dev --no-build"
    PARTS+=("venv: not yet built — background sync started; run 'make venv' in $GC for foreground + wait")
  fi
fi

# Reconcile the Cursor IDE profile (extensions machine-wide, .vscode/settings.json
# managed-key merge in the loaded workspace). Backgrounded + --quiet: extension
# installs are slow and must never block or fail a session start.
IDE_SETUP="$GC/ops/scripts/install_ide_profile.sh"
if [ -x "$IDE_SETUP" ] && [ -n "$REPO" ]; then
  run_reconciler bash "$IDE_SETUP" --quiet "$REPO"
  if [ -f "$REPO/.vscode/.l9-ide-desired-hash" ]; then
    PARTS+=("ide-profile: applied ($(basename "$REPO"))")
  else
    PARTS+=("ide-profile: reconciling (first run)")
  fi
fi

# Excerpt files from the *loaded workspace* memory-bank (CURSOR_PROJECT_DIR), never from
# the Cursor-Governance clone. Skip missing files; keep excerpts short for hook payload.
append_repo_memory_bank() {
  local repo="$1"
  local bank="$repo/memory-bank"
  local f excerpt
  if [ -z "$repo" ] || [ ! -d "$bank" ]; then
    PARTS+=("memory-bank: absent in workspace (wire/scaffold via setup_workspace_symlinks)")
    return 0
  fi
  PARTS+=("memory-bank repo=$(basename "$repo")")
  for f in activeContext.md SESSION_HANDOFF.md progress.md tasks.md tech-debt.md; do
    if [ -f "$bank/$f" ]; then
      excerpt="$(head -20 "$bank/$f" | tr '\n' ' ' | cut -c1-500)"
      PARTS+=("memory-bank/$f: ${excerpt}")
    fi
  done
}

needs_wire=0
if [ -n "$REPO" ]; then
  # Governance loads as a Cursor local plugin (rules/84-cursor-governance-wiring.mdc
  # v3.0.0), not as ~/.cursor/{rules,skills,commands} whole-directory symlinks.
  for check in "$REPO/.cursor-commands" "$HOME/.cursor/plugins/local/l9-governance"; do
    if [ ! -L "$check" ]; then
      needs_wire=1
      break
    fi
  done
fi

if [ "$needs_wire" -eq 1 ] && [ -n "$REPO" ] && [ -f "$SETUP" ]; then
  if (cd "$REPO" && bash "$SETUP" >/dev/null 2>&1); then
    PARTS+=("governance: auto-wired symlinks")
  else
    PARTS+=("governance: auto-wire failed — run: bash \"$SETUP\"")
  fi
else
  PARTS+=("governance: symlinks OK")
fi

# Status line for Claude Code plugins (install itself already backgrounded above)
PLUGIN_STAMP="$HOME/.claude/plugins/.l9-plugin-desired-hash"
if command -v claude >/dev/null 2>&1; then
  if [ -f "$PLUGIN_STAMP" ]; then
    PARTS+=("claude-plugins: desired-state stamped")
  else
    PARTS+=("claude-plugins: reconciling (background)")
  fi
else
  PARTS+=("claude-plugins: claude CLI not on PATH")
fi

# Graphiti env (defaults → machine → secrets → keychain) + memory-bank scaffold
# shellcheck source=/dev/null
[ -f "$GC/ops/hooks/graphiti_common.sh" ] && source "$GC/ops/hooks/graphiti_common.sh"
graphiti_load_env 2>/dev/null || true

if [ -f "$GC/ops/hooks/graphiti_common.sh" ]; then
  graphiti_scaffold_memory_bank "$REPO" 2>/dev/null || true
fi

# Ensure Graphiti SSH tunnel before health check (defaults + keychain + .env.local C1_SSH)
ENSURE_TUNNEL="$GC/ops/hooks/ensure_graphiti_tunnel.sh"
if [ -f "$ENSURE_TUNNEL" ]; then
  TUNNEL_STATUS="$(bash "$ENSURE_TUNNEL" 2>/dev/null || echo "tunnel: ensure failed")"
  PARTS+=("$TUNNEL_STATUS")
fi

if [ "${GRAPHITI_MEMORY_ENABLED:-1}" != "0" ] && [ -f "$GRAPHITI_CLI" ]; then
  # Prefer locked venv python (PATH may already include it after uv sync above).
  if [ -x "$GC/.venv/bin/python3" ]; then
    GPY="$GC/.venv/bin/python3"
  else
    GPY="python3"
  fi
  HEALTH_JSON="$("$GPY" "$GRAPHITI_CLI" health 2>/dev/null || echo '{"healthy":false}')"
  HEALTH_OK="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; print(json.load(sys.stdin).get('healthy',False))" 2>/dev/null || echo False)"
  LIVENESS_OK="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('liveness_ok', False))" 2>/dev/null || echo False)"
  if [ "$HEALTH_OK" = "True" ]; then
    PARTS+=("graphiti: healthy")
  elif [ "$LIVENESS_OK" = "True" ]; then
    PARTS+=("graphiti: tunnel up (MCP tools degraded — check VPS / graphiti-mcp-token)")
  else
    REASON="$(echo "$HEALTH_JSON" | "$GPY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('degraded') or d.get('liveness_error') or d.get('reason') or 'unreachable')" 2>/dev/null || echo unreachable)"
    PARTS+=("graphiti: ${REASON}")
  fi
else
  PARTS+=("graphiti: disabled or CLI missing")
fi

append_repo_memory_bank "$REPO"

if [ -n "$REPO" ] && [ -f "$GC/ops/scripts/check_governance_wiring.sh" ]; then
  if bash "$GC/ops/scripts/check_governance_wiring.sh" "$REPO" >/dev/null 2>&1; then
    PARTS+=("wiring: PASS")
  else
    PARTS+=("wiring: FAIL — run bash \"$GC/ops/scripts/wire_governance_workspace.sh\" \"$REPO\"")
  fi
fi

# Delegate prefetch / code-graph context to full orchestrator (SSOT clone path)
ORCH_CTX=""
if [ -f "$ORCH" ]; then
  ORCH_OUT="$(bash "$ORCH" 2>/dev/null || echo '{}')"
  ORCH_CTX="$(echo "$ORCH_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('additional_context',''))" 2>/dev/null || true)"
  [ -n "$ORCH_CTX" ] && PARTS+=("$ORCH_CTX")
fi

COMBINED="$(printf '%s | ' "${PARTS[@]}")"
COMBINED="${COMBINED% | }"
emit_json "$COMBINED"
exit 0
