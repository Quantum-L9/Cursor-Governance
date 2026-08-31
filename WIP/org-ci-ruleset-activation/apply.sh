#!/usr/bin/env bash
# Apply the canonical-CI required-workflow ruleset to the Quantum-L9 organization.
#
# This is the step that makes the sanctioned path live. Everything else in the
# architecture already assumes it has happened; nothing has ever performed it.
#
# ONE RULESET. Evaluate and active are enforcement STATES of a single ruleset
# identity, not two rulesets. Both payloads therefore carry the same .name, and
# this script refuses any sequence that would end with two of them.
#
# Self-contained ON PURPOSE. It does not read Quantum-L9/.github's rulesets/
# directory and does not go through `make apply-rulesets`, because that target
# points at ops/apply-rulesets.sh — a path that has never existed in any commit.
#
# Requires an identity with organization Administration: write (classic
# `admin:org`). Every /orgs/{org}/rulesets endpoint — GET included — requires it,
# so a successful read IS the authority proof. The governance GitHub App does NOT
# have it: its manifest grants repository contents/pull_requests plus organization
# members:read. Run this as a human org owner.
#
#   bash apply.sh                          # dry run — prints the plan, changes nothing
#   DRY_RUN=0 bash apply.sh                # create/update the EVALUATE (advisory) state
#   DRY_RUN=0 MODE=active bash apply.sh    # promote the SAME ruleset to ACTIVE (blocking)
#   ALLOW_DEMOTE=1 DRY_RUN=0 MODE=evaluate bash apply.sh   # deliberate rollback to advisory
set -euo pipefail

ORG="${ORG:-Quantum-L9}"
DRY="${DRY_RUN:-1}"
MODE="${MODE:-evaluate}"
ALLOW_DEMOTE="${ALLOW_DEMOTE:-0}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EVAL_PAYLOAD="$HERE/org-ci-required.ruleset.json"
ACTIVE_PAYLOAD="$HERE/org-ci-required.active.ruleset.json"
ID_RECEIPT="$HERE/evidence/ruleset-id"

case "$MODE" in
  evaluate) PAYLOAD="$EVAL_PAYLOAD" ;;
  active)   PAYLOAD="$ACTIVE_PAYLOAD" ;;
  *) echo "MODE must be 'evaluate' or 'active' (got '$MODE')" >&2; exit 2 ;;
esac

command -v gh >/dev/null || { echo "gh CLI required" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }
for p in "$EVAL_PAYLOAD" "$ACTIVE_PAYLOAD"; do
  [[ -f "$p" ]] || { echo "missing payload: $p" >&2; exit 1; }
done

echo "=== preconditions ==="

# 0. ONE IDENTITY. The two payloads must differ in exactly one field. If the
#    evaluate payload carries a decorated name ("... (evaluate)"), promotion
#    creates a SECOND ruleset instead of promoting the first, and the org ends up
#    with an advisory ruleset and a blocking ruleset that nobody reconciles.
NAME="$(jq -r '.name' "$PAYLOAD")"
EVAL_NAME="$(jq -r '.name' "$EVAL_PAYLOAD")"
ACTIVE_NAME="$(jq -r '.name' "$ACTIVE_PAYLOAD")"
if [[ "$EVAL_NAME" != "$ACTIVE_NAME" ]]; then
  cat >&2 <<EOF
FAIL: the two payloads do not share one ruleset identity.

  evaluate .name = '$EVAL_NAME'
  active   .name = '$ACTIVE_NAME'

apply.sh resolves an existing ruleset BY NAME. Different names mean
evaluate -> active creates a second ruleset rather than promoting the first.
Both payloads must carry the identical .name.
EOF
  exit 1
fi
if ! diff -q <(jq -S 'del(.enforcement)' "$EVAL_PAYLOAD") \
             <(jq -S 'del(.enforcement)' "$ACTIVE_PAYLOAD") >/dev/null; then
  echo "FAIL: payloads differ in more than .enforcement." >&2
  echo "      Promotion must change enforcement and nothing else. Diff:" >&2
  diff <(jq -S 'del(.enforcement)' "$EVAL_PAYLOAD") \
       <(jq -S 'del(.enforcement)' "$ACTIVE_PAYLOAD") >&2 || true
  exit 1
fi
[[ "$(jq -r '.enforcement' "$EVAL_PAYLOAD")" == "evaluate" ]] || {
  echo "FAIL: evaluate payload .enforcement is not 'evaluate'." >&2; exit 1; }
[[ "$(jq -r '.enforcement' "$ACTIVE_PAYLOAD")" == "active" ]] || {
  echo "FAIL: active payload .enforcement is not 'active'." >&2; exit 1; }
echo "identity:        '$NAME' — one ruleset, two enforcement states"

