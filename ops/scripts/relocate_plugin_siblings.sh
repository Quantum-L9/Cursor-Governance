#!/usr/bin/env bash
# Move every ~/.cursor/plugins/local/l9-governance.* sibling out to
# ~/.cursor/l9/backups/plugins/<stamp>/ so Cursor stops loading it as a
# plugin. Moves only; never deletes. Prints RELOCATED lines, or OK when clean.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/plugin_siblings.sh
source "$SCRIPT_DIR/lib/plugin_siblings.sh"

l9_relocate_plugin_siblings
