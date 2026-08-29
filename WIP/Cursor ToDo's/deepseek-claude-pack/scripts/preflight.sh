#!/usr/bin/env bash
set -uo pipefail
ok=0
check() { if command -v "$1" >/dev/null 2>&1; then echo "OK    $1 -> $(command -v "$1")"; else echo "MISS  $1"; ok=1; fi; }
check claude
check node
check git
echo "---"
claude --version 2>/dev/null || echo "WARN  'claude --version' failed"
[[ -f .env.local ]] && echo "OK    .env.local present" || echo "MISS  .env.local"
grep -qs '^\.env\.local$' .gitignore && echo "OK    .env.local git-ignored" || echo "MISS  .env.local not in .gitignore"
exit $ok
