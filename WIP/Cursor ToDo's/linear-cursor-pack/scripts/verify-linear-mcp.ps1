#Requires -Version 5.1
# RB-LIN-001 Section 5 - Linear MCP verification (Windows)

$fail = $false
function Ok($m)   { Write-Host "  [ok]   $m" }
function Bad($m)  { Write-Host "  [FAIL] $m"; $script:fail = $true }
function Warn($m) { Write-Host "  [warn] $m" }

Write-Host "RB-LIN-001 verification`n"

Write-Host "1. Repo context"
if (Test-Path AGENTS.md) { Ok "AGENTS.md present" } else { Bad "not at repo root" }
$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
if ($branch -eq "main") { Warn "on main branch" } else { Ok "branch: $branch" }

Write-Host "`n2. MCP config"
$cfg = ".cursor/mcp.json"
if (Test-Path $cfg) {
  Ok "$cfg exists"
  try {
    $d = Get-Content $cfg -Raw | ConvertFrom-Json
    $lin = $d.mcpServers.linear
    if (-not $lin) { Bad "no 'linear' server in mcpServers" }
    elseif ($lin.url -and $lin.url.EndsWith("/mcp")) { Ok "linear -> $($lin.url)" }
    elseif ($lin.url -and $lin.url.EndsWith("/sse")) { Warn "legacy SSE endpoint; prefer /mcp" }
    elseif ($lin.command) { Ok "linear via $($lin.command) fallback" }
    else { Bad "linear server has neither url nor command" }
  } catch { Bad "invalid JSON: $_" }
} else {
  Bad "$cfg missing (must NOT be .cursor/rules/mcp.json)"
}
if (Test-Path .cursor/rules/mcp.json) { Bad "stray .cursor/rules/mcp.json - wrong path" }

Write-Host "`n3. Workflow rule"
if (Test-Path .cursor/rules/linear-workflow.mdc) { Ok "linear-workflow.mdc installed" }
else { Bad "linear-workflow.mdc missing" }

Write-Host "`n4. Secret hygiene"
if ((Test-Path .gitignore) -and (Select-String -Path .gitignore -Pattern '^\.env\.local$' -Quiet)) {
  Ok ".env.local is git-ignored"
} else { Bad ".env.local not in .gitignore" }
$hits = git grep -I "lin_api_" -- . ":!linear-cursor-pack" 2>$null
if ($hits) { Bad "Linear API key pattern found in tracked files" } else { Ok "no lin_api_ pattern" }

Write-Host ""
if (-not $fail) {
  Write-Host "RESULT: PASS`n"
  Write-Host "Manual step remaining (cannot be scripted):"
  Write-Host "  Cursor Settings > Tools & MCP > Linear > 'Needs login' > authorize"
  Write-Host "  then refresh tools and confirm a non-zero tool count."
  exit 0
} else {
  Write-Host "RESULT: FAIL - see RUNBOOK.md Section 6"
  exit 1
}
