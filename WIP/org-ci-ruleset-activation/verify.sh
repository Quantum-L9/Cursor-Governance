#!/usr/bin/env bash
# Prove the sanctioned path is live. Produces the evidence that closes the two
# UNKNOWN claims in l9-ci-core/.l9/org-runtime-interface.yaml:
#
#   organization-ruleset-live-enforcement   evidence: []   status: UNKNOWN
#   remote-end-to-end-run                   evidence: []   status: UNKNOWN
#
#   bash verify.sh --check           # read-only: prove current state
#   bash verify.sh --pr <owner/repo> <pr-number>
#                                    # correlate a real PR's org-ci run and
#                                    # write evidence/
#
# This script never prints a generic PASS. Advisory and blocking are different
# states of the world and are reported as different results, because "PASS" on an
# evaluate-mode ruleset reads as "enforcement is live" when nothing is enforced:
#
#   ADVISORY_VALID        ruleset correct, enforcement=evaluate  (not blocking)
#   LIVE_ENFORCING        ruleset correct, enforcement=active    (blocking)
#   ADVISORY_CANARY_PASS  the above, plus a real consumer PR ran canonical CI green
#   LIVE_CANARY_PASS      the above, under active enforcement
#
# --check needs organization Administration: write (every /orgs/{org}/rulesets
# endpoint requires it, GET included). --pr needs read on the consumer repository.
set -euo pipefail

ORG="${ORG:-Quantum-L9}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$HERE/org-ci-required.ruleset.json"
ACTIVE_PAYLOAD="$HERE/org-ci-required.active.ruleset.json"

NAME="$(jq -r '.name' "$PAYLOAD")"
NAME_ACTIVE="$(jq -r '.name' "$ACTIVE_PAYLOAD")"
WF_PATH="$(jq -r '.rules[0].parameters.workflows[0].path' "$PAYLOAD")"
WF_REPO_ID="$(jq -r '.rules[0].parameters.workflows[0].repository_id' "$PAYLOAD")"
WF_REF="$(jq -r '.rules[0].parameters.workflows[0].ref' "$PAYLOAD")"
WF_REPO_NAME="${WF_REPO_NAME:-Quantum-L9/l9-ci-core}"
WANT_REPOS="$(jq -c '.conditions.repository_name.include' "$PAYLOAD")"
WANT_REFS="$(jq -c '.conditions.ref_name.include' "$PAYLOAD")"
WANT_TARGET="$(jq -r '.target' "$PAYLOAD")"
EFFECTIVE_CONSUMER="${EFFECTIVE_CONSUMER:-Quantum-L9/l9-observability-core}"
ENF_SCHEMA="l9.org-ci.organization-ruleset-live-enforcement/v1"
E2E_SCHEMA="l9.org-ci.remote-end-to-end-run/v1"

fail() { echo "  FAIL  $*"; FAILED=1; }
pass() { echo "  PASS  $*"; }
FAILED=0
ENFORCEMENT=""
RULESET_ID=""

# Both payloads must name one ruleset, or every lookup below is ambiguous.
if [[ "$NAME" != "$NAME_ACTIVE" ]]; then
  echo "  FAIL  payload names differ ('$NAME' vs '$NAME_ACTIVE') — one identity required"
  echo
  echo "RESULT: FAIL"
  exit 1
fi

