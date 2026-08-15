#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code environment — canonical Setup script (Web · Mobile · --cloud)
#
# NOT the script you paste. Paste web/setup.bootstrap.sh into
# claude.ai/code -> environment -> Setup script; it clones this repo and execs
# this file from the clone, so edits here reach every new session with no
# re-paste. (Pasting this file directly still works — you then own the drift.)
#
# Runs in Anthropic's ephemeral Linux sandbox before the model starts.
# Account-level: Mobile inherits the same environment. Credentials come only
# from the Environment variables field + GitHub — nothing from a host IDE.
#
# Env vars (see web/environment.env.example):
#   GH_TOKEN                       — required for gh
#   GRAPHITI_MCP_URL / _TOKEN      — Cursor Graphiti front door (ADR-0006/0007)
#   L9_GOVERNANCE_REMOTE / _BRANCH — default Quantum-L9/Cursor-Governance @ main
#   USER_ID / L9_MEMORY_AGENT_ID / L9_MEMORY_SOURCE — writer identity only
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

# 3.1) Governance RUNTIME dependencies.
#      The gates the adapter depends on are ordinary Python imports:
#        ops/graphiti/*            -> pydantic  (memory front door, phase-lock)
#        ops/autonomy/*            -> pyyaml    (surface profile, L4 gates)
#        program-execution/core/*  -> jsonschema
#      Without them the PreToolUse memory gate fails closed and every governed
#      write is denied. They CANNOT be installed with `pip install -e .`: this
#      repo is a flat-layout multi-package tree, so setuptools refuses automatic
#      discovery and the editable build errors out. Install the declared
#      `[project].dependencies` by name instead (tomllib is stdlib on 3.11+),
#      which stays in sync with pyproject.toml with no second list to maintain.
if [ -f "$GOV_DIR/pyproject.toml" ]; then
  log "Governance runtime deps (memory + autonomy gates)"
  GOV_DEPS=$(python3 - "$GOV_DIR/pyproject.toml" <<'PY' 2>/dev/null
import sys, tomllib
from pathlib import Path
try:
    data = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, tomllib.TOMLDecodeError):
    sys.exit(1)
for dep in data.get("project", {}).get("dependencies", []):
    print(dep)
PY
  )
  if [ -n "$GOV_DEPS" ]; then
    # shellcheck disable=SC2086 # deliberate word-splitting: one requirement per line
    python3 -m pip install --quiet --prefer-binary $GOV_DEPS 2>/dev/null \
      || echo "WARN: governance runtime deps failed to install — memory gate will fail closed (allowlist pypi.org)"
  else
    echo "WARN: could not read [project].dependencies from governance pyproject.toml"
  fi
  # Prove the gates can import before the model starts; this is the exact
  # failure that surfaces as "No conflict-checked phase-lock held".
  python3 -c 'import pydantic, yaml, jsonschema' 2>/dev/null \
    && echo "governance imports OK: pydantic + pyyaml + jsonschema" \
    || echo "WARN: governance imports still failing — Graphiti phase-lock and governed writes will be blocked"
fi

