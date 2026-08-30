#!/usr/bin/env bash
# Post-/ff shelf cleanup: unlink open-PR copies, verify Claude Code–clean tree.
set -euo pipefail

ROOT="$(cd "${1:-.}" && pwd)"
GOV="${GOV_ROOT:-$HOME/.cursor-governance}"
PY="${GOV}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

PRUNE="${ROOT}/skills/l9-git-work-preserve/scripts/prune_open_pr_copies.py"
VERIFY="${ROOT}/ops/scripts/verify_worktree_clean.py"
if [[ ! -f "$PRUNE" ]]; then
  PRUNE="${GOV}/skills/l9-git-work-preserve/scripts/prune_open_pr_copies.py"
  VERIFY="${GOV}/ops/scripts/verify_worktree_clean.py"
fi

echo "=== run_ff_post_shelf: prune open-PR copies (report) ==="
"$PY" "$PRUNE" --repo "$ROOT" || true
echo "=== run_ff_post_shelf: prune open-PR copies (apply) ==="
"$PY" "$PRUNE" --repo "$ROOT" --apply || true
echo "=== run_ff_post_shelf: verify worktree clean ==="
if "$PY" "$VERIFY" --workspace "$ROOT"; then
  echo "OK: verify_worktree_clean passed"
  exit 0
fi
echo "WARN: verify_worktree_clean failed — shelf publish or dirt-close may still be required" >&2
exit 1
