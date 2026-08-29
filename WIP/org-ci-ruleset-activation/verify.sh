#!/usr/bin/env bash
# Prove the sanctioned path is live. Produces the evidence that closes the two
# UNKNOWN claims in l9-ci-core/.l9/org-runtime-interface.yaml:
#
#   organization-ruleset-live-enforcement   evidence: []   status: UNKNOWN
#   remote-end-to-end-run                   evidence: []   status: UNKNOWN
#
#   bash verify.sh --check           # read-only: report current state
#   bash verify.sh --pr <owner/repo> <pr-number>
#                                    # correlate a real PR's org-ci run and
#                                    # write evidence/
#
# --check needs org read. --pr needs read on the consumer repository.
set -euo pipefail

ORG="${ORG:-Quantum-L9}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$HERE/org-ci-required.ruleset.json"
NAME_EVAL="$(jq -r '.name' "$PAYLOAD")"
NAME_ACTIVE="$(jq -r '.name' "$HERE/org-ci-required.active.ruleset.json")"
WF_PATH="$(jq -r '.rules[0].parameters.workflows[0].path' "$PAYLOAD")"
WF_REPO_ID="$(jq -r '.rules[0].parameters.workflows[0].repository_id' "$PAYLOAD")"

fail() { echo "  FAIL  $*"; FAILED=1; }
pass() { echo "  PASS  $*"; }
FAILED=0

check_ruleset() {
  echo "=== claim: organization-ruleset-live-enforcement ==="
  local rulesets
  if ! rulesets="$(gh api "orgs/$ORG/rulesets" 2>/dev/null)"; then
    fail "cannot read orgs/$ORG/rulesets — token is not org-scoped"
    echo
    echo "  A repo-scoped token cannot see organisation rulesets. This is the"
    echo "  same limit that stops a Claude Code session applying one."
    return
  fi

  local found
  found="$(jq -r --arg a "$NAME_EVAL" --arg b "$NAME_ACTIVE" \
    '[.[] | select(.name==$a or .name==$b)] | .[0] // empty' <<<"$rulesets")"
  if [[ -z "$found" ]]; then
    fail "no canonical-CI ruleset in the organisation"
    echo "        (org rulesets present: $(jq -r '[.[].name] | join(", ") // "none"' <<<"$rulesets"))"
    echo "        run: DRY_RUN=0 bash apply.sh"
    return
  fi

  local id enforcement
  id="$(jq -r '.id' <<<"$found")"
  enforcement="$(jq -r '.enforcement' <<<"$found")"
  pass "ruleset $id present, enforcement=$enforcement"

  local detail
  detail="$(gh api "orgs/$ORG/rulesets/$id")"
  local got_path got_id
  got_path="$(jq -r '[.rules[] | select(.type=="workflows") | .parameters.workflows[].path] | .[0] // ""' <<<"$detail")"
  got_id="$(jq -r '[.rules[] | select(.type=="workflows") | .parameters.workflows[].repository_id] | .[0] // 0' <<<"$detail")"

  [[ "$got_path" == "$WF_PATH" ]] \
    && pass "requires $got_path" \
    || fail "requires '$got_path', expected '$WF_PATH'"
  [[ "$got_id" == "$WF_REPO_ID" ]] \
    && pass "workflow source repository_id=$got_id" \
    || fail "repository_id=$got_id, expected $WF_REPO_ID"

  if [[ "$enforcement" == "active" ]]; then
    pass "ENFORCING — the sanctioned path is live"
  else
    echo "  NOTE  enforcement='$enforcement' — advisory only, not yet blocking."
    echo "        promote with: DRY_RUN=0 MODE=active bash apply.sh"
  fi
}

check_run() {
  local slug="$1" pr="$2"
  echo
  echo "=== claim: remote-end-to-end-run ==="
  local head
  head="$(gh api "repos/$slug/pulls/$pr" --jq '.head.sha')" || {
    fail "cannot read $slug#$pr"; return; }
  echo "  PR head: $head"

  local runs
  runs="$(gh api "repos/$slug/commits/$head/check-runs" --jq '.check_runs')" || {
    fail "cannot read check runs for $head"; return; }

  # Correlate on the exact head SHA. "Some run passed recently" is not evidence.
  local run
  run="$(jq -r '[.[] | select(.name | test("Analyze \\(central Core\\)|Organization CI"; "i"))] | .[0] // empty' <<<"$runs")"
  if [[ -z "$run" ]]; then
    fail "no canonical CI check run on $head"
    echo "        checks seen: $(jq -r '[.[].name] | join(", ") // "none"' <<<"$runs")"
    echo "        If the ruleset is active and this PR is targeted, the run"
    echo "        should appear. If it never does, the repository is not"
    echo "        matched by the ruleset conditions."
    return
  fi

  local conclusion url
  conclusion="$(jq -r '.conclusion // "pending"' <<<"$run")"
  url="$(jq -r '.html_url' <<<"$run")"
  pass "canonical CI ran on $head"
  echo "        $url"
  if [[ "$conclusion" == "success" ]]; then
    pass "conclusion=success — org-ci.yml has completed end-to-end"
  else
    fail "conclusion=$conclusion"
  fi

  mkdir -p "$HERE/evidence"
  jq -n --arg slug "$slug" --arg pr "$pr" --arg head "$head" \
        --arg url "$url" --arg conclusion "$conclusion" \
        --arg captured "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{consumer:$slug, pull_request:($pr|tonumber), head_sha:$head,
      check_run_url:$url, conclusion:$conclusion, captured_at:$captured}' \
    > "$HERE/evidence/remote-end-to-end-run.json"
  echo "  wrote evidence/remote-end-to-end-run.json"
}

case "${1:---check}" in
  --check) check_ruleset ;;
  --pr)
    [[ $# -eq 3 ]] || { echo "usage: verify.sh --pr <owner/repo> <pr-number>" >&2; exit 2; }
    check_ruleset; check_run "$2" "$3" ;;
  *) echo "usage: verify.sh [--check | --pr <owner/repo> <pr-number>]" >&2; exit 2 ;;
esac

echo
[[ "$FAILED" == "0" ]] && echo "RESULT: PASS" || { echo "RESULT: FAIL"; exit 1; }
