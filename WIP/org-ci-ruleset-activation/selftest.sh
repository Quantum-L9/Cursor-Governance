#!/usr/bin/env bash
# Self-test for the activation kit's decision logic.
#
# Runs apply.sh and verify.sh against a stubbed GitHub API so every refusal path
# is exercised without touching the organisation. No network, no credentials, no
# mutation — safe to run anywhere, including CI.
#
#   bash selftest.sh
#
# This exists because the kit's whole value is refusing to do the wrong thing.
# The defect that motivated it — the two payloads carrying different .name values
# while apply.sh resolves a ruleset BY NAME, so promotion silently created a
# second ruleset — was invisible to any check that only reads the scripts. T2
# below is that regression, pinned.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT

PASSED=0
FAILED=0

ok()   { printf '  ok    %s\n' "$1"; PASSED=$((PASSED + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; printf '        %s\n' "$2"; FAILED=$((FAILED + 1)); }

# Fresh copy of the kit per case, so receipts from one case cannot leak into another.
reset_kit() {
  rm -rf -- "${WORK:?}/kit"
  mkdir -p "$WORK/kit"
  cp "$HERE/apply.sh" "$HERE/verify.sh" "$WORK/kit/"
  cp "$HERE/org-ci-required.ruleset.json" "$HERE/org-ci-required.active.ruleset.json" "$WORK/kit/"
}

mkdir -p "$WORK/bin"
cat > "$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
# Stubbed `gh`. RULESETS_JSON drives the org ruleset list; RULESET_DETAIL drives a
# single ruleset read. RULESETS_JSON unset means "org read fails" (no authority).
args="$*"
case "$args" in
  *"/check-runs"*)
      [[ -n "${CHECK_RUNS:-}" ]] || exit 1
      printf '%s\n' "$CHECK_RUNS" ;;
  *"/pulls/"*)
      [[ -n "${CANARY_SHA:-}" ]] || exit 1
      printf '%s\n' "$CANARY_SHA" ;;
  *"orgs/Quantum-L9/rulesets/"*)
      [[ -n "${RULESET_DETAIL:-}" ]] || exit 1
      printf '%s\n' "$RULESET_DETAIL" ;;
  *"orgs/Quantum-L9/rulesets"*)
      [[ -n "${RULESETS_JSON:-}" ]] || exit 1
      printf '%s\n' "$RULESETS_JSON" ;;
  *"orgs/Quantum-L9"*)                        printf 'enterprise\n' ;;
  *"repos/Quantum-L9/l9-ci-core/contents/"*)  printf '.github/workflows/org-ci.yml\n' ;;
  *"repos/Quantum-L9/l9-ci-core"*)            printf '1285564308\n' ;;
  *) printf '{}\n' ;;
esac
STUB
chmod +x "$WORK/bin/gh"
export PATH="$WORK/bin:$PATH"

# A ruleset detail body that satisfies every shape assertion in verify.sh.
GOOD_DETAIL='{"id":42,"name":"L9 canonical CI required","target":"branch","enforcement":"evaluate","bypass_actors":[],"conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]},"repository_name":{"include":["~ALL"],"exclude":[]}},"rules":[{"type":"workflows","parameters":{"do_not_enforce_on_create":true,"workflows":[{"repository_id":1285564308,"path":".github/workflows/org-ci.yml","ref":"refs/heads/main"}]}}]}'
LIST_EVAL='[{"id":42,"name":"L9 canonical CI required","enforcement":"evaluate"}]'
LIST_ACTIVE='[{"id":42,"name":"L9 canonical CI required","enforcement":"active"}]'
LIST_DUPES='[{"id":42,"name":"L9 canonical CI required","enforcement":"evaluate"},{"id":43,"name":"L9 canonical CI required","enforcement":"active"}]'
active_detail() { jq -c '.enforcement="active"' <<<"$GOOD_DETAIL"; }

# expect_fail <label> <expected substring> -- <command...>
expect_fail() {
  local label="$1" want="$2"; shift 3
  local out rc
  out="$( "$@" 2>&1 )" && rc=0 || rc=$?
  if [[ "$rc" == "0" ]]; then
    bad "$label" "expected non-zero exit, got 0"
  elif ! grep -qF -- "$want" <<<"$out"; then
    bad "$label" "exit $rc but message missing: $want"
  else
    ok "$label"
  fi
}

