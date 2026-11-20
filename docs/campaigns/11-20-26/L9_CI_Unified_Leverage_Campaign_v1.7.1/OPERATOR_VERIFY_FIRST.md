# Operator-guided CodeQL + Sonar entitlement and activation verification

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

**Precondition G0 | Mandatory, read-only, interactive.** Run this walkthrough
before changes or new scan/test dispatch in the affected CodeQL/Sonar native
optimization lane: config, features, workflows, analysis modes, required checks
and promotion. G0 itself performs no writes, tests or scans. This is the existing
campaign interaction gate, not new organization law or a receipt schema.
Independent, already authorized Core/SDK engineering and its necessary validation
may continue while account facts are Unknown, provided it does not modify this
native lane, use its unresolved entitlement or bypass its trust boundary.
Read-only source/run inspection may continue. Missing billing facts block the
dependent paid-feature change, not unrelated engineering.

## First words of the CTO agent (start here)

> Before I touch CodeQL or Sonar configuration, I'll verify the existing repos, workflow runs and published scan outcomes myself. Then I'll walk you through **three short read-only checks** of GitHub and Sonar account settings, **one screen at a time**. Don't change settings or share tokens, payment card details or full invoices. I will tell you precisely what information I need from each screen and stop until you give it. This audit will not trigger tests or scans.

**Interaction:** Agent opens the exact page when an authorized interactive browser is available, otherwise provides a link + one navigation action. Ask only *one screen request at a time*. After each screen, summarize the observed state in one sentence and ask for the next. Do not invent access to the user's paid organization. Record a pointer to the observed vendor screen / operator confirmation as evidence; user recollection alone is not a billing receipt. If the operator cannot access a screen, record UNKNOWN, do not pressure for credentials and continue with what can be proven. A human must expressly authorize any later vendor-admin or billing change.

## Self-service source check, without involving the operator

Inspect latest default-branch CodeQL caller/reusable/default and nightly configs in `Quantum-L9/Cursor-Governance`, the latest CodeQL and Sonar run IDs and their **native analyzer log outcome**, exact PR heads, `sonar-project.properties`, `.sonarcloud.properties`, the Sonar workflow, and open PR #1062. Reconcile prior receipts before proposing a fix. Current evidence baseline as of Nov 19-20 2026:

- Cursor CodeQL PR #1067 run 44657558641 analyzed Python and uploaded results successfully, but overlay-base cache **missed** and it fell back, so overlay savings are unproven.
- Cursor Sonar PR #1067 run 44657558389 executed 8175 tests and parsed coverage.xml; native quality gate PASSED. A separate L9 test job also ran. This does **not** justify another test execution merely to reconfirm.
- Cursor PR #1062 is open and proposes a dispatch-only Sonar deep suite. It has not demonstrated a trusted Core mode=apply and published post-promotion native Sonar quality gate. Do not turn off the old trigger on static PR evidence.
- EIE native Sonar PR #364 run 44640276572 also ran 3927 tests; static scan/log coverage can be audited without rerunning.

## Screen 1 of 3: GitHub security activation, Cursor-Governance (read-only)

Open `https://github.com/Quantum-L9/Cursor-Governance` → **Settings** → **Advanced Security** (often under Security and quality). Use the CodeQL analysis / Code scanning section. Ask operator to report ONLY:

1. Does CodeQL show **Advanced setup**, **Default setup**, **Disabled**, or another state?
2. Is GitHub Code Security indicated as enabled/available for this repository? Is there any paid-product status shown, or is this a public repo using free scanning?
3. Under the repository **Security** tab → **Code scanning**, is there a current CodeQL analysis with alerts/last analyzed date? Summary counts only. Do not ask for raw unredacted alerts if sensitive.

**What this proves:** repository's effective native setup and UI analysis state. Do not assume the workflow's existence proves GitHub has accepted uploaded security results. Current architecture expects the custom advanced workflow, not a competing default-setup scan. **Never click Enable, Switch, Disable, Set up, Configure or Save during G0.** If the UI differs, ask the operator to read the actual visible label, do not fabricate a button.

## Screen 2 of 3: Sonar subscription/organization identity (read-only)

Open `https://sonarcloud.io` and select the organization where Cursor is analyzed, expected `quantum-l9`. Navigate to visible organization **Administration / Subscription / Billing / Plan** controls (wording varies). Ask operator for ONLY:

