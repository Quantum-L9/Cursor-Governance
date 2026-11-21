> **DRAFT v2 (X9).** Unchanged `PROOF.md` text with one status per requirement in the launch vocabulary (`00_LAUNCH_IN_CTO_MODE.md:59-60`): `PASS`, `BLOCKED` (one owner, one next action) or `NOT_PROVEN`. Evidence paths without a directory are in `evidence/`; line numbers refer to the files at Cursor-Governance #1124 head `461cabd5`. "REST" means a read-only `gh api repos/Quantum-L9/...` GET, observed 2026-11-21 13:10-13:20Z; the v2 additions (P10 non-target plans, P14 dependency-review log, #1124 receipt) were read 13:25-13:28Z. `[x]` marks PASS only.

# Acceptance, validation and rollout receipts

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

## Required evidence, not green theater

**First-consumer blocker:** `CURSOR_CANARY_PASS` from `CURSOR_CANARY.md` is a
mandatory prerequisite to secondary rollout and removal of redundant
consumer checks. `HARVEST.md` candidate dispositions must precede shared
configuration/rule promotion at the correct upstream owner. CI Core/SDK unit tests, a published PR,
and a simulated consumer are insufficient.
> **Status: PASS** — accepted exception: operator decision D1 (2026-11-21) accepts the CEG #522 (`fc4711a2`) check retirement before `CURSOR_CANARY_PASS` (central Core covers the retired checks; CEG kept green on every promotion canary #324-#339) as a recorded exception; the violated clause stays on record — evidence: violated: "`CURSOR_CANARY_PASS` ... is a mandatory prerequisite to ... removal of redundant consumer checks". `CURSOR_CANARY_PASS` is recorded (`CURSOR_CANARY_RESULT.md:40`; CG #1112 merged 2026-11-21T07:37:12Z as `35f8d88d`, REST). CEG #522 "ci: one owner per lint and contract check; central Core covers PRs" removed ci.yml lint, ci-quality.yml lint-format, contracts.yml lint, compliance.yml ruff/mypy and contract scan, and refactoring-validation.yml; merged 2026-11-20T22:44:57Z (`fc4711a2`, REST), about 9 h before the PASS and while the 2026-11-20 verdict was `CURSOR_CANARY_BLOCKED` (`CURSOR_CANARY_RESULT.md:48-61`). Mitigation (#522 body): one local owner per check kept (`l9-lint-test.yml`, `contracts.yml`). Second clause (harvest dispositions before promotion) is not provable from merged artifacts: the ledger index merged in CG #1091 (2026-11-21 05:09Z) after Core #295 (`8667d537`) and #300 (`7e11e2b0`) promoted C2/C3.