# expect_out <label> <expected substring> -- <command...>
expect_out() {
  local label="$1" want="$2"; shift 3
  local out rc
  out="$( "$@" 2>&1 )" && rc=0 || rc=$?
  if [[ "$rc" != "0" ]]; then
    bad "$label" "expected exit 0, got $rc: $(tail -3 <<<"$out")"
  elif ! grep -qF -- "$want" <<<"$out"; then
    bad "$label" "exit 0 but output missing: $want"
  else
    ok "$label"
  fi
}

echo "=== payload invariants ==="
reset_kit
if [[ "$(jq -r '.name' "$WORK/kit/org-ci-required.ruleset.json")" \
   == "$(jq -r '.name' "$WORK/kit/org-ci-required.active.ruleset.json")" ]]; then
  ok "both payloads carry one ruleset name"
else
  bad "both payloads carry one ruleset name" "names differ — promotion would create a second ruleset"
fi
if diff -q <(jq -S 'del(.enforcement)' "$WORK/kit/org-ci-required.ruleset.json") \
           <(jq -S 'del(.enforcement)' "$WORK/kit/org-ci-required.active.ruleset.json") >/dev/null; then
  ok "payloads differ in .enforcement only"
else
  bad "payloads differ in .enforcement only" "promotion would change more than enforcement"
fi

echo
echo "=== apply.sh refusals ==="

reset_kit
expect_fail "T1 no org authority -> refuse (dry run included)" \
  "cannot read orgs/Quantum-L9/rulesets" \
  -- env -u RULESETS_JSON bash "$WORK/kit/apply.sh"

# T2 pins the original defect: a decorated evaluate name must be refused outright.
reset_kit
jq '.name = "L9 canonical CI required (evaluate)"' \
  "$HERE/org-ci-required.ruleset.json" > "$WORK/kit/org-ci-required.ruleset.json"
expect_fail "T2 split identity in payload names -> refuse [regression]" \
  "do not share one ruleset identity" \
  -- env RULESETS_JSON="$LIST_EVAL" bash "$WORK/kit/apply.sh"

reset_kit
jq '.conditions.ref_name.include = ["~ALL"]' \
  "$HERE/org-ci-required.active.ruleset.json" > "$WORK/kit/org-ci-required.active.ruleset.json"
expect_fail "T3 payloads differ beyond enforcement -> refuse" \
  "differ in more than .enforcement" \
  -- env RULESETS_JSON="$LIST_EVAL" bash "$WORK/kit/apply.sh"

reset_kit
expect_fail "T4 MODE=active with no existing ruleset -> refuse to create" \
  "may not create one" \
  -- env RULESETS_JSON='[]' MODE=active bash "$WORK/kit/apply.sh"

reset_kit
expect_fail "T5 two rulesets share the canonical identity -> refuse" \
  "share the canonical identity" \
  -- env RULESETS_JSON="$LIST_DUPES" bash "$WORK/kit/apply.sh"

# The legacy decorated name is the SAME ruleset, not a missing one. Counting only
# the undecorated name reports zero, and CREATE then leaves the old org-wide
# workflow rule running beside the new one — two blocking rules, one org.
LIST_LEGACY='[{"id":42,"name":"L9 canonical CI required (evaluate)","enforcement":"evaluate"}]'
reset_kit
expect_out "T5a legacy decorated name resolves as the same identity [regression]" \
  "will UPDATE in place" \
  -- env RULESETS_JSON="$LIST_LEGACY" MODE=active bash "$WORK/kit/apply.sh"

reset_kit
expect_out "T5b legacy decorated name is renamed, not duplicated [regression]" \
  "*** RENAME" \
  -- env RULESETS_JSON="$LIST_LEGACY" MODE=active bash "$WORK/kit/apply.sh"

reset_kit
LIST_LEGACY_SPLIT='[{"id":42,"name":"L9 canonical CI required (evaluate)","enforcement":"evaluate"},{"id":43,"name":"L9 canonical CI required","enforcement":"active"}]'
expect_fail "T5c canonical + legacy decorate together -> refuse (split)" \
  "share the canonical identity" \
  -- env RULESETS_JSON="$LIST_LEGACY_SPLIT" bash "$WORK/kit/apply.sh"

