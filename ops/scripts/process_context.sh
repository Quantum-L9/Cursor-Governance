#!/bin/bash
# ops/scripts/process_context.sh
# Runs hourly - extracts context from chat exports
# Mirrors process_learnings.sh pattern

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONTEXT_DIR="$GLOBAL_COMMANDS/intelligence/context-memory"
SESSIONS_DIR="$CONTEXT_DIR/sessions"

# Ensure directories exist
mkdir -p "$SESSIONS_DIR"
mkdir -p "$HOME/.cursor-governance/logs"

# Use same chat export that learning system uses
CHAT_EXPORT_BASE="$HOME/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
EXPORT_DIR="$GLOBAL_COMMANDS/ops/logs/chat_exports"

# Find latest export
if [ -d "$EXPORT_DIR" ]; then
    LATEST_EXPORT=$(ls -t "$EXPORT_DIR" | head -1)
    if [ -n "$LATEST_EXPORT" ]; then
        # Extract context using Python
        python3 "$CONTEXT_DIR/context-extractor.py" \
            --export-dir "$EXPORT_DIR/$LATEST_EXPORT" \
            --output-dir "$SESSIONS_DIR"
        
        echo "[$(date)] Context processed: $LATEST_EXPORT" >> "$HOME/.cursor-governance/logs/context_processing.log"
    else
        echo "[$(date)] No chat exports found" >> "$HOME/.cursor-governance/logs/context_processing.log"
    fi
else
    echo "[$(date)] Export directory not found: $EXPORT_DIR" >> "$HOME/.cursor-governance/logs/context_processing.log"
fi

