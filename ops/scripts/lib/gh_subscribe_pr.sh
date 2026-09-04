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
# Usage (source, then call):
#   source ops/scripts/lib/gh_subscribe_pr.sh
#   gh_subscribe_pr OWNER REPO PR_NUMBER
#
# Exit 0 on SUBSCRIBED, already-subscribed, or a classified GraphQL refusal
# (GH_GRAPHQL_UNSUPPORTED=1). Exit 1 only when GraphQL is available and the
# mutation still fails. Callers on the publish path treat a non-zero as WARN
# and continue — ownership is not waived.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

# Sourcing is idempotent. gh_graphql.sh is a sibling.
_GH_SUBSCRIBE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=gh_graphql.sh
source "$_GH_SUBSCRIBE_LIB_DIR/gh_graphql.sh"

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
  if [[ -z "$owner" || -z "$name" || -z "$pr" ]]; then
    echo "WARN: gh_subscribe_pr requires OWNER REPO PR_NUMBER" >&2
    return 1
  fi

  node_id="$(gh api "repos/${owner}/${name}/pulls/${pr}" --jq .node_id 2>/dev/null || true)"
  if [[ -z "$node_id" ]]; then
    echo "WARN: could not resolve node_id for ${owner}/${name}#${pr} (REST pulls)" >&2
    return 1
  fi

  # Run gh_graphql in this function (not a $() subshell) so
  # GH_GRAPHQL_UNSUPPORTED survives the call.
  local gql_out gql_rc
  gql_out="$(mktemp)"
  local _had_errexit=0
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
    echo "WARN: updateSubscription failed for #${pr} (exit ${gql_rc})" >&2
    return 1
  fi

  state="$(printf '%s' "$out" | tr -d '[:space:]')"
  if [[ "$state" == "SUBSCRIBED" ]]; then
    echo "Subscribed to PR #${pr} (${owner}/${name})"
    return 0
  fi

  echo "WARN: updateSubscription did not return SUBSCRIBED for #${pr} (got: ${state:-<empty>})" >&2
  return 1
}
