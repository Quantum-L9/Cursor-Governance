#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Subscribe the viewer to a pull request.
#
# PUT repos/{owner}/{repo}/issues/{n}/subscription is not a live GitHub REST
# route — it 404s. The live REST equivalent is
# PUT /notifications/threads/{thread_id}/subscription, which needs a thread
# id this path does not have. GraphQL updateSubscription takes the PR node
# id from REST GET pulls/{n} (Context7: /websites/github_en_graphql
# UpdateSubscriptionInput.subscribableId + SubscriptionState.SUBSCRIBED).
#
# Usage:
#   source ops/scripts/lib/gh_subscribe_pr.sh   # bash or zsh
#   gh_subscribe_pr OWNER REPO PR_NUMBER
#   bash ops/scripts/lib/gh_subscribe_pr.sh OWNER REPO PR_NUMBER
#
# The sibling gh_graphql.sh is resolved from THIS file's directory. CWD is
# never a fallback. Sourcing from zsh used to set the lib dir to CWD because
# BASH_SOURCE is empty there; that produced
#   .../Cursor-Governance/gh_graphql.sh: No such file
#   gh_subscribe_pr: command not found: gh_graphql
#
# Exit 0 on SUBSCRIBED, already-subscribed, or a classified GraphQL refusal
# (GH_GRAPHQL_UNSUPPORTED=1). Exit 1 only when GraphQL is available and the
# mutation still fails. Callers on the publish path treat a non-zero as WARN
# and continue — ownership is not waived.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

_l9_subscribe_is_sourced() {
  if [ -n "${ZSH_EVAL_CONTEXT:-}" ]; then
    case "$ZSH_EVAL_CONTEXT" in
      *:file*) return 0 ;;
      *) return 1 ;;
    esac
  fi
  if [ -n "${BASH_VERSION:-}" ]; then
    [ "${BASH_SOURCE[0]}" != "$0" ]
    return $?
  fi
  return 1
}

# Path of this file. bash: BASH_SOURCE. zsh sourced: %x. never CWD, never $0
# when $0 is the shell name.
_l9_subscribe_self_path() {
  local self=""
  if [ -n "${BASH_SOURCE[0]:-}" ]; then
    self="${BASH_SOURCE[0]}"
  elif [ -n "${ZSH_VERSION:-}" ]; then
    # Prompt expansion is zsh-only; eval keeps bash from parsing %x.
    eval 'self=${(%):-%x}'
    if [ -z "$self" ] || [ "$self" = "%x" ]; then
      eval 'self=${(%):-%N}'
    fi
  fi
  case "${self:-}" in
    "" | zsh | -zsh | bash | -bash | sh | -sh | "%x" | "%N")
      case "${0:-}" in
        zsh | -zsh | bash | -bash | sh | -sh | "") self="" ;;
        *) self="$0" ;;
      esac
      ;;
  esac
  printf '%s' "$self"
}

_l9_subscribe_load_graphql() {
  local self dir sibling
  self="$(_l9_subscribe_self_path)"
  if [ -z "$self" ]; then
    echo "FAIL: gh_subscribe_pr.sh cannot resolve its own path (empty BASH_SOURCE / zsh %x / \$0). Source or run the absolute file; CWD=$(pwd) is never a fallback." >&2
    return 1
  fi
  dir="$(CDPATH= cd -- "$(dirname -- "$self")" && pwd)" || {
    echo "FAIL: gh_subscribe_pr.sh cannot cd to dirname of ${self}" >&2
    return 1
  }
  sibling="${dir}/gh_graphql.sh"
  if [ ! -f "$sibling" ]; then
    echo "FAIL: gh_subscribe_pr.sh expected sibling ${sibling} (self=${self}). CWD=$(pwd) is not consulted." >&2
    return 1
  fi
  _GH_SUBSCRIBE_LIB_DIR="$dir"
  # shellcheck source=gh_graphql.sh
  # shellcheck disable=SC1091
  source "$sibling"
  if ! command -v gh_graphql >/dev/null 2>&1; then
    echo "FAIL: sourced ${sibling} but gh_graphql is not defined" >&2
    return 1
  fi
  return 0
}

