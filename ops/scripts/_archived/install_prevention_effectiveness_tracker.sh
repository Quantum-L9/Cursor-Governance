#!/bin/bash
#
# === SUITE 6 CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "1.0.0"
# component_id: "OPS-INST-004"
# component_name: "Prevention Effectiveness Tracker LaunchAgent Installer"
# layer: "operations"
# domain: "learning"
# type: "installer"
# status: "active"
# created: "2025-11-17T22:06:00Z"
# updated: "2025-11-17T22:06:00Z"
# author: "Igor Beylin"
# maintainer: "Igor Beylin"
#
# === BUSINESS METADATA ===
# purpose: "Install LaunchAgent for hourly prevention effectiveness tracking"
# summary: "Schedules prevention_effectiveness_tracker.py to run hourly"
# business_value: "Enables continuous effectiveness measurement"
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_NAME="com.cursor.prevention-effectiveness-tracker"
PLIST_FILE="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
# Use $HOME-based path for cross-machine compatibility (MacBook and Mac Mini)
WRAPPER_SCRIPT="$HOME/.cursor-governance/ops/scripts/prevention_effectiveness_tracker_wrapper.sh"
LOG_FILE="$HOME/.cursor-governance/ops/logs/prevention_effectiveness_tracker.log"

echo "🔧 Installing Prevention Effectiveness Tracker LaunchAgent..."
echo "   Wrapper: $WRAPPER_SCRIPT"
echo "   Log: $LOG_FILE"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Create plist file (hourly execution)
cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${WRAPPER_SCRIPT}</string>
        <string>--calculate</string>
        <string>--daily-report</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_FILE}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ Created plist file: $PLIST_FILE"

# Unload if already exists
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "🔄 Unloading existing agent..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

# Load the agent
echo "🚀 Loading LaunchAgent..."
launchctl load "$PLIST_FILE"

# Verify it's loaded
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "✅ LaunchAgent installed and loaded successfully!"
    echo ""
    echo "📅 Schedule: Every hour (3600 seconds)"
    echo "📝 Log file: $LOG_FILE"
    echo ""
    echo "To check status:"
    echo "  launchctl list | grep $PLIST_NAME"
    echo ""
    echo "To uninstall:"
    echo "  launchctl unload $PLIST_FILE"
    echo "  rm $PLIST_FILE"
else
    echo "❌ Failed to load LaunchAgent"
    exit 1
fi

