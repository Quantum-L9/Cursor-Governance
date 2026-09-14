#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.local"

if (-not (Test-Path $envFile)) {
  Write-Error "$envFile not found. Copy env.local.example to .env.local first."
}

Get-Content $envFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $parts = $_ -split '=', 2
  [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
}

if (-not $env:DEEPSEEK_API_KEY -or $env:DEEPSEEK_API_KEY -eq "sk-REPLACE_ME") {
  Write-Error "Set DEEPSEEK_API_KEY in .env.local"
}

$env:ANTHROPIC_AUTH_TOKEN = $env:DEEPSEEK_API_KEY
Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

if (-not $env:ANTHROPIC_BASE_URL) { $env:ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic" }
if (-not $env:ANTHROPIC_MODEL) { $env:ANTHROPIC_MODEL = "deepseek-v4-pro[1m]" }
if (-not $env:ANTHROPIC_DEFAULT_OPUS_MODEL) { $env:ANTHROPIC_DEFAULT_OPUS_MODEL = "deepseek-v4-pro[1m]" }
if (-not $env:ANTHROPIC_DEFAULT_SONNET_MODEL) { $env:ANTHROPIC_DEFAULT_SONNET_MODEL = "deepseek-v4-pro[1m]" }
if (-not $env:ANTHROPIC_DEFAULT_HAIKU_MODEL) { $env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "deepseek-v4-flash" }
if (-not $env:CLAUDE_CODE_SUBAGENT_MODEL) { $env:CLAUDE_CODE_SUBAGENT_MODEL = "deepseek-v4-flash" }
if (-not $env:CLAUDE_CODE_EFFORT_LEVEL) { $env:CLAUDE_CODE_EFFORT_LEVEL = "max" }
if (-not $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW) { $env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = "786432" }

Write-Host "Claude Code -> $($env:ANTHROPIC_BASE_URL) ($($env:ANTHROPIC_MODEL))"
Set-Location $root
claude @args
