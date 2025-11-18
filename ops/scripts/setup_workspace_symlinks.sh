#!/usr/bin/env bash
# Version: 2.0.0
# Purpose: Setup .cursor-commands symlink and .cursor/commands symlink in current workspace
# Usage: Run this in any workspace to enable @.cursor-commands/ and slash commands access
# Updated: Use Dropbox GlobalCommands as single source of truth

set -e

# Log file for fallback notifications
FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"

# Use Dropbox GlobalCommands as single source of truth
# Set DISABLE_FALLBACK=1 to fail if Dropbox not found (no fallback to Library)
DISABLE_FALLBACK=${DISABLE_FALLBACK:-0}

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
    USING_DROPBOX=true
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    if [ "$DISABLE_FALLBACK" = "1" ]; then
        echo "❌ ERROR: Dropbox GlobalCommands not found and fallback disabled!"
        echo "   Set DISABLE_FALLBACK=0 to allow fallback, or fix Dropbox path"
        exit 1
    fi
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
    USING_DROPBOX=false
    
    # Log fallback usage with timestamp
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] FALLBACK USED: Library path instead of Dropbox" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Script: $0" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   Path: $GLOBAL_COMMANDS" >> "$FALLBACK_LOG"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)]   User: $USER" >> "$FALLBACK_LOG"
    echo "---" >> "$FALLBACK_LOG"
    
    # Loud notification
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  WARNING: USING FALLBACK PATH (NOT DROPBOX)          ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║  Expected: Dropbox/Cursor Governance/GlobalCommands       ║"
    echo "║  Using:    Library/Application Support/Cursor/GlobalCommands ║"
    echo "║                                                            ║"
    echo "║  This means changes won't sync across computers!          ║"
    echo "║  Logged to: $FALLBACK_LOG"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🔔 To disable fallback, set: export DISABLE_FALLBACK=1"
    echo ""
else
    echo "❌ GlobalCommands directory not found!"
    echo "   Checked:"
    echo "     - $HOME/Dropbox/Cursor Governance/GlobalCommands"
    echo "     - $HOME/Library/Application Support/Cursor/GlobalCommands"
    exit 1
fi

WORKSPACE_DIR="$(pwd)"
SYMLINK="$WORKSPACE_DIR/.cursor-commands"
COMMANDS_SYMLINK="$WORKSPACE_DIR/.cursor/commands"

echo "🔧 Setting up workspace symlinks..."
if [ "$USING_DROPBOX" = true ]; then
    echo "📍 GlobalCommands: $GLOBAL_COMMANDS (✅ Dropbox)"
else
    echo "📍 GlobalCommands: $GLOBAL_COMMANDS (⚠️  Library fallback)"
fi
echo ""

# Setup .cursor-commands symlink
if [ -L "$SYMLINK" ]; then
    TARGET=$(readlink "$SYMLINK")
    if [ "$TARGET" = "$GLOBAL_COMMANDS" ]; then
        echo "✅ .cursor-commands symlink already exists and points to correct location"
        echo "   Location: $SYMLINK"
        echo "   Target: $GLOBAL_COMMANDS"
    else
        echo "⚠️  Symlink exists but points to wrong location"
        echo "   Current target: $TARGET"
        echo "   Expected target: $GLOBAL_COMMANDS"
        echo "   Removing old symlink..."
        rm "$SYMLINK"
        ln -s "$GLOBAL_COMMANDS" "$SYMLINK"
        echo "✅ Updated .cursor-commands symlink"
    fi
elif [ -e "$SYMLINK" ]; then
    echo "⚠️  .cursor-commands exists but is not a symlink!"
    echo "   Please remove it manually: rm -rf .cursor-commands"
    exit 1
else
    echo "Creating .cursor-commands symlink..."
    ln -s "$GLOBAL_COMMANDS" "$SYMLINK"
    echo "✅ Created .cursor-commands symlink"
fi

# Setup .cursor/commands symlink
echo ""
if [ ! -d "$WORKSPACE_DIR/.cursor" ]; then
    echo "Creating .cursor directory..."
    mkdir -p "$WORKSPACE_DIR/.cursor"
fi

if [ -L "$COMMANDS_SYMLINK" ]; then
    TARGET=$(readlink "$COMMANDS_SYMLINK")
    if [ "$TARGET" = "$GLOBAL_COMMANDS/commands" ]; then
        echo "✅ .cursor/commands symlink already exists and points to correct location"
        echo "   Location: $COMMANDS_SYMLINK"
        echo "   Target: $GLOBAL_COMMANDS/commands"
    else
        echo "⚠️  Commands symlink exists but points to wrong location"
        echo "   Current target: $TARGET"
        echo "   Expected target: $GLOBAL_COMMANDS/commands"
        echo "   Removing old symlink..."
        rm "$COMMANDS_SYMLINK"
        ln -s "$GLOBAL_COMMANDS/commands" "$COMMANDS_SYMLINK"
        echo "✅ Updated .cursor/commands symlink"
    fi
elif [ -e "$COMMANDS_SYMLINK" ]; then
    echo "⚠️  .cursor/commands exists but is not a symlink!"
    echo "   Backing up existing directory..."
    mv "$COMMANDS_SYMLINK" "$COMMANDS_SYMLINK.backup.$(date +%Y%m%d_%H%M%S)"
    ln -s "$GLOBAL_COMMANDS/commands" "$COMMANDS_SYMLINK"
    echo "✅ Created .cursor/commands symlink (backed up existing)"
else
    echo "Creating .cursor/commands symlink..."
    ln -s "$GLOBAL_COMMANDS/commands" "$COMMANDS_SYMLINK"
    echo "✅ Created .cursor/commands symlink"
fi

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║     WORKSPACE SETUP COMPLETE             ║"
echo "╠═══════════════════════════════════════════╣"
echo "║  .cursor-commands symlink active         ║"
echo "║  .cursor/commands symlink active          ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "📁 You can now access:"
echo "   @.cursor-commands/learning/failures/repeated-mistakes.md"
echo "   @.cursor-commands/learning/patterns/quick-fixes.md"
echo "   @.cursor-commands/profiles/reasoning.md"
echo ""
echo "🚀 Slash commands available:"
echo "   /forge - Heavy Forge mode"
echo "   /ynp - YNP Mode"
echo "   /evaluate - Project evaluation"
echo "   /consolidate - File consolidation"
echo "   /analyze-toolkit - Complete toolkit analysis"
echo ""
echo "🎯 Test it: ls -la .cursor-commands && ls -la .cursor/commands"
