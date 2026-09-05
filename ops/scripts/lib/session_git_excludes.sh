#!/usr/bin/env bash
# Option B (Cursor-Governance#281): session-injected paths live in
# $GIT_COMMON_DIR/info/exclude (local, uncommitted) and optionally in the
# machine core.excludesFile. Tracked .gitignore is never mutated — that is
# Option A and is forbidden here.
#
# Never write a blanket `.claude/` / `/.claude/`. Those hide committable
# consumer wiring (settings.json, repo-owned hooks). Only generated mirrors
# and machine-local overrides belong on this list.
# shellcheck shell=bash

session_shared_exclude_globs() {
  printf '%s\n' \
    "/.cursor-commands" \
    "/.cursor/" \
    "/.l9/" \
    "memory-bank/"
}

# Slashless on purpose: a "dir/" pattern matches directories only, and
# `.claude/rules` is often a symlink, which git does not treat as a directory.
session_claude_mirror_exclude_globs() {
  printf '%s\n' \
    ".claude/skills" \
    ".claude/rules" \
    ".claude/commands" \
    ".mcp.json" \
    ".claude/settings.local.json"
}

session_is_forbidden_blanket_claude() {
  case "${1:-}" in
    .claude | .claude/ | /.claude | /.claude/) return 0 ;;
  esac
  return 1
}

session_exclude_file() {
  local workspace="${1:-}"
  local exclude_file
  [ -n "$workspace" ] || return 1
  git -C "$workspace" rev-parse --git-dir >/dev/null 2>&1 || return 1
  exclude_file="$(git -C "$workspace" rev-parse --git-common-dir)/info/exclude"
  case "$exclude_file" in
    /*) : ;;
    *) exclude_file="$workspace/$exclude_file" ;;
  esac
  printf '%s\n' "$exclude_file"
}

session_append_exclude_globs() {
  local exclude_file="${1:-}"
  local glob
  shift || true
  [ -n "$exclude_file" ] || return 1
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for glob in "$@"; do
    [ -n "$glob" ] || continue
    if session_is_forbidden_blanket_claude "$glob"; then
      printf 'session_git_excludes: refusing blanket %s (Option A)\n' "$glob" >&2
      continue
    fi
    grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >>"$exclude_file"
  done
}

apply_session_git_excludes() {
  local workspace="${1:-}"
  local exclude_file
  exclude_file="$(session_exclude_file "$workspace")" || return 0
  # Word-split is the contract: globs are single tokens, one per line.
  # shellcheck disable=SC2046
  session_append_exclude_globs "$exclude_file" \
    $(session_shared_exclude_globs) \
    $(session_claude_mirror_exclude_globs)
}

apply_session_claude_mirror_excludes() {
  local workspace="${1:-}"
  local exclude_file
  exclude_file="$(session_exclude_file "$workspace")" || return 0
  # shellcheck disable=SC2046
  session_append_exclude_globs "$exclude_file" $(session_claude_mirror_exclude_globs)
}

apply_session_untracked_artifact_excludes() {
  local workspace="${1:-}"
  local exclude_file artifact
  exclude_file="$(session_exclude_file "$workspace")" || return 0
  while IFS= read -r artifact; do
    [ -n "$artifact" ] || continue
    if session_is_forbidden_blanket_claude "$artifact"; then
      printf 'session_git_excludes: refusing blanket %s (Option A)\n' "$artifact" >&2
      continue
    fi
    if git -C "$workspace" ls-files --error-unmatch -- "$artifact" >/dev/null 2>&1; then
      continue
    fi
    session_append_exclude_globs "$exclude_file" "$artifact"
  done
}

apply_machine_session_excludes() {
  local gi="${1:-}"
  [ -n "$gi" ] || return 1
  mkdir -p "$(dirname "$gi")" 2>/dev/null || return 0
  touch "$gi" 2>/dev/null || return 0
  # shellcheck disable=SC2046
  session_append_exclude_globs "$gi" \
    "memory-bank/" \
    ".workflow_state_*.json" \
    ".cursor-globalcommands-fallback.log" \
    $(session_claude_mirror_exclude_globs)
}
