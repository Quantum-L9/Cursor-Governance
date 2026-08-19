#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Governance — Claude Code SessionStart bootstrap (CLI · Web · Mobile).
#
# Mobile-safe by construction: git-tracked, no ~/.cursor dependency, no editor
# machine state. Locates the governance clone, surfaces resume context, injects
# Autonomy Surface Profile doctrine, compiles bounded-autonomy campaign state,
# and emits a Claude Code SessionStart `additionalContext` JSON blob on stdout.
#
# Registered from .claude/settings.json (see settings.template.json). Copy this
# file to <consumer-repo>/.claude/hooks/ and COMMIT it — on Claude Code Web and
# Mobile only committed files survive the clone into the sandbox.
#
# Contract: FAIL-OPEN. A hook must never block a session. Every failure degrades
# to a smaller context blob; the script always exits 0.
#
# Spec: environment/agents/adapters/claude-code/hooks/SESSION_START_SPEC.md
# Profile SSOT: ops/autonomy/surface_profile.yaml
# ---------------------------------------------------------------------------
set -uo pipefail

resolve_governance_dir() {
  local d="$HOME/.cursor-governance"
  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$d" ]; then
    : # ignored — shared contract is always $HOME/.cursor-governance
  fi
  [ -f "$d/CANONICAL_LAW.md" ] && { printf '%s' "$d"; return 0; }
  return 1
}

json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

emit() {
  local ctx
  ctx=$(json_escape "$1")
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
  exit 0
}

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
LINES=()
LINES+=("L9 Governance — Claude Code session")
LINES+=("workspace: $WORKSPACE")

# --- Cloud-only governance refresh (CLAUDE_CODE_REMOTE=true) -----------------
# Anthropic documents CLAUDE_CODE_REMOTE=true as the supported discriminator
# for cloud-session-only setup. In cloud, the governance clone is an ephemeral
# environment artifact: refresh it from origin/main so every session starts on
# the current tip, and record the exact revision. On a local developer
# checkout (CLI / Desktop) NEVER reset — inspect and report only.
CLOUD_REFRESH_LOG="$HOME/.l9/claude/gov-refresh.log"
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if GOV=$(resolve_governance_dir); then
    mkdir -p "$(dirname "$CLOUD_REFRESH_LOG")"
    GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
    GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
    if git -C "$GOV" fetch --depth 1 origin "$GOV_BRANCH" >/dev/null 2>&1; then
      if git -C "$GOV" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" >/dev/null 2>&1; then
        echo "fresh $(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo '?')" > "$CLOUD_REFRESH_LOG"
        LINES+=("governance refresh: cloud session — reset ephemeral clone to origin/$GOV_BRANCH")
      else
        echo "reset-failed $(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo '?')" > "$CLOUD_REFRESH_LOG"
        LINES+=("governance refresh: WARN reset to origin/$GOV_BRANCH failed — reusing clone")
      fi
    else
      echo "fetch-failed $(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo '?')" > "$CLOUD_REFRESH_LOG"
      LINES+=("governance refresh: WARN fetch origin/$GOV_BRANCH failed — reusing clone (may be stale)")
    fi
    # Per-session, per-repository dependency work (consumer workspace toolchain
    # + pre-commit warm) moved out of the cached account Setup script.
    DEPS_HELPER="$GOV/environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh"
    if [ -f "$DEPS_HELPER" ]; then
      DEPS_LINE=$(bash "$DEPS_HELPER" --workspace "$WORKSPACE" 2>&1 | tail -1)
      LINES+=("session deps: ${DEPS_LINE:-unknown}")
    fi
  fi
fi

