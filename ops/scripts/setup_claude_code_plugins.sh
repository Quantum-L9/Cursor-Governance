#!/usr/bin/env bash
# Declarative, idempotent Claude Code (the `claude` CLI) plugin setup.
#
# Portability note: Claude Code plugin state lives in $HOME/.claude/ (user scope),
# which sits outside any git repo and is NOT portable — ~/.claude.json also carries
# a live OAuth session (oauthAccount, machineID, userID) that must never be checked
# into git. ~/.claude/plugins/ is a local cache of full marketplace clones (100s of
# MB) and is likewise not something to vendor here. What IS portable and safe to
# version-control is the small *declaration* of desired state: which marketplaces
# and which plugins should be enabled. That declaration lives below, and this
# script reconciles any machine to match it by calling the `claude` CLI directly
# (both `marketplace add` and `plugin install` are no-ops if already satisfied).
#
# Usage:
#   bash ops/scripts/setup_claude_code_plugins.sh
#
# Requires: `claude` (Claude Code CLI) already installed and reachable on PATH.
# Install docs: https://docs.claude.com/en/docs/claude-code

set -euo pipefail

# --- Desired state (edit here to add/remove plugins) -----------------------
# Parallel arrays (not associative — macOS ships bash 3.2, no `declare -A` support):
# "owner/repo" GitHub sources for `claude plugin marketplace add`
MARKETPLACE_REPOS=(
  "getzep/zep"
  "anthropics/claude-plugins-official"
)

# "plugin@marketplace" entries for `claude plugin install`
PLUGINS=(
  "building-with-zep@zep"
  "aws-core@claude-plugins-official"
  "hookify@claude-plugins-official"
  "pr-review-toolkit@claude-plugins-official"
  "desktop-commander@claude-plugins-official"
  "context7@claude-plugins-official"
)
# -----------------------------------------------------------------------------

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: 'claude' CLI not found on PATH." >&2
  echo "  Install: https://docs.claude.com/en/docs/claude-code" >&2
  echo "  (If installed via nvm-managed Node, add that Node's bin/ dir to PATH.)" >&2
  exit 1
fi

echo "Claude Code CLI: $(command -v claude)"

# Self-heal: old Claude Code versions ship stale/retired default model IDs that
# 404 against the current API, which blocks every `plugin` subcommand. Keeping
# the CLI current avoids that failure mode entirely.
echo "Checking for Claude Code updates..."
claude update || echo "WARN: 'claude update' failed — continuing with current version" >&2
echo ""

for repo in "${MARKETPLACE_REPOS[@]}"; do
  echo "Marketplace: $repo"
  claude plugin marketplace add "$repo"
done

echo ""
for plugin in "${PLUGINS[@]}"; do
  echo "Plugin: $plugin"
  claude plugin install "$plugin"
done

echo ""
echo "=== Installed plugins ==="
claude plugin list
