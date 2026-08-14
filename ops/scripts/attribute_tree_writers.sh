#!/usr/bin/env bash
# Name the actual writer behind gate dirtiness — do not trust pre-commit's blame.
#
# pre-commit prints "- files were modified by this hook" for whichever hook was
# running when the tracked worktree changed (pre_commit/commands/run.py
# _run_single_hook threads diff_before hook to hook). That names a wall-clock
# window, not an author. This script reports what actually changed, how each
# path is classified, who held the repo-write lock, and — for hooks declared
# read_only in ops/config/precommit-hook-contract.json — replays them one at a
# time under the lock to prove whether they write at all.
#
# Usage: attribute_tree_writers.sh <workspace> <status_before_file> [precommit_log]
# Always exits 0: this is a diagnostic, never a gate.
#
# Env:
#   PR_ATTRIBUTE_REPLAY=0   skip the read_only replay (report only)

set -uo pipefail

WS="${1:?workspace required}"
BEFORE="${2:?status_before file required}"
PRECOMMIT_LOG="${3:-}"
WS="$(cd "$WS" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$WS"

# shellcheck source=lib/repo_write_lock.sh
. "$SCRIPT_DIR/lib/repo_write_lock.sh"
# shellcheck source=lib/precommit_log.sh
. "$SCRIPT_DIR/lib/precommit_log.sh"

AFTER="$(mktemp)"
REPLAY="$(mktemp)"
trap 'rm -f "$AFTER" "$REPLAY"' EXIT
git status --porcelain >"$AFTER"

echo "=== tree-writer attribution ==="

# Hooks pre-commit blamed, and hooks that genuinely returned non-zero.
blamed=""
failed=""
if [[ -n "$PRECOMMIT_LOG" && -f "$PRECOMMIT_LOG" ]]; then
  blamed="$(precommit_blamed_hooks "$PRECOMMIT_LOG" | tr '\n' ' ')"
  failed="$(precommit_failed_hooks "$PRECOMMIT_LOG" | awk '{print $1}' | sort -u | tr '\n' ' ')"
fi
[[ -n "$blamed" ]] && echo "pre-commit blamed (window, not author): ${blamed% }"
[[ -n "$failed" ]] && echo "pre-commit hooks that actually failed:   ${failed% }"

holder="$(repo_write_lock_holder "$WS")"
if [[ -n "$holder" ]]; then
  echo "repo-write lock ledger: $holder"
else
  echo "repo-write lock ledger: unheld at attribution time"
fi

# Replay every read_only hook individually, under the lock, measuring the
# tracked diff around each. A read_only hook that shows a delta here is a real
# contract violation; one that shows none is exonerated and the writer is
# external to pre-commit.
replayed_note="skipped"
if [[ "${PR_ATTRIBUTE_REPLAY:-1}" != "0" ]] && command -v pre-commit >/dev/null 2>&1; then
  read_only_ids="$(python3 - "$SCRIPT_DIR/../config/precommit-hook-contract.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    hooks = json.loads(path.read_text(encoding="utf-8")).get("hooks", {})
except (OSError, json.JSONDecodeError):
    hooks = {}
print(" ".join(sorted(k for k, v in hooks.items() if v.get("mode") == "read_only")))
PY
)"
  if [[ -n "$read_only_ids" ]]; then
    repo_write_lock_acquire "$WS" "${PR_LOCK_WAIT_S:-30}" || true
    echo "--- read_only hook replay (declared read-only must show no delta) ---"
    for hook_id in $read_only_ids; do
      before_digest="$(git diff --no-ext-diff --no-textconv --ignore-submodules | shasum | awk '{print $1}')"
      pre-commit run "$hook_id" --all-files >/dev/null 2>&1
      after_digest="$(git diff --no-ext-diff --no-textconv --ignore-submodules | shasum | awk '{print $1}')"
      if [[ "$before_digest" = "$after_digest" ]]; then
        echo "  $hook_id: no tracked delta (read_only honoured)"
        printf '%s\tclean\n' "$hook_id" >>"$REPLAY"
      else
        echo "  $hook_id: WROTE tracked files — contract violation, update ops/config/precommit-hook-contract.json"
        printf '%s\tviolation\n' "$hook_id" >>"$REPLAY"
      fi
    done
    replayed_note="ran"
  fi
fi

python3 - "$WS" "$BEFORE" "$AFTER" "$REPLAY" "${blamed% }" "$replayed_note" "$SCRIPT_DIR/lib" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, sys.argv[7])
import dirtiness  # noqa: E402

before = {ln for ln in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if ln.strip()}
after = {ln for ln in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if ln.strip()}
replay_raw = Path(sys.argv[4]).read_text(encoding="utf-8").splitlines()
blamed = [h for h in sys.argv[5].split() if h]
replay_note = sys.argv[6]

replay = {}
for line in replay_raw:
    if "\t" in line:
        hook_id, verdict = line.split("\t", 1)
        replay[hook_id] = verdict

new_lines = sorted(after - before)
entries = []
for line in new_lines:
    path = dirtiness.porcelain_path(line)
    entries.append(
        {
            "path": path,
            "status": line[:2],
            "tracked": not line.startswith("??"),
            "classification": dirtiness.classify_path(root, path),
        }
    )

print("--- changed paths ---")
if not entries:
    print("  (none — dirtiness resolved before attribution ran)")
for entry in entries:
    domain = "tracked" if entry["tracked"] else "untracked"
    print(f"  [{entry['classification']:<9}] [{domain:<9}] {entry['status']} {entry['path']}")

untracked_only = bool(entries) and not any(e["tracked"] for e in entries)
if untracked_only:
    print(
        "note: untracked-only churn. pre-commit compares `git diff` (tracked, unstaged),\n"
        "      so it cannot have produced a 'files were modified by this hook' verdict here."
    )

exonerated = [h for h in blamed if replay.get(h) == "clean"]
violations = [h for h, verdict in replay.items() if verdict == "violation"]
if exonerated:
    print(
        "verdict: "
        + ", ".join(exonerated)
        + " declared read_only and showed no delta on replay — the writer was concurrent, "
          "not the hook. Check the lock ledger above and any backgrounded reconciler."
    )
if violations:
    print("verdict: contract violation by " + ", ".join(sorted(violations)))

receipt = root / ".l9" / "pr" / "gate-dirtiness.json"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(
    json.dumps(
        {
            "blamed_hooks": blamed,
            "replay": replay,
            "replay_status": replay_note,
            "exonerated_hooks": exonerated,
            "contract_violations": sorted(violations),
            "changed": entries,
            "untracked_only": untracked_only,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
print(f"receipt: {receipt.relative_to(root)}")
PY

exit 0
