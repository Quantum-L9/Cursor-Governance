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
if [ -n "${L9_MEMORY_HTTP_URL:-}" ]; then
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
