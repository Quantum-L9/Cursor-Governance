#!/usr/bin/env bash
# Thin shim — Cursor hook install/self-heal lives in setup_workspace_symlinks.sh
# (CANONICAL_LAW: one wiring path). Docs historically named this script.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WS="${1:-${CURSOR_PROJECT_DIR:-$(pwd)}}"
exec bash "$ROOT/ops/scripts/setup_workspace_symlinks.sh" "$WS"
