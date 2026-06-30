#!/usr/bin/env bash
# One-time machine bootstrap — installs sessionStart hook WITHOUT requiring repo symlinks.
# Usage: bash "$HOME/.cursor-governance/ops/scripts/install_cursor_hooks_bootstrap.sh"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

resolve_governance_paths_or_exit

BOOT_SRC="$GLOBAL_COMMANDS/ops/hooks/session_start_bootstrap.sh"
BOOT_DST="$HOME/.cursor/hooks/session-start-bootstrap.sh"
HOOKS_JSON="$HOME/.cursor/hooks.json"
TEMPLATE="$GLOBAL_COMMANDS/ops/hooks/hooks.json.template"

echo "=== Cursor hooks bootstrap (no repo symlinks required) ==="
echo "  GlobalCommands: $GLOBAL_COMMANDS"
echo ""

if [ ! -f "$BOOT_SRC" ]; then
  echo "ERROR: missing bootstrap hook: $BOOT_SRC"
  exit 1
fi

mkdir -p "$HOME/.cursor/hooks"
cp -f "$BOOT_SRC" "$BOOT_DST"
chmod +x "$BOOT_DST"
echo "INSTALLED: $BOOT_DST (real file, not symlink)"

python3 - "$HOOKS_JSON" "$TEMPLATE" "$BOOT_DST" <<'PY'
import json
import sys
from pathlib import Path

hooks_json = Path(sys.argv[1])
template = Path(sys.argv[2])
bootstrap_cmd = "./hooks/session-start-bootstrap.sh"

if template.is_file():
    data = json.loads(template.read_text())
else:
    data = {"version": 1, "hooks": {}}

existing = {"version": 1, "hooks": {}}
if hooks_json.exists():
    try:
        existing = json.loads(hooks_json.read_text())
    except json.JSONDecodeError:
        pass
if existing.get("version") != 1:
    existing = {"version": 1, "hooks": existing.get("hooks", {})}

merged = existing.setdefault("hooks", {})
template_hooks = data.get("hooks", {})

for event, entries in template_hooks.items():
    cur = merged.setdefault(event, [])
    known = {e.get("command") for e in cur if isinstance(e, dict)}
    for entry in entries:
        cmd = entry.get("command") if isinstance(entry, dict) else None
        if cmd and cmd not in known:
            cur.append(entry)
            known.add(cmd)

# sessionStart: bootstrap MUST be first; drop legacy orchestrator-only entry
ss = merged.setdefault("sessionStart", [])
ss = [e for e in ss if e.get("command") not in (
    "./hooks/session-start-memory-orchestrator.sh",
    "./hooks/session-start-bootstrap.sh",
)]
ss.insert(0, {"command": bootstrap_cmd, "timeout": 30})
merged["sessionStart"] = ss

hooks_json.parent.mkdir(parents=True, exist_ok=True)
hooks_json.write_text(json.dumps({"version": 1, "hooks": merged}, indent=2) + "\n")
print(f"OK: hooks.json updated — sessionStart -> {bootstrap_cmd}")
PY

# User-level symlinks (skills/commands/rules) — safe if already linked
link_or_update() {
  local link=$1 target=$2 label=$3
  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    rt=$(python3 -c "import os; print(os.path.realpath('$link'))")
    re=$(python3 -c "import os; print(os.path.realpath('$target'))")
    if [ "$rt" = "$re" ]; then
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

link_or_update "$HOME/.cursor/skills" "$GLOBAL_COMMANDS/skills" "~/.cursor/skills"
link_or_update "$HOME/.cursor/commands" "$GLOBAL_COMMANDS/commands" "~/.cursor/commands"
link_or_update "$HOME/.cursor/rules" "$GLOBAL_COMMANDS/rules" "~/.cursor/rules"

echo ""
echo "Bootstrap complete. Reload Cursor — sessionStart runs on every new chat."
echo "Optional: run setup_workspace_symlinks.sh in a repo to wire .cursor-commands."
