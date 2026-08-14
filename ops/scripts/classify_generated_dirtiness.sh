#!/usr/bin/env bash
# Compare two git porcelain snapshots. Exit 0 if every NEW/changed line's path
# is a generated-artifact allowlist path (or there are no new lines).
# Usage: classify_generated_dirtiness.sh <repo_root> <status_before_file> [status_after_file]
# If status_after_file omitted, uses current git status --porcelain.
set -euo pipefail

ROOT="${1:?repo root required}"
BEFORE="${2:?status_before file required}"
AFTER="${3:-}"
ROOT="$(cd "$ROOT" && pwd)"
cd "$ROOT"

if [[ -z "$AFTER" ]]; then
  AFTER="$(mktemp)"
  trap 'rm -f "$AFTER"' EXIT
  git status --porcelain >"$AFTER"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 - "$ROOT" "$BEFORE" "$AFTER" "$SCRIPT_DIR/lib" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
# Shared with attribute_tree_writers.sh so "generated" and "scratch" cannot
# drift between "does this fail the gate" and "who wrote it".
sys.path.insert(0, sys.argv[4])
import dirtiness  # noqa: E402

before = {
    line
    for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
    if line.strip()
}
after = {
    line
    for line in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines()
    if line.strip()
}
new_lines = sorted(after - before)
if not new_lines:
    print("OK: no new dirtiness")
    raise SystemExit(0)

non_generated: list[str] = []
generated: list[str] = []
scratch: list[str] = []
for line in new_lines:
    path = dirtiness.porcelain_path(line)
    classification = dirtiness.classify_path(root, path)
    if classification == "scratch":
        scratch.append(path)
    elif classification == "generated":
        generated.append(path)
    else:
        non_generated.append(path)

if non_generated:
    print("NON_GENERATED_NEW_DIRTY:")
    for path in non_generated:
        print(f"  {path}")
    raise SystemExit(1)
if scratch:
    print("SCRATCH_NEW_DIRTY (allowed):")
    for path in scratch:
        print(f"  {path}")
if generated:
    print("GENERATED_NEW_DIRTY:")
    for path in generated:
        print(f"  {path}")
elif not scratch:
    print("OK: no new dirtiness")
raise SystemExit(0)
PY