# 1. AUTHORITY. GET /orgs/{org}/rulesets requires organization Administration:
#    write, exactly as POST and PUT do. Succeeding here is therefore proof of
#    ruleset-administration authority — which reading /orgs/{org} is not. This
#    call gates the dry run too: a plan computed without seeing the current
#    inventory cannot tell CREATE from UPDATE, and would be a guess.
if ! RULESETS="$(gh api "orgs/$ORG/rulesets" 2>/dev/null)"; then
  cat >&2 <<EOF
FAIL: cannot read orgs/$ORG/rulesets.

Every organization ruleset endpoint — GET, POST and PUT — requires organization
Administration: write (classic admin:org). This read failing means the identity
lacks that permission, so it cannot apply one either.

Required workflows are an ORGANISATION ruleset. A repo-scoped token, the
governance GitHub App, and a Claude Code session all fail here by design.
Run as a human org owner.
EOF
  exit 1
fi
echo "authority:       orgs/$ORG/rulesets readable (Administration: write)"

# 2. Plan is INFORMATIONAL. The 'workflows' rule is GHEC / GHES >= 3.12 and the
#    'evaluate' enforcement level is Enterprise-only, but GitHub does not state a
#    plan requirement in prose and .plan.name is not a capability probe. The
#    authoritative capability check is step 1 plus GitHub accepting the payload;
#    a hard string match on "enterprise" only invents a false negative.
PLAN="$(gh api "orgs/$ORG" --jq '.plan.name // "unknown"' 2>/dev/null || echo "unreadable")"
echo "org plan:        $PLAN  (informational — GitHub decides, not this string)"

# 3. The workflow this ruleset points at must actually exist, and the numeric
#    repository_id in the payload must be the repository we think it is. Checked
#    via repos/{owner}/{repo} rather than repositories/{id}: it is the stronger
#    assertion (id AND identity, not just id resolves) and some API proxies
#    refuse numeric-id paths outright.
WF_REPO_ID="$(jq -r '.rules[0].parameters.workflows[0].repository_id' "$PAYLOAD")"
WF_PATH="$(jq -r '.rules[0].parameters.workflows[0].path' "$PAYLOAD")"
WF_REF="$(jq -r '.rules[0].parameters.workflows[0].ref' "$PAYLOAD")"
WF_REPO="${WF_REPO_SLUG:-Quantum-L9/l9-ci-core}"
ACTUAL_ID="$(gh api "repos/$WF_REPO" --jq '.id' 2>/dev/null || true)"
if [[ -z "$ACTUAL_ID" ]]; then
  echo "FAIL: cannot read repos/$WF_REPO" >&2
  exit 1
fi
if [[ "$ACTUAL_ID" != "$WF_REPO_ID" ]]; then
  echo "FAIL: payload repository_id=$WF_REPO_ID but $WF_REPO is id $ACTUAL_ID." >&2
  echo "      A wrong id silently requires somebody else's workflow." >&2
  exit 1
fi
echo "workflow source: $WF_REPO ($WF_REPO_ID) @ $WF_REF"
if ! gh api "repos/$WF_REPO/contents/$WF_PATH" --jq '.path' >/dev/null 2>&1; then
  echo "FAIL: $WF_REPO does not contain $WF_PATH" >&2
  exit 1
fi
echo "workflow path:   $WF_PATH  [present]"

# 4. Gating branch CREATION would block repository creation org-wide. GitHub's
#    own option name is "Do not require workflows checks on creation": it allows
#    branch creation regardless of the status check result.
if [[ "$(jq -r '.rules[0].parameters.do_not_enforce_on_create' "$PAYLOAD")" != "true" ]]; then
  echo "FAIL: do_not_enforce_on_create must be true." >&2
  echo "      A ruleset workflow cannot run for a branch-creation event, so a" >&2
  echo "      creation-gated check never resolves and repository creation hangs" >&2
  echo "      across the organisation." >&2
  exit 1
fi
echo "create-gating:   disabled (safe)"

# 5. EXACTLY ONE canonical ruleset. Zero is legal only before the first apply.
#    Two means a previous run split the identity; picking either one silently is
#    how an org ends up enforcing the wrong copy.
MATCHES="$(jq -r --arg n "$NAME" '[.[] | select(.name==$n)] | length' <<<"$RULESETS")"
if [[ "$MATCHES" -gt 1 ]]; then
  cat >&2 <<EOF
FAIL: $MATCHES rulesets are named '$NAME'.

$(jq -r --arg n "$NAME" '.[] | select(.name==$n) | "  id \(.id)  enforcement=\(.enforcement)"' <<<"$RULESETS")

The canonical name must resolve to exactly one ruleset. Delete the duplicates
before continuing — see the runbook's Rollback section — then re-run.
EOF
  exit 1
fi

