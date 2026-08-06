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

python3 - "$ROOT" "$BEFORE" "$AFTER" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "ops" / "scripts"))
from sync_generated_artifacts import is_generated_path  # noqa: E402

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
for line in new_lines:
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if is_generated_path(path):
        generated.append(path)
    else:
        non_generated.append(path)

if non_generated:
    print("NON_GENERATED_NEW_DIRTY:")
    for path in non_generated:
        print(f"  {path}")
    raise SystemExit(1)
print("GENERATED_NEW_DIRTY:")
for path in generated:
    print(f"  {path}")
raise SystemExit(0)
PY
