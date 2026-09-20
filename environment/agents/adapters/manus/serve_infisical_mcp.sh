#!/usr/bin/env bash
# Launch the native, stdio-based Manus Infisical capability connector.
#
# Connector-only L9_MANUS_INFISICAL_* values are inherited by this process.
# This launcher deliberately does not source a profile, write an environment
# file, call the Cursor bootstrap, or print any configuration values.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${L9_MANUS_INFISICAL_PYTHON:-python3}"

exec "$PYTHON_BIN" "$SCRIPT_DIR/infisical_mcp_server.py"
