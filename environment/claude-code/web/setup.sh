#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code environment — Setup script (Web & Mobile)
#
# Paste into claude.ai/code → your environment → Setup script.
# Runs in Anthropic's ephemeral Linux sandbox before the model starts.
# Account-level: Mobile inherits the same script. Credentials come only from
# the Claude environment variables field + GitHub — nothing from a host IDE.
#
# Env vars (from the Environment variables field):
#   GH_TOKEN                          — required for gh
#   L9_GOVERNANCE_REMOTE / _BRANCH    — defaults: GitHub Quantum-L9/Cursor-Governance @ main
#   L9_MEMORY_HTTP_URL + CLIENT_TOKEN — optional shared HTTP memory
#   USER_ID / L9_MEMORY_AGENT_ID / L9_MEMORY_SOURCE — memory identity
#
# Governance always lands at $HOME/.cursor-governance (GitHub main).
# See environment.env.example and network-policy.md.
# ---------------------------------------------------------------------------
set -uo pipefail
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
#    the sandbox never follows a host IDE path pasted into env by mistake.
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
GOV_DIR="$HOME/.cursor-governance"
if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$GOV_DIR" ]; then
  echo "WARN: ignoring L9_GOVERNANCE_DIR='${L9_GOVERNANCE_DIR}' — Web/Mobile SSOT is always \$HOME/.cursor-governance"
fi

if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
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

# 3.5) Install Claude Code triad into this workspace when the repo has not
#      committed it. Never overwrite files the repo already has.
CC_ENV="$GOV_DIR/environment/claude-code"
if [ -d "$CC_ENV" ]; then
  log "Activating Claude Code environment in $(pwd)"
  mkdir -p .claude/hooks
  [ -f .claude/settings.json ] \
    || cp "$CC_ENV/settings.template.json" .claude/settings.json
  [ -f .claude/hooks/session_start_claude_governance.sh ] \
    || cp "$CC_ENV/hooks/session_start_claude_governance.sh" .claude/hooks/
  chmod +x .claude/hooks/session_start_claude_governance.sh 2>/dev/null || true
  if [ -n "${L9_MEMORY_HTTP_URL:-}" ] && [ ! -f .mcp.json ]; then
    cp "$CC_ENV/mcp.template.json" .mcp.json
  fi
  echo "activated: .claude/settings.json + SessionStart hook -> $GOV_DIR"

  # Keep activation artifacts out of the working tree. setup_workspace_symlinks.sh
  # and skill reconciliation create machine-local wiring (.cursor-commands/.cursor
  # symlinks into the SSOT, generated .claude/{skills,rules} mirrors, per-workspace
  # .l9/ and memory-bank/ state). None are committable, but they otherwise show as
  # untracked and tempt a governed session into committing dangling symlinks.
  # Write them to .git/info/exclude — LOCAL and uncommitted, so this never mutates
  # a consumer's tracked .gitignore. Idempotent: only append globs not already present.
  # NOTE: excludes only the GENERATED .claude mirrors; .claude/settings.json and
  # .claude/hooks/ are committable consumer wiring and are deliberately left tracked.
  if git rev-parse --git-dir >/dev/null 2>&1; then
    exclude_file="$(git rev-parse --git-dir)/info/exclude"
    mkdir -p "$(dirname "$exclude_file")"
    touch "$exclude_file"
    for glob in "/.cursor-commands" "/.cursor/" ".claude/skills/" ".claude/rules/" "/.l9/" "memory-bank/"; do
      grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >> "$exclude_file"
    done
    echo "excluded: activation artifacts via $exclude_file (local, uncommitted)"
  fi

  # Reconcile L9 skills into Claude Code's native project discovery path before
  # the model starts. Consumer-local skills are preserved; managed links only.
  if [ -f "$GOV_DIR/ops/scripts/reconcile_claude_l9_skills.py" ]; then
    python3 "$GOV_DIR/ops/scripts/reconcile_claude_l9_skills.py" \
      --root "$GOV_DIR" --scope project --workspace "$(pwd)" --quiet \
      || echo "WARN: L9 Claude skill reconciliation reported drift or a local name conflict"
  fi
else
  echo "WARN: $CC_ENV missing — governance clone may be incomplete; SessionStart hook not installed."
fi

# 4) Language toolchains — only what the workspace declares.
if [ -f pyproject.toml ] || ls ./*.py >/dev/null 2>&1; then
  log "Python toolchain"
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f pyproject.toml ]; then
    pip install --only-binary :all: -e '.[dev,server]' 2>/dev/null \
      || pip install --only-binary :all: -e '.[dev]' 2>/dev/null \
      || pip install --only-binary :all: ruff mypy pytest build 2>/dev/null || true
  else
    pip install --only-binary :all: ruff mypy pytest 2>/dev/null || true
  fi
fi
if [ -f package.json ]; then
  log "Node toolchain"
  if have pnpm; then pnpm install --ignore-scripts || true
  elif have npm; then npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts || true
  fi
fi

# 4.5) pre-commit — REQUIRED by CANONICAL_LAW §12 (mandatory `make pr` gate).
#      `make pr` shells out to pre-commit, so it must be on PATH by default in
#      every L9 workspace, independent of language. Trigger is the presence of a
#      committed .pre-commit-config.yaml (the exact condition that needs it).
#      Warm the hook environments so the first `make pr` does not pay cold-start.
#      Needs pypi.org (the package) + github.com (hook repos) egress — both are in
#      the baseline Custom allowlist; Full covers them too (see network-policy.md).
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

# 5) Optional shared memory — HTTP MCP client only (no local server).
#    Primary wiring is .mcp.json from step 3.5. Production:
#    https://memory.quantumaipartners.com  (set L9_MEMORY_HTTP_URL in env).
if [ -n "${L9_MEMORY_HTTP_URL:-}" ]; then
  if [ "${USER_ID:-}" = "cursor_agent" ] || [ "${L9_MEMORY_AGENT_ID:-}" = "cursor_agent" ]; then
    echo "WARNING: memory identity 'cursor_agent' is reserved — set USER_ID=claude_code_agent and L9_MEMORY_AGENT_ID=claude-code."
  fi
  log "Memory identity: agent_id=${L9_MEMORY_AGENT_ID:-claude-code} user_id=${USER_ID:-claude_code_agent}"
  log "Shared memory: ${L9_MEMORY_HTTP_URL} (MCP /mcp via .mcp.json + Bearer env)"
  if [ ! -f .mcp.json ]; then
    echo "WARN: .mcp.json missing — step 3.5 should have copied mcp.template.json when L9_MEMORY_HTTP_URL is set."
  fi
  if have curl; then
    mem_base="${L9_MEMORY_HTTP_URL%/}"
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 8 "${mem_base}/healthz" 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "204" ]; then
      log "Memory healthz: HTTP ${code} OK"
    else
      echo "WARN: Memory healthz HTTP ${code} from ${mem_base}/healthz — allowlist the host or check the control plane"
    fi
  fi
fi

# 6) Versions for the setup log.
log "Tool versions"
have gh      && gh --version | head -1        || true
have python3 && python3 --version            || true
have ruff    && ruff --version               || echo "ruff:   (per-repo via .[dev])"
have mypy    && mypy --version               || echo "mypy:   (per-repo via .[dev])"
have pre-commit && pre-commit --version      || echo "pre-commit: (installed only when .pre-commit-config.yaml present)"
have node    && echo "node:   $(node --version)" || true
uname -s 2>/dev/null | awk '{print "os:     "$0}' || true

log "Setup complete — governance at $GOV_DIR (GitHub ${GOV_BRANCH})"
