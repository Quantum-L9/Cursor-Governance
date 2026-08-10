#!/bin/bash
# Opt-in reverse tunnel only. Never called by install_local.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="${L9_AGENT_UI_LOG_DIR:-$HOME/.l9/agent_ui_control/logs}"
PLIST_SRC="$SCRIPT_DIR/com.l9.agent_ui_control.tunnel.plist"
PLIST_DST="$LAUNCH_AGENTS_DIR/com.l9.agent_ui_control.tunnel.plist"

echo "=== L9 Agent UI Control — REMOTE TUNNEL (opt-in) ==="

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "ERROR: Do not run as root/sudo"
  exit 1
fi

mkdir -p "$LOG_DIR" "$LAUNCH_AGENTS_DIR"
chmod +x "$SCRIPT_DIR/reverse_tunnel.sh"

python3 - <<PY
from pathlib import Path
text = Path("$PLIST_SRC").read_text()
text = text.replace("__PACK_DIR__", "$SCRIPT_DIR")
text = text.replace("__LOG_DIR__", "$LOG_DIR")
Path("$PLIST_DST").write_text(text)
print(f"Wrote $PLIST_DST")
PY

# Unload legacy tunnel label if present
launchctl unload "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist" 2>/dev/null || true

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Tunnel LaunchAgent loaded: com.l9.agent_ui_control.tunnel"
echo "Unload: launchctl unload $PLIST_DST"
