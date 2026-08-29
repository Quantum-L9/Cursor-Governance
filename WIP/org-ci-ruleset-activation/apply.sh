#!/usr/bin/env bash
# Apply the canonical-CI required-workflow ruleset to the Quantum-L9 organization.
#
# This is the step that makes the sanctioned path live. Everything else in the
# architecture already assumes it has happened; nothing has ever performed it.
#
# Self-contained ON PURPOSE. It does not read Quantum-L9/.github's rulesets/
# directory and does not go through `make apply-rulesets`, because that target
# points at ops/apply-rulesets.sh — a path that has never existed in any commit.
#
# Requires an identity with `organization_administration: write` (classic
# `admin:org`). The governance GitHub App does NOT have it: its manifest grants
# repository contents/pull_requests plus organization members:read. Run this as
# a human org owner.
#
#   DRY_RUN=1 bash apply.sh          # default — prints the plan, changes nothing
#   DRY_RUN=0 bash apply.sh          # applies the EVALUATE (advisory) ruleset
#   DRY_RUN=0 MODE=active bash apply.sh   # applies the ACTIVE (blocking) ruleset
set -euo pipefail

ORG="${ORG:-Quantum-L9}"
DRY="${DRY_RUN:-1}"
MODE="${MODE:-evaluate}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$MODE" in
  evaluate) PAYLOAD="$HERE/org-ci-required.ruleset.json" ;;
  active)   PAYLOAD="$HERE/org-ci-required.active.ruleset.json" ;;
  *) echo "MODE must be 'evaluate' or 'active' (got '$MODE')" >&2; exit 2 ;;
esac

command -v gh >/dev/null || { echo "gh CLI required" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }
[[ -f "$PAYLOAD" ]] || { echo "missing payload: $PAYLOAD" >&2; exit 1; }

NAME="$(jq -r '.name' "$PAYLOAD")"
WF_REPO_ID="$(jq -r '.rules[0].parameters.workflows[0].repository_id' "$PAYLOAD")"
WF_PATH="$(jq -r '.rules[0].parameters.workflows[0].path' "$PAYLOAD")"

echo "=== preconditions ==="

# 1. Can we even see the org? A 403 here means the token is repo-scoped.
if ! PLAN="$(gh api "orgs/$ORG" --jq '.plan.name // "unknown"' 2>/dev/null)"; then
  echo "FAIL: cannot read orgs/$ORG — this token is not org-scoped." >&2
  echo "      Required workflows are an ORGANISATION ruleset; a repo-scoped" >&2
  echo "      token (or a Claude Code session) cannot apply one." >&2
  exit 1
fi
echo "org plan: $PLAN"

# 2. Required workflows are a GitHub Enterprise Cloud feature. Say so rather
#    than emitting a payload GitHub will reject with an opaque error.
if [[ "$PLAN" != "enterprise" ]]; then
  cat >&2 <<EOF
FAIL: org plan is '$PLAN', not 'enterprise'.

The 'workflows' ruleset rule (Require workflows to pass before merging) is a
GitHub Enterprise Cloud feature. On a lower plan the sanctioned enforcement
surface named in l9-ci-core/.l9/org-runtime-contract.yaml

    enforcement_mechanism: github_organization_required_workflow_ruleset

is NOT AVAILABLE, and no amount of tooling here changes that. See README.md
"If the org is not Enterprise Cloud" for the honest options.
EOF
  exit 1
fi

# 3. The workflow this ruleset points at must actually exist, and the numeric
#    repository_id in the payload must be the repository we think it is. Checked
#    via repos/{owner}/{repo} rather than repositories/{id}: it is the stronger
#    assertion (id AND identity, not just id resolves) and some API proxies
#    refuse numeric-id paths outright.
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
echo "workflow source: $WF_REPO ($WF_REPO_ID)"
if ! gh api "repos/$WF_REPO/contents/$WF_PATH" --jq '.path' >/dev/null 2>&1; then
  echo "FAIL: $WF_REPO does not contain $WF_PATH" >&2
  exit 1
fi
echo "workflow path:   $WF_PATH  [present]"

# 4. Gating branch CREATION would block repository creation org-wide, and
#    org-ci.yml has no push trigger so a creation check could never resolve.
if [[ "$(jq -r '.rules[0].parameters.do_not_enforce_on_create' "$PAYLOAD")" != "true" ]]; then
  echo "FAIL: do_not_enforce_on_create must be true." >&2
  echo "      Gating branch creation with a workflow that cannot run on push" >&2
  echo "      blocks repository creation across the organisation." >&2
  exit 1
fi
echo "create-gating:   disabled (safe)"

echo
echo "=== plan ==="
echo "ruleset name:    $NAME"
echo "enforcement:     $(jq -r '.enforcement' "$PAYLOAD")"
echo "targets:         $(jq -rc '.conditions.repository_name.include' "$PAYLOAD") @ $(jq -rc '.conditions.ref_name.include' "$PAYLOAD")"

EXISTING="$(gh api "orgs/$ORG/rulesets" --jq ".[] | select(.name==\"$NAME\") | .id" 2>/dev/null || true)"
if [[ -n "$EXISTING" ]]; then
  echo "existing:        id $EXISTING (will UPDATE)"
else
  echo "existing:        none (will CREATE)"
fi

if [[ "$DRY" == "1" ]]; then
  echo
  echo "DRY_RUN=1 — nothing applied. Re-run with DRY_RUN=0 to apply."
  exit 0
fi

echo
echo "=== apply ==="
if [[ -n "$EXISTING" ]]; then
  gh api -X PUT "orgs/$ORG/rulesets/$EXISTING" --input "$PAYLOAD" >/dev/null
  echo "updated ruleset $EXISTING: $NAME"
else
  NEW="$(gh api -X POST "orgs/$ORG/rulesets" --input "$PAYLOAD" --jq '.id')"
  echo "created ruleset $NEW: $NAME"
fi
echo
echo "Now run: bash verify.sh"