reset_kit
expect_fail "T6 evaluate over live active ruleset -> refuse to demote" \
  "would DEMOTE live organisation-wide enforcement" \
  -- env RULESETS_JSON="$LIST_ACTIVE" MODE=evaluate bash "$WORK/kit/apply.sh"

reset_kit
mkdir -p "$WORK/kit/evidence"; printf '99\n' > "$WORK/kit/evidence/ruleset-id"
expect_fail "T7 recorded ruleset id no longer resolves -> refuse" \
  "The identity changed under us" \
  -- env RULESETS_JSON="$LIST_EVAL" MODE=active bash "$WORK/kit/apply.sh"

echo
echo "=== apply.sh permitted paths ==="

reset_kit
expect_out "T8 evaluate with no existing ruleset -> plan CREATE" \
  "will CREATE" \
  -- env RULESETS_JSON='[]' MODE=evaluate bash "$WORK/kit/apply.sh"

reset_kit
expect_out "T9 active over existing evaluate -> plan UPDATE in place" \
  "will UPDATE in place" \
  -- env RULESETS_JSON="$LIST_EVAL" MODE=active bash "$WORK/kit/apply.sh"

reset_kit
expect_out "T10 ALLOW_DEMOTE=1 -> plan demotion explicitly" \
  "*** DEMOTION" \
  -- env RULESETS_JSON="$LIST_ACTIVE" MODE=evaluate ALLOW_DEMOTE=1 bash "$WORK/kit/apply.sh"

reset_kit
expect_out "T11 dry run writes nothing" \
  "DRY_RUN=1 — nothing applied" \
  -- env RULESETS_JSON='[]' MODE=evaluate bash "$WORK/kit/apply.sh"

echo
echo "=== verify.sh result states ==="

reset_kit
expect_out "V1 correct shape, evaluate -> ADVISORY_VALID" \
  "RESULT: ADVISORY_VALID" \
  -- env RULESETS_JSON="$LIST_EVAL" RULESET_DETAIL="$GOOD_DETAIL" bash "$WORK/kit/verify.sh" --check

reset_kit
expect_out "V2 correct shape, active -> LIVE_ENFORCING" \
  "RESULT: LIVE_ENFORCING" \
  -- env RULESETS_JSON="$LIST_ACTIVE" RULESET_DETAIL="$(active_detail)" bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V3 bypass actor present -> FAIL" \
  "bypass actors present" \
  -- env RULESETS_JSON="$LIST_ACTIVE" \
     RULESET_DETAIL="$(jq -c '.enforcement="active" | .bypass_actors=[{"actor_id":5}]' <<<"$GOOD_DETAIL")" \
     bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V4 wrong workflow path -> FAIL" \
  "expected '.github/workflows/org-ci.yml'" \
  -- env RULESETS_JSON="$LIST_ACTIVE" \
     RULESET_DETAIL="$(jq -c '.enforcement="active" | .rules[0].parameters.workflows[0].path=".github/workflows/l9-analysis.yml"' <<<"$GOOD_DETAIL")" \
     bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V5 wrong source repository_id -> FAIL" \
  "expected 1285564308" \
  -- env RULESETS_JSON="$LIST_ACTIVE" \
     RULESET_DETAIL="$(jq -c '.enforcement="active" | .rules[0].parameters.workflows[0].repository_id=999' <<<"$GOOD_DETAIL")" \
     bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V6 create-gating enabled -> FAIL" \
  "repository creation can hang org-wide" \
  -- env RULESETS_JSON="$LIST_ACTIVE" \
     RULESET_DETAIL="$(jq -c '.enforcement="active" | .rules[0].parameters.do_not_enforce_on_create=false' <<<"$GOOD_DETAIL")" \
     bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V7 split identity in the org -> FAIL" \
  "the canonical identity is split" \
  -- env RULESETS_JSON="$LIST_DUPES" bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V8 no canonical ruleset -> FAIL" \
  "no ruleset named" \
  -- env RULESETS_JSON='[]' bash "$WORK/kit/verify.sh" --check

reset_kit
expect_fail "V9 no org authority -> FAIL" \
  "cannot read orgs/Quantum-L9/rulesets" \
  -- env -u RULESETS_JSON bash "$WORK/kit/verify.sh" --check

# Only LIVE_ENFORCING may write the enforcement evidence file. An advisory run
# writing it is how an evaluate-mode rule gets recorded as live enforcement.
reset_kit
env RULESETS_JSON="$LIST_EVAL" RULESET_DETAIL="$GOOD_DETAIL" \
  bash "$WORK/kit/verify.sh" --check >/dev/null 2>&1 || true
