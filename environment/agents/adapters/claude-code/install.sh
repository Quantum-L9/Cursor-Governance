#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Claude Code adapter installer — VENDOR WIRING ONLY.
#
# Everything an L9 agent session needs that is not specific to Claude Code's
# config format is owned by the shared bootstrap, which every surface calls:
#
#   ops/scripts/bootstrap_agent_environment.sh
#     1. locked toolchain from uv.lock      4. repository-scoped identity
#     2. canonical checker binaries         5. shared git excludes
#     3. secret bootstrap (ops/secrets)     6. readiness preflight
#
# Codex, Gemini, Manus and the generic adapter invoke that same script with
# their own --surface id. Nothing below may duplicate it.
#
# What is genuinely Claude-specific, and therefore lives here:
#   - the .claude settings triad          (reconcile_claude_settings.py)
#   - Claude skill discovery              (reconcile_claude_l9_skills.py)
#   - the .claude/rules LLM rules mount   (project_llm_rules.py + reconcile_llm_rule_adapters.py)
#   - the .mcp.json memory front door     (mcp.template.json)
#   - excludes for the GENERATED .claude mirrors
#
# Reached identically from every Claude surface:
#   Web / Mobile / --cloud : web/setup.bootstrap.sh -> web/setup.sh -> install.sh
#   CLI / Desktop          : make claude-install    ->               install.sh
#
# If you are adding something every agent would need, add it to the SHARED
# bootstrap, not here. This script never clones governance and never handles
# credentials — that is the surface caller's job. Idempotent; safe to re-run.
#
# Usage:
#   install.sh [--governance <dir>] [--workspace <dir>] [--check] [--quiet]
# ---------------------------------------------------------------------------
set -uo pipefail

GOV_DIR="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
WORKSPACE="$PWD"
CHECK=0
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --governance) GOV_DIR="${2:?--governance needs a path}"; shift 2 ;;
    --workspace)  WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --check)      CHECK=1; shift ;;
    --quiet)      QUIET=1; shift ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

log()  { [ "$QUIET" = "1" ] || printf '\n=== %s ===\n' "$*"; }
say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
warn() { printf 'claude-adapter WARN: %s\n' "$*" >&2; }

# An unexpanded literal '$HOME' reaches us from .env-format environment fields,
# which perform no shell expansion. Refuse it rather than creating that directory.
case "$GOV_DIR" in
  *'$HOME'*|*'${HOME}'*)
    warn "governance path '$GOV_DIR' contains an unexpanded \$HOME; using $HOME/.cursor-governance"
    GOV_DIR="$HOME/.cursor-governance"
    ;;
esac

if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  warn "no governance SSOT at $GOV_DIR — the surface caller must clone it first"
  exit 1
fi