check_ruleset() {
  echo "=== claim: organization-ruleset-live-enforcement ==="
  local rulesets
  if ! rulesets="$(gh api "orgs/$ORG/rulesets" 2>/dev/null)"; then
    fail "cannot read orgs/$ORG/rulesets"
    echo
    echo "  Every organization ruleset endpoint requires organization"
    echo "  Administration: write. A repo-scoped token, the governance GitHub"
    echo "  App, and a Claude Code session all fail here by design."
    return
  fi

  # EXACTLY ONE. Two rulesets sharing the canonical name means a split identity
  # — the failure mode where evaluate and active became separate objects.
  local matches
  matches="$(jq -r --arg n "$NAME" '[.[] | select(.name==$n)] | length' <<<"$rulesets")"
  if [[ "$matches" == "0" ]]; then
    fail "no ruleset named '$NAME' in the organisation"
    echo "        (org rulesets present: $(jq -r '[.[].name] | join(", ") // "none"' <<<"$rulesets"))"
    echo "        run: DRY_RUN=0 MODE=evaluate bash apply.sh"
    return
  fi
  if [[ "$matches" -gt 1 ]]; then
    fail "$matches rulesets named '$NAME' — the canonical identity is split"
    jq -r --arg n "$NAME" '.[] | select(.name==$n) | "          id \(.id)  enforcement=\(.enforcement)"' <<<"$rulesets"
    echo "        Delete the duplicates before trusting any result here."
    return
  fi
  pass "exactly one canonical ruleset named '$NAME'"

  RULESET_ID="$(jq -r --arg n "$NAME" '.[] | select(.name==$n) | .id' <<<"$rulesets")"
  ENFORCEMENT="$(jq -r --arg n "$NAME" '.[] | select(.name==$n) | .enforcement' <<<"$rulesets")"
  echo "        id $RULESET_ID, enforcement=$ENFORCEMENT"

  # If a previous apply recorded an id, this must still be it.
  if [[ -f "$HERE/evidence/ruleset-id" ]]; then
    local recorded
    recorded="$(tr -d '[:space:]' < "$HERE/evidence/ruleset-id")"
    if [[ -n "$recorded" ]]; then
      [[ "$recorded" == "$RULESET_ID" ]] \
        && pass "id matches the recorded id ($recorded) — same ruleset throughout" \
        || fail "recorded id $recorded but the org now has $RULESET_ID"
    fi
  fi

  local detail
  detail="$(gh api "orgs/$ORG/rulesets/$RULESET_ID")" || {
    fail "cannot read orgs/$ORG/rulesets/$RULESET_ID"; return; }

  # --- shape: what the ruleset targets ------------------------------------
  local got_target got_repos got_refs got_bypass
  got_target="$(jq -r '.target' <<<"$detail")"
  got_repos="$(jq -c '.conditions.repository_name.include // []' <<<"$detail")"
  got_refs="$(jq -c '.conditions.ref_name.include // []' <<<"$detail")"
  got_bypass="$(jq -c '.bypass_actors // []' <<<"$detail")"

  [[ "$got_target" == "$WANT_TARGET" ]] \
    && pass "target=$got_target" \
    || fail "target='$got_target', expected '$WANT_TARGET'"
  [[ "$got_repos" == "$WANT_REPOS" ]] \
    && pass "repository include=$got_repos" \
    || fail "repository include=$got_repos, expected $WANT_REPOS"
  [[ "$got_refs" == "$WANT_REFS" ]] \
    && pass "ref include=$got_refs" \
    || fail "ref include=$got_refs, expected $WANT_REFS"
  [[ "$got_bypass" == "[]" ]] \
    && pass "no bypass actors" \
    || fail "bypass actors present: $got_bypass — enforcement is not universal"

  # --- shape: what the ruleset requires -----------------------------------
  local wf got_path got_id got_ref got_create
  wf="$(jq -c '[.rules[] | select(.type=="workflows")] | .[0] // empty' <<<"$detail")"
  if [[ -z "$wf" ]]; then
    fail "no 'workflows' rule on the ruleset — it requires nothing"
    return
  fi
  local wf_count
  wf_count="$(jq -r '.parameters.workflows | length' <<<"$wf")"
  [[ "$wf_count" == "1" ]] \
    && pass "requires exactly one workflow" \
    || fail "requires $wf_count workflows — expected exactly 1"

  got_path="$(jq -r '.parameters.workflows[0].path // ""' <<<"$wf")"
  got_id="$(jq -r '.parameters.workflows[0].repository_id // 0' <<<"$wf")"
  got_ref="$(jq -r '.parameters.workflows[0].ref // ""' <<<"$wf")"
  got_create="$(jq -r '.parameters.do_not_enforce_on_create' <<<"$wf")"

  [[ "$got_path" == "$WF_PATH" ]] \
    && pass "workflow path $got_path" \
    || fail "workflow path '$got_path', expected '$WF_PATH'"
  [[ "$got_id" == "$WF_REPO_ID" ]] \
    && pass "workflow source repository_id=$got_id" \
    || fail "repository_id=$got_id, expected $WF_REPO_ID"
  [[ "$got_ref" == "$WF_REF" ]] \
    && pass "workflow ref $got_ref" \
    || fail "workflow ref '$got_ref', expected '$WF_REF'"
  [[ "$got_create" == "true" ]] \
    && pass "branch creation not gated (do_not_enforce_on_create=true)" \
    || fail "do_not_enforce_on_create=$got_create — repository creation can hang org-wide"

  case "$ENFORCEMENT" in
    active)
      pass "enforcement=active — the sanctioned path is BLOCKING"
      if [[ "$FAILED" == "0" ]]; then
        mkdir -p "$HERE/evidence"
        local got_source target_ref
        got_source="$(jq -r '.source_type // empty' <<<"$detail")"
        target_ref="$(jq -r '.conditions.ref_name.include[0] // empty' <<<"$detail")"
        jq -n --arg schema "$ENF_SCHEMA" \
              --arg org "$ORG" --arg id "$RULESET_ID" --arg name "$NAME" \
              --arg source "$got_source" --arg enf "$ENFORCEMENT" \
              --arg target "$got_target" --arg target_ref "$target_ref" \
              --arg path "$got_path" --arg ref "$got_ref" \
              --arg repo_name "$WF_REPO_NAME" \
              --argjson repo_id "$got_id" \
              --arg create "$got_create" \
              --argjson bypass "$got_bypass" \
              --argjson repos "$got_repos" --argjson refs "$got_refs" \
              --arg consumer "$EFFECTIVE_CONSUMER" \
              --arg captured "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
          '{schema:$schema, captured_at:$captured, organization:$org,
            ruleset_id:($id|tonumber), ruleset_name:$name, source_type:$source,
            enforcement:$enf, target:$target,
            workflow_repository_id:$repo_id, workflow_repository:$repo_name,
            workflow_path:$path, workflow_ref:$ref, target_ref:$target_ref,
            do_not_enforce_on_create:($create=="true"),
            bypass_actors:$bypass,
            effective_consumer_repository:$consumer,
            workflow:{repository_id:$repo_id, path:$path, ref:$ref},
            targets:{repositories:$repos, refs:$refs}}' \
          > "$HERE/evidence/organization-ruleset-live-enforcement.json"
        echo "  wrote evidence/organization-ruleset-live-enforcement.json"
      fi
      ;;
    evaluate)
      echo "  NOTE  enforcement=evaluate — advisory, NOT blocking."
      echo "        Promote only after a real consumer canary passes:"
      echo "          bash verify.sh --pr Quantum-L9/<consumer> <pr>"
      echo "          DRY_RUN=0 MODE=active bash apply.sh"
      ;;
    *)
      fail "enforcement='$ENFORCEMENT' — neither 'evaluate' nor 'active'"
      ;;
  esac
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
    echo "        A ruleset created AFTER this PR opened does not retroactively"
    echo "        run on it. Push another commit, or close and reopen the PR,"
    echo "        then re-check. If the run never appears, the repository is not"
    echo "        matched by the ruleset conditions."
    return
  fi

  local conclusion url app check_name check_run_id run_status actions_run_id actions_job_id
  conclusion="$(jq -r '.conclusion // "pending"' <<<"$run")"
  url="$(jq -r '.html_url' <<<"$run")"
  app="$(jq -r '.app.slug // "unknown"' <<<"$run")"
  check_name="$(jq -r '.name // empty' <<<"$run")"
  check_run_id="$(jq -r '.id // empty' <<<"$run")"
  run_status="$(jq -r '.status // empty' <<<"$run")"
  actions_run_id="$(sed -n 's#.*/actions/runs/\([0-9][0-9]*\).*#\1#p' <<<"$url")"
  actions_job_id="$(sed -n 's#.*/job/\([0-9][0-9]*\).*#\1#p' <<<"$url")"
  [[ -n "$actions_job_id" ]] || actions_job_id="$check_run_id"
  pass "canonical CI ran on $head"
  echo "        $url"
  [[ "$app" == "github-actions" ]] \
    && pass "produced by GitHub Actions" \
    || fail "check run app is '$app', expected 'github-actions'"
  if [[ "$conclusion" == "success" ]]; then
    pass "conclusion=success — org-ci.yml has completed end-to-end"
  else
    fail "conclusion=$conclusion"
  fi

  # LIVE_CANARY_PASS must be a run that started after ACTIVE promotion.
  # Re-checking the Phase 3 PR without a new head would reuse the evaluate-mode
  # check while ENFORCEMENT already reads active.
  if [[ "$ENFORCEMENT" == "active" ]]; then
    if [[ ! -f "$HERE/evidence/promoted-at" ]]; then
      fail "ACTIVE canary requires evidence/promoted-at (MODE=active apply.sh writes it)"
    else
      local promoted started
      promoted="$(tr -d '[:space:]' < "$HERE/evidence/promoted-at")"
      started="$(jq -r '.started_at // empty' <<<"$run")"
      if [[ -z "$started" ]]; then
        fail "check run has no started_at — cannot prove it ran after promotion"
      elif [[ -z "$promoted" || "$started" < "$promoted" ]]; then
        fail "check run started_at=$started is before promotion $promoted — push a new canary commit after ACTIVE"
      else
        pass "check run started after ACTIVE promotion ($promoted)"
      fi
    fi
  fi

  mkdir -p "$HERE/evidence"
  jq -n --arg schema "$E2E_SCHEMA" \
        --arg slug "$slug" --arg pr "$pr" --arg head "$head" \
        --arg check_name "$check_name" --arg check_run_id "$check_run_id" \
        --arg actions_run_id "$actions_run_id" --arg actions_job_id "$actions_job_id" \
        --arg url "$url" --arg app "$app" --arg status "$run_status" \
        --arg conclusion "$conclusion" \
        --arg enforcement "${ENFORCEMENT:-unknown}" \
        --arg ruleset_id "${RULESET_ID:-unknown}" \
        --arg captured "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{schema:$schema, captured_at:$captured, consumer:$slug,
      pull_request:($pr|tonumber), head_sha:$head, check_name:$check_name,
      check_run_id:(if $check_run_id=="" then null else ($check_run_id|tonumber) end),
      actions_run_id:(if $actions_run_id=="" then null else ($actions_run_id|tonumber) end),
      actions_job_id:(if $actions_job_id=="" then null else ($actions_job_id|tonumber) end),
      check_run_url:$url, app:$app, status:$status, conclusion:$conclusion,
      check_run_app:$app, ruleset_id:$ruleset_id,
      enforcement_at_capture:$enforcement}' \
    > "$HERE/evidence/remote-end-to-end-run.json"
  echo "  wrote evidence/remote-end-to-end-run.json"
}

SAW_RUN=0
case "${1:---check}" in
  --check) check_ruleset ;;
  --pr)
    [[ $# -eq 3 ]] || { echo "usage: verify.sh --pr <owner/repo> <pr-number>" >&2; exit 2; }
    EFFECTIVE_CONSUMER="$2"
    check_ruleset; check_run "$2" "$3"; SAW_RUN=1 ;;
  *) echo "usage: verify.sh [--check | --pr <owner/repo> <pr-number>]" >&2; exit 2 ;;
esac

echo
if [[ "$FAILED" != "0" ]]; then
  echo "RESULT: FAIL"
  exit 1
fi

# Name the state. Never a bare PASS: advisory and blocking are not the same world.
case "$ENFORCEMENT:$SAW_RUN" in
  evaluate:0) echo "RESULT: ADVISORY_VALID" ;;
  evaluate:1) echo "RESULT: ADVISORY_CANARY_PASS" ;;
  active:0)   echo "RESULT: LIVE_ENFORCING" ;;
  active:1)   echo "RESULT: LIVE_CANARY_PASS" ;;
  *)          echo "RESULT: FAIL (indeterminate enforcement state)"; exit 1 ;;
esac
