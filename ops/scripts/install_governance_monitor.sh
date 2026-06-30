#!/usr/bin/env bash
# === SUITE 6 CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "1.0.0"
# component_id: "OPS-INS-004"
# component_name: "Governance Monitor LaunchAgent Installer"
# layer: "operations"
# domain: "installation"
# type: "installer_script"
# status: "active"
# created: "2025-11-20T09:30:00Z"

set -e

echo "🔧 Installing Governance Monitor LaunchAgent..."

# Find GlobalCommands path
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
elif [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
else
    echo "❌ Error: GlobalCommands directory not found"
    exit 1
fi

SCRIPT_DIR="$GLOBAL_COMMANDS/ops/scripts"
PLIST_PATH="$HOME/Library/LaunchAgents/com.cursor.governance-monitor.plist"

# Create wrapper script
WRAPPER_SCRIPT="$SCRIPT_DIR/governance-monitor-wrapper.sh"
cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/usr/bin/env bash
# Wrapper for governance-monitor.py

# Find GlobalCommands
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
elif [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
fi

MONITOR_SCRIPT="$GLOBAL_COMMANDS/ops/scripts/governance-monitor.py"
LOG_FILE="$GLOBAL_COMMANDS/ops/logs/governance_monitor_launchd.out"

echo "[$(date)] Running governance monitor..." >> "$LOG_FILE"

if [ -f "$MONITOR_SCRIPT" ]; then
    python3 "$MONITOR_SCRIPT" >> "$LOG_FILE" 2>&1
    echo "[$(date)] Governance monitor completed" >> "$LOG_FILE"
else
    echo "[$(date)] Error: governance-monitor.py not found" >> "$LOG_FILE"
fi
EOF

chmod +x "$WRAPPER_SCRIPT"

# Create LaunchAgent plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursor.governance-monitor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$WRAPPER_SCRIPT</string>
    </array>
    
    <key>StartInterval</key>
    <integer>7200</integer>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$GLOBAL_COMMANDS/ops/logs/governance_monitor_launchd.out</string>
    
    <key>StandardErrorPath</key>
    <string>$GLOBAL_COMMANDS/ops/logs/governance_monitor_launchd.err</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ Governance Monitor LaunchAgent installed"
echo "   Schedule: Every 2 hours"
echo "   Logs: $GLOBAL_COMMANDS/ops/logs/governance_monitor_launchd.out"
echo ""
echo "To check status: launchctl list | grep governance-monitor"

