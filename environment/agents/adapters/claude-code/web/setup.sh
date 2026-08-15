#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code — cloud sandbox provisioning (Web · Mobile · --cloud)
#
# THIN SURFACE CALLER. This file owns only what Anthropic's ephemeral Linux
# sandbox uniquely needs — a GitHub CLI, credentials, the governance clone, and
# the workspace's own language toolchain. Every piece of adapter wiring lives in
# the one shared installer and is delegated to it:
#
#   ../install.sh   <- locked toolchain, settings triad, skills, MCP, preflight
#
# CLI and Desktop reach that same installer through `make claude-install`. If
# you are adding adapter behaviour, add it to install.sh so both surfaces get
# it; add here only if it is genuinely cloud-sandbox-specific.
#
# NOT the script you paste. Paste web/setup.bootstrap.sh into
# claude.ai/code -> environment -> Setup script; it clones this repo and execs
# this file from the clone, so edits here reach every new session with no
# re-paste.
#
# Env vars (see web/environment.env.example):
#   GH_TOKEN                       — required for gh
#   GRAPHITI_MCP_URL / _TOKEN      — Cursor Graphiti front door (ADR-0006/0007)
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

# 2) Authenticate gh + git with the bot-user PAT so pushes trigger Actions.
if [ -n "${GH_TOKEN:-}" ] && have gh; then
  log "Authenticating gh"
  printf '%s' "$GH_TOKEN" | gh auth login --with-token 2>/dev/null && gh auth setup-git || true
  gh auth status 2>/dev/null || true
else
  echo "WARNING: GH_TOKEN unset or gh missing — gh is unauthenticated; CI/review/push skills will not work."
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
else
  echo "WARN: missing environment/agents/adapters/claude-code/install.sh — adapter NOT wired"
fi

# 5) The CONSUMER workspace's own language toolchain.
#    Distinct from step 4: that installs the governance repo's locked env from
#    its uv.lock; this installs whatever the repo you are working in declares.
#    A workspace that ships uv.lock gets the locked path too; otherwise fall
#    back to its pyproject/package.json. Never pin versions here — the
#    workspace's own manifest is its source of truth.
if [ -f uv.lock ] && have uv; then
  log "Workspace toolchain (uv.lock)"
  uv sync --locked --extra dev 2>/dev/null || uv sync --locked 2>/dev/null \
    || echo "WARN: workspace uv sync --locked failed"
elif [ -f pyproject.toml ] || ls ./*.py >/dev/null 2>&1; then
  log "Workspace toolchain (pip)"
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f pyproject.toml ]; then
    # NOTE: `--only-binary :all:` is deliberately NOT paired with `-e .` — an
    # editable install must build from source, so that combination can never
    # succeed. Flat-layout multi-package repos cannot be installed editable at
    # all; for those the fallback below is the expected path.
    pip install --prefer-binary -e '.[dev,server]' 2>/dev/null \
      || pip install --prefer-binary -e '.[dev]' 2>/dev/null \
      || pip install --prefer-binary -r requirements.txt 2>/dev/null \
      || pip install --only-binary :all: ruff mypy pytest build 2>/dev/null || true
  else
    pip install --only-binary :all: ruff mypy pytest 2>/dev/null || true
  fi
fi
if [ -f package.json ]; then
  log "Workspace toolchain (Node)"
  if have pnpm; then pnpm install --ignore-scripts || true
  elif have npm; then npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts || true
  fi
fi

# 6) pre-commit — REQUIRED by CANONICAL_LAW §12 (mandatory `make pr` gate).
#    `make pr` shells out to pre-commit, so it must be on PATH by default in
#    every L9 workspace, independent of language. Trigger is the presence of a
#    committed .pre-commit-config.yaml (the exact condition that needs it).
#    Warm the hook environments so the first `make pr` does not pay cold-start.
#    Needs pypi.org (the package) + github.com (hook repos) egress — both are in
#    the baseline Custom allowlist; Full covers them too (see network-policy.md).
if [ -f .pre-commit-config.yaml ]; then
  log "pre-commit (CANONICAL_LAW §12 — make pr gate)"
  if ! have pre-commit; then
    pip install --only-binary :all: pre-commit 2>/dev/null \
      || python3 -m pip install pre-commit 2>/dev/null \
      || echo "WARN: pre-commit install failed — 'make pr' will fail until installed (allowlist pypi.org)"
  fi
  if have pre-commit; then
    pre-commit install --install-hooks 2>/dev/null \
      || pre-commit install-hooks 2>/dev/null \
      || echo "WARN: pre-commit hook warm-up failed — first 'make pr' will fetch hook repos (allowlist github.com)"
    pre-commit --version 2>/dev/null || true
  fi
fi

# 7) Versions for the setup log.
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
