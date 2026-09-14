#!/usr/bin/env bash
# RB-LIN-001 Section 5 - Linear MCP verification
set -uo pipefail

fail=0
ok()   { printf '  [ok]   %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; fail=1; }
warn() { printf '  [warn] %s\n' "$1"; }

echo "RB-LIN-001 verification"
echo

echo "1. Repo context"
[ -f AGENTS.md ] && ok "AGENTS.md present" || bad "not at repo root"
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
[ "$branch" = "main" ] && warn "on main branch" || ok "branch: $branch"

echo
echo "2. MCP config"
CFG=".cursor/mcp.json"
if [ -f "$CFG" ]; then
  ok "$CFG exists"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$CFG" <<'PY'
import json,sys
p=sys.argv[1]
try:
    d=json.load(open(p))
except Exception as e:
    print("  [FAIL] invalid JSON: %s"%e); sys.exit(1)
srv=d.get("mcpServers",{})
if "linear" not in srv:
    print("  [FAIL] no 'linear' server in mcpServers"); sys.exit(1)
lin=srv["linear"]
url=lin.get("url","")
if url.endswith("/mcp"):
    print("  [ok]   linear -> %s"%url)
elif url.endswith("/sse"):
    print("  [warn] legacy SSE endpoint; prefer /mcp")
elif "command" in lin:
    print("  [ok]   linear via %s fallback"%lin["command"])
else:
    print("  [FAIL] linear server has neither url nor command"); sys.exit(1)
print("  [ok]   servers configured: %s"%", ".join(sorted(srv)))
PY
    [ $? -ne 0 ] && fail=1
  else
    warn "python3 unavailable; skipped JSON validation"
  fi
else
  bad "$CFG missing (must NOT be .cursor/rules/mcp.json)"
fi
[ -f .cursor/rules/mcp.json ] && bad "stray .cursor/rules/mcp.json found - wrong path"

echo
echo "3. Workflow rule"
[ -f .cursor/rules/linear-workflow.mdc ] \
  && ok "linear-workflow.mdc installed" \
  || bad "linear-workflow.mdc missing"

echo
echo "4. Secret hygiene"
grep -q '^\.env\.local$' .gitignore 2>/dev/null \
  && ok ".env.local is git-ignored" \
  || bad ".env.local not in .gitignore"
if git rev-parse --git-dir >/dev/null 2>&1; then
  if git grep -qI 'lin_api_' -- . ':!linear-cursor-pack' 2>/dev/null; then
    bad "Linear API key pattern found in tracked files"
  else
    ok "no lin_api_ pattern in tracked files"
  fi
fi

echo
echo "5. Fallback transport"
command -v npx >/dev/null 2>&1 && ok "npx available" || warn "npx absent (only needed for mcp-remote)"

echo
if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS"
  echo
  echo "Manual step remaining (cannot be scripted):"
  echo "  Cursor Settings > Tools & MCP > Linear > 'Needs login' > authorize"
  echo "  then click refresh tools and confirm a non-zero tool count."
  echo "  Finally, in Agent mode ask: 'List my open Linear issues. Use MCP tools.'"
  exit 0
else
  echo "RESULT: FAIL - see RUNBOOK.md Section 6"
  exit 1
fi
