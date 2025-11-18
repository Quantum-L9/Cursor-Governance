#!/bin/bash
#
# Wrapper script for recursive learning orchestrator
# Resolves paths dynamically for cross-machine compatibility
#

# Find GlobalCommands directory (works on both MacBook and Mac Mini)
# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
else
    echo "❌ GlobalCommands directory not found!" >&2
    echo "   Checked: $HOME/Dropbox/Cursor Governance/GlobalCommands" >&2
    echo "   Checked: $HOME/Library/Application Support/Cursor/GlobalCommands" >&2
    exit 1
fi

# Execute the script
exec "$GLOBAL_COMMANDS/ops/scripts/recursive_learning_orchestrator.py"

