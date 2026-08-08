#!/bin/bash
# Agent UI Control — local install (file queue + LaunchAgent → runner.py).
# Does NOT load reverse tunnel. Never references agent.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="${L9_AGENT_UI_LOG_DIR:-$HOME/.l9/agent_ui_control/logs}"
PLIST_SRC="$SCRIPT_DIR/com.l9.agent_ui_control.plist"
PLIST_DST="$LAUNCH_AGENTS_DIR/com.l9.agent_ui_control.plist"

# Prefer governance venv (Python 3.11+) over system /usr/bin/python3 (often 3.9).
PYTHON_BIN="${L9_AGENT_UI_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "$HOME/.cursor-governance/.venv/bin/python" ]; then
    PYTHON_BIN="$HOME/.cursor-governance/.venv/bin/python"
  elif [ -x "$HOME/Cursor-Governance/.venv/bin/python" ]; then
    PYTHON_BIN="$HOME/Cursor-Governance/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

echo "=== L9 Agent UI Control — local install ==="

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "ERROR: Do not run as root/sudo"
  exit 1
fi

mkdir -p "$LOG_DIR"
mkdir -p "$HOME/.l9/mac_tasks/pending" "$HOME/.l9/mac_tasks/completed"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Optional deps (non-fatal if pip fails in restricted envs)
if [ "${L9_AGENT_UI_SKIP_DEPS:-0}" != "1" ]; then
  echo "Installing Python deps (set L9_AGENT_UI_SKIP_DEPS=1 to skip)..."
  python3 -m pip install --user -r "$SCRIPT_DIR/requirements.txt" || \
    echo "WARN: pip install failed; continuing (stdlib smoke still works for shell)"
fi

# Unload legacy mac_agent LaunchAgents if present
for legacy in com.l9.agent com.l9.tunnel; do
  if [ -f "$LAUNCH_AGENTS_DIR/${legacy}.plist" ]; then
    echo "Unloading legacy $legacy..."
    launchctl unload "$LAUNCH_AGENTS_DIR/${legacy}.plist" 2>/dev/null || true
  fi
done

# Render plist with absolute paths (no agent.py)
"$PYTHON_BIN" - <<PY
from pathlib import Path
src = Path("$PLIST_SRC")
dst = Path("$PLIST_DST")
text = src.read_text()
text = text.replace("__PACK_DIR__", "$SCRIPT_DIR")
text = text.replace("__TOOLS_DIR__", "$TOOLS_DIR")
text = text.replace("__LOG_DIR__", "$LOG_DIR")
text = text.replace("/usr/bin/python3", "$PYTHON_BIN")
if "agent.py" in text:
    raise SystemExit("refuse: rendered plist still references agent.py")
if "runner.py" not in text:
    raise SystemExit("refuse: rendered plist missing runner.py")
dst.write_text(text)
print(f"Wrote {dst}")
print(f"Python: $PYTHON_BIN")
PY

chmod +x "$SCRIPT_DIR/runner.py" "$SCRIPT_DIR/local_console.py" "$SCRIPT_DIR/integrity_check.py"

echo "Loading LaunchAgent com.l9.agent_ui_control..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "=== Local install complete ==="
echo "Pack:  $SCRIPT_DIR"
echo "Logs:  $LOG_DIR/"
echo "Queue: ~/.l9/mac_tasks/"
echo ""
echo "Smoke:"
echo "  python3 $SCRIPT_DIR/local_console.py shell --cmd 'echo ok'"
echo ""
echo "Tunnel is NOT installed. Opt-in only:"
echo "  bash $SCRIPT_DIR/install_remote_tunnel.sh"
