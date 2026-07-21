#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: scripts
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: One-shot install — pip install, config write, preflight, done
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  L9 Graphite Memory — Install & Configure           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Step 1: Install package
echo "→ Step 1: Installing l9-graphite-memory..."
cd "$REPO_ROOT"
pip install -e ".[zep,server]" --quiet
echo "  ✓ Package installed"
echo ""

# Step 2: Write agent configs
echo "→ Step 2: Writing MCP configs for agents..."
python3 "$SCRIPT_DIR/write_cursor_config.py" 2>/dev/null && echo "  ✓ Cursor config written" || echo "  ⚠ Cursor config skipped"
python3 "$SCRIPT_DIR/write_claude_config.py" 2>/dev/null && echo "  ✓ Claude Desktop config written" || echo "  ⚠ Claude Desktop config skipped"
echo ""

# Step 3: Run preflight
echo "→ Step 3: Running preflight checks..."
echo ""
bash "$SCRIPT_DIR/preflight.sh"
PREFLIGHT_RC=$?
echo ""

if [ $PREFLIGHT_RC -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ✓ INSTALLATION COMPLETE                            ║"
    echo "║                                                     ║"
    echo "║  Start server:                                      ║"
    echo "║    python -m l9_graphite_memory.server              ║"
    echo "║                                                     ║"
    echo "║  Or restart Cursor/Claude — they'll auto-connect.   ║"
    echo "╚══════════════════════════════════════════════════════╝"
else
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ⚠ INSTALLATION COMPLETE (with warnings)            ║"
    echo "║                                                     ║"
    echo "║  Resolve preflight warnings, then start server:     ║"
    echo "║    python -m l9_graphite_memory.server              ║"
    echo "╚══════════════════════════════════════════════════════╝"
fi