if ! _l9_subscribe_load_graphql; then
  if _l9_subscribe_is_sourced; then
    return 1
  fi
  exit 1
fi

_GH_SUBSCRIBE_MUTATION='mutation($id: ID!) {
  updateSubscription(input: {subscribableId: $id, state: SUBSCRIBED}) {
    subscribable {
      ... on PullRequest {
        number
        viewerSubscription
      }
    }
  }
}'

gh_subscribe_pr() {
  local owner="$1" name="$2" pr="$3" node_id out state
  local rest_err gql_out gql_rc _had_errexit=0
  if [[ -z "$owner" || -z "$name" || -z "$pr" ]]; then
    echo "WARN: gh_subscribe_pr requires OWNER REPO PR_NUMBER" >&2
    return 1
  fi
  if ! command -v gh >/dev/null 2>&1; then
    echo "WARN: gh not on PATH; cannot subscribe to ${owner}/${name}#${pr}" >&2
    return 1
  fi
  if ! command -v gh_graphql >/dev/null 2>&1; then
    echo "FAIL: gh_graphql is not defined; source ${_GH_SUBSCRIBE_LIB_DIR:-ops/scripts/lib}/gh_subscribe_pr.sh (not a CWD-relative copy)" >&2
    return 1
  fi

  rest_err="$(mktemp "${TMPDIR:-/tmp}/l9-gh-subscribe-rest.XXXXXX")"
  node_id="$(gh api "repos/${owner}/${name}/pulls/${pr}" --jq .node_id 2>"$rest_err" || true)"
  if [[ -z "$node_id" ]]; then
    echo "WARN: could not resolve node_id for ${owner}/${name}#${pr} (REST GET pulls/${pr})" >&2
    if [[ -s "$rest_err" ]]; then
      echo "WARN: $(head -c 240 "$rest_err")" >&2
    fi
    rm -f "$rest_err"
    return 1
  fi
  rm -f "$rest_err"

  # Run gh_graphql in this function (not a $() subshell) so
  # GH_GRAPHQL_UNSUPPORTED survives the call.
  gql_out="$(mktemp "${TMPDIR:-/tmp}/l9-gh-subscribe-gql.XXXXXX")"
  [[ $- == *e* ]] && _had_errexit=1
  set +e
  gh_graphql api graphql \
    -f query="$_GH_SUBSCRIBE_MUTATION" \
    -f id="$node_id" \
    --jq '.data.updateSubscription.subscribable.viewerSubscription' \
    >"$gql_out"
  gql_rc=$?
  if [[ "$_had_errexit" -eq 1 ]]; then
    set -e
  else
    set +e
  fi
  out="$(cat "$gql_out")"
  rm -f "$gql_out"

  if [[ "${GH_GRAPHQL_UNSUPPORTED:-0}" == "1" ]]; then
    echo "NOTE: skip subscribe for ${owner}/${name}#${pr} — ${GH_GRAPHQL_CLASSIFICATION}"
    return 0
  fi
  if [[ "$gql_rc" -ne 0 ]]; then
    echo "WARN: updateSubscription failed for ${owner}/${name}#${pr} (exit ${gql_rc})" >&2
    return 1
  fi

  state="$(printf '%s' "$out" | tr -d '[:space:]')"
  if [[ "$state" == "SUBSCRIBED" ]]; then
    echo "Subscribed to PR #${pr} (${owner}/${name})"
    return 0
  fi

  echo "WARN: updateSubscription did not return SUBSCRIBED for ${owner}/${name}#${pr} (got: ${state:-<empty>})" >&2
  return 1
}

if ! _l9_subscribe_is_sourced; then
  case "${1:-}" in
    -h | --help)
      sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    "")
      echo "WARN: gh_subscribe_pr.sh OWNER REPO PR_NUMBER" >&2
      exit 1
      ;;
  esac
  gh_subscribe_pr "$@"
  exit $?
fi
