#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# GitHub GraphQL capability classification and transport guard.
#
# `gh pr ...`, `gh repo view`, and `gh api graphql` reach GitHub's GraphQL
# endpoint. Claude Code Web/Mobile session gateways may expose repository-scoped
# REST while refusing GraphQL. That is a surface capability, not an auth defect.
#
# The old behaviour learned this by making a GraphQL request, receiving the
# expected 403, then falling back to REST. That is too late on a model-controlled
# surface: the known-bad request still crosses the harness and can create a
# permission dialog or a noisy failed tool call before the recovery path runs.
#
# This library owns GraphQL capability classification only. It deliberately does
# NOT shadow the global `gh` command. Call sites that use a GraphQL-backed `gh`
# subcommand must route it through gh_graphql(); REST calls remain explicit
# `gh api ...` commands owned by the caller. That keeps transport decisions
# visible in code and prevents a sourced helper from changing unrelated gh calls.
#
# Flags:
#   GH_GRAPHQL_UNSUPPORTED=1             GraphQL must not be attempted
#   L9_GITHUB_GRAPHQL_MODE=rest-only     explicit operator/runtime override
#
# CLAUDE_CODE_REMOTE=true is the hosted-session discriminator already used by
# the Claude bootstrap. Local CLI/Desktop behaviour is unchanged unless the
# explicit override is set.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

GH_GRAPHQL_UNSUPPORTED="${GH_GRAPHQL_UNSUPPORTED:-0}"
GH_GRAPHQL_NOTED="${GH_GRAPHQL_NOTED:-0}"

#: The classification string callers and tests assert on.
GH_GRAPHQL_CLASSIFICATION="SURFACE_UNSUPPORTED_GRAPHQL"

_gh_graphql_surface_rest_only() {
  [ "${L9_GITHUB_GRAPHQL_MODE:-}" = "rest-only" ] || \
    [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]
}

_gh_graphql_mark_unsupported() {
  GH_GRAPHQL_UNSUPPORTED=1
  if [ "$GH_GRAPHQL_NOTED" = "0" ]; then
    GH_GRAPHQL_NOTED=1
    printf 'NOTE: %s — this session surface does not permit GitHub GraphQL;\n' \
      "$GH_GRAPHQL_CLASSIFICATION" >&2
    printf '      using repository-scoped REST (gh api repos/...) instead.\n' >&2
  fi
}

# Pre-classify hosted Claude sessions. Do not print at source time: a caller
# that never asks for GraphQL should stay quiet.
if _gh_graphql_surface_rest_only; then
  GH_GRAPHQL_UNSUPPORTED=1
fi

# gh_graphql <gh args...>
#   Runs the real gh binary, prints stdout, returns gh's exit code. On a
#   pre-classified surface it returns before any network call. Otherwise, on
#   failure it inspects stderr and classifies a GraphQL refusal, noting it once
#   per process.
gh_graphql() {
  local out err rc

  if [ "${GH_GRAPHQL_UNSUPPORTED:-0}" = "1" ] || _gh_graphql_surface_rest_only; then
    _gh_graphql_mark_unsupported
    return 1
  fi

  err="$(mktemp)"
  out="$(command gh "$@" 2>"$err")"
  rc=$?
  if [ "$rc" -ne 0 ] && grep -qiE 'graphql' "$err" \
     && grep -qiE '(^|[^0-9])403([^0-9]|$)|not enabled|forbidden' "$err"; then
    _gh_graphql_mark_unsupported
  fi
  rm -f "$err"
  printf '%s' "$out"
  return "$rc"
}
