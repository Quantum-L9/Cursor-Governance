#!/usr/bin/env bash
# L9 Claude Code cloud Setup script (thin bootstrap).
#
# Paste into claude.ai/code → environment → Setup script.
# Anthropic caches the VM snapshot after the first successful run — keep this
# stub small; put heavy probes in SSOT setup.sh / SessionStart hooks.
#
# Docs: https://code.claude.com/docs/en/cloud-environments
set -euo pipefail

# Cloud-only install paths (no-op on local CLI).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

GOV_DIR="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"

mkdir -p "$(dirname "$GOV_DIR")"
if [ -d "$GOV_DIR/.git" ]; then
  git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" || true
  git -C "$GOV_DIR" checkout -q "$GOV_BRANCH" || true
  git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" || true
else
  rm -rf "$GOV_DIR"
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR"
fi

# Prefer moved pack; transitional symlink keeps environment/claude-code working.
SETUP=""
for cand in \
  "$GOV_DIR/environment/agents/adapters/claude-code/web/setup.sh" \
  "$GOV_DIR/environment/claude-code/web/setup.sh"
 do
  if [ -f "$cand" ]; then SETUP="$cand"; break; fi
done
if [ -z "$SETUP" ]; then
  echo "L9 setup: missing web/setup.sh in governance clone" >&2
  exit 1
fi

# Preserve consumer workspace cwd (Anthropic runs setup before Claude starts).
bash "$SETUP"

# Optional durable exports for later Bash in-session (Anthropic CLAUDE_ENV_FILE).
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export L9_GOVERNANCE_DIR=$(printf %q "$GOV_DIR")"
    echo "export GRAPHITI_MCP_URL=$(printf %q "${GRAPHITI_MCP_URL:-https://memory.quantumaipartners.com/graphiti/mcp}")"
  } >> "$CLAUDE_ENV_FILE"
fi

# Per-repo Sonar override when present.
if [ -f sonar-project.properties ]; then
  key=$(sed -n 's/^sonar.projectKey=//p' sonar-project.properties | head -1)
  org=$(sed -n 's/^sonar.organization=//p' sonar-project.properties | head -1)
  if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "$key" ]; then
    echo "export SONAR_PROJECT_KEY=$(printf %q "$key")" >> "$CLAUDE_ENV_FILE"
  fi
  if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "$org" ]; then
    echo "export SONAR_ORG_KEY=$(printf %q "$org")" >> "$CLAUDE_ENV_FILE"
  fi
fi

echo "L9 cloud bootstrap: governance ready at $GOV_DIR"
exit 0
