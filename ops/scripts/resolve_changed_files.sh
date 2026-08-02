#!/usr/bin/env bash
# Resolve new/modified files for local PR gates (changed-files only).
# Mirrors l9-ci-core tools/l9_repo/change_policy.resolve_changed_files semantics:
#   explicit files win; else merge-base(base, HEAD) ∪ working-tree (staged/unstaged/untracked).
# Fail-closed if no comparison ref and the working tree is clean (no false empty set).
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

comparison_files() {
  local base="$1"
  local mb
  mb="$(git merge-base "$base" HEAD)"
  git -c core.quotePath=false diff --no-renames --name-only --diff-filter=ACMR "$mb" HEAD
}

WORKING="$(working_files || true)"
BASE=""
COMMITTED=""
SOURCE=""

if BASE="$(pick_base)"; then
  COMMITTED="$(comparison_files "$BASE" || true)"
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

{
  printf '%s\n' "$COMMITTED"
  printf '%s\n' "$WORKING"
} | awk 'NF' | sort -u

echo "SOURCE:$SOURCE" >&2
if [[ -z "$( {
  printf '%s\n' "$COMMITTED"
  printf '%s\n' "$WORKING"
} | awk 'NF' | sort -u)" ]]; then
  echo "ERROR: resolved empty change set against $BASE (nothing to gate)" >&2
  exit 1
fi
