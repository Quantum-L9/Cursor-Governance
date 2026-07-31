#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Governance — Claude Code SessionStart bootstrap (CLI · Web · Mobile).
#
# Mobile-safe by construction: git-tracked, no ~/.cursor dependency, no editor
# machine state. Locates the governance clone, surfaces resume context, and
# emits a Claude Code SessionStart `additionalContext` JSON blob on stdout.
#
# Registered from .claude/settings.json (see settings.template.json). Copy this
# file to <consumer-repo>/.claude/hooks/ and COMMIT it — on Claude Code Web and
# Mobile only committed files survive the clone into the sandbox.
#
# Contract: FAIL-OPEN. A hook must never block a session. Every failure degrades
# to a smaller context blob; the script always exits 0.
# ---------------------------------------------------------------------------
set -uo pipefail

# --- Resolve the governance clone (no hardcoded paths) ----------------------
# Order: explicit override -> conventional CLI clone -> a clone dropped by
# web/setup.sh into $HOME. On Web/Mobile the setup script is what puts it there.
resolve_governance_dir() {
  local candidates=(
    "${L9_GOVERNANCE_DIR:-}"
    "$HOME/.cursor-governance"
    "$HOME/Cursor-Governance"
    "$HOME/l9-governance"
  )
  local d
  for d in "${candidates[@]}"; do
    [ -n "$d" ] && [ -f "$d/CANONICAL_LAW.md" ] && { printf '%s' "$d"; return 0; }
  done
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
  LINES+=("governance clone: $GOV")
  LINES+=("authority order: CANONICAL_LAW.md > AGENTS.md > skills/*/SKILL.md > this context")
  # Surface the skill index cheaply, if present.
  if [ -d "$GOV/skills" ]; then
    n=$(find "$GOV/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    LINES+=("skills available: $n l9-* skills under \$GOV/skills (invoke by name)")
  fi
else
  LINES+=("governance clone: NOT FOUND — run web/setup.sh, or set L9_GOVERNANCE_DIR.")
  LINES+=("On Web/Mobile the account 'Setup script' must clone Cursor-Governance first.")
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
