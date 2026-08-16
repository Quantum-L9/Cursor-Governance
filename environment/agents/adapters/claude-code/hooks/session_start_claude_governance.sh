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

# The SessionStart event on stdin carries the session id. It is the only place
# this surface exposes it: the shared bootstrap runs before a session exists and
# cannot know it, so without this step every Claude Code session's readiness
# receipt records session.identity as UNKNOWN — and Program Execution refuses to
# mutate from a runtime it cannot attribute. Read it defensively; a hook must
# never block on stdin, and must never write to stdout except the final JSON.
EVENT=""
if [ ! -t 0 ]; then
  EVENT=$(timeout 2 cat 2>/dev/null || true)
fi
SESSION_ID=$(printf '%s' "$EVENT" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

LINES=()
LINES+=("L9 Governance — Claude Code session")
LINES+=("workspace: $WORKSPACE")

if GOV=$(resolve_governance_dir); then
  LINES+=("governance SSOT: $GOV (GitHub Quantum-L9/Cursor-Governance)")
  if [ -d "$GOV/.git" ]; then
    br=$(git -C "$GOV" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
    LINES+=("governance rev: ${br}@${sha}")
    if [ "$br" != "main" ] && [ "$br" != "autonomy-surface-parity" ]; then
      LINES+=("WARN: governance clone is not on main — web/setup.sh should sync origin/main")
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

  # --- Runtime readiness: stamp this session's identity onto the receipt ------
  # Restamp only: the bootstrap's observed degraded tally and revisions carry
  # over verbatim, so this resolves WHO is executing without ever upgrading a
  # degraded runtime to READY.
  RECEIPT_WRITER="$GOV/ops/scripts/write_runtime_readiness_receipt.py"
  if [ -n "$SESSION_ID" ] && [ -f "$RECEIPT_WRITER" ]; then
    if "$PY" "$RECEIPT_WRITER" \
      --surface "${L9_GOVERNANCE_SURFACE:-claude-code}" \
      --workspace "$WORKSPACE" \
      --governance "$GOV" \
      --session-id "$SESSION_ID" \
      --restamp-session >/dev/null 2>&1; then
      LINES+=("runtime readiness: session identity recorded ($SESSION_ID)")
    else
      LINES+=("runtime readiness: identity stamp failed — PE will refuse mutating execution")
    fi
  elif [ -z "$SESSION_ID" ]; then
    LINES+=("runtime readiness: no session id in SessionStart event — PE mutation stays blocked")
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
LINES+=("shared memory: Cursor Graphiti front door only (ops/graphiti inject / phase-lock / write); no L9_MEMORY_HTTP side door; memory-bank retired")

CONTEXT=$(printf '%s\n' "${LINES[@]}")
emit "$CONTEXT"
