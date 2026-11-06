#!/usr/bin/env bash
# Changed-file scope for `make test` inside a GitHub Actions pull_request run.
# shellcheck shell=bash
#
# Core's required Analyze job runs `make test` on a depth-1, token-free checkout
# of github.sha, so the test phase has no PR file list and ran the whole suite on
# every pull request. For pull_request, github.sha is the merge commit
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
# Returns 0 with the changed paths that exist on HEAD on stdout (possibly none,
# for a deletion-only PR). Returns 1 whenever the full suite should run instead:
# not GitHub Actions, not pull_request, L9_CI_FULL_SUITE=1, HEAD not a
# two-parent merge commit, the parents could not be fetched, or the raw diff is
# empty. Never exits the caller. Run from the repository root.

_l9_ci_scope_full() {
  # Quiet outside CI, so a local `make test` prints nothing new.
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    printf '[ci-scope] full suite: %s\n' "$1" >&2
  fi
}

l9_ci_pr_changed_files() {
  local sha parents raw path count=0
  if [[ "${L9_CI_FULL_SUITE:-}" == "1" ]]; then
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
    _l9_ci_scope_full "no HEAD commit"
    return 1
  fi
  if ! git rev-parse --verify -q 'HEAD^2' >/dev/null 2>&1 &&
    [[ "$(git rev-parse --is-shallow-repository 2>/dev/null)" == "true" ]]; then
    if ! git fetch --quiet --no-tags --depth=2 origin "$sha" >/dev/null 2>&1; then
      _l9_ci_scope_full "could not fetch the merge commit's parents"
      return 1
    fi
  fi
  # rev-list --parents prints the commit followed by its parents.
  parents="$(git rev-list --parents -n 1 HEAD 2>/dev/null | wc -w | tr -d ' ')"
  if [[ "$parents" != "3" ]]; then
    _l9_ci_scope_full "HEAD is not a two-parent merge commit"
    return 1
  fi
  if ! raw="$(git diff --name-only --no-renames 'HEAD^1' HEAD 2>/dev/null)"; then
    _l9_ci_scope_full "git diff against the base parent failed"
    return 1
  fi
  if [[ -z "$raw" ]]; then
    _l9_ci_scope_full "the merge commit changes no files"
    return 1
  fi
  while IFS= read -r path; do
    if [[ -n "$path" && -e "$path" ]]; then
      printf '%s\n' "$path"
      count=$((count + 1))
    fi
  done <<<"$raw"
  printf '[ci-scope] pull_request: %s changed path(s) on HEAD\n' "$count" >&2
  return 0
}
