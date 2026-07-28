#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code cloud-environment Setup script (Web & Mobile).
#
# Paste into claude.ai/code -> your environment -> Setup script. Runs before each
# session, in the ephemeral sandbox, BEFORE the model starts. Account-level, so
# Claude Code Mobile runs the same script. Idempotent; language-auto-detecting;
# fail-tolerant (a session must still start if an optional step fails).
#
# Reads from the environment's "Environment variables" field:
#   GH_TOKEN (required for gh), L9_GOVERNANCE_DIR, L9_MEMORY_* (optional).
# See environment.env.example and network-policy.md.
# ---------------------------------------------------------------------------
set -uo pipefail
log() { printf '\n=== %s ===\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1) GitHub CLI — gh-driven skills need it for CI logs, reviews, pushes.
if ! have gh; then
  log "Installing GitHub CLI (gh)"
  if have apt-get; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null 2>&1 || true
    sudo apt-get update -qq && sudo apt-get install -y gh || echo "WARN: gh install failed"
  else
    echo "WARN: no apt-get; install gh manually (https://cli.github.com)"
  fi
fi

# 2) Authenticate gh + git with the BOT-USER PAT so pushes trigger Actions.
if [ -n "${GH_TOKEN:-}" ] && have gh; then
  log "Authenticating gh"
  printf '%s' "$GH_TOKEN" | gh auth login --with-token 2>/dev/null && gh auth setup-git || true
  gh auth status 2>/dev/null || true
else
  echo "WARNING: GH_TOKEN unset or gh missing — gh is unauthenticated; skills that read CI/reviews or push will not work."
fi

# 3) Governance clone — the SessionStart hook and skills resolve against this.
GOV_DIR="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  log "Cloning Cursor-Governance -> $GOV_DIR"
  git clone --depth 1 https://github.com/Quantum-L9/Cursor-Governance "$GOV_DIR" \
    || echo "WARN: governance clone failed — set L9_GOVERNANCE_DIR or check network allowlist"
else
  log "Governance clone present -> $GOV_DIR"
fi

# 3.5) Activate the Claude Code governance environment in THIS workspace.
# This is what makes every mobile chat self-activate: if the repo has not committed
# the .claude/ triad, install it from the clone so the SessionStart hook fires and
# governance boots. Never clobber files the repo already committed.
CC_ENV="$GOV_DIR/environment/claude-code"
if [ -d "$CC_ENV" ]; then
  log "Activating Claude Code environment in $(pwd)"
  mkdir -p .claude/hooks
  [ -f .claude/settings.json ] \
    || cp "$CC_ENV/settings.template.json" .claude/settings.json
  [ -f .claude/hooks/session_start_claude_governance.sh ] \
    || cp "$CC_ENV/hooks/session_start_claude_governance.sh" .claude/hooks/
  chmod +x .claude/hooks/session_start_claude_governance.sh 2>/dev/null || true
  # Shared-memory MCP only when the account provides an endpoint; never overwrite a
  # repo's own .mcp.json.
  if [ -n "${L9_MEMORY_HTTP_URL:-}" ] && [ ! -f .mcp.json ]; then
    cp "$CC_ENV/mcp.template.json" .mcp.json
  fi
  echo "activated: .claude/settings.json + SessionStart hook -> governance at $GOV_DIR"
else
  echo "WARN: $CC_ENV missing — governance clone may be incomplete; SessionStart hook not installed."
fi

# 4) Language toolchains — install only what the workspace declares.
if [ -f pyproject.toml ] || ls ./*.py >/dev/null 2>&1; then
  log "Python toolchain"
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f pyproject.toml ]; then
    pip install -e '.[dev,server]' 2>/dev/null \
      || pip install -e '.[dev]' 2>/dev/null \
      || pip install ruff mypy pytest build 2>/dev/null || true
  else
    pip install ruff mypy pytest 2>/dev/null || true
  fi
fi
if [ -f package.json ]; then
  log "Node toolchain"
  if have pnpm; then pnpm install || true
  elif have npm; then npm ci 2>/dev/null || npm install || true
  fi
fi

# 5) Optional: L9 shared agent memory. Only the package is installed here; the
#    canonical DB is owned by ONE long-running HTTP server, not per-session stdio.
#    Identity guard: Claude Code writes under its OWN agent id, never cursor_agent
#    (group_id/repo namespace is shared with Cursor; writing identity is not).
if [ -n "${L9_MEMORY_HTTP_URL:-}" ]; then
  if [ "${USER_ID:-}" = "cursor_agent" ] || [ "${L9_MEMORY_AGENT_ID:-}" = "cursor_agent" ]; then
    echo "WARNING: memory identity is 'cursor_agent' — collides with Cursor. Set USER_ID=claude_code_agent / L9_MEMORY_AGENT_ID=claude-code."
  fi
  log "Memory identity: agent_id=${L9_MEMORY_AGENT_ID:-claude-code} user_id=${USER_ID:-claude_code_agent} (distinct from Cursor's cursor_agent)"
  log "Provisioning L9 memory client (l9-graphiti-memory)"
  MEM_DIR="${L9_MEMORY_SRC:-$HOME/l9-graphiti-memory}"
  [ -d "$MEM_DIR/.git" ] || git clone --depth 1 https://github.com/Quantum-L9/l9-graphiti-memory "$MEM_DIR" 2>/dev/null || echo "memory clone skipped"
  [ -d "$MEM_DIR" ] && { pip install -e "${MEM_DIR}[server]" 2>/dev/null || pip install -e "$MEM_DIR" 2>/dev/null || true; }
  echo "note: for cross-session sharing, run the shared HTTP memory server and register mcp.template.json."
fi

# 6) Surface resolved versions so drift is visible in the setup log.
log "Tool versions"
have gh     && gh --version | head -1        || true
have python3 && python3 --version            || true
have ruff   && ruff --version                || echo "ruff:   (per-repo via .[dev])"
have mypy   && mypy --version                || echo "mypy:   (per-repo via .[dev])"
have node   && echo "node:   $(node --version)" || true

log "Setup complete — governance at $GOV_DIR"
