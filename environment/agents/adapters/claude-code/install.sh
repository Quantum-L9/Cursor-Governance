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
#   - the Claude projection engine        (ops/scripts/claude_projection.py:
#     settings triad, skills, commands, rules mount, hooks, plugins)
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
# --check is a DIAGNOSIS, and a diagnosis that rewrites the thing it diagnoses
# is not one. `make claude-env` documents itself as read-only, yet its first step
# reconciled nothing and still overwrote this file — so a doctor run against a
# different --workspace, or with a different environment, silently replaced the
# session's own verdicts. Four components inverted between a SessionStart read
# and a post-doctor read of the same path, for that reason alone. Check mode now
# writes beside the real receipt; the session's stays whatever SessionStart left.
if [ "${CHECK:-0}" = "1" ] && [ -z "${L9_CLAUDE_BOOTSTRAP_RECEIPT:-}" ]; then
  RECEIPT="$HOME/.l9/claude/bootstrap-check.json"
else
  RECEIPT="${L9_CLAUDE_BOOTSTRAP_RECEIPT:-$HOME/.l9/claude/bootstrap-state.json}"
fi
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

# --- Workspace sanity -------------------------------------------------------
# A caller that resolves the wrong workspace (e.g. the PARENT of a lone
# checkout) would produce a complete .claude/ tree the editor never loads, and
# still report settings/skills/rules READY. Fail loud in the receipt instead.
#
# But "not a git repository" is not the same question. A cloud container holds
# several repositories side by side and the harness roots the session at their
# PARENT, which is exactly the tree Claude Code loads project scope from. The
# old check refused precisely that directory. Two signals separate a real
# multi-repo workspace from a stray parent, and neither is git-repo-ness:
#   * the harness names it (CLAUDE_PROJECT_DIR), or
#   * it directly contains two or more git repositories.
# Anything else that is not a repository stays BLOCKED, as before. Git-specific
# steps (shared excludes) already guard on rev-parse further down, so a non-repo
# workspace skips them without any change here.
workspace_is_repo() { git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; }

workspace_is_multirepo_root() {
  local n=0 d
  for d in "$WORKSPACE"/*/ "$WORKSPACE"/.*/; do
    case "$d" in *'/./'|*'/../') continue ;; esac
    [ -d "$d/.git" ] || continue
    n=$((n + 1))
    [ "$n" -ge 2 ] && return 0
  done
  return 1
}

if ! workspace_is_repo; then
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ "$WORKSPACE" = "$CLAUDE_PROJECT_DIR" ]; then
    say "workspace $WORKSPACE is the harness project directory - wiring project artifacts"
  elif workspace_is_multirepo_root; then
    say "workspace $WORKSPACE is a multi-repo container root - wiring project artifacts"
  else
    warn "workspace $WORKSPACE is not a git repository - refusing to wire project artifacts"
    downgrade STATUS_SETTINGS BLOCKED "workspace is not a git repository"
    downgrade STATUS_SKILLS BLOCKED "workspace is not a git repository"
    downgrade STATUS_RULES BLOCKED "workspace is not a git repository"
  fi
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

# --- 1) Claude projection engine (settings, hooks, skills, commands, rules,
#         plugins) ------------------------------------------------------------
# ops/scripts/claude_projection.py is the one projection entrypoint: it drives
# the settings triad (merge-patching ~/.claude and the workspace without
# clobbering consumer keys), per-skill and per-command symlinks, the generated
# llm-rules mount, and declarative plugin state, then writes the projection
# receipt (~/.l9/claude/projection-receipt.json). Same call on CLI, Desktop,
# Web and Mobile — and from SessionStart, so cached environments self-repair.
stage "claude-projection"
PROJECTION_ENGINE="$GOV_DIR/ops/scripts/claude_projection.py"
if [ -n "$GOV_PY" ] && [ -f "$PROJECTION_ENGINE" ]; then
  projection_args=(--root "$GOV_DIR" --workspace "$WORKSPACE" --summary)
  [ "$CHECK" = "1" ] && projection_args+=(--check)
  projection_out="$("$GOV_PY" "$PROJECTION_ENGINE" "${projection_args[@]}" 2>&1)"
  projection_rc=$?
  printf '%s\n' "$projection_out"
  if ! printf '%s' "$projection_out" | grep -q '^projection='; then
    # The engine crashed before emitting a summary — nothing was classified,
    # so no domain can claim health from silence.
    downgrade STATUS_SETTINGS BLOCKED "projection engine failed (exit $projection_rc)"
    downgrade STATUS_SKILLS DEGRADED "projection engine failed (exit $projection_rc)"
    downgrade STATUS_RULES DEGRADED "projection engine failed (exit $projection_rc)"
    downgrade STATUS_PLUGINS DEGRADED "projection engine failed (exit $projection_rc)"
  fi
  domain_status() {
    printf '%s\n' "$projection_out" \
      | sed -n "s/^domain=$1 status=\([a-z]*\).*/\1/p" | head -n 1
  }
  for pair in \
    "settings STATUS_SETTINGS" \
    "skills STATUS_SKILLS" \
    "rules STATUS_RULES" \
    "plugins STATUS_PLUGINS"; do
    domain="${pair%% *}"
    var="${pair##* }"
    dstatus="$(domain_status "$domain")"
    case "$dstatus" in
      ok|skipped|"") : ;;
      drift|conflict)
        downgrade "$var" DEGRADED "projection $domain: $dstatus" ;;
      error)
        if [ "$domain" = "settings" ]; then
          downgrade "$var" BLOCKED "projection settings failed"
        else
          downgrade "$var" DEGRADED "projection $domain failed"
        fi
        ;;
    esac
  done
