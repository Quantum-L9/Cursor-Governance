#!/usr/bin/env bash
# Hook registry reconcile prunes entries that cannot run, sweeps dangling
# governance links, and leaves everything else alone. Runs against a throwaway
# $HOME so it never touches the machine's real ~/.cursor.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_SCRIPTS="$(cd "$SCRIPT_DIR/.." && pwd)"
RECONCILE="$OPS_SCRIPTS/reconcile_hooks_registry.py"
TEMPLATE="$(cd "$OPS_SCRIPTS/../hooks" && pwd)/hooks.json.template"
[ -f "$RECONCILE" ]
[ -f "$TEMPLATE" ]

TMP="$(mktemp -d "${TMPDIR:-/tmp}/hooks-registry.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
HOOKS_DIR="$HOME/.cursor/hooks"
HOOKS_JSON="$HOME/.cursor/hooks.json"
mkdir -p "$HOOKS_DIR"

run_reconcile() {
  python3 "$RECONCILE" --hooks-json "$HOOKS_JSON" --template "$TEMPLATE" \
    --hooks-dir "$HOOKS_DIR"
}
run_check() {
  python3 "$RECONCILE" --check --hooks-json "$HOOKS_JSON" --hooks-dir "$HOOKS_DIR"
}
fail() { echo "FAIL: $1" >&2; exit 1; }

# setup_workspace_symlinks.sh installs every template script before it
# reconciles; stub them so the template entries are live, as they are in use.
python3 - "$TEMPLATE" "$HOOKS_DIR" <<'PY'
import json, shlex, sys
from pathlib import Path

template, hooks_dir = Path(sys.argv[1]), Path(sys.argv[2])
for entries in json.loads(template.read_text())["hooks"].values():
    for entry in entries:
        for token in shlex.split(entry["command"]):
            if token.startswith("./hooks/"):
                script = hooks_dir / token[len("./hooks/"):]
                script.write_text("#!/bin/sh\nexit 0\n")
                script.chmod(0o755)
PY

# A healthy non-template hook: an agent-registered debug gate. Nothing may
# remove it just because the template does not declare it.
printf '#!/bin/sh\nexit 0\n' > "$HOOKS_DIR/l4-gate-abc123.sh"
chmod +x "$HOOKS_DIR/l4-gate-abc123.sh"

# The reported fault: a governance symlink whose target was deleted.
ln -sfn "$TMP/clone/Cursor-Governance/ops/hooks/sacred-wip-transport.sh" \
  "$HOOKS_DIR/sacred-wip-transport.sh"
# A dangling link owned by some other tool: must survive untouched.
ln -sfn "$TMP/elsewhere/other-tool.sh" "$HOOKS_DIR/other-tool.sh"

python3 - "$HOOKS_JSON" <<'PY'
import json, sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({"version": 1, "hooks": {
    "preToolUse": [
        {"command": "./hooks/sacred-wip-transport.sh", "matcher": "Read", "timeout": 5},
        {"command": "./hooks/sacred-wip-transport.sh", "matcher": "Write",
         "timeout": 5, "failClosed": True},
    ],
    # Interpreter prefix: the command does not start with ./hooks/, so a
    # prefix-only rule would leave this dead entry registered forever.
    "beforeShellExecution": [
        {"command": "bash ./hooks/l4-gate-abc123.sh"},
        {"command": "bash ./hooks/l4-gate-deleted.sh"},
        {"command": "/usr/local/bin/some-other-tool --flag"},
    ],
}}, indent=2) + "\n")
PY

# --- before the reconcile: the check must fail, and say which one blocks ---
if run_check > "$TMP/check-before.txt"; then
  fail "--check passed with two dead entries registered"
fi
grep -q "sacred-wip-transport.sh" "$TMP/check-before.txt" \
  || fail "--check did not name the dead hook"
grep -q "failClosed: blocks every guarded tool" "$TMP/check-before.txt" \
  || fail "--check did not escalate the failClosed entry"
grep -q "l4-gate-deleted.sh" "$TMP/check-before.txt" \
  || fail "--check missed the interpreter-prefixed dead entry"
echo "PASS: --check fails on dead registered hooks"

