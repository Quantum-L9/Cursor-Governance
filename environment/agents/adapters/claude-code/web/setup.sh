#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code — cloud sandbox provisioning (Web · Mobile · --cloud)
#
# THIN SURFACE CALLER. This file owns only what Anthropic's ephemeral Linux
# sandbox uniquely needs as MACHINE-LEVEL provisioning — a GitHub CLI, the
# governance clone, and the adapter install. Every piece of adapter wiring
# lives in the one shared installer and is delegated to it:
#
#   ../install.sh   <- locked toolchain, settings triad, skills, MCP, preflight
#
# The account Setup script is environment provisioning: Anthropic caches the
# environment after the first successful run and does NOT re-run it on every
# session. Mutable per-session work — governance refresh and the consumer
# workspace's own language toolchain — therefore lives in the committed
# SessionStart path (hooks/session_start_claude_governance.sh ->
# hooks/session_deps_cloud.sh), which runs on every session and resume.
#
# CLI and Desktop reach install.sh through `make claude-install`. If you are
# adding adapter behaviour, add it to install.sh so both surfaces get it;
# add here only if it is genuinely cloud-sandbox-specific.
#
# NOT the script you paste. Paste web/setup.bootstrap.sh into
# claude.ai/code -> environment -> Setup script; it clones this repo and execs
# this file from the clone, so edits here reach every new session with no
# re-paste.
#
# Env vars (see web/environment.env.example):
#   GH_TOKEN=proxy-injected        — not a PAT; Anthropic git/gh proxy
#   GRAPHITI_MCP_URL               — Cursor Graphiti front door URL (no bearer)
#   L9_CAPABILITY_BROKER_URL       — optional; Infisical stays behind the broker
#   L9_GOVERNANCE_REMOTE / _BRANCH — default Quantum-L9/Cursor-Governance @ main
#
# Governance always lands at $HOME/.cursor-governance (GitHub main).
# See web/environment.env.example and web/network-policy.md.
# ---------------------------------------------------------------------------
set -uo pipefail

# Cloud Graphiti default when unset (CLI hosts export the loopback tunnel URL).
: "${GRAPHITI_MCP_URL:=https://memory.quantumaipartners.com/graphiti/mcp}"

log() { printf '\n=== %s ===\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1) GitHub CLI — needed for CI logs, reviews, pushes.
if ! have gh; then
  log "Installing GitHub CLI (gh)"
  if have apt-get; then
    curl -fsSL --proto '=https' --tlsv1.2 https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null 2>&1 || true
    sudo apt-get update -qq && sudo apt-get install -y gh || echo "WARN: gh install failed"
  else
    echo "WARN: no apt-get; install gh from https://cli.github.com (sandbox should be Debian/Ubuntu)"
  fi
fi

# 2) gh — platform proxy only. A real PAT here is a contract violation (S3/S7).
if [ -n "${GH_TOKEN:-}" ] && [ "$GH_TOKEN" != "proxy-injected" ]; then
  echo "WARN: GH_TOKEN looks like a real credential — PROHIBITED; unsetting"
  unset GH_TOKEN
fi
if have gh; then
  log "GitHub CLI present (auth is the Anthropic git/gh proxy, not a pasted PAT)"
  gh auth status 2>/dev/null || echo "NOTE: gh unauthenticated until the platform proxy injects credentials"
else
  echo "WARNING: gh missing — CI/review skills that shell out to gh will not work."
fi

# 3) Governance SSOT — GitHub main only (Quantum-L9/Cursor-Governance).
#    Always materialize at $HOME/.cursor-governance. Ignore other overrides so
#    the sandbox never follows a host IDE path pasted into env by mistake, and
#    never follows an unexpanded literal '$HOME' from the .env-format field.
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
GOV_DIR="$HOME/.cursor-governance"
if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$GOV_DIR" ]; then
  echo "WARN: ignoring L9_GOVERNANCE_DIR='${L9_GOVERNANCE_DIR}' — Web/Mobile SSOT is always \$HOME/.cursor-governance"
fi
export L9_GOVERNANCE_DIR="$GOV_DIR"

# 3a) Validated bootstrap handoff.
#     setup.bootstrap.sh must materialize the governance clone in order to find
#     THIS file, so re-cloning/fetching/resetting the same tree here is pure
#     duplicate work. The bootstrap signals what it did with
#     L9_GOVERNANCE_BOOTSTRAPPED=1 — but the marker is never trusted on its own.
#     It is honoured only if the tree it claims to have produced independently
#     validates as usable and on the requested ref. Any failed check falls
#     through to the normal synchronization path below, so direct invocation of
#     this script (no bootstrap, no marker) is completely unaffected.
governance_handoff_valid() {
  [ "${L9_GOVERNANCE_BOOTSTRAPPED:-}" = "1" ] || return 1
  [ -d "$GOV_DIR" ] || { echo "WARN: handoff marker set but $GOV_DIR is absent"; return 1; }
  git -C "$GOV_DIR" rev-parse --git-dir >/dev/null 2>&1 \
    || { echo "WARN: handoff marker set but $GOV_DIR is not a git repository"; return 1; }
  local required
  for required in \
    CANONICAL_LAW.md \
    AGENTS.md \
    ops/scripts/ensure_uv_environment.sh \
    ops/scripts/reconcile_claude_settings.py \
    environment/agents/adapters/claude-code/install.sh
  do
    [ -f "$GOV_DIR/$required" ] \
      || { echo "WARN: handoff tree incomplete (missing $required)"; return 1; }
  done
  local head_ref
  head_ref="$(git -C "$GOV_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
  if [ "$head_ref" != "$GOV_BRANCH" ] && [ "$head_ref" != "HEAD" ]; then
    echo "WARN: handoff tree is on '$head_ref', requested '$GOV_BRANCH'"
    return 1
  fi
  git -C "$GOV_DIR" rev-parse HEAD >/dev/null 2>&1 \
    || { echo "WARN: handoff tree has no resolvable HEAD"; return 1; }
  return 0
}

if governance_handoff_valid; then
  log "Governance handed off by bootstrap — validated, skipping duplicate sync"
  log "Governance at $(git -C "$GOV_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown) (${GOV_BRANCH})"