if GOV=$(resolve_governance_dir); then
  LINES+=("governance SSOT: $GOV (GitHub Quantum-L9/Cursor-Governance)")
  if [ -d "$GOV/.git" ]; then
    br=$(git -C "$GOV" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
    if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
      # Local/Desktop: this is a developer checkout — SessionStart NEVER resets
      # it. Report revision and drift against origin/main instead.
      LINES+=("governance rev: ${br}@${sha} (local checkout — SessionStart never resets it)")
      if [ "$br" != "main" ]; then
        LINES+=("WARN: governance checkout is not on main (branch: $br) — drift is expected for in-flight work; report only")
      fi
      if git -C "$GOV" fetch --depth 1 origin main >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
        remote_sha=$(git -C "$GOV" rev-parse --short FETCH_HEAD 2>/dev/null || echo "?")
        if [ "$local_sha" = "$remote_sha" ]; then
          LINES+=("governance drift: none (HEAD == origin/main @$local_sha)")
        else
          LINES+=("governance drift: local @$local_sha vs origin/main @$remote_sha")
        fi
      fi
    else
      LINES+=("governance rev: ${br}@${sha}")
    fi
  fi
  LINES+=("authority order: CANONICAL_LAW.md > Autonomy Surface Profile > AGENTS.md > skills > agent-invented contracts")
  if [ -d "$GOV/skills" ]; then
    n=$(find "$GOV/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    LINES+=("skills available: $n l9-* skills under \$GOV/skills (invoke by name)")
  fi

  # --- Autonomy Surface Profile doctrine (standing A4) ---------------------
  PROFILE_LOADER="$GOV/ops/autonomy/profile_loader.py"
  if [ -x "$GOV/.venv/bin/python3" ]; then
    PY="$GOV/.venv/bin/python3"
  elif [ -x "$GOV/.venv/bin/python" ]; then
    PY="$GOV/.venv/bin/python"
  else
    PY="python3"
  fi
  if [ -f "$PROFILE_LOADER" ] && command -v "$PY" >/dev/null 2>&1; then
    PROFILE_BLOCK=$("$PY" "$PROFILE_LOADER" 2>/dev/null || true)
    if [ -n "$PROFILE_BLOCK" ]; then
      LINES+=("--- autonomy surface profile ---")
      while IFS= read -r line || [ -n "$line" ]; do
        LINES+=("$line")
      done <<< "$PROFILE_BLOCK"
    else
      LINES+=("autonomy profile: unreadable; continue under base governance")
    fi
  else
    LINES+=("autonomy profile: loader unavailable; continue under base governance")
  fi

  # --- Bounded-autonomy campaign context (fail-open; read-only probe) ------
  AUTONOMY_BOOTSTRAP="$GOV/environment/program-execution/peer_execution/autonomy/bootstrap.py"
  if [ -f "$AUTONOMY_BOOTSTRAP" ] && command -v "$PY" >/dev/null 2>&1; then
    AUTONOMY_CONTEXT=$("$PY" "$AUTONOMY_BOOTSTRAP" --workspace "$WORKSPACE" 2>/dev/null || true)
    [ -n "$AUTONOMY_CONTEXT" ] && LINES+=("--- bounded autonomy ---" "$AUTONOMY_CONTEXT")
  else
    LINES+=("bounded autonomy: runtime unavailable; continue under base governance")
  fi

  # Skill-router readiness hint
  if [ -f "$GOV/ops/generated/skill-registry.json" ]; then
    LINES+=("skill-router: ops/generated/skill-registry.json ready (UserPromptSubmit)")
  fi
else
  LINES+=("governance SSOT: NOT FOUND — web/setup.sh must clone GitHub main to \$HOME/.cursor-governance")
  LINES+=("remote: https://github.com/Quantum-L9/Cursor-Governance (branch main)")
fi

# memory-bank/ retired — resume from Graphiti inject/PICKUP only (no T0 excerpt)

# --- Memory: single front door = Cursor Graphiti (CANONICAL_LAW §8)
LINES+=("shared memory: Cursor Graphiti front door only (ops/graphiti inject / write); no L9_MEMORY_HTTP side door; memory-bank retired; memory never gates repository writes")

# --- L9 Claude environment status (from the installer receipt) --------------
# The canonical installer writes ~/.l9/claude/bootstrap-state.json
# (schema l9.claude-bootstrap.v1). Project it compactly so the model — and the
# operator on mobile — sees what is actually available instead of discovering
# bootstrap breakage when a later memory or publish operation fails.
emit_bootstrap_status() {
  local receipt="$HOME/.l9/claude/bootstrap-state.json"
  if [ ! -f "$receipt" ]; then
    LINES+=("L9 Claude environment: bootstrap receipt absent — run 'make claude-install' once")
    return 0
  fi
  local py="$1"
  if [ -n "$py" ] && command -v "$py" >/dev/null 2>&1; then
    local block
    block=$(CLAUDE_CODE_REMOTE="${CLAUDE_CODE_REMOTE:-false}" "$py" -c 'import json,sys,os
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(1)
remote = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
print("surface: %s" % d.get("surface", "?"))
print("execution: %s" % ("anthropic-cloud" if remote else "local"))
# The receipt is written at INSTALL time and never refreshed, so its revision and
# workspace can both be stale. Label the revision and compare it against live git;
# compare the wired workspace against the project dir of this session. Without these
# two lines a receipt written for another directory reports READY for artifacts that
# Claude Code never loads.
live = os.environ.get("LIVE_GOV_REV", "")
rec = d.get("governance_revision", "?") or "?"
stale = bool(live) and not rec.startswith(live)
print("governance (at install): %s%s"
      % (rec[:8], ("  STALE — live is %s" % live) if stale else ""))
ws = d.get("workspace", "?")
proj = os.environ.get("PROJECT_DIR", "") or ws
if ws != proj:
    print("WARN: bootstrap wired %s, but this project is %s — .claude mirrors may be missing"
          % (ws, proj))
print("bootstrap: %s" % d.get("shared_bootstrap", "?"))
print("settings: %s" % d.get("settings", "?"))
print("capability broker: %s" % d.get("capabilities", "?"))
# "memory" here is the BROKERED MCP plane only. The Graphiti CLI front door is
# reported separately by memory_prefetch.py and is frequently healthy while this
# reads DEGRADED. Qualify the label so the two do not contradict each other.
print("memory (brokered MCP): %s%s" % (d.get("memory", "?"),
    " — no broker-authenticated cloud identity" if d.get("memory") == "DEGRADED" else ""))
print("skills: %s" % d.get("skills", "?"))
print("rules: %s" % d.get("rules", "?"))
' "$receipt" 2>/dev/null || true)
    if [ -n "$block" ]; then
      LINES+=("--- L9 Claude environment ---")
      while IFS= read -r line || [ -n "$line" ]; do
        LINES+=("$line")
      done <<< "$block"
      return 0
    fi
  fi
  LINES+=("L9 Claude environment: receipt unreadable — see $receipt")
}

# PY was resolved above for the autonomy profile block; reuse it. LIVE_GOV_REV and
# PROJECT_DIR let the projection flag a stale receipt / a wrong wired workspace.
LIVE_GOV_REV="${sha:-}" PROJECT_DIR="$WORKSPACE" emit_bootstrap_status "$PY"

CONTEXT=$(printf '%s\n' "${LINES[@]}")
emit "$CONTEXT"