elif [ -n "$GOV_PY" ]; then
  warn "missing ops/scripts/claude_projection.py"
  downgrade STATUS_SETTINGS BLOCKED "projection engine missing"
  downgrade STATUS_SKILLS DEGRADED "projection engine missing"
  downgrade STATUS_RULES DEGRADED "projection engine missing"
  downgrade STATUS_PLUGINS DEGRADED "projection engine missing"
fi

# --- 3) Memory MCP front door (Claude .mcp.json format) ---------------------
# Graphiti HTTPS front door: the template points at ${GRAPHITI_MCP_URL} and
# carries NO bearer. The capability broker never shipped (retired 2026-08-29).
stage "mcp-front-door"
# .mcp.json is a PROJECTION of mcp.template.json (the single MCP authority),
# already rendered in the claude-projection stage above. The old `cp only if
# absent` left a committed, diverged .mcp.json untouched forever — the exact
# parallel-authority hazard the projection domain removes. Here we only classify
# the result: confirm the render matches the template, never re-copy.
if command -v domain_status >/dev/null 2>&1; then
  MCP_STATUS="$(domain_status mcp)"
else
  MCP_STATUS=""
fi
case "$MCP_STATUS" in
  ok) say ".mcp.json is a current projection of mcp.template.json" ;;
  "") downgrade STATUS_MCP DEGRADED "mcp projection did not run (engine unavailable)" ;;
  drift) downgrade STATUS_MCP DEGRADED ".mcp.json drifted from mcp.template.json (check mode)" ;;
  *) downgrade STATUS_MCP DEGRADED "mcp projection: $MCP_STATUS" ;;
esac

# Capability plane retired 2026-08-29 (never shipped). Do not probe a dead
# broker or mark memory DEGRADED for its absence. Graphiti is GRAPHITI_MCP_URL.
stage "capability-plane"
say "capability broker experiment retired (never shipped; not probed)"
if [ -n "${GRAPHITI_MCP_URL:-}" ]; then
  say "memory front door: GRAPHITI_MCP_URL set (no bearer in this process)"
else
  downgrade STATUS_MEMORY DEGRADED "GRAPHITI_MCP_URL unset"
fi
if [ -f "$WORKSPACE/.mcp.json" ] \
   && grep -q 'L9_CAPABILITY_BROKER_URL' "$WORKSPACE/.mcp.json" 2>/dev/null; then
  downgrade STATUS_MCP DEGRADED "front door still routes through retired capability broker"
fi

# --- 3b) Marketplace plugins ------------------------------------------------
# Plugin convergence is a projection-engine domain (declarative desired state
# in plugins.desired.json; setup_claude_code_plugins.sh only as fallback) and
# already ran in stage claude-projection. What remains here is the honest
# posture: a platform-disabled marketplace, or a missing claude CLI, still
# means the PreToolUse matcher's context7 plugin cannot exist.
stage "marketplace-plugins"
if [ "${SKIP_PLUGIN_MARKETPLACE:-}" = "true" ]; then
  say "plugin marketplace disabled by the platform (SKIP_PLUGIN_MARKETPLACE=true)"
  downgrade STATUS_PLUGINS DEGRADED "marketplace disabled by the platform"
elif ! command -v claude >/dev/null 2>&1; then
  downgrade STATUS_PLUGINS DEGRADED "claude CLI unavailable — plugins not converged"
fi

# --- 4) Excludes for the GENERATED .claude mirrors --------------------------
# Shared activation artifacts are excluded by the shared bootstrap; these globs
# are Claude-specific. Only the GENERATED mirrors are excluded —
# .claude/settings.json and .claude/hooks/ are committable consumer wiring.
#
# .mcp.json belongs in this list for the same reason the mirrors do: it is a
# render of mcp.template.json (claude_projection.py), not hand-authored, and in
# a consumer that does not commit it the projection shows as untracked on every
# session. Measured across the four in-scope repos: tracked in Cursor-Governance,
# untracked in l9-ci-core, l9-cognitive-runtime and l9-meta-injector.
#
# Excluding it is a no-op wherever it IS committed — .git/info/exclude only
# governs untracked paths, so a tracked .mcp.json keeps showing its real diff.
# That is what makes one list correct for both cases.
if [ "$CHECK" != "1" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  exclude_file="$(git -C "$WORKSPACE" rev-parse --git-dir)/info/exclude"
  case "$exclude_file" in /*) : ;; *) exclude_file="$WORKSPACE/$exclude_file" ;; esac
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for glob in ".claude/skills/" ".claude/rules/" ".claude/commands/" ".mcp.json"; do
    grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >> "$exclude_file"
  done
  say "excluded generated .claude mirrors + .mcp.json (local, uncommitted)"
fi

# --- 5) Thin l9 dispatcher --------------------------------------------------
# One facade over the canonical Governance Makefile (make -C "$GOV" <target>
# WS="$PWD"). Installed to $HOME/.local/bin/l9 as a real file so it survives a
# runtime-clone refresh. Not a receipt dimension — reported, never fatal.
stage "l9-dispatcher"
DISPATCHER_INSTALLER="$GOV_DIR/ops/scripts/install_l9_dispatcher.sh"
if [ -f "$DISPATCHER_INSTALLER" ]; then
  if [ "$CHECK" = "1" ]; then
    L9_GOV_ROOT="$GOV_DIR" bash "$DISPATCHER_INSTALLER" --check || warn "l9 dispatcher drift (make l9-dispatcher-install)"
  else
    L9_GOV_ROOT="$GOV_DIR" bash "$DISPATCHER_INSTALLER" || warn "l9 dispatcher install failed"
  fi
else
  warn "missing ops/scripts/install_l9_dispatcher.sh — l9 facade not installed"
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
