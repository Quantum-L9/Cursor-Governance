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
# HEALTH CONTRACT: every step classifies itself BLOCKED / DEGRADED / READY.
#   BLOCKED   governance SSOT absent, locked interpreter unusable, or required
#             settings wiring failed (exit code reflects it).
#   DEGRADED  optional capability unavailable, marketplace plugin unavailable,
#             memory unavailable, or an optional checker unavailable.
#   READY     required environment contract satisfied.
# The machine-readable receipt lands at ~/.l9/claude/bootstrap-state.json
# (schema l9.claude-bootstrap.v1); the SessionStart hook projects it. There is
# no unconditional "adapter ready" — the last line states the classification.
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
    -h|--help)    sed -n '2,50p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

log()  { [ "$QUIET" = "1" ] || printf '\n=== %s ===\n' "$*"; }
say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
warn() { printf 'claude-adapter WARN: %s\n' "$*" >&2; }

# --- Health accumulator ------------------------------------------------------
# Plain variables (macOS bash 3.2 has no associative arrays). A step may only
# downgrade: READY -> DEGRADED -> BLOCKED.
STATUS_SHARED="READY"; STATUS_SETTINGS="READY"; STATUS_SKILLS="READY"
STATUS_RULES="READY"; STATUS_CAPABILITIES="READY"; STATUS_MEMORY="READY"
STATUS_MCP="READY"; STATUS_PLUGINS="READY"

downgrade() { # $1=step-var-name $2=new-status $3=reason
  local name="$1" want="$2" cur="${!1}"
  # A step may only worsen: READY -> DEGRADED -> BLOCKED.
  if [ "$want" = "BLOCKED" ] || { [ "$want" = "DEGRADED" ] && [ "$cur" = "READY" ]; }; then
    eval "$name='$want'"
    [ "$QUIET" = "1" ] || say "  $name -> $want${3:+: $3}"
  fi
}

# --- Receipt machinery (installed BEFORE the first exit path) ----------------
# The receipt used to be written only at the bottom of the script, and only
# inside `if [ -n "$GOV_PY" ]`. Every failure path above that line — no
# governance SSOT, unusable interpreter, a workspace that is not a repository —
# therefore produced NO receipt at all, and the SessionStart projection had
# nothing to report but silence (audit B-04). An absent receipt is now the one
# thing a reader may treat as `never_ran`; every other outcome leaves a file.
#
# Written in bash rather than through the locked interpreter deliberately: the
# case that most needs a receipt is the case where that interpreter is missing.
RECEIPT="${L9_CLAUDE_BOOTSTRAP_RECEIPT:-$HOME/.l9/claude/bootstrap-state.json}"
RECEIPT_STAGE="startup"
RECEIPT_REMEDIATION="bash $GOV_DIR/environment/agents/adapters/claude-code/install.sh"
RECEIPT_WRITTEN=0

stage() { RECEIPT_STAGE="$1"; }

json_token() { printf '%s' "$1" | tr -d '\n\r\t"\\' | head -c 200; }

write_receipt() {
  local state="$1" ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')"
  mkdir -p "$(dirname "$RECEIPT")" 2>/dev/null || return 0
  {
    printf '{\n'
    printf '  "schema": "l9.claude-bootstrap.v1",\n'
    printf '  "surface": "claude-code",\n'
    printf '  "mode": "%s",\n' "$([ "$CHECK" = "1" ] && echo check || echo local)"
    printf '  "state": "%s",\n' "$(json_token "$state")"
    printf '  "stage": "%s",\n' "$(json_token "$RECEIPT_STAGE")"
    printf '  "remediation": "%s",\n' "$(json_token "$RECEIPT_REMEDIATION")"
    printf '  "generated_at": "%s",\n' "$ts"
    printf '  "ttl_seconds": %s,\n' "${L9_CLAUDE_BOOTSTRAP_TTL:-86400}"
    printf '  "governance_revision": "%s",\n' \
      "$(json_token "$(git -C "$GOV_DIR" rev-parse HEAD 2>/dev/null || echo unknown)")"
    printf '  "workspace": "%s",\n' "$(json_token "$WORKSPACE")"
    printf '  "shared_bootstrap": "%s",\n' "$(json_token "$STATUS_SHARED")"
    printf '  "settings": "%s",\n' "$(json_token "$STATUS_SETTINGS")"
    printf '  "skills": "%s",\n' "$(json_token "$STATUS_SKILLS")"
    printf '  "rules": "%s",\n' "$(json_token "$STATUS_RULES")"
    printf '  "capabilities": "%s",\n' "$(json_token "$STATUS_CAPABILITIES")"
    printf '  "memory": "%s",\n' "$(json_token "$STATUS_MEMORY")"
    printf '  "mcp": "%s",\n' "$(json_token "$STATUS_MCP")"
    printf '  "plugins": "%s",\n' "$(json_token "$STATUS_PLUGINS")"
    printf '  "overall": "%s"\n' "$(json_token "$state")"
    printf '}\n'
  } > "$RECEIPT" 2>/dev/null || return 0
  RECEIPT_WRITTEN=1
}

