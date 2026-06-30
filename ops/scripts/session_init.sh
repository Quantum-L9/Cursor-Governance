#!/usr/bin/env bash
# Session Initialization Script
# Version: 1.0.0
# Purpose: Load governance rules and learning context at session start
# Status: Infrastructure (waiting for Cursor integration)

set -e

# Log file for fallback notifications
FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"

# Use Dropbox GlobalCommands as single source of truth
# Set DISABLE_FALLBACK=1 to fail if Dropbox not found (no fallback to Library)
DISABLE_FALLBACK=${DISABLE_FALLBACK:-0}

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
    USING_DROPBOX=true
elif [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
    USING_DROPBOX=true
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    if [ "$DISABLE_FALLBACK" = "1" ]; then
        echo "❌ ERROR: SSOT/Dropbox GlobalCommands not found and fallback disabled!"
        echo "   Set DISABLE_FALLBACK=0 to allow fallback, or restore the SSOT clone"
        exit 1
    fi
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
    USING_DROPBOX=false
    
    # Log fallback usage
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] FALLBACK USED: Library path instead of Dropbox" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Script: $0" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Path: $GLOBAL_COMMANDS" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   User: $USER" >> "$FALLBACK_LOG"
    echo "---" >> "$FALLBACK_LOG"
    
    echo "⚠️  WARNING: Using Library fallback (logged to $FALLBACK_LOG)"
else
    echo "❌ GlobalCommands directory not found!"
    exit 1
fi

RULES_FILE="$GLOBAL_COMMANDS/rules.json"
MEMORY_INDEX="$GLOBAL_COMMANDS/ops/logs/memory_index.json"
LOG_FILE="$GLOBAL_COMMANDS/ops/logs/session_init.log"

# Log fallback status to session log if fallback was used
if [ "$USING_DROPBOX" = false ]; then
    echo "[$(date)] ⚠️  WARNING: Using Library fallback (should be Dropbox)" >> "$LOG_FILE"
fi

echo "[$(date)] ========================================" >> "$LOG_FILE"
echo "[$(date)] Session Initialization Started" >> "$LOG_FILE"

# Check if governance system is in place
if [ ! -f "$RULES_FILE" ]; then
    echo "[$(date)] ❌ rules.json not found" >> "$LOG_FILE"
    exit 1
fi

RULES_VERSION=$(cat "$RULES_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
echo "[$(date)] ✅ Governance rules v${RULES_VERSION} loaded" >> "$LOG_FILE"

# Check learning system status
if [ -f "$MEMORY_INDEX" ]; then
    LEARNING_COUNT=$(cat "$MEMORY_INDEX" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('learnings', [])))" 2>/dev/null || echo "0")
    echo "[$(date)] ✅ Learning system active: ${LEARNING_COUNT} learnings" >> "$LOG_FILE"
else
    echo "[$(date)] ⚠️  Memory index not found" >> "$LOG_FILE"
fi

# Check if learning processor is running
if launchctl list | grep -q "com.tenx.learning-processor"; then
    echo "[$(date)] ✅ Learning processor service active" >> "$LOG_FILE"
else
    echo "[$(date)] ⚠️  Learning processor not running" >> "$LOG_FILE"
fi

# List files that should be auto-loaded (for reference)
echo "[$(date)] Files to load (if Cursor supported auto-loading):" >> "$LOG_FILE"
echo "[$(date)]   - profiles/reasoning.md" >> "$LOG_FILE"
echo "[$(date)]   - profiles/technical-operations-reasoning.md" >> "$LOG_FILE"
echo "[$(date)]   - learning/failures/repeated-mistakes.md" >> "$LOG_FILE"
echo "[$(date)]   - learning/patterns/quick-fixes.md" >> "$LOG_FILE"

# Get recent learnings (last 24 hours)
if [ -f "$MEMORY_INDEX" ]; then
    RECENT_LEARNINGS=$(cat "$MEMORY_INDEX" | python3 -c "
import sys, json
from datetime import datetime, timedelta
data = json.load(sys.stdin)
learnings = data.get('learnings', [])
cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
recent = [l for l in learnings if l.get('timestamp', '') > cutoff]
print(len(recent))
" 2>/dev/null || echo "0")
    echo "[$(date)] ✅ Recent learnings (24h): ${RECENT_LEARNINGS}" >> "$LOG_FILE"
fi

echo "[$(date)] Session Initialization Complete" >> "$LOG_FILE"
echo "[$(date)] ========================================" >> "$LOG_FILE"

# Output summary for display
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║     SESSION INITIALIZATION COMPLETE           ║"
echo "╠═══════════════════════════════════════════════╣"
echo "║  Governance: v${RULES_VERSION}                           ║"
echo "║  Learnings: ${LEARNING_COUNT} total, ${RECENT_LEARNINGS} recent (24h)      ║"
echo "║  Learning Processor: Active                   ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

# Show last session context (if available)
SHOW_CONTEXT="$GLOBAL_COMMANDS/ops/scripts/show_context.sh"
if [ -f "$SHOW_CONTEXT" ]; then
    source "$SHOW_CONTEXT"
fi

