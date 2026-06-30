#!/usr/bin/env bash
# sessionStart bootstrap — works before repo symlinks exist.
# Resolves GlobalCommands from $HOME/Dropbox, auto-wires governance, Graphiti health, memory prefetch.
# Installed as a REAL file at ~/.cursor/hooks/session-start-bootstrap.sh (not a symlink).
set -uo pipefail

REPO="${CURSOR_PROJECT_DIR:-}"
PARTS=()

# Auto-sync the ~/.cursor-governance SSOT clone in the background (guarded: ff-only,
# never destroys local edits, single-flight). Replaces the unsafe reset --hard pattern.
SYNC="$HOME/.cursor-governance/ops/scripts/governance_sync.sh"
[ -x "$SYNC" ] && ( "$SYNC" >/dev/null 2>&1 & )

resolve_global_commands() {
  # SSOT: ~/.cursor-governance (repo-root layout == GlobalCommands); Dropbox = transition fallback.
  GLOBAL_COMMANDS=""
  for root in "$HOME/.cursor-governance" "$HOME/Dropbox/cursor governance" "$HOME/Dropbox/Cursor Governance"; do
    if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
      GLOBAL_COMMANDS="$root"; return 0          # clone root is GlobalCommands
    elif [ -d "$root/GlobalCommands" ]; then
      GLOBAL_COMMANDS="$root/GlobalCommands"; return 0   # legacy nested layout
    fi
  done
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
SETUP="$GC/ops/scripts/setup_workspace_symlinks.sh"
ORCH="$GC/ops/hooks/session_start_memory_orchestrator.sh"
GRAPHITI_CLI="$GC/ops/graphiti/graphiti_memory_client.py"

needs_wire=0
if [ -n "$REPO" ]; then
  for check in "$REPO/.cursor-commands" "$HOME/.cursor/skills" "$HOME/.cursor/commands" "$HOME/.cursor/rules"; do
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

# Graphiti env + memory-bank scaffold
# shellcheck source=/dev/null
[ -f "$GC/ops/hooks/graphiti_common.sh" ] && source "$GC/ops/hooks/graphiti_common.sh"
graphiti_load_env 2>/dev/null || true
if [ -f "$HOME/.cursor/graphiti.env" ]; then
  # shellcheck disable=SC1090
  set -a && source "$HOME/.cursor/graphiti.env" && set +a
fi

if [ -f "$GC/ops/hooks/graphiti_common.sh" ]; then
  graphiti_scaffold_memory_bank "$REPO" 2>/dev/null || true
fi

if [ "${GRAPHITI_MEMORY_ENABLED:-1}" != "0" ] && [ -f "$GRAPHITI_CLI" ]; then
  HEALTH_JSON="$(python3 "$GRAPHITI_CLI" health 2>/dev/null || echo '{"healthy":false}')"
  HEALTH_OK="$(echo "$HEALTH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('healthy',False))" 2>/dev/null || echo False)"
  if [ "$HEALTH_OK" = "True" ]; then
    PARTS+=("graphiti: healthy")
  else
    REASON="$(echo "$HEALTH_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reason') or d.get('error') or 'degraded')" 2>/dev/null || echo degraded)"
    PARTS+=("graphiti: ${REASON} — check ~/.cursor/graphiti.env and VPS tunnel")
  fi
else
  PARTS+=("graphiti: disabled or CLI missing")
fi

if [ -n "$REPO" ] && [ -f "$REPO/memory-bank/activeContext.md" ]; then
  EXCERPT="$(head -12 "$REPO/memory-bank/activeContext.md" | tr '\n' ' ' | cut -c1-400)"
  PARTS+=("memory-bank: ${EXCERPT}")
fi

if [ -n "$REPO" ] && [ -f "$GC/ops/scripts/check_governance_wiring.sh" ]; then
  if bash "$GC/ops/scripts/check_governance_wiring.sh" "$REPO" >/dev/null 2>&1; then
    PARTS+=("wiring: PASS")
  else
    PARTS+=("wiring: FAIL — run bash \"$GC/ops/scripts/wire_governance_workspace.sh\" \"$REPO\"")
  fi
fi

# Delegate prefetch / code-graph context to full orchestrator (Dropbox path — no symlink required)
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