# --- reconcile ---
run_reconcile > "$TMP/reconcile.txt"
# sacred-wip is on the explicit retirement list, which runs first, so the
# general prune never sees it. The interpreter-prefixed entry is on no list
# and is removed by liveness alone -- the case no retirement list can cover.
grep -q "PRUNED: beforeShellExecution bash ./hooks/l4-gate-deleted.sh (target missing)" \
  "$TMP/reconcile.txt" || fail "reconcile did not report the liveness-pruned entry"
grep -q "REMOVED: dangling hooks/sacred-wip-transport.sh" "$TMP/reconcile.txt" \
  || fail "reconcile did not report the removed dangling link"

python3 - "$HOOKS_JSON" "$TEMPLATE" <<'PY'
import json, sys
from pathlib import Path

hooks = json.loads(Path(sys.argv[1]).read_text())["hooks"]
commands = {e["command"] for entries in hooks.values() for e in entries}

assert not any("sacred-wip" in c for c in commands), "dead entry survived"
assert "bash ./hooks/l4-gate-deleted.sh" not in commands, "dead prefixed entry survived"
assert "bash ./hooks/l4-gate-abc123.sh" in commands, "healthy non-template entry removed"
assert "/usr/local/bin/some-other-tool --flag" in commands, "foreign command removed"

for entries in json.loads(Path(sys.argv[2]).read_text())["hooks"].values():
    for entry in entries:
        assert entry["command"] in commands, f"template entry lost: {entry['command']}"
PY

[ ! -e "$HOOKS_DIR/sacred-wip-transport.sh" ] \
  && [ ! -L "$HOOKS_DIR/sacred-wip-transport.sh" ] \
  || fail "dangling governance link survived the sweep"
[ -L "$HOOKS_DIR/other-tool.sh" ] || fail "foreign dangling link was swept"
[ -x "$HOOKS_DIR/l4-gate-abc123.sh" ] || fail "healthy hook script was removed"
echo "PASS: reconcile prunes dead entries and dangling governance links"

# --- after the reconcile: the check passes, and a second run is a no-op ---
run_check > "$TMP/check-after.txt" || fail "--check still fails after reconcile"
[ ! -s "$TMP/check-after.txt" ] || fail "--check reported dead hooks after reconcile"
echo "PASS: --check passes after reconcile"

cp "$HOOKS_JSON" "$TMP/first.json"
run_reconcile > /dev/null
diff -u "$TMP/first.json" "$HOOKS_JSON" || fail "second reconcile changed hooks.json"
echo "PASS: reconcile is idempotent"

# --- the per-event collapses this module inherited must still happen ---
# An env-var-prefixed bootstrap variant and the superseded beforeShell and
# subagentStart predecessors all have live scripts, so liveness cannot remove
# them: only the retirement lists can.
printf '#!/bin/sh\nexit 0\n' > "$HOOKS_DIR/graphiti-gate-shell.sh"
printf '#!/bin/sh\nexit 0\n' > "$HOOKS_DIR/graphiti-gate-subagent.sh"
chmod +x "$HOOKS_DIR/graphiti-gate-shell.sh" "$HOOKS_DIR/graphiti-gate-subagent.sh"
python3 - "$HOOKS_JSON" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["hooks"]["sessionStart"].append(
    {"command": "GOVERNANCE_SYNC_PUSH=0 ./hooks/session-start-bootstrap.sh"}
)
d["hooks"]["beforeShellExecution"].append({"command": "./hooks/graphiti-gate-shell.sh"})
d["hooks"].setdefault("subagentStart", []).append(
    {"command": "./hooks/graphiti-gate-subagent.sh"}
)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
run_reconcile > /dev/null
python3 - "$HOOKS_JSON" <<'PY'
import json, sys
from pathlib import Path

hooks = json.loads(Path(sys.argv[1]).read_text())["hooks"]
starts = [e["command"] for e in hooks["sessionStart"]]
assert starts == ["./hooks/session-start-bootstrap.sh"], starts
bse = [e["command"] for e in hooks["beforeShellExecution"]]
assert "./hooks/graphiti-gate-shell.sh" not in bse, bse
assert bse[0] == "./hooks/before-shell-execution-gate.sh", bse
sub = [e["command"] for e in hooks["subagentStart"]]
assert sub == ["./hooks/lifecycle-subagent-start.sh subagent_start"], sub
PY
echo "PASS: per-event retirements still collapse live-but-superseded entries"
