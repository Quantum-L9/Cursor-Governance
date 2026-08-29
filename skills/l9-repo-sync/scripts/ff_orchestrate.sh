#!/usr/bin/env bash
# /ff pipeline: classify leftover work, commit valuable dirt, reconcile a
# conflict-free stack, publish via make pr-check + make pr, then catch up.
# Never git push. Never activate_fresh. Never stash -u.
set -euo pipefail

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
CLONE="$(cd "$CLONE" && pwd)"
export CURSOR_GOVERNANCE_DIR="$CLONE"
export FF_GOV_ROOT="${FF_GOV_ROOT:-$CLONE}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRESERVE_SCRIPTS="$(cd "$SCRIPT_DIR/../../l9-git-work-preserve/scripts" && pwd)"

if [[ -x "$FF_GOV_ROOT/.venv/bin/python" ]]; then
  PY="$FF_GOV_ROOT/.venv/bin/python"
elif [[ -x "$CLONE/.venv/bin/python" ]]; then
  PY="$CLONE/.venv/bin/python"
else
  PY="python3"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="${L9_FF_STATE:-$HOME/.cursor/l9-ff-state}/${STAMP}"
mkdir -p "$WORKDIR"

echo "ff: orchestrate clone=$CLONE stamp=$STAMP"

"$PY" "$PRESERVE_SCRIPTS/classify_ff_work.py" --repo "$CLONE" >"$WORKDIR/classify.json"
if grep -q '"blocked": true' "$WORKDIR/classify.json"; then
  echo "FAIL: classify blocked (mixed dest commit or ambiguous path). Catch-up aborted." >&2
  cat "$WORKDIR/classify.json" >&2
  exit 1
fi

NOVEL_COUNT="$(git -C "$CLONE" rev-list --count HEAD --not --remotes=origin || echo 0)"
VALUABLE_DIRT="$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get("valuable_dirt") or [])+len(d.get("other_repo_dirt") or []))' "$WORKDIR/classify.json")"
VALUABLE_NOVEL="$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get("valuable_novel") or [])+len(d.get("other_repo_novel") or []))' "$WORKDIR/classify.json")"

if [ "$VALUABLE_DIRT" = "0" ] && [ "$VALUABLE_NOVEL" = "0" ]; then
  echo "OK: no valuable leftover dirt or novel commits — catch-up only"
  export FF_NOVEL_PUBLISHED=1
  exec bash "$SCRIPT_DIR/ff.sh"
fi

echo "OK: classified valuable_dirt=${VALUABLE_DIRT} valuable_novel=${VALUABLE_NOVEL}"

if ! "$PY" "$SCRIPT_DIR/reconcile_ff_stack.py" \
  --repo "$CLONE" \
  --classify "$WORKDIR/classify.json" \
  --out "$WORKDIR/stack.json"; then
  echo "FAIL: reconcile aborted — novel/dirt not published; catch-up skipped." >&2
  exit 1
fi

if ! bash "$SCRIPT_DIR/publish_ff_stack.sh" "$WORKDIR/stack.json"; then
  echo "FAIL: make pr-check / make pr failed — catch-up skipped so leftover work stays." >&2
  exit 1
fi

if [ "$NOVEL_COUNT" != "0" ] || [ "$VALUABLE_NOVEL" != "0" ]; then
  export FF_NOVEL_PUBLISHED=1
fi
echo "OK: published leftover work via make pr-check + make pr; catching up in place"
exec bash "$SCRIPT_DIR/ff.sh"
