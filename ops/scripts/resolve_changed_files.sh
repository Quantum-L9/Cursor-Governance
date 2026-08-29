#!/usr/bin/env bash
# Resolve new/modified files for local PR gates (changed-files only).
# Mirrors l9-ci-core tools/l9_repo/change_policy.resolve_changed_files semantics:
#   explicit files win; else merge-base(base, HEAD) ∪ working-tree (staged/unstaged/untracked).
# Fail-closed if no comparison ref and the working tree is clean (no false empty set).
#
# Scratch / reference trees (WIP/, archives, harvest dumps) are dropped from the
# default change set so they never block make pr or burn CI bandwidth. Explicit
# path arguments still win unchanged (escape hatch for intentional scans).
#
# Usage:
#   resolve_changed_files.sh [--base REF] [--] [explicit paths...]
# Env:
#   PR_BASE   default comparison ref (origin/main, then main, then master)
#   WS / cwd  repository root
set -euo pipefail

WS="${WS:-$(pwd)}"
WS="$(cd "$WS" && pwd)"
BASE_REF="${PR_BASE:-}"
EXPLICIT=()

# Keep in sync with ops/scripts/run_pr_security.sh EXCLUDE_PREFIXES and
# .pre-commit-config.yaml exclude.
SCRATCH_PREFIXES=(
  _archived/ _archive/ archive/ archived/
  WIP/ current_work/ C_GOV_FILES/
  .venv/ node_modules/ reports/ workflows/
)

is_scratch() {
  local f="$1" p
  for p in "${SCRATCH_PREFIXES[@]}"; do
    [[ "$f" == "$p"* ]] && return 0
  done
  return 1
}

filter_scratch() {
  local f
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    is_scratch "$f" && continue
    printf '%s\n' "$f"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      BASE_REF="${2:?}"
      shift 2
      ;;
    --)
      shift
      EXPLICIT+=("$@")
      break
      ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
    *)
      EXPLICIT+=("$1")
      shift
      ;;
  esac
done

cd "$WS"

if [[ ${#EXPLICIT[@]} -gt 0 ]]; then
  printf '%s\n' "${EXPLICIT[@]}" | awk 'NF' | sort -u
  echo "SOURCE:explicit" >&2
  exit 0
fi

pick_base() {
  local cand
  for cand in "$BASE_REF" origin/main main master; do
    [[ -z "$cand" ]] && continue
    if git rev-parse --verify "$cand" >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

working_files() {
  # Unstaged vs HEAD, staged, and untracked (exclude-standard).
  {
    git -c core.quotePath=false diff --no-renames --name-only --diff-filter=ACMR HEAD 2>/dev/null || true
    git -c core.quotePath=false diff --cached --no-renames --name-only --diff-filter=ACMR 2>/dev/null || true
    git -c core.quotePath=false ls-files --others --exclude-standard 2>/dev/null || true
  } | awk 'NF' | sort -u
}

# Exit 2 = the comparison could not be computed (distinct from "computed, and
# it is empty"). Collapsing those two is how a gate reports PASS on work it
# never looked at.
comparison_files() {
  local base="$1"
  local mb
  if ! mb="$(git merge-base "$base" HEAD 2>/dev/null)" || [[ -z "$mb" ]]; then
    # A cloud SessionStart fetches the base with `--depth 1`, so the base and
    # this branch can share no reachable ancestor and merge-base fails outright.
    # Deepen once and retry before giving up: on a shallow clone the history is
    # missing, not absent.
    if [[ -f "$(git rev-parse --git-dir)/shallow" ]]; then
      git fetch --deepen=200 origin "${base#origin/}" >/dev/null 2>&1 \
        || git fetch --unshallow origin >/dev/null 2>&1 || true
      mb="$(git merge-base "$base" HEAD 2>/dev/null || true)"
    fi
  fi
  if [[ -z "$mb" ]]; then
    echo "ERROR: no merge base between $base and HEAD — the comparison is UNKNOWN, not empty" >&2
    return 2
  fi
  git -c core.quotePath=false diff --no-renames --name-only --diff-filter=ACMR "$mb" HEAD
}

WORKING="$(working_files || true)"
BASE=""
COMMITTED=""
SOURCE=""

if BASE="$(pick_base)"; then
  COMPARISON_RC=0
  COMMITTED="$(comparison_files "$BASE")" || COMPARISON_RC=$?
  if [[ "$COMPARISON_RC" -eq 2 ]]; then
    # Fail closed. Reporting an undeterminable comparison as "nothing changed"
    # let the gate PASS a branch of 117 changed files without running a single
    # checker, because a `--depth 1` base has no merge base with it.
    echo "ERROR: cannot determine the change set against $BASE (no merge base)." >&2
    echo "       Deepen the clone (git fetch --unshallow) or pass explicit paths." >&2
    exit 1
  fi
  if [[ -n "$WORKING" && -n "$COMMITTED" ]]; then
    SOURCE="comparison+working-tree base=$BASE"
  elif [[ -n "$COMMITTED" ]]; then
    SOURCE="comparison base=$BASE"
  else
    SOURCE="working-tree;comparison-empty base=$BASE"
  fi
else
  if [[ -z "$WORKING" ]]; then
    echo "ERROR: no changed-file context — provide files, set PR_BASE, or have a dirty tree" >&2
    exit 1
  fi
  SOURCE="working-tree;comparison-unavailable"
fi

RAW="$(
  {
    printf '%s\n' "$COMMITTED"
    printf '%s\n' "$WORKING"
  } | awk 'NF' | sort -u
)"
if [[ -z "$RAW" ]]; then
  if [[ "${PR_ALLOW_EMPTY:-0}" = "1" ]]; then
    echo "SOURCE:empty" >&2
    exit 0
  fi
  echo "ERROR: resolved empty change set against $BASE (nothing to gate)" >&2
  exit 1
fi

RESOLVED="$(printf '%s\n' "$RAW" | filter_scratch || true)"
printf '%s\n' "$RESOLVED"
echo "SOURCE:$SOURCE" >&2
# Empty after scratch exclusions is success: only WIP/archive/etc. changed.
# Callers (pre-commit / security) treat an empty file list as nothing-in-scope.
