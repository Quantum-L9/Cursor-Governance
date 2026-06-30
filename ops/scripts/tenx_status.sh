#!/usr/bin/env bash
# 10X Governance Health Diagnostic
# Version: 2.0.0
# Updated: Use Dropbox GlobalCommands as single source of truth

# Log file for fallback notifications
FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"

# Use Dropbox GlobalCommands as single source of truth
# Set DISABLE_FALLBACK=1 to fail if Dropbox not found (no fallback to Library)
DISABLE_FALLBACK=${DISABLE_FALLBACK:-0}

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ]; then
    ROOT="$HOME/.cursor-governance"
    USING_DROPBOX=true
elif [ -d "$HOME/.cursor-governance" ]; then
    if [ "$DISABLE_FALLBACK" = "1" ]; then
        echo "❌ ERROR: Dropbox GlobalCommands not found and fallback disabled!"
        echo "   Set DISABLE_FALLBACK=0 to allow fallback, or fix Dropbox path"
        exit 1
    fi
    ROOT="$HOME/.cursor-governance"
    USING_DROPBOX=false
    
    # Log fallback usage
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] FALLBACK USED: Library path instead of Dropbox" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Script: $0" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Path: $ROOT" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   User: $USER" >> "$FALLBACK_LOG"
    echo "---" >> "$FALLBACK_LOG"
    
    echo "⚠️  WARNING: Using Library fallback (logged to $FALLBACK_LOG)"
else
    echo "❌ GlobalCommands directory not found!"
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
check "Integrity Layer" "$ROOT/integrity"
check "Manifest Lock" "$ROOT/integrity/manifest-lock.json"
check "Integrity Activity Log" "$ROOT/ops/logs/integrity_activity.log"

echo "---------------------------------------------"
if grep -q "Verify+Repair executed" "$ROOT/ops/logs/integrity_activity.log" 2>/dev/null; then
  echo "🧠 Integrity Agent — Active (last run logged)"
else
  echo "⚠️ Integrity Agent — No recent runs logged"
fi

if launchctl list | grep -q "com.tenx.integritycheck"; then
  echo "🔁 LaunchAgent (Integrity) — Loaded"
else
  echo "⚠️ LaunchAgent (Integrity) — Not loaded"
fi

if launchctl list | grep -q "com.tenx.chat-export"; then
  echo "🧠 LaunchAgent (Chat Export) — Loaded"
else
  echo "⚠️ LaunchAgent (Chat Export) — Not loaded"
fi

echo "---------------------------------------------"
echo "[INFO] Full status logged to $LOG"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") — Status check complete" >> "$LOG"
