#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Report what `gh` can DO, not what a sentinel string looks like.
#
# On an Anthropic-hosted surface the platform proxy authenticates git and gh and
# exports GH_TOKEN=proxy-injected — a placeholder, not a credential.
# `gh auth status` validates that value by a route the proxy does not rewrite,
# so it reports "The token in GH_TOKEN is invalid" while `gh api user` returns
# the real account. The setup log therefore announced "gh unauthenticated" on a
# surface where every GitHub REST call worked (audit B-20).
#
# A capability probe answers the question the operator actually has, so this
# tries the REST call first and falls back to `gh auth status` for surfaces
# where the reverse is true.
#
# Echoes one line and returns 0 when authenticated, 1 when not.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

gh_auth_probe() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh: NOT INSTALLED — CI/review skills that shell out to gh will not work"
    return 1
  fi
  if gh api user >/dev/null 2>&1; then
    echo "gh: authenticated via platform proxy (REST verified with gh api user)"
    return 0
  fi
  if gh auth status >/dev/null 2>&1; then
    echo "gh: authenticated (gh auth status)"
    return 0
  fi
  echo "NOTE: gh unauthenticated — neither 'gh api user' nor 'gh auth status' succeeded"
  return 1
}