EXISTING=""
CURRENT_ENFORCEMENT=""
if [[ "$MATCHES" == "1" ]]; then
  EXISTING="$(jq -r --arg n "$NAME" '.[] | select(.name==$n) | .id' <<<"$RULESETS")"
  CURRENT_ENFORCEMENT="$(jq -r --arg n "$NAME" '.[] | select(.name==$n) | .enforcement' <<<"$RULESETS")"
fi

# 6. Only EVALUATE may create. ACTIVE promotes something that already exists and
#    has already been proven by a real consumer canary. Letting active create
#    from nothing is how org-wide blocking enforcement goes live unproven.
if [[ -z "$EXISTING" && "$MODE" == "active" ]]; then
  cat >&2 <<EOF
FAIL: no ruleset named '$NAME' exists, and MODE=active may not create one.

ACTIVE is a promotion, never a first write. The sequence is:

    DRY_RUN=0 MODE=evaluate bash apply.sh     # create, advisory
    bash verify.sh --check                    # RESULT: ADVISORY_VALID
    <real consumer canary PR passes>          # RESULT: ADVISORY_CANARY_PASS
    DRY_RUN=0 MODE=active bash apply.sh       # promote the SAME ruleset id
EOF
  exit 1
fi

# 7. Evaluate must not silently demote live enforcement. Rolling back is a real
#    operation, but it is a deliberate one.
if [[ "$MODE" == "evaluate" && "$CURRENT_ENFORCEMENT" == "active" && "$ALLOW_DEMOTE" != "1" ]]; then
  cat >&2 <<EOF
FAIL: ruleset $EXISTING is currently enforcement=active.

Re-running evaluate would DEMOTE live organisation-wide enforcement to advisory.
If that is the intent, say so explicitly:

    ALLOW_DEMOTE=1 DRY_RUN=0 MODE=evaluate bash apply.sh
EOF
  exit 1
fi

# 8. Same-identity promotion. If a previous run recorded the ruleset id, the id
#    we are about to write must be that one.
if [[ -f "$ID_RECEIPT" ]]; then
  RECORDED="$(tr -d '[:space:]' < "$ID_RECEIPT")"
  if [[ -n "$RECORDED" && -n "$EXISTING" && "$RECORDED" != "$EXISTING" ]]; then
    echo "FAIL: recorded ruleset id $RECORDED but '$NAME' now resolves to $EXISTING." >&2
    echo "      The identity changed under us. Investigate before writing." >&2
    exit 1
  fi
fi

echo
echo "=== plan ==="
echo "ruleset name:    $NAME"
echo "enforcement:     $(jq -r '.enforcement' "$PAYLOAD")"
echo "targets:         $(jq -rc '.conditions.repository_name.include' "$PAYLOAD") @ $(jq -rc '.conditions.ref_name.include' "$PAYLOAD")"
echo "bypass actors:   $(jq -rc '.bypass_actors' "$PAYLOAD")"
if [[ -n "$EXISTING" ]]; then
  echo "existing:        id $EXISTING (enforcement=$CURRENT_ENFORCEMENT) — will UPDATE in place"
  [[ "$MODE" == "evaluate" && "$CURRENT_ENFORCEMENT" == "active" ]] \
    && echo "                 *** DEMOTION: active -> evaluate (ALLOW_DEMOTE=1) ***"
else
  echo "existing:        none — will CREATE (first and only canonical ruleset)"
fi

if [[ "$DRY" == "1" ]]; then
  echo
  echo "DRY_RUN=1 — nothing applied. Re-run with DRY_RUN=0 to apply."
  exit 0
fi

echo
echo "=== apply ==="
mkdir -p "$HERE/evidence"
if [[ -n "$EXISTING" ]]; then
  gh api -X PUT "orgs/$ORG/rulesets/$EXISTING" --input "$PAYLOAD" >/dev/null
  echo "updated ruleset $EXISTING: $NAME  ($CURRENT_ENFORCEMENT -> $(jq -r '.enforcement' "$PAYLOAD"))"
  printf '%s\n' "$EXISTING" > "$ID_RECEIPT"
else
  NEW="$(gh api -X POST "orgs/$ORG/rulesets" --input "$PAYLOAD" --jq '.id')"
  echo "created ruleset $NEW: $NAME  (enforcement=$(jq -r '.enforcement' "$PAYLOAD"))"
  printf '%s\n' "$NEW" > "$ID_RECEIPT"
fi
echo "recorded id -> evidence/ruleset-id"

# Post-write invariant: still exactly one.
POST="$(gh api "orgs/$ORG/rulesets" 2>/dev/null \
  | jq -r --arg n "$NAME" '[.[] | select(.name==$n)] | length' || echo "?")"
if [[ "$POST" != "1" ]]; then
  echo "FAIL: after applying, $POST rulesets are named '$NAME' (expected 1)." >&2
  exit 1
fi
echo "post-check:      exactly one canonical ruleset"

echo
echo "Now run: bash verify.sh --check"
