#!/usr/bin/env bash
# Sanctioned removal of Python cache directories inside ONE workspace.
#
# CI-025 / IMP-08. Routine cache hygiene previously meant an agent reaching for
# `rm -rf`, which `ops/autonomy/git_guardrails.py` refuses when the target is
# unproven — correctly, because that is the command that deletes a parent when
# a variable expands empty. The answer is not to relax the guardrail. It is to
# provide a path whose target is provably disposable, so the general policy
# never has to bend:
#
#   * the only names removed are __pycache__ and .pytest_cache, matched exactly;
#   * they are regenerable by definition, which is what makes them disposable;
#   * the search is rooted at one workspace, refuses an empty or missing root,
#     and refuses `/`;
#   * .git/ is pruned, so no object store is ever a candidate;
#   * nothing else is touched, at any depth.
#
# Usage:
#   clean_pyc.sh [<workspace>]          remove (default: cwd)
#   CLEAN_PYC_MODE=plan clean_pyc.sh    list what WOULD be removed, delete nothing
#
# The plan mode mirrors `make clean`'s CLEAN_MODE idiom, and exists because
# "observe before destroying" is rule 54's requirement, not a nicety.
set -euo pipefail

MODE="${CLEAN_PYC_MODE:-apply}"

# `${1:-default}` treats an EMPTY argument as absent, so an caller whose
# variable expanded empty — `clean_pyc.sh "$WS"` with WS unset, which is the
# exact shape rule 54 refuses — would silently fall through to the default and
# clean whatever directory it happened to be in. Distinguish the two: passing
# nothing means "use the default", passing empty is a resolution failure.
if [[ $# -ge 1 ]]; then
  ROOT="$1"
else
  ROOT="${WS:-$PWD}"
fi

if [[ -z "$ROOT" ]]; then
  echo "clean-pyc: refusing — workspace root resolved empty" >&2
  exit 2
fi
if [[ ! -d "$ROOT" ]]; then
  echo "clean-pyc: refusing — not a directory: $ROOT" >&2
  exit 2
fi
ROOT="$(cd "$ROOT" && pwd)"
if [[ "$ROOT" == "/" ]]; then
  echo "clean-pyc: refusing — workspace root is /" >&2
  exit 2
fi

mapfile -t targets < <(
  find "$ROOT" \
    -name .git -prune -o \
    \( -type d \( -name __pycache__ -o -name .pytest_cache \) \) -print
)

if [[ "${#targets[@]}" -eq 0 ]]; then
  echo "clean-pyc: no Python cache directories under $ROOT"
  exit 0
fi

if [[ "$MODE" == "plan" ]]; then
  printf 'clean-pyc: would remove %d directories under %s\n' "${#targets[@]}" "$ROOT"
  printf '  %s\n' "${targets[@]}"
  exit 0
fi

# Each path came from the find above, so it exists, is a directory, and carries
# one of the two names. Re-assert the name here anyway: this is the line that
# deletes, and it should not trust a variable it did not just check.
removed=0
for target in "${targets[@]}"; do
  case "$(basename "$target")" in
    __pycache__ | .pytest_cache) ;;
    *)
      echo "clean-pyc: refusing unexpected target: $target" >&2
      exit 2
      ;;
  esac
  rm -rf -- "$target"
  removed=$((removed + 1))
done

printf 'clean-pyc: removed %d Python cache directories under %s\n' "$removed" "$ROOT"