if [[ -f "$WORK/kit/evidence/organization-ruleset-live-enforcement.json" ]]; then
  bad "V10 advisory run writes no enforcement evidence" "evidence file written while enforcement=evaluate"
else
  ok "V10 advisory run writes no enforcement evidence"
fi

reset_kit
env RULESETS_JSON="$LIST_ACTIVE" RULESET_DETAIL="$(active_detail)" \
  bash "$WORK/kit/verify.sh" --check >/dev/null 2>&1 || true
if jq -e '.enforcement=="active" and .ruleset_id==42 and (.bypass_actors|length)==0' \
     "$WORK/kit/evidence/organization-ruleset-live-enforcement.json" >/dev/null 2>&1; then
  ok "V11 LIVE_ENFORCING writes well-formed enforcement evidence"
else
  bad "V11 LIVE_ENFORCING writes well-formed enforcement evidence" "evidence missing or malformed"
fi

echo
echo "=== verify.sh: ACTIVE canary must post-date promotion ==="

# A canary run from the EVALUATE phase still sits on the PR head after promotion.
# Re-checking without a new commit would report LIVE_CANARY_PASS off an
# advisory-mode run — the exact "proved it under evaluate, claimed it under
# active" confusion the phase ordering exists to prevent.
CANARY_SHA="4e2d4e9d64a8a5ca89da91c5ef18314c0331d4b4"
runs_started() {
  printf '[{"name":"Analyze (central Core)","id":99370863320,"status":"completed","conclusion":"success","started_at":"%s","html_url":"https://github.com/Quantum-L9/l9-observability-core/actions/runs/33353393558/job/99370863320","app":{"slug":"github-actions"}}]' "$1"
}

reset_kit
mkdir -p "$WORK/kit/evidence"
expect_fail "P1 active canary with no promoted-at receipt -> FAIL" \
  "requires evidence/promoted-at" \
  -- env RULESETS_JSON="$LIST_ACTIVE" RULESET_DETAIL="$(active_detail)" \
     CANARY_SHA="$CANARY_SHA" CHECK_RUNS="$(runs_started 2026-08-31T03:19:00Z)" \
     bash "$WORK/kit/verify.sh" --pr Quantum-L9/l9-observability-core 4

reset_kit
mkdir -p "$WORK/kit/evidence"; printf '2026-08-31T03:17:28Z\n' > "$WORK/kit/evidence/promoted-at"
expect_fail "P2 active canary that ran BEFORE promotion -> FAIL [regression]" \
  "before promotion" \
  -- env RULESETS_JSON="$LIST_ACTIVE" RULESET_DETAIL="$(active_detail)" \
     CANARY_SHA="$CANARY_SHA" CHECK_RUNS="$(runs_started 2026-08-31T03:10:00Z)" \
     bash "$WORK/kit/verify.sh" --pr Quantum-L9/l9-observability-core 4

reset_kit
mkdir -p "$WORK/kit/evidence"; printf '2026-08-31T03:17:28Z\n' > "$WORK/kit/evidence/promoted-at"
expect_out "P3 active canary that ran AFTER promotion -> LIVE_CANARY_PASS" \
  "RESULT: LIVE_CANARY_PASS" \
  -- env RULESETS_JSON="$LIST_ACTIVE" RULESET_DETAIL="$(active_detail)" \
     CANARY_SHA="$CANARY_SHA" CHECK_RUNS="$(runs_started 2026-08-31T03:19:00Z)" \
     bash "$WORK/kit/verify.sh" --pr Quantum-L9/l9-observability-core 4

reset_kit
expect_out "P4 evaluate-phase canary needs no promotion receipt" \
  "RESULT: ADVISORY_CANARY_PASS" \
  -- env RULESETS_JSON="$LIST_EVAL" RULESET_DETAIL="$GOOD_DETAIL" \
     CANARY_SHA="$CANARY_SHA" CHECK_RUNS="$(runs_started 2026-08-31T03:10:00Z)" \
     bash "$WORK/kit/verify.sh" --pr Quantum-L9/l9-observability-core 4

echo
printf 'selftest: %d passed, %d failed\n' "$PASSED" "$FAILED"
[[ "$FAILED" == "0" ]] || exit 1
