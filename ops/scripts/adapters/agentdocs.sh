#!/usr/bin/env bash
# IDE-profile adapter: agent docs (AGENTS.md / CLAUDE.md).
#
# Renders environment/ide/policy.json into a delimited managed block in the
# workspace's AGENTS.md and CLAUDE.md. Those two files are git-TRACKED, which is the
# entire point: .vscode/ and .cursor/ are untracked, so a cloud agent that clones the
# repo (Claude Code mobile, Cursor cloud agents) never sees the editor rendering. The
# generated block is the only carrier of formatter ownership that survives a clone.
#
# Usage:
#   bash adapters/agentdocs.sh WORKSPACE CLASS [--dry-run] [--force] [--quiet]
#
# Contract with the dispatcher:
#   stdout: "agentdocs=<state>" — written | current | absent | dry-run
#   exit 0 on success; nonzero only on a real error.
#
# Scope: workspace. The stamp lives in <workspace>/.vscode/.l9-agentdocs-hash so it
# never collides with the extension stamp (machine scope) or the settings stamp.
#
# The block is only ever written into a file that ALREADY EXISTS. This adapter does
# not create AGENTS.md in a repo that has none — that is a repo authoring decision,
# not something an IDE reconciler should make.

set -euo pipefail

WORKSPACE="${1:-}"
WS_CLASS="${2:-}"
shift 2 2>/dev/null || true

DRY_RUN=0
FORCE=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --quiet|-q) QUIET=1 ;;
  esac
done

[ -n "$WORKSPACE" ] && [ -n "$WS_CLASS" ] || {
  echo "usage: agentdocs.sh WORKSPACE CLASS [--dry-run] [--force] [--quiet]" >&2
  exit 2
}
[ -d "$WORKSPACE" ] || { echo "not a directory: $WORKSPACE" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=../resolve_governance_paths.sh
. "$SCRIPT_DIR/../resolve_governance_paths.sh"
resolve_governance_paths || { echo "governance root not found" >&2; exit 1; }

IDE_DIR="${L9_IDE_DIR:-$GLOBAL_COMMANDS/environment/ide}"
POLICY_FILE="$IDE_DIR/policy.json"
[ -f "$POLICY_FILE" ] || { echo "ownership policy missing: $POLICY_FILE" >&2; exit 1; }

L9_WORKSPACE="$WORKSPACE" \
L9_CLASS="$WS_CLASS" \
L9_POLICY="$POLICY_FILE" \
L9_DRY_RUN="$DRY_RUN" \
L9_FORCE="$FORCE" \
L9_QUIET="$QUIET" \
python3 <<'PY'
"""Render policy.json into a delimited managed block in AGENTS.md / CLAUDE.md."""
# Hooks may run this under the system python3 (3.9 on macOS), where `str | None` in a
# signature is a runtime TypeError. Defer annotation evaluation instead of downgrading.
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN L9 FORMATTER OWNERSHIP (generated — do not edit) -->"
END = "<!-- END L9 FORMATTER OWNERSHIP -->"
TARGETS = ("AGENTS.md", "CLAUDE.md")

workspace = Path(os.environ["L9_WORKSPACE"])
ws_class = os.environ["L9_CLASS"]
dry_run = os.environ["L9_DRY_RUN"] == "1"
force = os.environ["L9_FORCE"] == "1"

policy = json.loads(Path(os.environ["L9_POLICY"]).read_text())
try:
    klass = policy["classes"][ws_class]
except KeyError:
    msg = f"policy.json declares no ownership for class {ws_class!r}"
    raise SystemExit(msg) from None


def render_block() -> str:
    rows = []
    for entry in klass["ownership"]:
        languages = ", ".join(f"`{lang}`" for lang in entry["languages"])
        if entry.get("authority") == "governance":
            owner = f"**{entry['tool']}**"
            note = "bound by the governed IDE profile"
        else:
            owner = f"{entry['tool']} (this repo's own config)"
            note = "do not add a competing formatter config"
        rows.append(f"| {languages} | {owner} | {note} |")

    lines = [
        BEGIN,
        "",
        "## Formatter ownership",
        "",
        f"Workspace class: `{ws_class}` — {klass['description']}",
        "",
        "Exactly one formatter owns each language. Do not reformat a file with a tool"
        " other than its owner, and do not add config for a competing formatter:"
        " the result is a diff that churns on every save.",
        "",
        "| Languages | Owner | Note |",
        "|---|---|---|",
        *rows,
        "",
        "Generated from `environment/ide/policy.json` in the governance clone by"
        " `ops/scripts/adapters/agentdocs.sh`. Edit the policy, not this block.",
        "",
        END,
    ]
    return "\n".join(lines)


block = render_block()
block_hash = hashlib.sha256(block.encode()).hexdigest()

stamp_path = workspace / ".vscode" / ".l9-agentdocs-hash"
prior_hash = ""
if stamp_path.is_file():
    try:
        prior_hash = str(json.loads(stamp_path.read_text()).get("hash", ""))
    except (json.JSONDecodeError, OSError):
        pass

present = [workspace / name for name in TARGETS if (workspace / name).is_file()]
if not present:
    print("agentdocs=absent")
    raise SystemExit(0)

pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)


def updated_text(path: Path) -> str | None:
    """Return new file text, or None when the file already matches."""
    text = path.read_text()
    if pattern.search(text):
        replaced = pattern.sub(lambda _: block, text)
        return None if replaced == text else replaced
    separator = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + separator + block + "\n"


pending = {path: new for path in present if (new := updated_text(path)) is not None}

if not pending and prior_hash == block_hash and not force:
    print("agentdocs=current")
    raise SystemExit(0)

if dry_run:
    print("agentdocs=dry-run")
    raise SystemExit(0)

for path, new_text in pending.items():
    path.write_text(new_text)
    if os.environ["L9_QUIET"] != "1":
        # stderr: stdout carries the single state word the dispatcher parses.
        print(f"agentdocs: updated {path.name}", file=sys.stderr)

stamp_path.parent.mkdir(parents=True, exist_ok=True)
stamp_path.write_text(
    json.dumps({"hash": block_hash, "class": ws_class}, indent=2) + "\n"
)
print("agentdocs=written" if pending else "agentdocs=current")
PY
