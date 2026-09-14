$ErrorActionPreference = "Continue"
foreach ($c in @("claude","node","git")) {
  $p = Get-Command $c -ErrorAction SilentlyContinue
  if ($p) { Write-Host "OK    $c -> $($p.Source)" } else { Write-Host "MISS  $c" }
}
claude --version
if (Test-Path ".env.local") { Write-Host "OK    .env.local present" } else { Write-Host "MISS  .env.local" }
if (Select-String -Path ".gitignore" -Pattern '^\.env\.local$' -Quiet) { Write-Host "OK    ignored" } else { Write-Host "MISS  add .env.local to .gitignore" }
