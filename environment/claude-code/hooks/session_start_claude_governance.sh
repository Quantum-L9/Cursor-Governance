#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Governance — Claude Code SessionStart bootstrap (CLI · Web · Mobile).
#
# Mobile-safe by construction: git-tracked, no ~/.cursor dependency, no editor
# machine state. Locates the governance clone, surfaces resume context, compiles
# bounded-autonomy campaign state, and emits a Claude Code SessionStart
# `additionalContext` JSON blob on stdout.
#
# Registered from .claude/settings.json (see settings.template.json). Copy this
# file to <consumer-repo>/.claude/hooks/ and COMMIT it — on Claude Code Web and
# Mobile only committed files survive the clone into the sandbox.
#
# Contract: FAIL-OPEN. A hook must never block a session. Every failure degrades
# to a smaller context blob; the script always exits 0.
# ---------------------------------------------------------------------------
set -uo pipefail

# --- Resolve governance: GitHub main clone only (Linux sandbox-safe) --------
# Canonical path is $HOME/.cursor-governance (materialized by web/setup.sh from
# https://github.com/Quantum-L9/Cursor-Governance @ main). Other L9_GOVERNANCE_DIR
# values are ignored so a host IDE path cannot hijack the session.
resolve_governance_dir() {
  local d="$HOME/.cursor-governance"
  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$d" ]; then
    : # ignored — Web/Mobile / CLI shared contract is always $HOME/.cursor-governance
  fi
  [ -f "$d/CANONICAL_LAW.md" ] && { printf '%s' "$d"; return 0; }
  return 1
}

# --- JSON string escaper (no jq dependency on a fresh sandbox) --------------
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
  # $1 = plain-text context; wrap it in the SessionStart hook envelope.
  local ctx
  ctx=$(json_escape "$1")
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
  exit 0
}

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
LINES=()
LINES+=("L9 Governance — Claude Code session")
LINES+=("workspace: $WORKSPACE")

if GOV=$(resolve_governance_dir); then
  LINES+=("governance SSOT: $GOV (GitHub Quantum-L9/Cursor-Governance)")
  if [ -d "$GOV/.git" ]; then
    br=$(git -C "$GOV" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
    LINES+=("governance rev: ${br}@${sha}")
    if [ "$br" != "main" ]; then
      LINES+=("WARN: governance clone is not on main — web/setup.sh should sync origin/main")
    fi
  fi
  LINES+=("authority order: CANONICAL_LAW.md > AGENTS.md > skills/*/SKILL.md > this context")
  if [ -d "$GOV/skills" ]; then
    n=$(find "$GOV/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    LINES+=("skills available: $n l9-* skills under \$GOV/skills (invoke by name)")
  fi

  # --- Bounded-autonomy campaign context (fail-open; read-only probe) --------
  # Reconstructs any active campaign's next dependency-ready action set so a
  # resumed session continues without re-planning. bootstrap.py never blocks:
  # it swallows its own errors and the `|| true` guards a missing interpreter.
  AUTONOMY_BOOTSTRAP="$GOV/environment/claude-code/autonomy/bootstrap.py"
  if [ -f "$AUTONOMY_BOOTSTRAP" ] && command -v python3 >/dev/null 2>&1; then
    AUTONOMY_CONTEXT=$(python3 "$AUTONOMY_BOOTSTRAP" --workspace "$WORKSPACE" 2>/dev/null || true)
    [ -n "$AUTONOMY_CONTEXT" ] && LINES+=("--- bounded autonomy ---" "$AUTONOMY_CONTEXT")
  else
    LINES+=("bounded autonomy: runtime unavailable; continue under base governance")
  fi
else
  LINES+=("governance SSOT: NOT FOUND — web/setup.sh must clone GitHub main to \$HOME/.cursor-governance")
  LINES+=("remote: https://github.com/Quantum-L9/Cursor-Governance (branch main)")
fi

# --- T0 resume context: memory-bank/activeContext.md in the workspace -------
ACTIVE="$WORKSPACE/memory-bank/activeContext.md"
if [ -f "$ACTIVE" ]; then
  EXCERPT=$(head -c 1200 "$ACTIVE" 2>/dev/null || true)
  [ -n "$EXCERPT" ] && LINES+=("--- resume context (memory-bank/activeContext.md) ---" "$EXCERPT")
fi

# --- Shared memory reachability hint (no secrets read/printed) ---------------
if [ -n "${L9_MEMORY_HTTP_URL:-}" ]; then
  LINES+=("shared memory: L9_MEMORY_HTTP_URL set — l9-shared-memory MCP expected (see mcp.template.json)")
fi

CONTEXT=$(printf '%s\n' "${LINES[@]}")
emit "$CONTEXT"