# --- Shared agent bootstrap (identical on every surface) --------------------
SHARED_BOOTSTRAP="$GOV_DIR/ops/scripts/bootstrap_agent_environment.sh"
if [ -f "$SHARED_BOOTSTRAP" ]; then
  shared_args=(--surface claude-code --governance "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && shared_args+=(--check)
  [ "$QUIET" = "1" ] && shared_args+=(--quiet)
  bash "$SHARED_BOOTSTRAP" "${shared_args[@]}"
else
  warn "missing ops/scripts/bootstrap_agent_environment.sh — toolchain, secrets,"
  warn "  repo-scoped identity and preflight are all UNCONFIGURED"
fi

# The shared bootstrap owns the locked interpreter; reuse its result.
GOV_PY="$GOV_DIR/.venv/bin/python3"
[ -x "$GOV_PY" ] || GOV_PY="python3"

log "Claude Code vendor wiring"
say "governance=$GOV_DIR workspace=$WORKSPACE"

# --- 1) Settings triad (Claude-specific) ------------------------------------
# reconcile_claude_settings.py is the SSOT reconciler: it syncs the governance
# copy, merge-patches ~/.claude/settings.json without clobbering user keys, and
# installs the consumer workspace triad as real files. Same call on CLI, Desktop,
# Web and Mobile — never hand-roll `cp settings.template.json`.
RECONCILE_SETTINGS="$GOV_DIR/ops/scripts/reconcile_claude_settings.py"
if [ -f "$RECONCILE_SETTINGS" ]; then
  settings_args=(--root "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && settings_args+=(--check)
  python3 "$RECONCILE_SETTINGS" "${settings_args[@]}" \
    || warn "settings triad reconciliation reported drift"
else
  warn "missing ops/scripts/reconcile_claude_settings.py"
fi

# --- 2) Claude skill discovery ----------------------------------------------
RECONCILE_SKILLS="$GOV_DIR/ops/scripts/reconcile_claude_l9_skills.py"
if [ -f "$RECONCILE_SKILLS" ]; then
  skills_args=(--root "$GOV_DIR" --scope project --workspace "$WORKSPACE" --quiet)
  [ "$CHECK" = "1" ] && skills_args+=(--check)
  python3 "$RECONCILE_SKILLS" "${skills_args[@]}" \
    || warn "skill reconciliation reported drift or a local name conflict"
else
  warn "missing ops/scripts/reconcile_claude_l9_skills.py"
fi

# --- 2b) LLM rules mount (Claude .claude/rules) -----------------------------
# The generated rules (rules/*.mdc -> environment/generated/llm-rules) are the
# static governance layer every peer loads: Cursor via the l9-governance plugin,
# Claude CLI via setup_workspace_symlinks.sh. The cloud path reaches only this
# installer, so project + reconcile here too — web/mobile sessions get the same
# generated-rule mount as their CLI and Cursor peers. Both scripts import yaml,
# so run them on the locked interpreter, not the sandbox's system python3.
PROJECT_RULES="$GOV_DIR/ops/scripts/project_llm_rules.py"
RECONCILE_RULES="$GOV_DIR/ops/scripts/reconcile_llm_rule_adapters.py"
if [ -f "$PROJECT_RULES" ] && [ -f "$RECONCILE_RULES" ]; then
  if [ "$CHECK" = "1" ]; then
    "$GOV_PY" "$RECONCILE_RULES" --root "$GOV_DIR" --workspace "$WORKSPACE" --check --quiet \
      || warn "LLM rules adapter reconcile reported drift"
  else
    "$GOV_PY" "$PROJECT_RULES" --root "$GOV_DIR" --quiet \
      || warn "llm-rules projection failed (non-blocking)"
    "$GOV_PY" "$RECONCILE_RULES" --root "$GOV_DIR" --workspace "$WORKSPACE" --quiet \
      || warn "LLM rules adapter reconcile failed (non-blocking)"
  fi
else
  warn "missing ops/scripts/project_llm_rules.py or reconcile_llm_rule_adapters.py"
fi

# --- 3) Memory MCP front door (Claude .mcp.json format) ---------------------
# ADR-0006: graphiti-memory is the only memory plane. The template carries
# ${GRAPHITI_MCP_URL} / ${GRAPHITI_MCP_TOKEN} references, never a literal token.
MCP_TEMPLATE="$GOV_DIR/environment/agents/adapters/claude-code/mcp.template.json"
if [ -f "$WORKSPACE/.mcp.json" ]; then
  say ".mcp.json already present — left as the repo committed it"
elif [ "$CHECK" = "1" ]; then
  warn ".mcp.json missing (check mode: not writing)"
elif [ -f "$MCP_TEMPLATE" ]; then
  cp "$MCP_TEMPLATE" "$WORKSPACE/.mcp.json" && say "installed .mcp.json from mcp.template.json"
else
  warn "missing mcp.template.json — memory front door not wired"
fi

# --- 4) Excludes for the GENERATED .claude mirrors --------------------------
# Shared activation artifacts are excluded by the shared bootstrap; these two
# globs are Claude-specific. Only the GENERATED mirrors are excluded —
# .claude/settings.json and .claude/hooks/ are committable consumer wiring.
if [ "$CHECK" != "1" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  exclude_file="$(git -C "$WORKSPACE" rev-parse --git-dir)/info/exclude"
  case "$exclude_file" in /*) : ;; *) exclude_file="$WORKSPACE/$exclude_file" ;; esac
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for glob in ".claude/skills/" ".claude/rules/"; do
    grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >> "$exclude_file"
  done
  say "excluded generated .claude mirrors (local, uncommitted)"
fi

log "Claude Code adapter ready"
exit 0
