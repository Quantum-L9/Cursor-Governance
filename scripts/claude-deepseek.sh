#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSOT="${HOME}/.cursor-governance"
# Prefer the live SSOT. After governance_activate_fresh swap, a shell can
# still be sitting in ~/.cursor-governance.bak.* while the prompt looks current.
if [[ -f "${SSOT}/.env.local" ]]; then
  ROOT="$SSOT"
elif [[ -f "${SCRIPT_ROOT}/.env.local" ]]; then
  ROOT="$SCRIPT_ROOT"
else
  echo "ERROR: .env.local not found in ${SSOT} or ${SCRIPT_ROOT}." >&2
  echo "Hydrate DEEPSEEK_API_KEY into ${SSOT}/.env.local (gitignored)." >&2
  exit 1
fi
ENV_FILE="${ROOT}/.env.local"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DEEPSEEK_API_KEY:-}" || "${DEEPSEEK_API_KEY}" == "sk-REPLACE_ME" ]]; then
  echo "ERROR: set DEEPSEEK_API_KEY in .env.local" >&2
  exit 1
fi

export ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY}"
unset ANTHROPIC_API_KEY || true

export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.deepseek.com/anthropic}"
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-deepseek-v4-pro[1m]}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${ANTHROPIC_DEFAULT_OPUS_MODEL:-deepseek-v4-pro[1m]}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-deepseek-v4-pro[1m]}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-deepseek-v4-flash}"
export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-deepseek-v4-flash}"
export CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_CODE_EFFORT_LEVEL:-max}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW="${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-786432}"

echo "Claude Code -> ${ANTHROPIC_BASE_URL} (${ANTHROPIC_MODEL})"
cd "$ROOT"
exec claude "$@"