1. Exact organization name/key and subscription tier (Free/Team/Enterprise or other as displayed).
2. Paid private lines-of-code allowance, current billable/used LOC or plan limit, if displayed (do **not** infer from public LOC).
3. Whether **AI CodeFix**, **Advanced Security/SCA** or other paid features appear available/enabled; report UNKNOWN if UI does not show entitlement.

**What this proves:** account ownership and visible product entitlement, not analysis effectiveness. Do not request invoices, card details, credentials, or enable trials/add-ons. The separate `cryptoxdog` Sonar project is outside the `quantum-l9` organization; do **not** conflate its account/charges or assume the operator has access. Its account verification is optional and separate when Odoo is in campaign scope.

## Screen 3 of 3: Actual Sonar project configuration and gate (read-only)

Open `https://sonarcloud.io/dashboard?id=Quantum-L9_Cursor-Governance` while logged into the proper account. Ask operator to confirm:

1. Is the project present and bound to the intended GitHub repository? What is the visible **last analysis date**, default branch and **quality gate** state? A PR scan for #1067 is documented but must not substitute for current branch status.
2. Under project analysis settings, which mode is active: **CI-based analysis** or **Automatic Analysis**? Both cannot be presumed active simultaneously.
3. Under **Quality Gate / New Code / Coverage**, what gate is assigned, what's the new-code definition, and does the project show imported coverage? Report values already visible, not estimates.

**What this proves:** Sonar service project binding, effective analysis mode and value-bearing quality controls. A GitHub job green status or token preflight alone does not prove native Quality Gate. **Do not click Save/Analyze/Recompute, alter quality profile, connect account, or dispatch a workflow.**

## CTO stop/go summary, no changes yet

Return a compact table with columns: Tool/Scope; current activation; plan/entitlement; live scan proof; config/scope gap; UNKNOWN; proposed minimum change; owner. Distinguish `observed` vs `operator-reported` vs `inferred`. Produce a short prioritized action plan emphasizing:

- **Avoid repeating 8175 tests:** inspect PR #1062 and Core dispatch before any heavy-suite changes; reuse trusted existing coverage where supported. No further scans until explicitly admitted for parity proof.
- **CodeQL:** preserve the accepted workflow; compare actual default/advanced state, current native alerts and scan results, cache miss and nightly unknown; don't casually require its check or enable default setup.
- **Sonar:** identify paid features useful at the observed tier, quality gate/new code/coverage, source scope, analysis mode; no subscription changes without a new user instruction.

Stop guided verification at this table. Before a native change, identify its
exact proposed action, owner and evidence. Use authorization already supplied
for that action; otherwise request the explicit go-ahead required by this
user-requested G0 workflow. A G0-complete label cannot grant it. Do not ask again
for independent work that is already authorized, or claim observations not made.

**Gate closure:** G0 COMPLETE means the walkthrough occurred and every material account/UI field has `OBSERVED`, `OPERATOR_REPORTED`, or `UNKNOWN` with its source. G0 COMPLETE does **not** mean entitlements were proved or implementation is authorized. Changes depending on UNKNOWN remain blocked. Do not manufacture paid-account confirmations from public repo metadata.

## Acceptance tests for G0

- The G0 verification activity makes no file changes, remote writes, settings
  mutations, scan dispatches or test runs. Independent authorized engineering
  remains outside this activity under the scoped boundary above.
- Exactly one operator-facing screen request at a time; software/CI evidence the agent can retrieve is collected autonomously.
- Each answer is recorded with its precise service and organization boundary; billing secrets and tokens are never requested.
- G0 summary exists with all observed/missing facts and explicit prior-version scan receipts; operator's later authorization is treated separately from G0 completion.


## Read-only follow-up for other tools (v1.6.0)

After the original three screens, consume `G0_OTHER_VENDOR_CHECK.md`: ask for
**only** the necessary Codecov/GitGuardian account details not available from
sampled GitHub source and run logs. One screen at a time. No credentials or
secret values. Account gaps are recorded UNKNOWN, not inferred from action
success, and do not block independent authorized Core/SDK work or its necessary
tests. The extension itself dispatches no scan/test and changes no dashboard,
plan or feature; dependent native changes require applicable explicit authorization.
