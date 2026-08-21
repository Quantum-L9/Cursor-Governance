#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# gh GraphQL classification — shared by every script on the publish path.
#
# `gh pr view`, `gh pr list`, `gh pr checks`, `gh pr merge` and
# `gh repo view --json` all go through GitHub's GraphQL endpoint. Some session
# gateways serve only a pinned set of REST operations and answer every GraphQL
# query with HTTP 403. That is a FIXED PROPERTY of the surface, not a transient
# error, and it is not fixable from this repository.
#
# What is fixable is the reporting. The publish path used to write
# `gh pr view --json url -q .url 2>/dev/null || true`, which turned that 403
# into an empty string indistinguishable from "no PR is open" — so the script
# proceeded to build `repos/o/n/issues//subscription` and warn about a
# notification problem it did not have (audit B-12, INV-7).
#
# This helper keeps GraphQL primary — behaviour is unchanged wherever it works —
# but names the failure once and sets a flag the caller can branch on:
#
#   GH_GRAPHQL_UNSUPPORTED=1   the gateway refuses GraphQL; use REST
#
# Sourcing this file is idempotent.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

GH_GRAPHQL_UNSUPPORTED="${GH_GRAPHQL_UNSUPPORTED:-0}"
GH_GRAPHQL_NOTED="${GH_GRAPHQL_NOTED:-0}"

#: The classification string callers and tests assert on.
GH_GRAPHQL_CLASSIFICATION="SURFACE_UNSUPPORTED_GRAPHQL"

# gh_graphql <gh args...>
#   Runs gh, prints stdout, returns gh's exit code. On failure, inspects stderr
#   and classifies a GraphQL refusal, noting it once per process.
gh_graphql() {
  local out err rc
  err="$(mktemp)"
  out="$(gh "$@" 2>"$err")"
  rc=$?
  if [ "$rc" -ne 0 ] && grep -qiE 'graphql' "$err" \
     && grep -qiE '(^|[^0-9])403([^0-9]|$)|not enabled|forbidden' "$err"; then
    GH_GRAPHQL_UNSUPPORTED=1
    if [ "$GH_GRAPHQL_NOTED" = "0" ]; then
      GH_GRAPHQL_NOTED=1
      printf 'NOTE: %s — this session gateway refuses GitHub GraphQL;\n' \
        "$GH_GRAPHQL_CLASSIFICATION" >&2
      printf '      falling back to REST (gh api repos/...) for PR operations.\n' >&2
    fi
  fi
  rm -f "$err"
  printf '%s' "$out"
  return "$rc"
}
