#!/usr/bin/env bash
# ===========================================================================
# L9 Claude Code cloud-environment Setup script — THE cross-platform consistency lever.
#
# This one account-level file is the only executable carrier that Web AND Mobile
# both read (Mobile inherits the Web environment; there is no separate mobile
# config). Paste it into claude.ai/code -> your environment -> Setup script. It
# runs in the ephemeral sandbox before the model starts, on every new session.
#
# Design contract — every chat, every surface, boots the SAME governance:
#   * IDEMPOTENT     — re-running changes nothing already in place (safe per session).
#   * FAIL-OPEN      — `set -uo pipefail` WITHOUT `-e`; no optional step can block a
#                      session. Every fallible action ends in `|| true` / a WARN.
#   * SELF-HEALING   — refreshes the governance clone so long-lived CLI sandboxes see
#                      the same current law a fresh Web/Mobile clone does (no drift
#                      between chats).
#   * SELF-ACTIVATING— installs the `.claude/` triad from the clone into any repo that
#                      has not committed it, so the SessionStart hook always fires.
#   * AUTO-DETECTING — installs only the toolchain the workspace declares (Python/Node).
#   * ZERO-SECRET    — reads credentials from the "Environment variables" field only;
#                      nothing sensitive lives in this file.
#
# Reads (from the environment's "Environment variables" field):
#   GH_TOKEN                 required for gh (CI logs, reviews, pushes)
#   L9_GOVERNANCE_DIR        where to clone/find Cursor-Governance (default ~/.cursor-governance)
#   L9_GOVERNANCE_REF        optional git ref/branch to pin governance to (default: repo default)
#   L9_MEMORY_HTTP_URL/_*    optional shared agent memory (see environment.env.example)
# See environment.env.example and network-policy.md for the other two fields.
# ===========================================================================
set -uo pipefail
# Fail-open contract, enforced: the cloud runner executes this script under `set -e`,
# so a single failed optional step (e.g. a cp of a template that isn't where we
# looked) would abort the run and BLOCK the session. Explicitly clear errexit here;
# every fallible step below degrades to a WARN instead of killing the session.
set +e
log()  { printf '\n=== %s ===\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1) GitHub CLI — gh-driven skills need it for CI logs, reviews, pushes.
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
#    Precedence, and every candidate MUST actually contain CANONICAL_LAW.md:
#      a) explicit L9_GOVERNANCE_DIR (only if it holds CANONICAL_LAW.md)
#      b) the workspace itself — a session run directly against Cursor-Governance
#         IS its own clone; do not clone a second copy
#      c) a $HOME clone we create (fresh) or fast-forward refresh (subsequent chats)
GOV_URL="https://github.com/Quantum-L9/Cursor-Governance"
WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ -f "${L9_GOVERNANCE_DIR}/CANONICAL_LAW.md" ]; then
  GOV_DIR="$L9_GOVERNANCE_DIR"
  log "Governance clone (L9_GOVERNANCE_DIR) -> $GOV_DIR"
elif [ -f "$WORKSPACE/CANONICAL_LAW.md" ]; then
  GOV_DIR="$WORKSPACE"
  log "Workspace IS the governance clone -> $GOV_DIR (no separate clone needed)"
else
  GOV_DIR="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
  if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
    log "Cloning Cursor-Governance -> $GOV_DIR"
    git clone --depth 1 --single-branch ${L9_GOVERNANCE_REF:+--branch "$L9_GOVERNANCE_REF"} \
      "$GOV_URL" "$GOV_DIR" \
      || echo "WARN: governance clone failed — set L9_GOVERNANCE_DIR or check the network allowlist (needs github.com)."
  else
    log "Refreshing governance clone -> $GOV_DIR"
    # --ff-only never merges or conflicts; tolerated if the checkout is a live work tree.
    git -C "$GOV_DIR" fetch --depth 1 origin "${L9_GOVERNANCE_REF:-HEAD}" 2>/dev/null \
      && git -C "$GOV_DIR" merge --ff-only FETCH_HEAD 2>/dev/null \
      || echo "note: governance refresh skipped (offline, pinned, or local work tree) — using existing clone"
  fi
fi

# 3.5) Activate the Claude Code governance environment in THIS workspace.
# Makes every mobile/web chat self-activate: if the repo has not committed the
# .claude/ triad, install it from the clone so the SessionStart hook fires. Guarded
# on the TEMPLATE FILE (not just the dir) and fully fail-open — a missing template
# emits a WARN and must never abort the session. Never clobbers committed files.
CC_ENV="$GOV_DIR/environment/claude-code"
if [ -f "$WORKSPACE/.claude/settings.json" ]; then
  log "Workspace already ships a committed .claude/ triad — self-activation not needed"
elif [ -f "$CC_ENV/settings.template.json" ]; then
  log "Activating Claude Code environment in $(pwd)"
  mkdir -p .claude/hooks 2>/dev/null || true
  [ -f .claude/settings.json ] \
    || cp "$CC_ENV/settings.template.json" .claude/settings.json 2>/dev/null \
    || echo "WARN: could not install .claude/settings.json from $CC_ENV"
  [ -f .claude/hooks/session_start_claude_governance.sh ] \
    || cp "$CC_ENV/hooks/session_start_claude_governance.sh" .claude/hooks/ 2>/dev/null \
    || echo "WARN: could not install the SessionStart hook from $CC_ENV"
  chmod +x .claude/hooks/session_start_claude_governance.sh 2>/dev/null || true
  # Shared-memory MCP only when the account provides an endpoint; never overwrite a
  # repo's own .mcp.json.
  if [ -n "${L9_MEMORY_HTTP_URL:-}" ] && [ ! -f .mcp.json ]; then
    cp "$CC_ENV/mcp.template.json" .mcp.json 2>/dev/null || echo "WARN: could not install .mcp.json"
  fi
  echo "activated: .claude/ triad -> governance at $GOV_DIR"
else
  echo "WARN: templates not found under $CC_ENV (GOV_DIR=$GOV_DIR) — clone incomplete or path wrong; SessionStart hook not installed. Session still starts."
fi

# 4) Language toolchains — install only what the workspace declares.
#    Detection is broad enough to cover flat repos, src layouts, and monorepos
#    without per-repo edits (no friction), yet installs nothing a repo doesn't use.
if [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ] || [ -f requirements.txt ] \
   || ls ./*.py >/dev/null 2>&1; then
  log "Python toolchain"
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f pyproject.toml ]; then
    pip install --only-binary :all: -e '.[dev,server]' 2>/dev/null \
      || pip install --only-binary :all: -e '.[dev]' 2>/dev/null \
      || pip install --only-binary :all: -e . 2>/dev/null \
      || pip install --only-binary :all: ruff mypy pytest build 2>/dev/null || true
  elif [ -f requirements.txt ]; then
    pip install --only-binary :all: -r requirements.txt 2>/dev/null || true
    pip install --only-binary :all: ruff mypy pytest 2>/dev/null || true
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
have gh      && gh --version | head -1          || true
have python3 && python3 --version               || true
have ruff    && ruff --version                  || echo "ruff:   (per-repo via .[dev])"
have mypy    && mypy --version                  || echo "mypy:   (per-repo via .[dev])"
have node    && echo "node:   $(node --version)" || true

log "Setup complete — governance at $GOV_DIR"