# The trap is the guarantee. Any exit that has not already written a receipt —
# including `exit 1` from a guard clause and any unexpected termination — leaves
# a `failed` receipt naming the stage that was in flight.
on_exit() {
  local rc=$?
  if [ "$RECEIPT_WRITTEN" = "0" ]; then
    write_receipt failed
    warn "wrote FAILED bootstrap receipt at stage '$RECEIPT_STAGE' (exit $rc): $RECEIPT"
  fi
  return 0
}
trap on_exit EXIT

# --- Workspace sanity: never wire a directory that is not a git repository ----
# A caller that resolves the wrong workspace (e.g. the PARENT of the checkout)
# would otherwise produce a complete .claude/ tree the editor never loads, and
# still report settings/skills/rules READY. Fail loud in the receipt instead.
if ! git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  warn "workspace $WORKSPACE is not a git repository - refusing to wire project artifacts"
  downgrade STATUS_SETTINGS BLOCKED "workspace is not a git repository"
  downgrade STATUS_SKILLS BLOCKED "workspace is not a git repository"
  downgrade STATUS_RULES BLOCKED "workspace is not a git repository"
fi

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
  warn "BLOCKED: governance SSOT absent"
  exit 1
fi

# --- Shared agent bootstrap (identical on every surface) --------------------
# Its exit code is part of the contract: a nonzero bootstrap means the locked
# interpreter / toolchain / secret plane is unusable, and this installer no
# longer paperes over that with a later "adapter ready".
stage "shared-bootstrap"
SHARED_BOOTSTRAP="$GOV_DIR/ops/scripts/bootstrap_agent_environment.sh"
# Testing seam. The shared bootstrap needs network egress and a uv sync, and it
# has its own suite; adapter-level tests set this to exercise the vendor wiring
# alone. It is never set by any surface caller — if it appears in a real
# environment, the receipt below still records what was skipped.
if [ "${L9_SKIP_SHARED_BOOTSTRAP:-0}" = "1" ]; then
  warn "L9_SKIP_SHARED_BOOTSTRAP=1 — toolchain, secrets and preflight NOT run"
  downgrade STATUS_SHARED DEGRADED "shared bootstrap skipped by request"
