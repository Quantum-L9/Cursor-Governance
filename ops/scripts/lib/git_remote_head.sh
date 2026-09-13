#!/usr/bin/env bash
# Bind refs/remotes/origin/HEAD after a prune, including shallow single-branch
# checkouts where Git has not fetched the remote's advertised default branch.
#
# This helper is deliberately fail-soft: callers use it for local telemetry,
# not a publication or authorization decision. It never changes the remote.
# shellcheck shell=bash

GIT_REMOTE_HEAD_ERROR=""

bind_origin_head() {
  local workspace="${1:-}"
  local symref default_branch refspec

  GIT_REMOTE_HEAD_ERROR=""
  if [ -z "$workspace" ] || ! git -C "$workspace" rev-parse --git-dir >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="workspace is not a Git repository"
    return 1
  fi
  if ! git -C "$workspace" remote get-url origin >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="origin remote is not configured"
    return 1
  fi
  if git -C "$workspace" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
    return 0
  fi

  # `remote set-head -a` only creates origin/HEAD when its target remote-tracking
  # ref is already present. A depth-1, --single-branch clone lacks that ref, so
  # discover the advertised target and fetch only that one bounded ref first.
  symref="$(git -C "$workspace" ls-remote --symref origin HEAD 2>/dev/null)" || {
    GIT_REMOTE_HEAD_ERROR="could not discover origin's advertised default branch"
    return 1
  }
  default_branch="$(printf '%s\n' "$symref" | awk '/^ref: refs\/heads\// {sub("refs/heads/", "", $2); print $2; exit}')"
  if [ -z "$default_branch" ]; then
    GIT_REMOTE_HEAD_ERROR="origin did not advertise a HEAD branch"
    return 1
  fi
  if ! git -C "$workspace" check-ref-format --branch "$default_branch" >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="origin advertised an invalid HEAD branch name"
    return 1
  fi

  refspec="+refs/heads/$default_branch:refs/remotes/origin/$default_branch"
  if ! git -C "$workspace" fetch --no-tags origin "$refspec" >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="could not fetch origin's advertised default branch '$default_branch'"
    return 1
  fi
  if ! git -C "$workspace" remote set-head origin -a >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="could not bind origin/HEAD to '$default_branch'"
    return 1
  fi
  if ! git -C "$workspace" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
    GIT_REMOTE_HEAD_ERROR="origin/HEAD remained unresolved after fetching '$default_branch'"
    return 1
  fi
}

_git_remote_head_is_sourced() {
  [ "${BASH_SOURCE[0]}" != "$0" ]
}

# A CLI entry point seals this helper as the single executable binding path for
# non-shell callers. They may orchestrate their own prune/reporting, but must
# delegate all default-ref discovery, fetch, and origin/HEAD mutation here.
if ! _git_remote_head_is_sourced; then
  case "${1:-}" in
    -h | --help)
      cat <<'USAGE'
usage: git_remote_head.sh WORKSPACE

Bind refs/remotes/origin/HEAD in WORKSPACE. The helper discovers origin's
advertised default branch, fetches only that remote-tracking ref when absent,
and binds origin/HEAD. It changes no remote configuration.
USAGE
      exit 0
      ;;
    "")
      echo "usage: git_remote_head.sh WORKSPACE" >&2
      exit 2
      ;;
  esac
  if bind_origin_head "$1"; then
    git -C "$1" symbolic-ref --short refs/remotes/origin/HEAD
    exit 0
  fi
  echo "git_remote_head: $GIT_REMOTE_HEAD_ERROR" >&2
  exit 1
fi
