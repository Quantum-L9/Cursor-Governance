#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env.local"
[[ -f "$ENV_FILE" ]] || { echo "FAIL .env.local missing"; exit 1; }

set -a; source "$ENV_FILE"; set +a

fail=0
[[ "${ANTHROPIC_BASE_URL:-}" == https://api.deepseek.com/anthropic ]] \
  && echo "OK   base url" || { echo "FAIL base url = ${ANTHROPIC_BASE_URL:-unset}"; fail=1; }
[[ "${ANTHROPIC_MODEL:-}" == deepseek-* ]] \
  && echo "OK   model ${ANTHROPIC_MODEL}" || { echo "FAIL model"; fail=1; }
if [[ -n "${DEEPSEEK_API_KEY:-}" && "${DEEPSEEK_API_KEY}" != "sk-REPLACE_ME" ]]; then
  echo "OK   key present (${#DEEPSEEK_API_KEY} chars, not printed)"
else
  echo "FAIL key not set"; fail=1
fi
git -C "$ROOT" check-ignore -q .env.local && echo "OK   .env.local ignored" || { echo "FAIL not ignored"; fail=1; }
if git -C "$ROOT" grep -nI --cached -E 'sk-[a-f0-9]{20,}' >/dev/null 2>&1; then
  echo "FAIL possible key committed"; fail=1
else
  echo "OK   no key-looking string in tracked files"
fi
exit $fail
