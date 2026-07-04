#!/bin/bash
# ops/scripts/install_context_processor.sh
# Install launchd job to process context hourly
# Mirrors install_learning_processor.sh pattern

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.cursor.context.processor.plist"

# Create launchd plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursor.context.processor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_DIR/process_context.sh</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$HOME/.cursor-governance/logs/context_processing.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HOME/.cursor-governance/logs/context_processing.err</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ Created plist: $PLIST_PATH"

# Unload existing if present (ignore errors)
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load new plist
launchctl load "$PLIST_PATH"

echo "✅ Context processor installed"
echo "   - Runs: Every hour on the hour"
echo "   - Script: $SCRIPT_DIR/process_context.sh"
echo "   - Logs: ~/.cursor-governance/logs/context_processing.log"
echo ""
echo "To test manually:"
echo "  $SCRIPT_DIR/process_context.sh"

