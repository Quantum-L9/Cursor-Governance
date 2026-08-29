#!/usr/bin/env bash
# 10X Governance Health Diagnostic
# Version: 2.1.0
# SSOT: $HOME/.cursor-governance only (Dropbox / Library fallbacks retired)

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ] && [ -f "$HOME/.cursor-governance/CANONICAL_LAW.md" ]; then
    ROOT="$HOME/.cursor-governance"
else
    echo "❌ ERROR: governance SSOT not found at \$HOME/.cursor-governance"
    echo "   Fix: git clone https://github.com/Quantum-L9/Cursor-Governance.git \"\$HOME/.cursor-governance\""
    echo "   Dropbox and Library paths are not fallbacks."
    exit 1
fi

LOG="$ROOT/ops/logs/tenx_status.log"

function check() {
  local label=$1
  local path=$2
  if [ -f "$path" ] || [ -d "$path" ]; then
    echo "✅  $label — OK"
  else
    echo "❌  $label — Missing"
  fi
}

echo "🩺 10X Governance Suite — Health Diagnostic"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "---------------------------------------------"

check ".cursor brain" "$ROOT/.cursor/rules.json"
check "Environment Layer" "$ROOT/environment"
check "Commands Layer" "$ROOT/commands"
check "OPS Layer" "$ROOT/ops"
check "Security Layer" "$ROOT/security"
check "Pipeline Layer" "$ROOT/pipeline"
check "Intelligence Layer" "$ROOT/intelligence"

echo "---------------------------------------------"
if launchctl list | grep -q "com.tenx.chat-export"; then
  echo "🧠 LaunchAgent (Chat Export) — Loaded"
else
  echo "⚠️ LaunchAgent (Chat Export) — Not loaded"
fi

echo "---------------------------------------------"
echo "[INFO] Full status logged to $LOG"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") — Status check complete" >> "$LOG"