elif [ -f "$SHARED_BOOTSTRAP" ]; then
  shared_args=(--surface claude-code --governance "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && shared_args+=(--check)
  [ "$QUIET" = "1" ] && shared_args+=(--quiet)
  bash "$SHARED_BOOTSTRAP" "${shared_args[@]}"
  shared_rc=$?
  # Exit 6 is the shared bootstrap's "usable but degraded" code. Treating it as
  # BLOCKED would mark every hosted-surface install permanently blocked, since
  # the capability plane there is BLOCKED_BY_PLATFORM by construction (INV-4).
  if [ "$shared_rc" -eq 6 ]; then
    downgrade STATUS_SHARED DEGRADED "shared bootstrap reported degraded components"
  elif [ "$shared_rc" -ne 0 ]; then
    downgrade STATUS_SHARED BLOCKED "shared bootstrap exited $shared_rc"
  fi
else
  warn "missing ops/scripts/bootstrap_agent_environment.sh — toolchain, secrets,"
  warn "  repo-scoped identity and preflight are all UNCONFIGURED"
  downgrade STATUS_SHARED BLOCKED "shared bootstrap missing"
fi

# The shared bootstrap owns the locked interpreter; reuse its result. Every
# Python step below runs on it — never the sandbox's system python3.
GOV_PY="$GOV_DIR/.venv/bin/python3"
if [ ! -x "$GOV_PY" ]; then
  warn "locked interpreter $GOV_PY unusable — Python wiring cannot run"
  downgrade STATUS_SHARED BLOCKED "locked interpreter unusable"
  GOV_PY=""
fi

log "Claude Code vendor wiring"
say "governance=$GOV_DIR workspace=$WORKSPACE"

# --- 1) Settings triad (Claude-specific) ------------------------------------
# reconcile_claude_settings.py is the SSOT reconciler: it syncs the governance
# copy, merge-patches ~/.claude/settings.json without clobbering user keys, and
# installs the consumer workspace triad as real files. Same call on CLI, Desktop,
# Web and Mobile — never hand-roll `cp settings.template.json`.
stage "settings-triad"
RECONCILE_SETTINGS="$GOV_DIR/ops/scripts/reconcile_claude_settings.py"
if [ -n "$GOV_PY" ] && [ -f "$RECONCILE_SETTINGS" ]; then
  settings_args=(--root "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && settings_args+=(--check)
  "$GOV_PY" "$RECONCILE_SETTINGS" "${settings_args[@]}"
  settings_rc=$?
  if [ "$settings_rc" -ne 0 ]; then
    if [ "$CHECK" = "1" ]; then
      downgrade STATUS_SETTINGS DEGRADED "reconcile reported drift (check mode)"
    else
      downgrade STATUS_SETTINGS BLOCKED "settings triad reconciliation failed (exit $settings_rc)"
    fi
  fi
elif [ -n "$GOV_PY" ]; then
  warn "missing ops/scripts/reconcile_claude_settings.py"
  downgrade STATUS_SETTINGS BLOCKED "reconciler missing"
fi

# --- 2) Claude skill discovery ----------------------------------------------
stage "skill-discovery"
RECONCILE_SKILLS="$GOV_DIR/ops/scripts/reconcile_claude_l9_skills.py"
if [ -n "$GOV_PY" ] && [ -f "$RECONCILE_SKILLS" ]; then
  # Both scopes. Project scope is invisible when the session's project directory
  # is not this repository — the audited session read the whole repo only as an
  # additional directory — so user scope is the floor that always resolves
  # (B-01, B-15). The SSOT's 53 skills replace the 8-skill account-sync copy.
  skills_args=(--root "$GOV_DIR" --scope user --scope project --workspace "$WORKSPACE" --quiet)
  [ "$CHECK" = "1" ] && skills_args+=(--check)
  "$GOV_PY" "$RECONCILE_SKILLS" "${skills_args[@]}" \
    || downgrade STATUS_SKILLS DEGRADED "skill reconciliation drift or local name conflict"
elif [ -n "$GOV_PY" ]; then
  warn "missing ops/scripts/reconcile_claude_l9_skills.py"
  downgrade STATUS_SKILLS DEGRADED "skill reconciler missing"
fi

# --- 2b) LLM rules mount (Claude .claude/rules) -----------------------------
# The generated rules (rules/*.mdc -> environment/generated/llm-rules) are the
# static governance layer every peer loads: Cursor via the l9-governance plugin,
# Claude CLI via setup_workspace_symlinks.sh. The cloud path reaches only this
# installer, so project + reconcile here too — web/mobile sessions get the same
# generated-rule mount as their CLI and Cursor peers. Both scripts import yaml,
# so run them on the locked interpreter, not the sandbox's system python3.
stage "llm-rules-mount"
PROJECT_RULES="$GOV_DIR/ops/scripts/project_llm_rules.py"
RECONCILE_RULES="$GOV_DIR/ops/scripts/reconcile_llm_rule_adapters.py"
if [ -n "$GOV_PY" ] && [ -f "$PROJECT_RULES" ] && [ -f "$RECONCILE_RULES" ]; then
  if [ "$CHECK" = "1" ]; then
    "$GOV_PY" "$RECONCILE_RULES" --root "$GOV_DIR" --workspace "$WORKSPACE" --check --quiet \
      || downgrade STATUS_RULES DEGRADED "LLM rules adapter reconcile reported drift"
  else
    "$GOV_PY" "$PROJECT_RULES" --root "$GOV_DIR" --quiet \
      || downgrade STATUS_RULES DEGRADED "llm-rules projection failed (non-blocking)"
    "$GOV_PY" "$RECONCILE_RULES" --root "$GOV_DIR" --workspace "$WORKSPACE" --quiet \
      || downgrade STATUS_RULES DEGRADED "LLM rules adapter reconcile failed (non-blocking)"
  fi
elif [ -n "$GOV_PY" ]; then
  warn "missing ops/scripts/project_llm_rules.py or reconcile_llm_rule_adapters.py"
  downgrade STATUS_RULES DEGRADED "rules projector missing"
fi

# --- 3) Memory MCP front door (Claude .mcp.json format) ---------------------
# Brokered front door: the template points at ${L9_CAPABILITY_BROKER_URL}
# (/mcp/graphiti) and carries NO bearer (contract S3/§12). The broker speaks
# the MCP handshake and maps search_memory/write_governed to
# graphiti.query/graphiti.write_governed.
stage "mcp-front-door"
MCP_TEMPLATE="$GOV_DIR/environment/agents/adapters/claude-code/mcp.template.json"
if [ -f "$WORKSPACE/.mcp.json" ]; then
  say ".mcp.json already present — left as the repo committed it"
elif [ "$CHECK" = "1" ]; then
  downgrade STATUS_MCP DEGRADED ".mcp.json missing (check mode: not writing)"
elif [ -f "$MCP_TEMPLATE" ]; then
  cp "$MCP_TEMPLATE" "$WORKSPACE/.mcp.json" && say "installed .mcp.json from mcp.template.json" \
    || downgrade STATUS_MCP DEGRADED "could not install .mcp.json"
else
  warn "missing mcp.template.json — memory front door not wired"
  downgrade STATUS_MCP DEGRADED "mcp.template.json missing"
fi

# Capability plane + memory posture for the receipt. The brokered MCP path is
# usable only where a broker endpoint is configured; without it, capabilities
# and memory are DEGRADED — the honest posture, never a token-paste fix.
if [ -z "${L9_CAPABILITY_BROKER_URL:-}" ]; then
  downgrade STATUS_CAPABILITIES DEGRADED "L9_CAPABILITY_BROKER_URL unset"
  downgrade STATUS_MEMORY DEGRADED "no broker-authenticated identity path"
fi

# --- 3b) Marketplace plugins ------------------------------------------------
# The PreToolUse matcher references mcp__plugin_context7_context7__.*, so the
# settings triad expects the context7 plugin to exist. Nothing installed it:
# install.sh never invoked setup_claude_code_plugins.sh, and the audited runtime
# also had SKIP_PLUGIN_MARKETPLACE=true. A matcher pointing at a guaranteed-
# absent plugin is a dangling reference either way, so resolve it here rather
# than leaving the two halves disagreeing.
stage "marketplace-plugins"
PLUGINS_SCRIPT="$GOV_DIR/ops/scripts/setup_claude_code_plugins.sh"
if [ "${SKIP_PLUGIN_MARKETPLACE:-}" = "true" ]; then
  say "plugin marketplace disabled by the platform (SKIP_PLUGIN_MARKETPLACE=true)"
  downgrade STATUS_PLUGINS DEGRADED "marketplace disabled by the platform"
elif [ "$CHECK" = "1" ]; then
  say "plugins: check mode, not installing"
elif [ -f "$PLUGINS_SCRIPT" ]; then
  bash "$PLUGINS_SCRIPT" ${WORKSPACE:+--workspace "$WORKSPACE"} \
    || downgrade STATUS_PLUGINS DEGRADED "plugin install reported failure"
else
  warn "missing ops/scripts/setup_claude_code_plugins.sh — marketplace plugins NOT installed"
  downgrade STATUS_PLUGINS DEGRADED "plugin installer missing"
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

# --- Receipt + final classification -----------------------------------------
OVERALL="READY"
for st in "$STATUS_SHARED" "$STATUS_SETTINGS" "$STATUS_SKILLS" "$STATUS_RULES" \
          "$STATUS_CAPABILITIES" "$STATUS_MEMORY" "$STATUS_MCP" "$STATUS_PLUGINS"; do
  case "$st" in
    BLOCKED)  OVERALL="BLOCKED"; break ;;
    DEGRADED) OVERALL="DEGRADED" ;;
  esac
done

stage "receipt"
# Unconditional, and no longer gated on the locked interpreter. A missing
# interpreter is now recorded IN the receipt rather than being the reason no
# receipt exists — the old branch downgraded to BLOCKED and then wrote nothing,
# which is the least useful combination available (audit B-04).
write_receipt "$OVERALL"
say "bootstrap receipt: $RECEIPT ($OVERALL)"

log "Claude Code adapter: $OVERALL"
[ "$QUIET" = "1" ] || printf '  shared=%s settings=%s skills=%s rules=%s capabilities=%s memory=%s mcp=%s plugins=%s\n' \
  "$STATUS_SHARED" "$STATUS_SETTINGS" "$STATUS_SKILLS" "$STATUS_RULES" \
  "$STATUS_CAPABILITIES" "$STATUS_MEMORY" "$STATUS_MCP" "$STATUS_PLUGINS"

if [ "$OVERALL" = "BLOCKED" ]; then
  warn "BLOCKED — see classification above; SessionStart will report the degraded contract"
  exit 1
fi
exit 0