P0: every observed required check is actually governed. Record correct
organization ruleset target, correct working/source revision, enforced mode,
executed providers and permissions, plus any exceptions. `cryptoxdog` must
have separate, verified enforcement.
> **Status: PASS** — evidence: Cursor-Governance: org ruleset 21895545 "L9 canonical CI required" `enforcement: active`, target `~DEFAULT_BRANCH`, required workflow `.github/workflows/org-ci.yml@refs/heads/main` in repository id 1285564308 (= `Quantum-L9/l9-ci-core`), required check `Analyze (central Core)`; repo ruleset 20855699 `active`, strict, requires Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene (REST `rules/branches/main`, `rulesets/{id}`). Working revision: Core `main` `acb73463` org-ci pins actions `2ee1720b`, SDK `4a887396`, Semgrep 1.186.0; workflow and `analyze` job `permissions: contents: read` (REST read of `org-ci.yml`). Executed providers: Semgrep python/typescript/consumer instances, Biome, repository verification, security scan (`CURSOR_CANARY_RESULT.md:24-38`; `CLOSEOUT_RECEIPT.md:13`). Exceptions: `OrganizationAdmin` bypass `always` on 21895545, `EnterpriseOwner` bypass on 20855699, `strict_required_status_checks_policy: false` on 21895545 (`CLOSEOUT_RECEIPT.md:58`). `cryptoxdog`: IB-Odoo_19 is not bound by 21895545 and carries its own ruleset 17291607 with four required checks (`STAGE1_INTEGRATION.md:55`, observed 2026-11-20; not re-read, repository outside this session's allowed set).

P1: detection is complete and accurate. Known-good mixed Python+TS repository
selects both. Framework/supply-chain capabilities select correctly. Deliberate
missing/invalid metadata and scanner failures yield incomplete/fail rather
than PASS. Document detectors' blind spots and known unsupported languages.
> **Status: NOT_PROVEN** — evidence: Shown: mixed Python+TS selects both (`STAGE1_INTEGRATION.md:33`; live CG plan python + typescript + consumer, `CURSOR_CANARY_RESULT.md:27`); an incomplete required instance fails (`CURSOR_CANARY_RESULT.md:34`); Django rules only where Django is detected (SDK #141); blind spots documented (JavaScript/shell `unsupported` in CG, `OPEN_ITEMS.md:42`, T32). Missing, across two owners: Odoo framework capability selection (no SDK Odoo pack exists, `HARVEST_LEDGER.md` S1a-S1f), supply-chain capability selection on a consumer (C5 step two not on Core `main`, `HARVEST_LEDGER.md:174`), and a deliberate missing/invalid-metadata witness.

P2: real tool runs. Capture native executable version, SHA/digest where
available, exact central config/rulepack digest, file scope, normalized
findings/coverage, status, run link and exact repository SHA. A provider that
can only issue an advisory artifact cannot be presented as a blocking gate.
Separate the inspected source snapshot, PR head, actual analyzed/merge checkout,
and resolved reusable workflow/action revision. Missing coordinates remain
Unknown; a default-branch SHA cannot substitute for the code a hosted run used.
> **Status: BLOCKED** — owner: CTO — next action: record the central rulepack content digest and the analyzed merge-checkout SHA for run 44876362790 from its instance bundle and checkout log — evidence: CG canary records Semgrep 1.171.0 from Core's lock, SDK `4a887396`, file scope (884 files), normalized findings, status, run link, PR head `6ef0ae35` merged with `main` `d7e929f2`, actions `284a5eb6` (`CURSOR_CANARY_RESULT.md:9-25`). Missing: rulepack content digest and the analyzed merge ref as distinct from the PR head. The live required job now runs Semgrep 1.186.0 (Core #339 `acb73463`); its CG coordinates exist only as promotion-canary leg run 44903350118, job 136844062053 success (REST).

P3: parity. For every retired local check, test a known-bad case that fails
and a known-good case that passes in the central successor. Reproduce unique
consumer rule findings and preserve project tests. Compare historical live
runs before and after. No local workflow/config removal before parity.
> **Status: BLOCKED** — owner: CG-CUTOVER — next action: produce the parity receipts listed in `REQUIRED_CHECK_CUTOVER.md:51-52` (ruff, format and stale-lock negative witnesses failing `Analyze (central Core)`; Test Suite count parity on `merge_group` and push) before any local check is retired — evidence: No CG local check is retired: rules on `main` still require all five local checks (REST; `REQUIRED_CHECK_CUTOVER.md:4`). Biome has a known-good (#1088) and known-bad receipt (`8043a32e`, run 44877881561 failure, REST).

P4: coverage across four canaries, then every eligible org repo. Publish
repo-by-repo coverage and policy ledger, not merely a percentage without
unscanned repository names. Include external owner separately. A new supported
repo proves Core/SDK runtime inheritance without routine copies/repins. Record
retained native callers and their required SHA-pin updates, managed native files,
project identities and product settings separately; do not claim these vanished.
> **Status: NOT_PROVEN** — out of scope: operator, 2026-11-20 21:50Z — the campaign cuts Cursor-Governance over to organization CI, debugged and proven; rolling out to other repositories is a separate campaign (`CLOSEOUT_RECEIPT.md:5-6`) — evidence: per-repository enforcement boundary recorded for six Quantum-L9 repositories plus IB-Odoo_19 (`STAGE1_INTEGRATION.md:45-57`), kept for the rollout campaign.

P5: paid-tool leverage. Each tool must have actual tier/entitlement and native
project configuration proof, demonstrable unique value or explicitly
substantiated retirement decision, before/after scan cost and coverage where
measurable, and no unapproved vendor billing or permission changes. If native
access is unavailable, label optimization blocked by access and do not certify
complete spend optimization.
> **Status: NOT_PROVEN** — evidence: Cannot be shown from GitHub content: tier, seats, entitlement and spend live in vendor and GitHub billing views. GitHub Secret Protection / Code Security licence count unknown (`OPEN_ITEMS.md:40`, T31); Semgrep Free is operator-reported (`SEMGREP_REVIEW.md`); CodeRabbit is a trial (`OPEN_ITEMS.md:31`, T27); Codecov plan not read (`CODECOV_REVIEW.md:5`); Copilot fails on quota (T26).

P6: no unauthorized changes. PRs published by target-verified `make pr`; no
manual raw pushes, branch protection bypass, merge, deployment or payments.
All open PR overlap reconciled by exact head and base SHA before writing.
> **Status: PASS** — accepted exception: operator decision D2 (2026-11-21) accepts the direct pushes to the throwaway #1096 canary branch (never merged; #1096 closed unmerged) as a recorded exception; the violated clause stays on record — evidence: violated: "no manual raw pushes". The witnesses for `CURSOR_CANARY_PASS` "were pushed to the canary branch directly on CTO instruction" because `run_pr_security.sh` cannot judge consumer-rule expect-fail fixtures (`CURSOR_CANARY_RESULT.md:46`; PR #1096, DO NOT MERGE). Merges were operator-authorized (`OPEN_ITEMS.md` recorded decisions, 2026-11-20 18:55Z and 19:10Z). Open-PR overlap reconciliation by exact head/base SHA: not evidenced.

P7: rollback. Preserve SHA of Core, SDK, org rulesets and native-provider
config before promotion. Central canary failure halts next rollout wave;
rollback is narrowly scoped to faulty owning release, never consumer-local
policy bypass. Verify rollback itself against the affected required checks.
> **Status: BLOCKED** — owner: N1e (Core canary/pins) — next action: run one scoped pin-rollback drill on a canary branch and record the affected required checks before and after — evidence: Halt-on-failure shown: Core #319 canary run 44864948490 failure and #319 unmerged (REST `merged_at: null`; `CLOSEOUT_RECEIPT.md:34`); pre-promotion SHAs kept as canary base pins. Missing: no rollback executed or verified. Caveat: #324's verdict job 136761385630 passed while both CG legs failed (jobs 136759651393, 136759651380, REST; `CLOSEOUT_RECEIPT.md:36`), the masking defect fixed as row 27 (Core #328 `03028b6a`).

P8: invariant closure. For EACH ID in `INVARIANTS.yaml`, show (a) exact
source-owner change/accepted existing law, (b) type/schema compatibility,
(c) known-bad witness that fails before/when tested, (d) known-good witness
that passes, (e) real enforcement observation, (f) revision-bound integrated
Core+SDK run, and (g) disposition (implemented, already satisfied, invalid,
blocked). Merely including a statement in YAML is not an enforcement receipt.
Global constitutional refs remain canonical at `.github`; campaign candidates
must not self-admit. No local check retirement if any relevant invariant's
negative witness or parity evidence remains missing.
> **Status: BLOCKED** — owner: CTO — next action: compile the per-ID (a)-(g) table for L9-CI-CORE-001..006 and L9-CI-SDK-001..005 from the contracts, witness tests and canary receipts — evidence: Invariants are in the owner contracts (Core `.l9/governance-contract.yaml` `ci_runtime_invariants`; SDK `.l9/integration-contract.yaml` `ci_provider_invariants`, REST) with witness test files (Core #283 `1942a1be` adds `tests/governance/test_ci_runtime_invariants.py`; SDK #122 `0089b76c` adds `tests/invariants/test_ci_provider_invariants.py`). No per-ID (e) enforcement observation, (f) integrated run or (g) disposition exists.

## Concrete tests

- Capability selection fixtures (SDK-001, Core-003): Python-only, TypeScript-only, mixed,
  Odoo Python+XML, no supported code, malformed manifests, unsupported env.
  > **Status: BLOCKED** — owner: L1 (SDK) — next action: add TypeScript-only, Odoo Python+XML, malformed-manifest and unsupported-environment inventory fixtures and record their plans — evidence: Observed: mixed, Python-only and no-supported-code fixtures (`STAGE1_INTEGRATION.md:31-36`).

- Provider failures (SDK-002, Core-003): missing executable, hash mismatch, registry/network
  failure, invalid custom rulepack, report parse failure, scanner timeout,
  missing token for externally required native scanner.
  > **Status: BLOCKED** — owner: L1 (SDK) — next action: add provider-failure witnesses for missing executable, hash mismatch, registry/network failure, invalid rulepack and report-parse failure (a parse error must not count as covered) — evidence: Observed: rule timeouts counted incomplete (SDK #131 `9af1a202`; B5 at `CURSOR_CANARY_RESULT.md:61`); a required instance that cannot complete fails (runs 44825395263, 44826737909). Open defect: a Semgrep parse error is still counted as covered (`CURSOR_CANARY_RESULT.md:44`). The missing-token case for a native scanner is Core-side and stays unproven after this action.

- Policy effects (Core-001, Core-006): blocking known-bad, approved advisory finding, true
  not_applicable, failing native project test, missing required run, known
  unowned exception, read-only PR vs native write-scope boundaries.
  > **Status: BLOCKED** — owner: L2 (Core) — next action: add witnesses for true not_applicable, a failing native project test, a missing required run, a known unowned exception and the native write-scope boundary — evidence: Observed: blocking known-bad (run 44879445868), pre-existing finding advisory (CENTRAL-DIFF, `CURSOR_CANARY_RESULT.md:25`), read-only PR permissions (`contents: read`, REST).

- Tool value: each proposed setting activates on the entitled project and
  changes actual coverage/precision/cost in a measurable manner, or is
  explicitly rejected as duplicative/ineffective.
  > **Status: NOT_PROVEN** — evidence: No setting has been shown to change coverage, precision or cost on an entitled project; T26, T27, T29, T30 are separate decisions (`OPEN_ITEMS.md:30-39`) and no measurement exists.

- CI performance: PR-fast elapsed runtime and total job-minute deltas; no
  reduction in required findings or native tests.
  > **Status: BLOCKED** — owner: CTO — next action: measure the per-PR runner-seconds delta on the next Cursor-Governance PR head (operator applied click-path 2, GitHub Code Quality off, and click-path 3, Semgrep managed diff scans off, 2026-11-21) — evidence: Baseline ~1001 runner-seconds per CG push on #1107; projected saving ~520 s; measured delta NOT MEASURED (`CLOSEOUT_RECEIPT.md:70-81`).

- Default-branch and release: clean PR, push, nightly and release/profile
  evidence; no green-on-skip; integrity of rulepack and tool locks.
  > **Status: BLOCKED** — owner: L2 (Core) — next action: dispatch the nightly sink so the now-granted App mints its token and the Cursor-Governance leg uploads SARIF, writes the rolling issue and runs Sonar (operator applied click-path 7, 2026-11-21) — evidence: Clean PR evidence: run 44876362790. Nightly: the sink ran the scans and failed at the App-token mint (runs 44891263316, 44896873853, REST conclusion failure; `CLOSEOUT_RECEIPT.md:15`). Toolchain-lock integrity: audit 105 audited, 0 open (`CLOSEOUT_RECEIPT.md:47`). Release/profile and push receipts not recorded.

## P12: CodeRabbit activation and paid-utilization evidence

- Verify authenticated subscription tier, seats, GitHub App installation, native dashboard activation, and any usage-based billing settings separately for `Quantum-L9` and `cryptoxdog` where applicable. Billing and token state not visible from GitHub content remain UNKNOWN.
  > **Status: NOT_PROVEN** — evidence: Cannot be shown from GitHub content: seats, billing and `cryptoxdog` state live in the CodeRabbit account. Operator-reported only: Advanced 2-week trial, app on `.github`, CEG and EIE (`OPEN_ITEMS.md:31`, T27).

- Verify central `coderabbit` repository installation and effective configuration source using official PR configuration command, plus local `inheritance: true` where genuinely necessary. Keep domain-specific instructions owned locally.
  > **Status: NOT_PROVEN** — operator decision D7 (2026-11-21): `Quantum-L9/coderabbit` does not exist, so `inheritance: true` in CEG and EIE has no organization parent and no effective-configuration receipt can be produced; each repository configuration stands alone — evidence: CEG #516 (`e1ccd1b2`) and EIE #368 (`4324e0df`, merged 2026-11-20T18:42Z, REST) add `inheritance: true`. No effective-configuration receipt from the official PR configuration command.

- Verify an actual substantive or explicit no-action review on a Cursor-Governance PR, and a separate specialized-consumer review. A CodeRabbit skip/status comment never counts as executed review. Preserve CodeQL and normal CI.
  > **Status: NOT_PROVEN** — declined by operator decision D8 (2026-11-21): CodeRabbit is not installed on Cursor-Governance; Codex reviews every Cursor-Governance PR (findings acted on in #1120 and #1124) — evidence: Not installed on Cursor-Governance (`OPEN_ITEMS.md:31`), so no CG review exists; no specialized-consumer review receipt was found.

- Reconcile Odoo #556 sub-10-star skip with real paid entitlement. Provide manual trigger only as fallback; do not claim automatic review from a manually invoked result.
  > **Status: NOT_PROVEN** — out of scope: operator, 2026-11-20 21:50Z — the campaign cuts Cursor-Governance over to organization CI, debugged and proven; rolling out to other repositories is a separate campaign (`CLOSEOUT_RECEIPT.md:5-6`) — evidence: Odoo #556 is `cryptoxdog/IB-Odoo_19`.

- Record accepted unique findings, coverage and actual spend or BLOCKED_EXTERNAL_ACCOUNT. No purchase or overage switch is implied.
  > **Status: BLOCKED** — owner: CTO — next action: score the CodeRabbit trial per pull request against Codex and record unique findings and spend, or `BLOCKED_EXTERNAL_ACCOUNT` — evidence: No accepted unique findings, coverage or spend recorded (`OPEN_ITEMS.md:31`).

## P13: CodeQL and SonarQube Cloud native-proof closure

**Precondition G0:** `OPERATOR_VERIFY_FIRST.md` read-only walkthrough is completed first. Evidence includes no mutations/scans, all three UI scope observations or explicit Unknowns, one-screen-at-a-time operator interaction, and CTO gap matrix. G0 is not proof that any subscription tier is active nor permission to configure. Configuration changes must have distinct operator approval.
> **Status: BLOCKED** — owner: CTO — next action: write the G0 close-out table and CTO gap matrix from the screens already answered, marking Screen 3 Unknown — evidence: G0 ran in part (operator-reported rows in `OPEN_ITEMS.md`); Screen 3 is held (`OPEN_ITEMS.md:121`, H2); no G0 close-out table was found.

- `CODEQL_SONAR_LEVERAGE.md` is the exact native-provider acceptance contract.
  Keep existing CodeQL architecture intact. Prove PR-default and scheduled
  nightly outcomes separately, multi-language selection, fail-closed unknown
  language detection and non-duplicate default setup. An overlay cache miss
  is an optimization gap, not a false security PASS.
  > **Status: BLOCKED** — owner: CTO — next action: confirm on the next Cursor-Governance `main` push that only `codeql.yml` runs CodeQL (operator disabled GitHub Code Quality, click-path 2, 2026-11-21) — evidence: PR default and nightly proven separately: `codeql.yml` PR run 44883333312 (#1119 head `cebc1590`, success) and `codeql-nightly.yml` schedule run 44899338541 (`c6b7d713`, success), REST. Fail-closed language lookup: CG #1081 (`fe8288c5`). Remaining duplicate: GitHub Code Quality (`dynamic/github-code-quality/codeql`) runs CodeQL on every PR beside `codeql.yml`, which already runs "CodeQL (security + code quality)" (T30; `CI_CONFIG_FINDINGS.md:31`; `CLOSEOUT_RECEIPT.md:86`). Separately unproven after that action: multi-language selection, since both runs analyze `python` only (owner of the CodeQL reusable: Cursor-Governance).

- Record matched Sonar project, actual analyzed production file set,
  source/test exclusions, imported current-revision coverage, new-code
  quality-gate result and reviewed hotspots. Credential check alone is not a scan.
  > **Status: BLOCKED** — owner: L2 (Core) — next action: dispatch the nightly sink so the now-granted App mints its token and the Cursor-Governance leg uploads SARIF, writes the rolling issue and runs Sonar (operator applied click-path 7, 2026-11-21) — evidence: Cursor-Governance Sonar is `NOT_EXECUTED`: zero `workflow_dispatch` runs of `sonarcloud.yml`; last run 44772875111 on 2026-11-20 16:23Z (REST; `OPEN_ITEMS.md:28`, T15; `CLOSEOUT_RECEIPT.md:60`). No matched file set, coverage import, gate result or hotspot review for CG.

- Reconcile open Cursor #1062: `workflow_dispatch` mode=plan is not analysis;
  only a trusted Core-driven mode=apply on exact main SHA with a real Sonar
  result can replace the old native trigger. Stop native scanner retirement
  until that proof exists.
  > **Status: PASS** — accepted exception: operator decision D3 (2026-11-21) accepts CG #1062 (`a95562c9`) making Sonar dispatch-only, on condition that Sonar is restored through click-path 7 (applied by the operator; proof tracked in the Sonar rows below) as a recorded exception; the violated clause stays on record — evidence: violated: "Stop native scanner retirement until that proof exists". #1062 merged 2026-11-20T16:23:56Z (REST) and made Sonar dispatch-only; no Core `mode=apply` run with a Sonar result exists since (REST: 0 dispatch runs). #1062 merged before this binding was written (`09_EXECUTION_BINDING.md` B02). Recovery without revert: click-path 7, then an apply dispatch with an `nd1-` key and a Sonar result on an exact `main` SHA (`HARVEST_LEDGER.md:162`).

- Reconcile Odoo #552 as a candidate scope correction. No Sonar runtime
  observation was recovered for Odoo at the inspected head, and the separate
  `cryptoxdog` owner requires separate authorization.
  > **Status: NOT_PROVEN** — out of scope: operator, 2026-11-20 21:50Z — the campaign cuts Cursor-Governance over to organization CI, debugged and proven; rolling out to other repositories is a separate campaign (`CLOSEOUT_RECEIPT.md:5-6`) — evidence: Odoo #552 is `cryptoxdog/IB-Odoo_19`.

- No duplicate deep test execution merely to produce identical coverage;
  prove test artifact identity and native coverage import before reusing it.
  Live Cursor 8175-test scan and EIE 3927-test scan are baseline expense signals.
  > **Status: BLOCKED** — owner: L2 (Core) — next action: dispatch the nightly sink so the now-granted App mints its token and the Cursor-Governance leg uploads SARIF, writes the rolling issue and runs Sonar (operator applied click-path 7, 2026-11-21) — evidence: CG #1062 refuses a PR full suite; CG #1100 (`756ba14a`) and Core #301 route Sonar through Core's step reusing consumer coverage. No CG Sonar run since 2026-11-20 16:23Z.

- Confirm actual GitHub Code Security eligibility and Sonar subscription LOC,
  available AI CodeFix and optional Advanced Security add-on; no automatic
  AI-credit usage, purchase, gate escalation or admin toggle.
  > **Status: NOT_PROVEN** — evidence: Cannot be shown from GitHub content: Code Security licence count and bill (`OPEN_ITEMS.md:40`, T31), Sonar LOC (settled only for public repositories, T25) and AI CodeFix / AI-credit state (T29) live in billing views.

- Each native status has run URL, analyzed SHA, project or suite, exit result,
  findings/scope and evidence; unresolved credentials/account rights are
  `BLOCKED_EXTERNAL_ACCOUNT` rather than completed optimization.
  > **Status: BLOCKED** — owner: CTO — next action: compile the native-status table (run URL, analyzed SHA, project or suite, result, scope) for CodeQL now and for Sonar after its first apply run — evidence: CodeQL rows are available (runs 44883333312, 44899338541); CG Sonar has no run.



## P10: targeted cross-tool configuration and rule harvest

- Perform a lightweight path/config index, then deep-inspect only real custom
  candidates. Known donors: Cursor (4 rules), EIE (8), CEG (8 overlapping),
  Odoo Staging (36, with #553 pending at baseline).
  > **Status: PASS** — evidence: Four-donor census at pinned heads (CG `605bb681`, EIE `8f46df4d`, CEG `e66fa5ef`, IB-Odoo_19 `25fd3282`) with per-row inspection (`HARVEST_LEDGER.md:7-24`); Semgrep rules ledgered separately in SDK `docs/harvest/semgrep-donor-ledger.yaml`, 59 rows (SDK #124, merged 2026-11-20 19:31Z, `CLOSEOUT_RECEIPT.md:163`).

- Every considered rule/config delta receives `already_satisfied`, `promote_global`,
  `promote_language`, `promote_framework`, `retain_domain`,
  `retire_duplicate` or `defer_unknown`, with exact donor/upstream revision,
  source/generator owner, target path/native key and scope. Behavioral changes
  need good/bad and non-target witnesses; service-owned settings need effective
  config/native receipts appropriate to the change, not fabricated fixtures.
  > **Status: NOT_PROVEN** — evidence: Every index row has a disposition; full fields exist only for C1-C5 (`HARVEST_LEDGER.md:104-175`). C6-C15, S1-S4 and G1-G4 keep Unknown fields as rollout backlog (`HARVEST_LEDGER.md:35-46`, 177-182); some of them are Cursor-Governance donors (C12, C13, G3) and are therefore not out of scope.

- Cover each observed configured tool using `HARVEST.md` owner routing. Prove
  SDK rule, Core profile, native CodeQL, CodeRabbit source/rendered inheritance,
  Dependabot generation, Sonar/native settings and retained product semantics
  reach their proper owners wherever those deltas exist. No invented candidate
  is required for a tool without a real delta.
  > **Status: NOT_PROVEN** — evidence: C1-C5 reach Core; CodeRabbit inheritance merged (CEG #516, EIE #368). Not delivered, with different owners: Dependabot generation for Core/SDK (`CI_CONFIG_FINDINGS.md` row 16), Sonar/native settings (T19, row 21).

- Record owner PR/change receipt, admission, actual promotion, effective
  inherited config/digest and execution proof separately. A published candidate
  or Semgrep-only inventory cannot close the cross-tool delivery obligation.
  > **Status: NOT_PROVEN** — evidence: Recorded separately for C1-C5 (merged / effective / observed). Not effective, with two owners: C4 waits on click-path 7 (`HARVEST_LEDGER.md:162`); C5 step two is not on Core `main` (`HARVEST_LEDGER.md:174`). C1 is effective: Core #312 merged 2026-11-21T08:16:54Z as `63ff7da5` (REST; correction appended to `HARVEST_LEDGER.md` in #1124).

- Before retirement, bind exact successor, relevant canary/parity and preceding
  known-good owner configuration, with scoped rollback and validation. Working
  checks remain when delivery, native access or proof is blocked. Never promote
  secret values, customer data or product/account identity as shared defaults.
  > **Status: BLOCKED** — owner: CG-CUTOVER — next action: bind each planned Cursor-Governance retirement in `REQUIRED_CHECK_CUTOVER.md` to its successor, canary parity receipt and scoped rollback — evidence: No CG check retired; working checks remain (REST rules; `REQUIRED_CHECK_CUTOVER.md:4`). CEG #522's retirement is handled under the first-consumer blocker.

- Prove non-target repositories do **not** receive Odoo/PlasticOS/memory
  specialty rules. The SDK baseline remains mandatory everywhere applicable.
  > **Status: PASS** — evidence: Promotion-canary run 44903350118 (Core #339, SDK `4a887396`), head-leg instance plans read from artifacts (REST): Cursor-Governance `c6b7d713` plans `semgrep:consumer:quantum-l9.cursor-governance`, `semgrep:language:python`, `semgrep:language:typescript`; CEG `e1eb4f2d`, EIE `5460ffd6`, l9-ci-sdk `d4398a4c` and l9-ci-core `2ee1720b` each plan only `semgrep:language:python` (SDK baseline, "required by central governance") and no consumer instance. The Cursor memory rules load only through the CG consumer instance (`CURSOR_CANARY_RESULT.md:29`), and no SDK Odoo/PlasticOS pack exists to deliver (`HARVEST_LEDGER.md` S1a). Second witness: EIE run 44878546690 plan, `language:python` only.

- Do not equate "60 repos" with "60 deep harvest targets". Fleet required-check
  coverage is separately verified in the rollout stage.
  > **Status: PASS** — evidence: Harvest targets were the four donors only (`HARVEST_LEDGER.md:7-24`); fleet required-check coverage is left to the rollout stage (`HARVEST_LEDGER.md:200-205`).

## P11: mandatory Cursor-Governance live canary

- Actual `Quantum-L9/Cursor-Governance` repo and exact evaluated head,
  effective org required-workflow ruleset, promoted Core+SDK runtime and real
  `Analyze (central Core)` job, not SDK-only fixtures or a static workflow diff.
  > **Status: PASS** — evidence: Run 44876362790 (job 136761824478), event `pull_request`, head `6ef0ae3566fe`, workflow `org-ci.yml`, conclusion success (REST) on CG #1112; ruleset 21895545 active (REST); Core actions `284a5eb6` (#323), SDK `4a887396` (`CURSOR_CANARY_RESULT.md:9-25`). #1112 later merged at head `7ab2381c` (merge `35f8d88d`).

- Independently verify every required language/provider and custom-rule scope,
  inherited config/pins, adverse provider failure, tamper resistance,
  known-good/bad witnesses, native CodeQL and product test preservation.
  > **Status: NOT_PROVEN** — evidence: Met: languages (`CURSOR_CANARY_RESULT.md:27`), central config (`:28`), consumer-rule scope (`:29`), known-bad/good (`:31-32`), nosemgrep/.semgrepignore tamper refused (`:33`), incomplete provider fails (`:34`), Biome (`:35`), CodeQL and Test Suite preserved (`:30`, `:36`). Missing, across owners: version/severity override attempts never exercised (`:129-133`); a parse error counted as covered (`:44`, SDK); no `--baseline-commit` for the consumer execution (`:45`, Core); no independent verifier recorded.

- Compare live baseline and successor findings/runtimes and keep existing
  local enforcement until parity is proven. Report `CURSOR_CANARY_PASS` or
  `CURSOR_CANARY_BLOCKED` with concrete evidence, owner and failed clause.
  > **Status: PASS** — evidence: Findings: 29 blocking on `main` (2026-11-20) to 0 new / 79 pre-existing advisory (`CURSOR_CANARY_RESULT.md:37`). Runtime: 3 min 12 s baseline on `4accb109` (`:135`); successor run 44876362790 06:36:45Z-06:43:57Z (REST). Local enforcement kept (five local checks still required, REST). Verdict `CURSOR_CANARY_PASS` (`:40`) after the earlier `CURSOR_CANARY_BLOCKED` with owners and failed clauses (`:48-61`).

- `CURSOR_CANARY_BLOCKED` halts **secondary rollout, fleet rollout, and
  consumer cleanup**, not all independent in-scope engineering or PR publication.
  No local bypass/waiver is a substitute for an upstream correction.
  > **Status: PASS** — accepted exception: operator decision D1 (2026-11-21) accepts CEG #522 (`fc4711a2`) consumer cleanup while `CURSOR_CANARY_BLOCKED` as a recorded exception; the violated clause stays on record — evidence: violated: "`CURSOR_CANARY_BLOCKED` halts ... consumer cleanup". Core #294 made `Analyze (central Core)` red on every CG PR from 2026-11-20 21:52Z (B4; `CI_CONFIG_FINDINGS.md:27`); CEG #522 removed redundant lint/contract jobs at 22:44:57Z (REST). Same event as the first-consumer blocker. No local bypass or waiver was added for B1-B5 (`CURSOR_CANARY_RESULT.md:48-51`).

Produce a single readable closeout with: accepted decisions, PR links and
head SHAs, exact rulesets/revisions, canary and fleet coverage ledger,
rulepack tests, true/false fixture proof, tool ROI matrix, spend unknowns,
rollout status, and every finding marked fixed, already satisfied, invalid,
or blocked with owner/next action. PR published is NOT fleet rollout complete.
No claims that tests, live rulesets, entitlements or canaries passed without
real outputs. If any required objective remains blocked, state the frontier
plainly and keep the campaign open.
> **Status: BLOCKED** — owner: CTO — next action: add to `CLOSEOUT_RECEIPT.md` the per-PR head SHAs, rulepack test listing, true/false fixture table, tool ROI matrix, spend-unknowns table and per-finding dispositions — evidence: `CLOSEOUT_RECEIPT.md` holds decisions, PR list, rulesets, canary verdicts and drift and states the frontier (status OPEN, `:3`).

## P9: ADR placement, decision closure and precedence

- Every new ADR is proposed **at its owner**, not simply referenced in the campaign. Core 0001 and 0002 must be published as owner documents with their index; SDK 0020 must be published with an index entry and the applicable ADR 0005/0016/0017 amendment notes. No existing accepted ADR may be rewritten or silently superseded.
  > **Status: PASS** — evidence: Core 0001 and 0002 published with a new index, status Proposed (Core #283 merged 2026-11-20T19:03:27Z as `1942a1be`; REST read of `docs/adr/README.md`). SDK 0020 published with index row "Proposed" (SDK #122 `0089b76c`) and its amendment note "This amends in scope, but does not rewrite, ADR 0005/0016/0017" (`0020-...md:34`, REST). Neither PR modifies an existing ADR file (REST file lists).

- For each ADR record owner, exact target path, preflight base SHA, authorizing decision/status, matching scoped invariant IDs, prohibited alternatives, code/contract realization PR and tested acceptance evidence. Proposal publication alone does not make it Accepted, implemented, effective or fleet-enforced.
  > **Status: BLOCKED** — owner: CTO — next action: write the per-ADR record (owner, path, preflight base SHA, authorizing decision/status, invariant IDs, prohibited alternatives, realization PR, tested acceptance evidence) for Core 0001, 0002 and SDK 0020 — evidence: No such record found; all three ADRs remain Proposed.

- Test the top-down precedence: organization required-workflow ruleset -> Core governance/versions/permissions -> SDK provider facts/technical gates, while product-native semantics remain with the product and native SaaS trust scopes remain with their authorized owner. Evidence must flow back with source/revision identity.
  > **Status: PASS** — evidence: On one CG head: org ruleset selects Core `org-ci.yml@main` and evaluates the exact head (`CURSOR_CANARY_RESULT.md:26`); Core resolves pins/policy and provisions the SDK (`:28`); consumer-owned rules stay with CG, scoped (`:29`); CodeQL and Sonar keep their owners (`:30`); org-ci runs read-only (`contents: read`, REST). Evidence carries revision identity (`:9-18`).

- Reject simulated pass when a second language, mandatory rule, product-specific test or required native result is absent. Verify that the current CodeQL owner and native PR/nightly profiles remain intact.
  > **Status: BLOCKED** — owner: L2 (Core) — next action: add witnesses that an absent product-specific test and an absent required native result each fail the required check — evidence: Met: a second language that cannot complete fails the job (run 44826737909 failure, REST); a failing mandatory consumer rule fails the aggregate (run 44879445868 failure, REST); CodeQL PR and nightly profiles intact (runs 44883333312, 44899338541).

- Verify unambiguous live owner references, ADR index links, new target paths and schema compatibility. Core has no existing `docs/adr` ledger at the inspected revision, so its proposed first two ADR numbers are deliberately provisional; if a new live ADR has appeared, resolve the collision without modifying its accepted meaning.
  > **Status: PASS** — evidence: Core now has `docs/adr/` with a README linking 0001 and 0002, no collision (REST); SDK index entries resolve to files 0020, 0021, 0023, 0024 (REST); the invariants sit in the existing top-level contract fields with tests (`09_EXECUTION_BINDING.md` B13), and Core's full suite passed after the T34 repair, 1165 tests OK (`STAGE1_INTEGRATION.md:18-21`).

- No global constitutional ADR is required merely to repeat `L9-OWNER-001`, `L9-MONOTONIC-001`, `L9-UNKNOWN-001` or existing `.github` ADR-010. Change global law only if a genuinely new cross-domain obligation is independently established and separately authorized.
  > **Status: PASS** — evidence: No `Quantum-L9/.github` pull request appears among the 149 merged campaign PRs (`CLOSEOUT_RECEIPT.md:97-273`); no global constitutional ADR was added.


## P14: Native tool execution truth and paid value (v1.6.0)

**Mandatory:** `OTHER_TOOLS_EVIDENCE.md` T01-T14 are inherited observations and
risks with their recorded evidence limits; the remediation/acceptance contract
is `OTHER_TOOLS_EXECUTION.md`. T14 is supporting detail of T02 and shares its
owner, correction and terminal receipt, not an independent defect or PR. T07
retains the aggregate-outcome obligation dependent on T01/T02. Each finding receives a
terminal disposition: `FIXED_PROVEN`, `ALREADY_SATISFIED` with fresh proof,
`INVALID` with contradiction, or `BLOCKED` with exact owner/dependency. No
finding silently disappears when branch or vendor evidence changes. Do not
fabricate completion because the tool name is in a workflow file.
> **Status: BLOCKED** — owner: CTO — next action: write the terminal-disposition table for T01-T14 (FIXED_PROVEN, ALREADY_SATISFIED, INVALID or BLOCKED with owner) — evidence: `09_EXECUTION_BINDING.md` Findings register records status changes, not terminal dispositions; T03 was declared changed (B03) but never closed with a fresh run.

- [ ] CEG GitGuardian: native CI-mode scanning succeeds on a real authorized
  event. Witnesses cover missing CI context, unavailable scanner, a successful
  container pull followed by scanner failure, detected synthetic test secret,
  and clean scan. Preserve the actual outcome and authorized required/advisory
  mode; neither wrapper classification nor aggregate may impersonate execution.
  Prior observed https://github.com/Quantum-L9/Cognitive.Engine.Graphs/actions/runs/44655221257
  (job 136019664092) had workflow success but native scan failure.
  > **Status: BLOCKED** — owner: C-CEG — next action: run the four live negative witnesses (missing CI context, unavailable scanner, pull followed by scanner failure, detected synthetic secret) on a CEG canary PR and record each outcome — evidence: Fix merged: CEG #515 (`74f9cc38`). Live clean scan: Quality Gates run 44883136549, job 136782578101 on `main` `e1eb4f2d` logs "No secrets have been found" and "GitGuardian SCANNED_CLEAN" (REST log). The GitGuardian dashboard monitors no Quantum-L9 repository (`OPEN_ITEMS.md:54`, T41, operator).

- [ ] CEG Codecov: new accepted exact-revision upload (vendor or independently
  verifiable accepted-upload receipt); missing token/failed upload cannot be
  represented as accepted coverage. Prior same run job 136019663740 returned
  `Token required - not valid tokenless upload` with an overall success.
  > **Status: PASS** — terminal disposition: Codecov RETIRED by operator decision D4 (2026-11-21); T02 and T42 close on this disposition — evidence: No accepted upload exists; the upload path was retired instead: CEG #518 (`5e7fd0f6`) and #520 (`e66fa5ef`, deletes `dev-layer-gmp.yml`); verdict `RETIRE_CANDIDATE` (`CODECOV_REVIEW.md:21`); T42 OPEN (`OPEN_ITEMS.md:55`).

- [ ] CEG G01: required product verifier is no longer falsely attributed to
  Semgrep/Core; prove the sibling Odoo mapper integration or mark actual
  G01 not-run block. Never suppress to manufacture Core pass.
  > **Status: BLOCKED** — owner: C-CEG — next action: run `Analyze (central Core)` on a CEG head and record the G01 sibling-mapper proof result or its explicit not-run block — evidence: No fresh G01 result found (`09_EXECUTION_BINDING.md` B03 asks for one); CEG canary #517 not re-run on PIN-ADVANCE-3 (`CLOSEOUT_RECEIPT.md:17`).

- [ ] EIE Gitleaks: Dependabot PR exception explicitly documented and verified
  with native execution/skip status. An authorized premerge repair must verify
  trigger/job/actor predicates as well as secret availability; supplying a
  license alone is not closure. Post-merge is not counted as pre-merge.
  > **Status: BLOCKED** — owner: C-EIE — next action: record the Gitleaks job of the next hosted Dependabot PR on EIE after #366 — evidence: Fix merged: EIE #366 (`e538bdfa`) runs the licence-free Gitleaks 8.24.3 binary on Dependabot events and labels the action skip `SKIPPED_BY_POLICY`. Every `gitleaks.yml` run since is by `cryptoxdog` (REST, last 10 runs).

- [ ] EIE GitGuardian: key missing and API failure cannot be classified as
  `EXECUTED_VERIFIED`; retained successful native evidence remains valid.
  > **Status: BLOCKED** — owner: C-EIE — next action: record an executed run of the negative witnesses in `tests/ci/test_secret_scan_truthfulness.py` (missing, rejected and unreachable key classified `NOT_EXECUTED`) — evidence: Fix merged: EIE #366 (`e538bdfa`) adds a `/v1/health` preflight; PR body: "failing without the fix is not measured". Retained native success after the fix: run 44894557872, job 136817337544, steps "Verify GitGuardian can scan" and "GitGuardian scan" success (REST).

- [ ] CEG dependency-review: dependency-graph availability and actual review
  reported separately; a skipped PR cannot claim clean SCA result.
  > **Status: BLOCKED** — owner: C-CEG — next action: record a graph-unavailable witness showing the review reported `NOT_EXECUTED`, not clean — evidence: Fix merged: CEG #515 (`74f9cc38`). Live separate reporting: supply-chain run 44848726907, job 136674735202 (head `1991e49a`) logs "dependency graph: AVAILABLE (the compare API answered)" and "review: EXECUTED_PASSED" (REST log). The skip path is not observed.

- [x] Core Bandit/npm audit: profile/requiredness and skip reason explicit;
  no unconditional reenable without policy authority and coverage proof.
  > **Status: PASS** — evidence: Core `.github/workflows/security.yml` on `main` (REST): bandit "advisory when a Python project is detected", npm audit "not run unless the caller sets run-npm-audit: true; then required" (lines 20-22, 41-45); bandit reports completed / findings / did-not-complete as distinct notices (lines 387-415); npm audit requires `package-lock.json` when requested (lines 419-431). Made explicit by Core #285 (`c512c66b`, "report each scan's real outcome in security.yml (L2 T04)"); no unconditional re-enable.

- [ ] Codecov and Sonar coverage: one trusted immutable source/test pass per
  intended validation scope where supported; compare old/new test count,
  setup and wall time. No reduced rule/source/coverage parity.
  > **Status: NOT_PROVEN** — evidence: No old/new test count, setup or wall-time comparison exists for any repository. Coverage reuse is wired (Core #289 `c9d436a9`, EIE #371/#372, CEG #521, CG #1100) without a before/after; CG Sonar has not run since 2026-11-20 (T15). Several owners.

- [ ] Other provider inventory: CodeRabbit, Perplexity, Copilot, OpenSSF,
  Syft, license checks, Gitleaks, Dependabot, Mypy/Ruff/Biome, optional
  Trivy, paid tools. Each receives an owner, state, evidence and cost/unique
  value. Not-installed is not a PASS, unverified subscription is UNKNOWN.
  > **Status: BLOCKED** — owner: CTO — next action: compile one provider inventory (owner, state, evidence, cost/unique value) for every tool listed, marking unverified subscriptions NOT_PROVEN — evidence: Partial rows exist in `OPEN_ITEMS.md` (T26 Copilot, T27 CodeRabbit, T28 Perplexity, T41 GitGuardian, T42 Codecov) and `SEMGREP_REVIEW.md`.

- [ ] First mandatory live integrated Core/SDK consumer remains Cursor,
  then secondary native tool canaries (EIE, CEG, Odoo) as currently scoped.
  > **Status: BLOCKED** — owner: C-CEG — next action: re-run CEG canary #517 on the PIN-ADVANCE-3 pins and record Gates 2-3 — evidence: Cursor was the first live consumer canary (2026-11-20 run 44819081765; PASS 2026-11-21 run 44876362790). EIE secondary recorded (runs 44874376220, 44878546690; run 1 started 06:11:39Z, 25 min before the CG PASS evaluation run started at 06:36:45Z, REST). Odoo is outside scope.

- [ ] All auth/feature changes occurred after G0 with applicable explicit
  operator authorization. Reuse authorization already supplied for the same
  action; G0 completion grants none. No secret values disclosed and no tool
  installation required merely to complete verification.
  > **Status: NOT_PROVEN** — evidence: Cannot be shown: no G0 close-out table exists, so the order of vendor changes against G0 is unrecorded. Semgrep changes record operator authorization (`OPEN_ITEMS.md:49`, T37); the SonarCloud visibility and deletion change (T18, `OPEN_ITEMS.md:16`) records none. Credentials appear as counts only; no secret disclosure was found.


## Proof summary

| Section | PASS | BLOCKED | NOT_PROVEN | Total |
|---|---|---|---|---|
| Required evidence | 3 | 4 | 3 | 10 |
| Concrete tests | 0 | 5 | 1 | 6 |
| P12 CodeRabbit | 0 | 1 | 4 | 5 |
| P13 CodeQL and Sonar | 1 | 5 | 2 | 8 |
| P10 Harvest | 3 | 1 | 3 | 7 |
| P11 Cursor canary | 3 | 1 | 1 | 5 |
| P9 ADRs | 4 | 2 | 0 | 6 |
| P14 Native tool truth | 2 | 8 | 2 | 12 |
| **Total** | **16** | **27** | **16** | **59** |

BLOCKED by owner:

| Owner | Rows |
|---|---|
| CTO | 11 |
| L2 (Core) | 5 |
| C-CEG | 4 |
| CG-CUTOVER | 2 |
| L1 (SDK) | 2 |
| C-EIE | 2 |
| N1e (Core canary/pins) | 1 |
| **Total** | **27** |

NOT_PROVEN includes 3 out-of-scope rows. Checklist ticks: 1 of 11 (`Core Bandit/npm audit`). X9 stays open until every BLOCKED and NOT_PROVEN row is resolved or accepted.

Evidence corrections made in this PR (REST read versus file text; each stale row is corrected inline):

- `OPEN_ITEMS.md` C1/C2 row: EIE #368 is merged (2026-11-20T18:42:01Z, `4324e0df`), not open.
- `HARVEST_LEDGER.md` C1 and C2 delivery rows: Core #312 (`63ff7da5`) and CEG #524 (`e1eb4f2d`) are merged, not open.
- `OPEN_ITEMS.md` T32: CodeQL on Cursor-Governance analyzes `python` only; it does not cover JavaScript.
- `CLOSEOUT_RECEIPT.md` click-path 2 and the X10 audit row: the duplicate "Analyze (python)" is GitHub Code Quality; CodeQL default setup is `not-configured`.