# 3.5) Install the Claude Code triad into this workspace when the repo has not
#      committed it. Never overwrite files the repo already has.
CC_ENV="$GOV_DIR/environment/agents/adapters/claude-code"
if [ -d "$CC_ENV" ]; then
  log "Activating Claude Code environment in $(pwd)"
  mkdir -p .claude/hooks
  [ -f .claude/settings.json ] \
    || cp "$CC_ENV/settings.template.json" .claude/settings.json
  [ -f .claude/hooks/session_start_claude_governance.sh ] \
    || cp "$CC_ENV/hooks/session_start_claude_governance.sh" .claude/hooks/
  chmod +x .claude/hooks/session_start_claude_governance.sh 2>/dev/null || true
  # Always install Graphiti front-door MCP template when absent (ADR-0006).
  if [ ! -f .mcp.json ] && [ -f "$CC_ENV/mcp.template.json" ]; then
    cp "$CC_ENV/mcp.template.json" .mcp.json
  fi
  echo "activated: .claude/settings.json + SessionStart hook -> $GOV_DIR"

  # Keep activation artifacts out of the working tree. setup_workspace_symlinks.sh
  # and skill reconciliation create machine-local wiring (.cursor-commands/.cursor
  # symlinks into the SSOT, generated .claude/{skills,rules} mirrors, per-workspace
  # .l9/ state). None are committable, but they otherwise show as untracked and
  # tempt a governed session into committing dangling symlinks.
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
#    NOTE: `--only-binary :all:` is applied to third-party resolution only. It is
#    NOT combined with `-e .` (an editable install must build from source, so the
#    pair always fails), and the L9 flat-layout repos cannot be installed editable
#    at all — their deps come from step 3.1 / the `[dev]` extra by name.
if [ -f pyproject.toml ] || ls ./*.py >/dev/null 2>&1; then
  log "Python toolchain"
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f pyproject.toml ]; then
    pip install --prefer-binary -e '.[dev,server]' 2>/dev/null \
      || pip install --prefer-binary -e '.[dev]' 2>/dev/null \
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

# 5) Memory — Cursor Graphiti front door only (ADR-0006). No HTTP side door.
if [ "${USER_ID:-}" = "cursor_agent" ] || [ "${L9_MEMORY_AGENT_ID:-}" = "cursor_agent" ]; then
  echo "WARNING: memory identity 'cursor_agent' is reserved — set USER_ID=claude_code_agent and L9_MEMORY_AGENT_ID=claude-code."
fi
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  [ -n "${!retired:-}" ] && echo "WARN: $retired set — retired ADR-0006 side door; remove it from the environment variables field"
done
log "Memory identity: agent_id=${L9_MEMORY_AGENT_ID:-claude-code} user_id=${USER_ID:-claude_code_agent}"
log "Shared memory: Cursor Graphiti front door ($GRAPHITI_MCP_URL via mcp.template.json)"
if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
  echo "WARN: GRAPHITI_MCP_TOKEN unset — SessionStart hydrate and governed-write phase-lock run DEGRADED."
fi
if [ ! -f .mcp.json ]; then
  echo "WARN: .mcp.json missing — step 3.5 should have copied mcp.template.json (Graphiti front door)."
fi

# 6) L4 local autonomy — report the publish gate the session will run under.
#    Read-only: never begin a phase or authorize a release on the setup path.
#    Brain: ops/autonomy/l4_local.py + local_execution_gate.py (SSOT:
#    ops/autonomy/surface_profile.yaml). Mid-execution push/PR stay denied until
#    the kernels are recorded and release is authorized.
if [ -f "$GOV_DIR/ops/autonomy/l4_local.py" ] && git rev-parse --git-dir >/dev/null 2>&1; then
  log "L4 local autonomy"
  python3 "$GOV_DIR/ops/autonomy/l4_local.py" status 2>/dev/null \
    || echo "phase: not begun (push/PR denied until 'l4_local.py authorize-release')"
  for kernel in "Recursive Alignment.md" "Validate & Repair.md"; do
    [ -f "$GOV_DIR/kernels/$kernel" ] \
      || echo "WARN: missing required kernel: kernels/$kernel"
  done
  # Restore any scratch-hold parked by a previous session before work resumes
  # (surface_profile: sacred WIP is never lost to a clean `make pr`).
  if [ -f "$GOV_DIR/ops/scripts/scratch_hold.py" ]; then
    python3 "$GOV_DIR/ops/scripts/scratch_hold.py" restore --all 2>/dev/null \
      || true
  fi
fi

# 7) Versions for the setup log.
log "Tool versions"
have gh      && gh --version | head -1        || true
have python3 && python3 --version            || true
have ruff    && ruff --version               || echo "ruff:   (per-repo via .[dev])"
have mypy    && mypy --version               || echo "mypy:   (per-repo via .[dev])"
have pre-commit && pre-commit --version      || echo "pre-commit: (installed only when .pre-commit-config.yaml present)"
have node    && echo "node:   $(node --version)" || true
uname -s 2>/dev/null | awk '{print "os:     "$0}' || true

log "Setup complete — governance at $GOV_DIR (GitHub ${GOV_BRANCH})"
