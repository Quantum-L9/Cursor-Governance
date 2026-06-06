#!/usr/bin/env bash
# Version: 3.4.0 — GlobalCommands ONLY via .cursor-commands (never under .cursor/governance)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

FALLBACK_LOG="$HOME/.cursor-globalcommands-fallback.log"
DISABLE_FALLBACK=${DISABLE_FALLBACK:-1}

if ! resolve_governance_paths; then
  if [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ] && [ "$DISABLE_FALLBACK" != "1" ]; then
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
    GOV_ROOT="$(dirname "$GLOBAL_COMMANDS")"
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] FALLBACK: $GLOBAL_COMMANDS" >> "$FALLBACK_LOG"
  else
    echo "ERROR: GlobalCommands not found under Dropbox."
    exit 1
  fi
fi

WORKSPACE_DIR="$(pwd)"

link_or_update() {
  local link=$1 target=$2 label=$3
  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    if [ "$(python3 -c "import os; print(os.path.realpath('$link'))")" = "$(python3 -c "import os; print(os.path.realpath('$target'))")" ]; then
      echo "OK: $label"
      return
    fi
    rm "$link"
  elif [ -e "$link" ]; then
    mv "$link" "${link}.backup.$(date +%Y%m%d_%H%M%S)"
  fi
  ln -sfn "$target" "$link"
  echo "LINKED: $label -> $target"
}

remove_repo_duplicate() {
  local path=$1 label=$2
  if [ -L "$path" ]; then
    rm "$path"
    echo "REMOVED: $label"
  elif [ -e "$path" ]; then
    mv "$path" "${path}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "BACKED UP: $label"
  else
    echo "OK: no $label"
  fi
}

setup_local_governance_dir() {
  local dir="$WORKSPACE_DIR/.cursor/governance"
  local law_link="$dir/CANONICAL_LAW.md"
  local law_src="$GOV_ROOT/CANONICAL_LAW.md"

  if [ -L "$dir" ]; then
    rm "$dir"
    echo "REMOVED: .cursor/governance root symlink (must be local dir, not Dropbox root)"
  elif [ -d "$dir" ] && [ -e "$dir/GlobalCommands" ]; then
    rm -rf "$dir/GlobalCommands" 2>/dev/null || true
    echo "REMOVED: .cursor/governance/GlobalCommands (use .cursor-commands only)"
  fi

  mkdir -p "$dir"
  link_or_update "$law_link" "$law_src" ".cursor/governance/CANONICAL_LAW.md"
}

echo "Governance root:  $GOV_ROOT"
echo "GlobalCommands:   $GLOBAL_COMMANDS"
echo "Workspace:        $WORKSPACE_DIR"
echo ""

link_or_update "$HOME/.cursor/skills" "$GLOBAL_COMMANDS/skills" "~/.cursor/skills"
link_or_update "$HOME/.cursor/commands" "$GLOBAL_COMMANDS/commands" "~/.cursor/commands"

link_or_update "$WORKSPACE_DIR/.cursor-commands" "$GLOBAL_COMMANDS" ".cursor-commands"
mkdir -p "$WORKSPACE_DIR/.cursor"

setup_local_governance_dir

remove_repo_duplicate "$WORKSPACE_DIR/.cursor/commands" ".cursor/commands"
remove_repo_duplicate "$WORKSPACE_DIR/.cursor/skills" ".cursor/skills"

install_session_end_governance_hook() {
  local hook_src="$GLOBAL_COMMANDS/ops/hooks/session_end_governance_backup.sh"
  local hook_link="$HOME/.cursor/hooks/governance-backup.sh"
  local session_start_src="$GLOBAL_COMMANDS/ops/hooks/session_start_code_graph_health.sh"
  local session_start_link="$HOME/.cursor/hooks/code-graph-health.sh"
  local hooks_json="$HOME/.cursor/hooks.json"
  local template="$GLOBAL_COMMANDS/ops/hooks/hooks.json.template"

  if [ ! -f "$hook_src" ]; then
    echo "WARN: session end hook missing: $hook_src"
    return 0
  fi

  mkdir -p "$HOME/.cursor/hooks"
  chmod +x "$hook_src"
  link_or_update "$hook_link" "$hook_src" "~/.cursor/hooks/governance-backup.sh"

  if [ -f "$session_start_src" ]; then
    chmod +x "$session_start_src"
    link_or_update "$session_start_link" "$session_start_src" "~/.cursor/hooks/code-graph-health.sh"
  else
    echo "WARN: sessionStart hook missing: $session_start_src"
  fi

  python3 - "$hooks_json" "$template" <<'PY'
import json
import sys
from pathlib import Path

hooks_json = Path(sys.argv[1])
template = Path(sys.argv[2])
data = json.loads(template.read_text())
if hooks_json.exists():
    try:
        existing = json.loads(hooks_json.read_text())
    except json.JSONDecodeError:
        existing = {"version": 1, "hooks": {}}
    if existing.get("version") != 1:
        existing = {"version": 1, "hooks": existing.get("hooks", {})}
    merged_hooks = existing.setdefault("hooks", {})
    for event, entries in data.get("hooks", {}).items():
        merged = merged_hooks.setdefault(event, [])
        known = {e.get("command") for e in merged if isinstance(e, dict)}
        for entry in entries:
            cmd = entry.get("command") if isinstance(entry, dict) else None
            if cmd and cmd not in known:
                merged.append(entry)
                known.add(cmd)
    data = existing
hooks_json.parent.mkdir(parents=True, exist_ok=True)
hooks_json.write_text(json.dumps(data, indent=2) + "\n")
print(f"OK: governance hooks registered in {hooks_json}")
PY
}

install_session_end_governance_hook

echo ""
bash "$SCRIPT_DIR/validate_governance_symlinks.sh" "$WORKSPACE_DIR"
