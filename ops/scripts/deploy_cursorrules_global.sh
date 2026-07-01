#!/usr/bin/env bash
# Version: 2.0.0
# Purpose: Deploy .cursorrules to a workspace (or all workspaces)
# Usage: 
#   In workspace: bash ~/.cursor-governance/ops/scripts/deploy_cursorrules_global.sh
#   Or provide path: bash deploy_cursorrules_global.sh /path/to/workspace
# Updated: Use ~/.cursor-governance as single source of truth (Dropbox is legacy fallback)

set -e

# Log file for fallback notifications
FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"

# Use Dropbox GlobalCommands as single source of truth
# Set DISABLE_FALLBACK=1 to fail if Dropbox not found (no fallback to Library)
DISABLE_FALLBACK=${DISABLE_FALLBACK:-0}

# ALWAYS use $HOME - NEVER hardcode /Users/[username] paths
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
    USING_SYNCED_SOURCE=true
elif [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
    USING_SYNCED_SOURCE=true
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    if [ "$DISABLE_FALLBACK" = "1" ]; then
        echo "❌ ERROR: SSOT/Dropbox GlobalCommands not found and fallback disabled!"
        echo "   Set DISABLE_FALLBACK=0 to allow fallback, or restore the SSOT clone"
        exit 1
    fi
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
    USING_SYNCED_SOURCE=false
    
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
    echo "║  Expected: .cursor-governance       ║"
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
    exit 1
fi

SOURCE_CURSORRULES="$GLOBAL_COMMANDS/templates/.cursorrules"
TARGET_DIR="${1:-$(pwd)}"

echo "🚀 Deploying .cursorrules to workspace..."
if [ "$USING_SYNCED_SOURCE" = true ]; then
    echo "📍 GlobalCommands: $GLOBAL_COMMANDS (✅ synced source)"
else
    echo "📍 GlobalCommands: $GLOBAL_COMMANDS (⚠️  Library fallback)"
fi
echo ""

# Check if source template exists
if [ ! -f "$SOURCE_CURSORRULES" ]; then
    echo "⚠️  No .cursorrules template found at: $SOURCE_CURSORRULES"
    echo "   Using current workspace .cursorrules as template..."
    SOURCE_CURSORRULES="$(pwd)/.cursorrules"
    
    if [ ! -f "$SOURCE_CURSORRULES" ]; then
        echo "❌ No .cursorrules found to use as template!"
        exit 1
    fi
fi

# Ensure target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Target directory not found: $TARGET_DIR"
    exit 1
fi

TARGET_FILE="$TARGET_DIR/.cursorrules"

# Backup existing if present
if [ -f "$TARGET_FILE" ]; then
    BACKUP="$TARGET_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backing up existing .cursorrules to:"
    echo "   $BACKUP"
    cp "$TARGET_FILE" "$BACKUP"
fi

# Copy template to target
cp "$SOURCE_CURSORRULES" "$TARGET_FILE"

echo ""
echo "✅ Deployed .cursorrules to: $TARGET_DIR"
echo ""

# Setup symlinks
SYMLINK="$TARGET_DIR/.cursor-commands"
COMMANDS_SYMLINK="$TARGET_DIR/.cursor/commands"

# Setup .cursor-commands symlink
if [ -L "$SYMLINK" ]; then
    echo "✅ .cursor-commands symlink already exists"
else
    echo "🔗 Creating .cursor-commands symlink..."
    ln -s "$GLOBAL_COMMANDS" "$SYMLINK"
    echo "✅ .cursor-commands symlink created"
fi

# Setup .cursor/commands symlink
if [ ! -d "$TARGET_DIR/.cursor" ]; then
    mkdir -p "$TARGET_DIR/.cursor"
fi

if [ -L "$COMMANDS_SYMLINK" ]; then
    echo "✅ .cursor/commands symlink already exists"
else
    if [ -e "$COMMANDS_SYMLINK" ]; then
        echo "⚠️  .cursor/commands exists but is not a symlink, backing up..."
        mv "$COMMANDS_SYMLINK" "$COMMANDS_SYMLINK.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    echo "🔗 Creating .cursor/commands symlink..."
    ln -s "$GLOBAL_COMMANDS/commands" "$COMMANDS_SYMLINK"
    echo "✅ .cursor/commands symlink created"
fi

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║     WORKSPACE SETUP COMPLETE             ║"
echo "╠═══════════════════════════════════════════╣"
echo "║  .cursorrules deployed                   ║"
echo "║  .cursor-commands symlink active         ║"
echo "║  .cursor/commands symlink active         ║"
echo "║  All governance files accessible         ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "📁 You can now use: @.cursor-commands/ in this workspace!"
echo "🚀 Slash commands available: /forge, /ynp, /evaluate, /consolidate, /analyze-toolkit"

