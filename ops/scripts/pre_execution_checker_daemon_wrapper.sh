#!/bin/bash
#
# Wrapper script for pre-execution checker 
# Resolves paths dynamically for cross-machine compatibility
#

# Find GlobalCommands directory (works on both MacBook and Mac Mini)
# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
elif [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
else
    echo "❌ GlobalCommands directory not found!" >&2
    echo "   Checked: $HOME/.cursor-governance" >&2
    echo "   Checked: $HOME/.cursor-governance" >&2
    exit 1
fi

# Execute the daemon script
exec python3 "$GLOBAL_COMMANDS/ops/scripts/pre_execution_checker_daemon.py"

