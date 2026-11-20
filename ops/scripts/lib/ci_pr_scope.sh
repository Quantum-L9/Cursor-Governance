#!/usr/bin/env bash
# Changed-file scope for `make test` inside a GitHub Actions pull_request run.
# shellcheck shell=bash
#
# Core's required Analyze job runs `make test` on a depth-1, token-free checkout
# of github.sha. For pull_request, github.sha is the merge commit
# refs/pull/N/merge: parent 1 is the base tip and parent 2 the PR head, so
# `git diff HEAD^1 HEAD` is exactly what the PR changes on top of its base. The
# repository is public, so the two parents are fetched by SHA without a token.
#
# The selection policy is not re-implemented here. The caller passes the list to
# run_python_test_suites.py --profile local --changed-file, the same path the
# required Test Suite (.github/workflows/l9-lint-test.yml) takes for pull
# requests; paths missing on HEAD are dropped the same way.
#
# Usage:
#   source ops/scripts/lib/ci_pr_scope.sh
#   if paths="$(l9_ci_pr_changed_files)"; then ...--changed-file...; fi
#
# Exit 0 (SELECTED): stdout is the changed paths that exist on HEAD, possibly
# none for a deletion-only pull request. The caller must not treat an empty
# list as the full suite.
# Exit 2 (UNKNOWN or POLICY_PR_DEEP_FORBIDDEN): a pull_request whose scope
# cannot be proved, or L9_CI_FULL_SUITE=1 on a pull_request. The caller exits
# with this status. Never a signal to run --profile ci or the full suite.
# Exit 1: not a pull_request. A local or push caller may run the non-PR
# profile. Never exits the caller. Run from the repository root.

_l9_ci_scope_full() {
  # Quiet outside CI, so a local `make test` prints nothing new.
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    printf '[ci-scope] full suite: %s\n' "$1" >&2
  fi
}

_l9_ci_scope_unknown() {
  printf 'PR_SCOPE_UNKNOWN: %s\n' "$1" >&2
}

_l9_ci_path_unsafe() {
  case "$1" in
    -* | /* | .. | ../* | */.. | */../*) return 0 ;;
    *) return 1 ;;
  esac
}

l9_ci_pr_changed_files() {
  local sha parents diff_file path count=0
  local -a kept=()
  if [[ "${L9_CI_FULL_SUITE:-}" == "1" ]]; then
    if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
      printf 'POLICY_PR_DEEP_FORBIDDEN: L9_CI_FULL_SUITE=1\n' >&2
      return 2
    fi
    _l9_ci_scope_full "L9_CI_FULL_SUITE=1"
    return 1
  fi
  if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
    return 1
  fi
  if [[ "${GITHUB_EVENT_NAME:-}" != "pull_request" ]]; then
    _l9_ci_scope_full "event ${GITHUB_EVENT_NAME:-unset}"
    return 1
  fi
  if ! sha="$(git rev-parse --verify -q HEAD 2>/dev/null)"; then
    _l9_ci_scope_unknown "no HEAD commit"
    return 2
  fi
  if ! git rev-parse --verify -q 'HEAD^2' >/dev/null 2>&1 &&
    [[ "$(git rev-parse --is-shallow-repository 2>/dev/null)" == "true" ]]; then
    if ! git fetch --quiet --no-tags --depth=2 origin "$sha" >/dev/null 2>&1; then
      _l9_ci_scope_unknown "could not fetch the merge commit's parents"
      return 2
    fi
  fi
  # rev-list --parents prints the commit followed by its parents.
  parents="$(git rev-list --parents -n 1 HEAD 2>/dev/null | wc -w | tr -d ' ')"
  if [[ "$parents" != "3" ]]; then
    _l9_ci_scope_unknown "HEAD is not a two-parent merge commit"
    return 2
  fi
  diff_file="$(mktemp)"
  if ! git diff -z --name-only --no-renames 'HEAD^1' HEAD >"$diff_file" 2>/dev/null; then
    rm -f "$diff_file"
    _l9_ci_scope_unknown "git diff against the base parent failed"
    return 2
  fi
  if [[ ! -s "$diff_file" ]]; then
    rm -f "$diff_file"
    _l9_ci_scope_unknown "the merge commit changes no files"
    return 2
  fi
  while IFS= read -r -d '' path; do
    [[ -z "$path" ]] && continue
    if _l9_ci_path_unsafe "$path"; then
      rm -f "$diff_file"
      _l9_ci_scope_unknown "unsafe path"
      return 2
    fi
    if [[ -e "$path" ]]; then
      kept+=("$path")
    fi
  done <"$diff_file"
  rm -f "$diff_file"
  if ((${#kept[@]})); then
    printf '%s\n' "${kept[@]}"
    count=${#kept[@]}
  fi
  printf '[ci-scope] pull_request: %s changed path(s) on HEAD\n' "$count" >&2
  printf '[ci-scope] SELECTED\n' >&2
  return 0
}