elif [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  log "Cloning governance from GitHub (${GOV_BRANCH}) -> $GOV_DIR"
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR" \
    || echo "WARN: governance clone failed — allowlist github.com"
else
  log "Syncing governance to GitHub ${GOV_BRANCH} -> $GOV_DIR"
  git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE" 2>/dev/null || true
  if git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" 2>/dev/null; then
    git -C "$GOV_DIR" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" 2>/dev/null \
      || git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" 2>/dev/null \
      || echo "WARN: could not reset to origin/${GOV_BRANCH}"
    log "Governance at $(git -C "$GOV_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown) (origin/${GOV_BRANCH})"
  else
    echo "WARN: git fetch origin/${GOV_BRANCH} failed — using existing clone (may be stale)"
  fi
fi

# 4) THE adapter install — identical call on CLI, Desktop, Web and Mobile.
#    Locked toolchain from uv.lock, settings triad, skills, MCP front door,
#    git excludes, preflight. Do not reimplement any of that here.
ADAPTER_INSTALL="$GOV_DIR/environment/agents/adapters/claude-code/install.sh"
if [ -f "$ADAPTER_INSTALL" ]; then
  bash "$ADAPTER_INSTALL" --governance "$GOV_DIR" --workspace "$(pwd)"
  adapter_rc=$?
  echo "NOTE: adapter install exited $adapter_rc (see ~/.l9/claude/bootstrap-state.json)"
else
  echo "WARN: missing environment/agents/adapters/claude-code/install.sh — adapter NOT wired"
fi

# NOT here: the consumer workspace's own language toolchain (uv/pip/npm) and
# pre-commit warm. This account Setup script is environment provisioning and
# may be cached for ~7 days; project dependencies are per-repository work and
# belong in the committed SessionStart path
# (hooks/session_start_claude_governance.sh -> hooks/session_deps_cloud.sh),
# which runs on every session and resume.

# 5) Versions for the setup log.
log "Tool versions"
have gh      && gh --version | head -1        || true
have uv      && echo "uv:     $(uv --version)" || echo "uv:     (missing — uv.lock cannot be applied)"
have python3 && echo "system python3: $(python3 --version 2>&1)" || true
[ -x "$GOV_DIR/.venv/bin/python3" ] \
  && echo "locked  python3: $("$GOV_DIR/.venv/bin/python3" --version 2>&1) ($GOV_DIR/.venv)" \
  || echo "locked  python3: (absent — governance gates run on system python)"
have pre-commit && pre-commit --version      || echo "pre-commit: (installed only when .pre-commit-config.yaml present)"
have node    && echo "node:   $(node --version)" || true
uname -s 2>/dev/null | awk '{print "os:     "$0}' || true

log "Setup complete — governance at $GOV_DIR (GitHub ${GOV_BRANCH})"
