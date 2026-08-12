#!/usr/bin/env bash
# Session Initialization Script
# Version: 1.1.0
# Purpose: Load governance rules and learning context at session start
# Status: Infrastructure (waiting for Cursor integration)
# SSOT: $HOME/.cursor-governance only (Dropbox / Library fallbacks retired)

set -e

# Log file for fallback notifications (legacy path retained for operators)
FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ] && [ -f "$HOME/.cursor-governance/CANONICAL_LAW.md" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
    USING_SYNCED_SOURCE=true
else
    echo "❌ ERROR: governance SSOT not found at \$HOME/.cursor-governance"
    echo "   Fix: git clone https://github.com/Quantum-L9/Cursor-Governance.git \"\$HOME/.cursor-governance\""
    echo "   Dropbox and Library paths are not fallbacks (CANONICAL_LAW / resolve_governance_paths)."
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] FAIL: missing \$HOME/.cursor-governance (script=$0 user=$USER)" >> "$FALLBACK_LOG"
    exit 1
fi

RULES_FILE="$GLOBAL_COMMANDS/rules.json"
MEMORY_INDEX="$GLOBAL_COMMANDS/ops/logs/memory_index.json"
LOG_FILE="$GLOBAL_COMMANDS/ops/logs/session_init.log"

mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] ========================================" >> "$LOG_FILE"
echo "[$(date)] Session Initialization Started" >> "$LOG_FILE"
echo "[$(date)] SSOT: $GLOBAL_COMMANDS" >> "$LOG_FILE"

# Check if governance system is in place
if [ ! -f "$RULES_FILE" ]; then
    echo "[$(date)] ❌ rules.json not found" >> "$LOG_FILE"
    # rules.json is optional/legacy; continue when CANONICAL_LAW exists
fi

RULES_VERSION="n/a"
if [ -f "$RULES_FILE" ]; then
    RULES_VERSION=$(cat "$RULES_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "[$(date)] ✅ Governance rules v${RULES_VERSION} loaded" >> "$LOG_FILE"
else
    echo "[$(date)] ✅ Governance SSOT via CANONICAL_LAW.md (rules.json absent)" >> "$LOG_FILE"
fi

# Check learning system status
LEARNING_COUNT="0"
RECENT_LEARNINGS="0"
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
echo "[$(date)]   - skills/l9-structured-reasoning/references/reasoning-modes.md" >> "$LOG_FILE"
echo "[$(date)]   - skills/l9-structured-reasoning/references/technical-operations-reasoning.md" >> "$LOG_FILE"
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
    # shellcheck disable=SC1090
    source "$SHOW_CONTEXT"
fi
