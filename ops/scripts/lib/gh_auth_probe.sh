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

# ---------------------------------------------------------------------------
# One verdict per GitHub transport, because they fail independently (CG-10).
# `gh api user` succeeding says nothing about reading <owner>/.github (the PR
# template make pr needs), GraphQL (403 on some session gateways), or a tool
# that calls api.github.com itself with $GH_TOKEN (zizmor, osv). Collapsing
# them into one boolean is how "authenticated" coexisted with a publish that
# could not read its template.
#
# Prints `name=OK|DENIED|UNKNOWN`, one per line, for rest_user,
# org_template_read, graphql and direct_api. OK: the call succeeded. DENIED:
# it ran and was refused. UNKNOWN: it could not be asked (tool absent, no
# owner, timeout). Each call is bounded; the token never reaches argv.
# ---------------------------------------------------------------------------

_gh_capability() { # $1=name, rest=command
  local name="$1" rc=0
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${GH_CAPABILITY_TIMEOUT_S:-5}" "$@" >/dev/null 2>&1 || rc=$?
  else
    "$@" >/dev/null 2>&1 || rc=$?
  fi
  case "$rc" in
    0) echo "$name=OK" ;;
    124 | 126 | 127) echo "$name=UNKNOWN" ;;
    *) echo "$name=DENIED" ;;
  esac
}

gh_capability_probe() { # $1=owner of <owner>/.github
  local owner="${1:-}" token code
  if command -v gh >/dev/null 2>&1; then
    _gh_capability rest_user gh api user
    if [ -n "$owner" ]; then
      _gh_capability org_template_read \
        gh api "repos/${owner}/.github/contents/.github/pull_request_template.md"
    else
      echo "org_template_read=UNKNOWN"
    fi
    _gh_capability graphql gh api graphql -f 'query={viewer{login}}'
  else
    echo "rest_user=UNKNOWN"
    echo "org_template_read=UNKNOWN"
    echo "graphql=UNKNOWN"
  fi
  token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if command -v curl >/dev/null 2>&1 && [ -n "$token" ]; then
    # The header arrives on stdin (-H @-), so the token is never in argv.
    code="$(printf 'Authorization: Bearer %s\n' "$token" \
      | curl -sS -o /dev/null -w '%{http_code}' --max-time "${GH_CAPABILITY_TIMEOUT_S:-5}" \
        -H @- https://api.github.com/user 2>/dev/null || true)"
    case "$code" in
      2??) echo "direct_api=OK" ;;
      401 | 403) echo "direct_api=DENIED" ;;
      *) echo "direct_api=UNKNOWN" ;;
    esac
  else
    echo "direct_api=UNKNOWN"
  fi
}
