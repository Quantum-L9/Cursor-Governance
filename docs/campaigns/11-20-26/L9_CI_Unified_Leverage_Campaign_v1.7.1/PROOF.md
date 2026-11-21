> **Filled from real runs, 2026-11-21 13:30Z (X9).** Unchanged `PROOF.md` text with one status per requirement. Evidence paths without a directory are in `evidence/`; "REST" means a read-only `gh api repos/Quantum-L9/...` GET made for this draft. `[x]` marks PASS only.

# Acceptance, validation and rollout receipts

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

## Required evidence, not green theater

**First-consumer blocker:** `CURSOR_CANARY_PASS` from `CURSOR_CANARY.md` is a
mandatory prerequisite to secondary rollout and removal of redundant
consumer checks. `HARVEST.md` candidate dispositions must precede shared
configuration/rule promotion at the correct upstream owner. CI Core/SDK unit tests, a published PR,
and a simulated consumer are insufficient.
> **Status: FAIL** — Clause 1 met in part: `CURSOR_CANARY_PASS` is recorded (`CURSOR_CANARY_RESULT.md:40`; CG #1112 merged 2026-11-21T07:37:12Z as `35f8d88d`, REST-verified). Clause violated: CEG #522 "ci: one owner per lint and contract check; central Core covers PRs" removed redundant consumer checks (ci.yml lint, ci-quality.yml lint-format, contracts.yml lint, compliance.yml ruff/mypy and contract scan, refactoring-validation.yml) and merged 2026-11-20T22:44:57Z (`fc4711a2`, REST-verified), about 9 h before `CURSOR_CANARY_PASS` existed, while the 2026-11-20 verdict was `CURSOR_CANARY_BLOCKED` (`CURSOR_CANARY_RESULT.md:48-61`). Mitigation (from the #522 body): one local owner per check was kept (`l9-lint-test.yml`, `contracts.yml`). Second clause (harvest dispositions precede promotion): cannot be established from merged artifacts; the ledger index merged in CG #1091 (2026-11-21 05:09Z) after Core #295 (`8667d537`, 2026-11-20 22:09Z) and #300 (`7e11e2b0`, 2026-11-21 01:35Z) promoted C2/C3. Unblock: operator decides whether #522 is an accepted exception or is reverted pending CEG parity.

P0: every observed required check is actually governed. Record correct
organization ruleset target, correct working/source revision, enforced mode,
executed providers and permissions, plus any exceptions. `cryptoxdog` must
have separate, verified enforcement.
> **Status: PASS** — Cursor-Governance (in scope): org ruleset 21895545 "L9 canonical CI required" `enforcement: active`, target `~DEFAULT_BRANCH`, required workflow `.github/workflows/org-ci.yml@refs/heads/main` in repo id 1285564308 (= `Quantum-L9/l9-ci-core`), required check `Analyze (central Core)`; repo ruleset 20855699 `active`, strict, requires Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene (REST `rules/branches/main` and `rulesets/{id}`, read 2026-11-21). Working revision: Core `main` `acb73463` org-ci pins actions `2ee1720b`, SDK `4a887396`, Semgrep 1.186.0; workflow and `analyze` job `permissions: contents: read` (REST read of `org-ci.yml`). Executed providers: Semgrep python/typescript/consumer instances, Biome, repository verification, security scan (`CURSOR_CANARY_RESULT.md:24-38`; `CLOSEOUT_RECEIPT.md:13`). Exceptions: `OrganizationAdmin` bypass `always` on 21895545 and `EnterpriseOwner` bypass on 20855699; `strict_required_status_checks_policy: false` on 21895545 (`CLOSEOUT_RECEIPT.md:58`). `cryptoxdog`: IB-Odoo_19 is not bound by 21895545 and carries its own ruleset 17291607 with four required checks (`STAGE1_INTEGRATION.md:55`, observed 2026-11-20; not re-read here, repo outside this session's allowed set).

P1: detection is complete and accurate. Known-good mixed Python+TS repository
selects both. Framework/supply-chain capabilities select correctly. Deliberate
missing/invalid metadata and scanner failures yield incomplete/fail rather
than PASS. Document detectors' blind spots and known unsupported languages.
> **Status: OPEN** — Mixed Python+TS selects both (`STAGE1_INTEGRATION.md:33`; live CG plan python + typescript + consumer, `CURSOR_CANARY_RESULT.md:27`); incomplete required instance fails (`CURSOR_CANARY_RESULT.md:34`); Django rules only where Django is detected (SDK #141); blind spot documented: JavaScript/shell `unsupported` in CG (`OPEN_ITEMS.md:42`, T32). Missing: framework capability selection for Odoo (no SDK Odoo pack exists, `HARVEST_LEDGER.md` S1a-S1f), supply-chain capability selection on a consumer (C5 step two not on Core `main`), and a deliberate missing/invalid-metadata witness. Owner: SDK (L1) and Core (L2).

P2: real tool runs. Capture native executable version, SHA/digest where
available, exact central config/rulepack digest, file scope, normalized
findings/coverage, status, run link and exact repository SHA. A provider that
can only issue an advisory artifact cannot be presented as a blocking gate.
Separate the inspected source snapshot, PR head, actual analyzed/merge checkout,
and resolved reusable workflow/action revision. Missing coordinates remain
Unknown; a default-branch SHA cannot substitute for the code a hosted run used.
> **Status: OPEN** — CG canary records executable version (Semgrep 1.171.0 from Core lock), SDK revision `4a887396`, file scope (884 files), normalized findings, status, run link and PR head `6ef0ae35` merged with `main` `d7e929f2`, actions `284a5eb6` (`CURSOR_CANARY_RESULT.md:9-25`). Missing: the exact central rulepack/config content digest for that run, and the analyzed merge-checkout SHA (the PR merge ref) as distinct from the PR head. Also, the live required job has since moved to Semgrep 1.186.0 (Core #339 `acb73463`); its CG coordinates exist only as the promotion-canary leg (run 44903350118, job 136844062053 success, REST-verified), not as a recorded receipt. Owner: CTO / Core.

P3: parity. For every retired local check, test a known-bad case that fails
and a known-good case that passes in the central successor. Reproduce unique
consumer rule findings and preserve project tests. Compare historical live
runs before and after. No local workflow/config removal before parity.
> **Status: OPEN** — No Cursor-Governance local check has been retired (rules on `main` still require all five local checks, REST-verified; `REQUIRED_CHECK_CUTOVER.md:4`). Biome has a known-good (#1088) and known-bad (`8043a32e`, run 44877881561 failure, REST-verified) receipt. The parity receipts required before any retirement (ruff/format/stale-lock negative witnesses failing `Analyze (central Core)`; Test Suite count parity on `merge_group` and push) do not exist yet (`REQUIRED_CHECK_CUTOVER.md:51-52`). Owner: CG-CUTOVER.

P4: coverage across four canaries, then every eligible org repo. Publish
repo-by-repo coverage and policy ledger, not merely a percentage without
unscanned repository names. Include external owner separately. A new supported
repo proves Core/SDK runtime inheritance without routine copies/repins. Record
retained native callers and their required SHA-pin updates, managed native files,
project identities and product settings separately; do not claim these vanished.
> **Status: N/A (out of scope)** — Fleet coverage and the remaining canaries are rollout. Operator, 2026-11-20 21:50Z: the campaign cuts Cursor-Governance over to organization CI, debugged and proven; rolling out to other repositories is a separate campaign (`CLOSEOUT_RECEIPT.md:5-6`). Partial in-scope evidence kept for that campaign: per-repository enforcement boundary for six Quantum-L9 repositories plus IB-Odoo_19 (`STAGE1_INTEGRATION.md:45-57`).

P5: paid-tool leverage. Each tool must have actual tier/entitlement and native
project configuration proof, demonstrable unique value or explicitly
substantiated retirement decision, before/after scan cost and coverage where
measurable, and no unapproved vendor billing or permission changes. If native
access is unavailable, label optimization blocked by access and do not certify
complete spend optimization.
> **Status: UNKNOWN** — Tier, seat, entitlement and spend are not visible from GitHub content: GitHub Secret Protection / Code Security licence count UNKNOWN (`OPEN_ITEMS.md:40`, T31); Semgrep Free is operator-reported (`SEMGREP_REVIEW.md`); CodeRabbit is a trial (`OPEN_ITEMS.md:31`, T27); Codecov plan not read (`CODECOV_REVIEW.md:5`); Copilot quota failures (T26). Closes when the operator reads each native billing page once (G0 extension).

P6: no unauthorized changes. PRs published by target-verified `make pr`; no
manual raw pushes, branch protection bypass, merge, deployment or payments.
All open PR overlap reconciled by exact head and base SHA before writing.
> **Status: FAIL** — Canary witnesses for `CURSOR_CANARY_PASS` were "pushed to the canary branch directly on CTO instruction" rather than through `make pr` (`CURSOR_CANARY_RESULT.md:46`; PR #1096, DO NOT MERGE). Merges were operator-authorized (`OPEN_ITEMS.md` recorded decisions, 2026-11-20 18:55Z and 19:10Z), not unauthorized. Open-PR overlap reconciliation by exact head/base SHA: not evidenced. Unblock: operator records whether the direct canary-branch push is an accepted exception; root cause `run_pr_security.sh` cannot judge consumer-rule expect-fail fixtures (same line).

P7: rollback. Preserve SHA of Core, SDK, org rulesets and native-provider
config before promotion. Central canary failure halts next rollout wave;
rollback is narrowly scoped to faulty owning release, never consumer-local
policy bypass. Verify rollback itself against the affected required checks.
> **Status: OPEN** — Halt-on-canary-failure demonstrated: Core #319 canary run 44864948490 FAIL (REST: conclusion failure) and #319 not merged (REST `merged_at: null`) (`CLOSEOUT_RECEIPT.md:34`). Pre-promotion SHAs preserved as canary base pins. Missing: no rollback has been executed and verified against the affected required checks. Caveat: the #324 canary verdict passed (run 44875640013, verdict job 136761385630 success) while both Cursor-Governance legs failed (jobs 136759651393, 136759651380, REST-verified), the masking defect later fixed as row 27 (Core #328 `03028b6a`). Owner: Core.

P8: invariant closure. For EACH ID in `INVARIANTS.yaml`, show (a) exact
source-owner change/accepted existing law, (b) type/schema compatibility,
(c) known-bad witness that fails before/when tested, (d) known-good witness
that passes, (e) real enforcement observation, (f) revision-bound integrated
Core+SDK run, and (g) disposition (implemented, already satisfied, invalid,
blocked). Merely including a statement in YAML is not an enforcement receipt.
Global constitutional refs remain canonical at `.github`; campaign candidates
must not self-admit. No local check retirement if any relevant invariant's
negative witness or parity evidence remains missing.
> **Status: OPEN** — Invariants are in the owner contracts (Core `.l9/governance-contract.yaml` `ci_runtime_invariants` L9-CI-CORE-001..006; SDK `.l9/integration-contract.yaml` `ci_provider_invariants` L9-CI-SDK-001..005, REST-read) with witness test files (Core #283 `1942a1be` adds `tests/governance/test_ci_runtime_invariants.py`; SDK #122 `0089b76c` adds `tests/invariants/test_ci_provider_invariants.py`). Missing: the per-ID (a)-(g) table, in particular (e) real enforcement observation, (f) revision-bound integrated run and (g) disposition for each of the 11 IDs. Owner: CTO, from the canary and promotion-canary receipts.

## Concrete tests

- Capability selection fixtures (SDK-001, Core-003): Python-only, TypeScript-only, mixed,
  Odoo Python+XML, no supported code, malformed manifests, unsupported env.
  > **Status: OPEN** — Observed: mixed, Python-only and no-supported-code fixtures (`STAGE1_INTEGRATION.md:31-36`). Missing: TypeScript-only, Odoo Python+XML, malformed manifests, unsupported environment.

- Provider failures (SDK-002, Core-003): missing executable, hash mismatch, registry/network
  failure, invalid custom rulepack, report parse failure, scanner timeout,
  missing token for externally required native scanner.
  > **Status: OPEN** — Observed: scanner timeout counted incomplete (SDK #131 `9af1a202`, #137; B5 at `CURSOR_CANARY_RESULT.md:61`); required instance that cannot complete fails (runs 44825395263, 44826737909). Missing: missing executable, hash mismatch, registry/network failure, invalid custom rulepack, report-parse failure, missing token. Note an open defect: a Semgrep parse error is still counted as covered (`CURSOR_CANARY_RESULT.md:44`).

- Policy effects (Core-001, Core-006): blocking known-bad, approved advisory finding, true
  not_applicable, failing native project test, missing required run, known
  unowned exception, read-only PR vs native write-scope boundaries.
  > **Status: OPEN** — Observed: blocking known-bad (run 44879445868), pre-existing finding reported advisory (CENTRAL-DIFF, `CURSOR_CANARY_RESULT.md:25`), read-only PR permissions (`contents: read` in org-ci). Missing: true not_applicable, failing native project test, missing required run, known unowned exception, native write-scope boundary witness.

- Tool value: each proposed setting activates on the entitled project and
  changes actual coverage/precision/cost in a measurable manner, or is
  explicitly rejected as duplicative/ineffective.
  > **Status: OPEN** — No setting has been shown to change coverage, precision or cost on an entitled project; T29, T30, T26, T27 remain decisions (`OPEN_ITEMS.md:30-39`).

- CI performance: PR-fast elapsed runtime and total job-minute deltas; no
  reduction in required findings or native tests.
  > **Status: OPEN** — Baseline measured (~1001 runner-seconds per CG push on #1107); projected saving ~520 s; measured delta NOT MEASURED (`CLOSEOUT_RECEIPT.md:64-75`). Unblocked by merging the path-scoping/duplicate-trigger fixes and click-paths 2-3 (X10).

- Default-branch and release: clean PR, push, nightly and release/profile
  evidence; no green-on-skip; integrity of rulepack and tool locks.
  > **Status: OPEN** — Clean PR evidence exists (run 44876362790). Nightly evidence: the nightly sink ran the scans but failed at the App-token mint (runs 44891263316, 44896873853, REST: conclusion failure) (`CLOSEOUT_RECEIPT.md:15`). Release/profile and push receipts not recorded. Tool-lock integrity: toolchain audit 105 audited, 0 open (`CLOSEOUT_RECEIPT.md:47`). Unblock: click-path 7 (nightly App permissions), then two dispatches.

## P12: CodeRabbit activation and paid-utilization evidence

- Verify authenticated subscription tier, seats, GitHub App installation, native dashboard activation, and any usage-based billing settings separately for `Quantum-L9` and `cryptoxdog` where applicable. Billing and token state not visible from GitHub content remain UNKNOWN.
  > **Status: UNKNOWN** — Operator-reported only: CodeRabbit Advanced 2-week trial, app installed on `.github`, CEG and EIE (`OPEN_ITEMS.md:31`, T27). Seats, billing and `cryptoxdog` state are not visible from GitHub content.

- Verify central `coderabbit` repository installation and effective configuration source using official PR configuration command, plus local `inheritance: true` where genuinely necessary. Keep domain-specific instructions owned locally.
  > **Status: OPEN** — CEG #516 (`e1ccd1b2`) and EIE #368 (`4324e0df`, merged 2026-11-20T18:42Z per REST; `OPEN_ITEMS.md:43` still says open) add `inheritance: true`. Missing: existence of a central `coderabbit` repository (B19, `09_EXECUTION_BINDING.md`) and an effective-configuration receipt from the official PR configuration command.

- Verify an actual substantive or explicit no-action review on a Cursor-Governance PR, and a separate specialized-consumer review. A CodeRabbit skip/status comment never counts as executed review. Preserve CodeQL and normal CI.
  > **Status: OPEN** — CodeRabbit is not installed on Cursor-Governance (`OPEN_ITEMS.md:31`), so no CG review exists; no specialized-consumer review receipt was found in the evidence. Unblock: operator installs the app on Cursor-Governance; then one substantive review on a CG PR.

- Reconcile Odoo #556 sub-10-star skip with real paid entitlement. Provide manual trigger only as fallback; do not claim automatic review from a manually invoked result.
  > **Status: N/A (out of scope)** — Odoo #556 is `cryptoxdog/IB-Odoo_19`; rollout to other repositories is a separate campaign (operator, 2026-11-20 21:50Z).

- Record accepted unique findings, coverage and actual spend or BLOCKED_EXTERNAL_ACCOUNT. No purchase or overage switch is implied.
  > **Status: OPEN** — Trial scoring against Codex not recorded; no accepted unique findings, coverage or spend recorded (`OPEN_ITEMS.md:31`). Operator decides near trial day 12.

## P13: CodeQL and SonarQube Cloud native-proof closure

**Precondition G0:** `OPERATOR_VERIFY_FIRST.md` read-only walkthrough is completed first. Evidence includes no mutations/scans, all three UI scope observations or explicit Unknowns, one-screen-at-a-time operator interaction, and CTO gap matrix. G0 is not proof that any subscription tier is active nor permission to configure. Configuration changes must have distinct operator approval.
> **Status: OPEN** — G0 walkthrough happened in part (operator-reported rows in `OPEN_ITEMS.md`), but Screen 3 (CG Sonar project) is held (`OPEN_ITEMS.md:121`, H2) and no G0 close-out table or CTO gap matrix was found in the campaign files.

- `CODEQL_SONAR_LEVERAGE.md` is the exact native-provider acceptance contract.
  Keep existing CodeQL architecture intact. Prove PR-default and scheduled
  nightly outcomes separately, multi-language selection, fail-closed unknown
  language detection and non-duplicate default setup. An overlay cache miss
  is an optimization gap, not a false security PASS.
  > **Status: OPEN** — PR default and nightly proven separately: `codeql.yml` PR run 44883333312 (#1119 head `cebc1590`, success) and `codeql-nightly.yml` schedule run 44899338541 (`c6b7d713`, success), REST-verified. Fail-closed language lookup: CG #1081 (`fe8288c5`). Default setup: REST `code-scanning/default-setup` `state: not-configured`. Missing/contradicted: both runs analyze `python` only while T32 states "CodeQL covers JavaScript separately" (`OPEN_ITEMS.md:42`) and GitHub lists `actions` as a detected language; GitHub Code Quality (`dynamic/github-code-quality/codeql`) runs a second CodeQL on every PR (T30, `CI_CONFIG_FINDINGS.md:31`), and click-path 2 (`CLOSEOUT_RECEIPT.md:80`) names "Default setup", which REST shows is already off.

- Record matched Sonar project, actual analyzed production file set,
  source/test exclusions, imported current-revision coverage, new-code
  quality-gate result and reviewed hotspots. Credential check alone is not a scan.
  > **Status: OPEN** — Cursor-Governance Sonar is `NOT_EXECUTED`: zero `workflow_dispatch` runs of `sonarcloud.yml`, last run 44772875111 on 2026-11-20 16:23Z (REST-verified; `OPEN_ITEMS.md:28`, T15). No matched project file set, coverage import, gate result or hotspot review recorded for CG.

- Reconcile open Cursor #1062: `workflow_dispatch` mode=plan is not analysis;
  only a trusted Core-driven mode=apply on exact main SHA with a real Sonar
  result can replace the old native trigger. Stop native scanner retirement
  until that proof exists.
  > **Status: FAIL** — The old native trigger was removed before the replacement was proven: CG #1062 merged 2026-11-20T16:23:56Z as `a95562c9` (REST) making Sonar dispatch-only, and no Core `mode=apply` run with a Sonar result exists since (REST: 0 dispatch runs). #1062 merged before this binding was written (`09_EXECUTION_BINDING.md` B02). Recovery: click-path 7 (nightly App), then an apply dispatch with an `nd1-` key and a Sonar result on an exact `main` SHA (`HARVEST_LEDGER.md:162`).

- Reconcile Odoo #552 as a candidate scope correction. No Sonar runtime
  observation was recovered for Odoo at the inspected head, and the separate
  `cryptoxdog` owner requires separate authorization.
  > **Status: N/A (out of scope)** — Odoo #552 is `cryptoxdog/IB-Odoo_19`; rollout to other repositories is a separate campaign (operator, 2026-11-20 21:50Z).

- No duplicate deep test execution merely to produce identical coverage;
  prove test artifact identity and native coverage import before reusing it.
  Live Cursor 8175-test scan and EIE 3927-test scan are baseline expense signals.
  > **Status: OPEN** — CG #1062 refuses a PR full suite; CG #1100 (`756ba14a`) and Core #301 route Sonar through Core's step reusing consumer coverage. No run has yet proven test-artifact identity and native coverage import (no CG Sonar run since 2026-11-20 16:23Z).

- Confirm actual GitHub Code Security eligibility and Sonar subscription LOC,
  available AI CodeFix and optional Advanced Security add-on; no automatic
  AI-credit usage, purchase, gate escalation or admin toggle.
  > **Status: UNKNOWN** — Code Security licence count and bill UNKNOWN (`OPEN_ITEMS.md:40`, T31); Sonar LOC settled only for public repositories (T25); AI CodeFix / AI credit state not visible (T29). Native billing pages only.

- Each native status has run URL, analyzed SHA, project or suite, exit result,
  findings/scope and evidence; unresolved credentials/account rights are
  `BLOCKED_EXTERNAL_ACCOUNT` rather than completed optimization.
  > **Status: OPEN** — Per-status run URL/SHA/project table not compiled for CodeQL and Sonar; CG Sonar has no run. Owner: CTO after T15 closes.



## P10: targeted cross-tool configuration and rule harvest

- Perform a lightweight path/config index, then deep-inspect only real custom
  candidates. Known donors: Cursor (4 rules), EIE (8), CEG (8 overlapping),
  Odoo Staging (36, with #553 pending at baseline).
  > **Status: PASS** — Four-donor census at pinned heads (CG `605bb681`, EIE `8f46df4d`, CEG `e66fa5ef`, IB-Odoo_19 `25fd3282`) with per-row deep inspection (`HARVEST_LEDGER.md:7-24`); Semgrep rules ledgered separately in SDK `docs/harvest/semgrep-donor-ledger.yaml`, 59 rows (SDK #124, merged 2026-11-20 19:31Z per `CLOSEOUT_RECEIPT.md:157`).

- Every considered rule/config delta receives `already_satisfied`, `promote_global`,
  `promote_language`, `promote_framework`, `retain_domain`,
  `retire_duplicate` or `defer_unknown`, with exact donor/upstream revision,
  source/generator owner, target path/native key and scope. Behavioral changes
  need good/bad and non-target witnesses; service-owned settings need effective
  config/native receipts appropriate to the change, not fabricated fixtures.
  > **Status: OPEN** — Every index row has a disposition; full fields (donor revision/blob, owner, target, witnesses) exist only for C1-C5 (`HARVEST_LEDGER.md:104-175`). All other rows are explicitly Unknown backlog for the rollout campaign (`HARVEST_LEDGER.md:35-46`, 177-182).

- Cover each observed configured tool using `HARVEST.md` owner routing. Prove
  SDK rule, Core profile, native CodeQL, CodeRabbit source/rendered inheritance,
  Dependabot generation, Sonar/native settings and retained product semantics
  reach their proper owners wherever those deltas exist. No invented candidate
  is required for a tool without a real delta.
  > **Status: OPEN** — C1-C5 reach Core; CodeRabbit inheritance PRs merged (CEG #516, EIE #368); Dependabot generation and Sonar/native settings deltas not delivered (CCF rows 16, 21; T19). Owners per row.

- Record owner PR/change receipt, admission, actual promotion, effective
  inherited config/digest and execution proof separately. A published candidate
  or Semgrep-only inventory cannot close the cross-tool delivery obligation.
  > **Status: OPEN** — Recorded separately for C1-C5 (merged / effective / observed). Not effective: C4 (no apply run, `HARVEST_LEDGER.md:162`) and C5 step two (`HARVEST_LEDGER.md:174`). C1 ledger row is stale: it says Core #312 open, REST shows merged 2026-11-21T08:16:54Z as `63ff7da5` (`CLOSEOUT_RECEIPT.md:13` agrees with REST).

- Before retirement, bind exact successor, relevant canary/parity and preceding
  known-good owner configuration, with scoped rollback and validation. Working
  checks remain when delivery, native access or proof is blocked. Never promote
  secret values, customer data or product/account identity as shared defaults.
  > **Status: OPEN** — Cursor-Governance: no check retired and working checks remain (REST rules; `REQUIRED_CHECK_CUTOVER.md:4`), but no retirement is yet bound to successor, canary parity and rollback. CEG #522 retired copies on a documented parity table before `CURSOR_CANARY_PASS` (see First-consumer blocker).

- Prove non-target repositories do **not** receive Odoo/PlasticOS/memory
  specialty rules. The SDK baseline remains mandatory everywhere applicable.
  > **Status: OPEN** — Scope evidence on CG: consumer memory rules fire only on the planted known-bad and not on #1112's tree (`CURSOR_CANARY_RESULT.md:29`). Missing: a non-target repository run (EIE, CEG, SDK, Core) showing no `semgrep:consumer:quantum-l9.cursor-governance` instance and no Odoo/PlasticOS rules. Owner: SDK (ADR 0021) / CTO.

- Do not equate "60 repos" with "60 deep harvest targets". Fleet required-check
  coverage is separately verified in the rollout stage.
  > **Status: PASS** — Harvest targets were the four donors only (`HARVEST_LEDGER.md:7-24`); fleet required-check coverage is left to the rollout stage (`HARVEST_LEDGER.md:200-205`).

## P11: mandatory Cursor-Governance live canary

- Actual `Quantum-L9/Cursor-Governance` repo and exact evaluated head,
  effective org required-workflow ruleset, promoted Core+SDK runtime and real
  `Analyze (central Core)` job, not SDK-only fixtures or a static workflow diff.
  > **Status: PASS** — Run 44876362790 (job 136761824478), event `pull_request`, head `6ef0ae3566fe`, workflow `org-ci.yml`, conclusion success (REST-verified) on CG #1112; ruleset 21895545 active (REST); Core actions `284a5eb6` (#323) and SDK `4a887396` (`CURSOR_CANARY_RESULT.md:9-25`). Note: #1112 later merged at head `7ab2381c` (merge `35f8d88d`), after the evaluated head.

- Independently verify every required language/provider and custom-rule scope,
  inherited config/pins, adverse provider failure, tamper resistance,
  known-good/bad witnesses, native CodeQL and product test preservation.
  > **Status: OPEN** — Met: languages/instances (`:27`), central config (`:28`), consumer-rule scope (`:29`), known-bad/good (`:31-32`), nosemgrep/.semgrepignore tamper refused (`:33`), incomplete provider fails (`:34`), Biome (`:35`), CodeQL and Test Suite preserved (`:36`, `:30`). Missing: version/severity override attempts were never exercised (`CURSOR_CANARY_RESULT.md:129-133`); a Semgrep parse error is counted as covered (`:44`); the consumer execution gets no `--baseline-commit` (`:45`); no independent verifier agent recorded.

- Compare live baseline and successor findings/runtimes and keep existing
  local enforcement until parity is proven. Report `CURSOR_CANARY_PASS` or
  `CURSOR_CANARY_BLOCKED` with concrete evidence, owner and failed clause.
  > **Status: PASS** — Findings compared: 29 blocking on `main` (2026-11-20) to 0 new / 79 pre-existing advisory (`CURSOR_CANARY_RESULT.md:37`); runtime baseline 3 min 12 s on `4accb109` (`:135`) and successor run 44876362790 06:36:45Z-06:43:57Z (REST); local enforcement kept (five local checks still required, REST); verdict `CURSOR_CANARY_PASS` reported with evidence (`:40`) after the earlier `CURSOR_CANARY_BLOCKED` with owners and failed clauses (`:48-61`).

- `CURSOR_CANARY_BLOCKED` halts **secondary rollout, fleet rollout, and
  consumer cleanup**, not all independent in-scope engineering or PR publication.
  No local bypass/waiver is a substitute for an upstream correction.
  > **Status: FAIL** — Consumer cleanup proceeded during `CURSOR_CANARY_BLOCKED`: Core #294 made `Analyze (central Core)` red on every CG PR from 2026-11-20 21:52Z (B4; `CI_CONFIG_FINDINGS.md:27`), and CEG #522 removed redundant lint/contract jobs at 22:44:57Z (REST). Same root event as the First-consumer blocker. No local bypass or waiver was added for B1-B5 (`CURSOR_CANARY_RESULT.md:48-51`).

Produce a single readable closeout with: accepted decisions, PR links and
head SHAs, exact rulesets/revisions, canary and fleet coverage ledger,
rulepack tests, true/false fixture proof, tool ROI matrix, spend unknowns,
rollout status, and every finding marked fixed, already satisfied, invalid,
or blocked with owner/next action. PR published is NOT fleet rollout complete.
No claims that tests, live rulesets, entitlements or canaries passed without
real outputs. If any required objective remains blocked, state the frontier
plainly and keep the campaign open.
> **Status: OPEN** — `CLOSEOUT_RECEIPT.md` exists with decisions, PR list, rulesets, canary verdicts and drift, and states the frontier (status OPEN, `:3`). Missing from it: PR head SHAs per PR, rulepack test listing, true/false fixture proof table, tool ROI matrix, spend-unknowns table, and per-finding fixed/satisfied/invalid/blocked dispositions. This draft is the X9 input.

## P9: ADR placement, decision closure and precedence

- Every new ADR is proposed **at its owner**, not simply referenced in the campaign. Core 0001 and 0002 must be published as owner documents with their index; SDK 0020 must be published with an index entry and the applicable ADR 0005/0016/0017 amendment notes. No existing accepted ADR may be rewritten or silently superseded.
  > **Status: PASS** — Core 0001 and 0002 published with a new index, status Proposed (Core #283 merged 2026-11-20T19:03:27Z as `1942a1be`; REST read of `docs/adr/README.md`). SDK 0020 published with an index row "Proposed" (SDK #122 `0089b76c`) and its amendment note "This amends in scope, but does not rewrite, ADR 0005/0016/0017" (`0020-...md:34`, REST). Neither PR modifies an existing ADR file (REST file lists).

- For each ADR record owner, exact target path, preflight base SHA, authorizing decision/status, matching scoped invariant IDs, prohibited alternatives, code/contract realization PR and tested acceptance evidence. Proposal publication alone does not make it Accepted, implemented, effective or fleet-enforced.
  > **Status: OPEN** — No per-ADR record of preflight base SHA, authorizing decision, prohibited alternatives, realization PR and tested acceptance evidence was found. Both Core ADRs and SDK 0020 remain Proposed.

- Test the top-down precedence: organization required-workflow ruleset -> Core governance/versions/permissions -> SDK provider facts/technical gates, while product-native semantics remain with the product and native SaaS trust scopes remain with their authorized owner. Evidence must flow back with source/revision identity.
  > **Status: PASS** — Live chain observed on one CG head: org ruleset selects Core `org-ci.yml@main` and evaluates the exact head (`CURSOR_CANARY_RESULT.md:26`); Core resolves pins/policy and provisions SDK (`:28`); consumer-owned rules stay with CG, scoped (`:29`); CodeQL and Sonar keep their owners (`:30`); org-ci runs read-only (`contents: read`, REST). Evidence carries revision identity (`:9-18`).

- Reject simulated pass when a second language, mandatory rule, product-specific test or required native result is absent. Verify that the current CodeQL owner and native PR/nightly profiles remain intact.
  > **Status: OPEN** — Met: second language that cannot complete fails the job (run 44826737909 failure, REST); missing mandatory consumer rule result fails the aggregate (run 44879445868 failure, REST); CodeQL PR and nightly profiles intact (runs 44883333312, 44899338541). Missing: witnesses for an absent product-specific test and an absent required native result.

- Verify unambiguous live owner references, ADR index links, new target paths and schema compatibility. Core has no existing `docs/adr` ledger at the inspected revision, so its proposed first two ADR numbers are deliberately provisional; if a new live ADR has appeared, resolve the collision without modifying its accepted meaning.
  > **Status: PASS** — Core now has `docs/adr/` with README linking 0001 and 0002, no collision (REST); SDK index links resolve (REST file list includes 0020, 0021, 0023, 0024); contract schema compatibility: invariants sit in the existing top-level fields with tests (`09_EXECUTION_BINDING.md` B13), and Core's full suite passed after the T34 repair, 1165 tests OK (`STAGE1_INTEGRATION.md:18-21`).

- No global constitutional ADR is required merely to repeat `L9-OWNER-001`, `L9-MONOTONIC-001`, `L9-UNKNOWN-001` or existing `.github` ADR-010. Change global law only if a genuinely new cross-domain obligation is independently established and separately authorized.
  > **Status: PASS** — No `Quantum-L9/.github` pull request appears among the 149 merged campaign PRs (`CLOSEOUT_RECEIPT.md:91-267`), and no global constitutional ADR was added.


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
> **Status: OPEN** — No terminal-disposition table for T01-T14 exists. `09_EXECUTION_BINDING.md` (Findings register) records status changes, not terminal dispositions; per-item status follows below. T03 was declared changed by merged work (B03) but never closed with a fresh run.

- [ ] CEG GitGuardian: native CI-mode scanning succeeds on a real authorized
  event. Witnesses cover missing CI context, unavailable scanner, a successful
  container pull followed by scanner failure, detected synthetic test secret,
  and clean scan. Preserve the actual outcome and authorized required/advisory
  mode; neither wrapper classification nor aggregate may impersonate execution.
  Prior observed https://github.com/Quantum-L9/Cognitive.Engine.Graphs/actions/runs/44655221257
  (job 136019664092) had workflow success but native scan failure.
  > **Status: OPEN** — Fix merged: CEG #515 (`74f9cc38`) passes CI context to ggshield and classifies by exit code. Live clean scan proven: CEG Quality Gates run 44883136549, job 136782578101 on `main` `e1eb4f2d` logs "No secrets have been found" and "GitGuardian SCANNED_CLEAN" (REST log read). Missing live witnesses: missing CI context, unavailable scanner, pull-then-scanner-failure, detected synthetic secret. Also T41: the GitGuardian dashboard monitors no Quantum-L9 repository (`OPEN_ITEMS.md:54`). Owner: CEG lane / rollout campaign; operator for T41.

- [ ] CEG Codecov: new accepted exact-revision upload (vendor or independently
  verifiable accepted-upload receipt); missing token/failed upload cannot be
  represented as accepted coverage. Prior same run job 136019663740 returned
  `Token required - not valid tokenless upload` with an overall success.
  > **Status: OPEN** — No accepted upload exists. The upload path was retired instead: CEG #518 (`5e7fd0f6`) and #520 (`e66fa5ef`, deletes `dev-layer-gmp.yml`); verdict `RETIRE_CANDIDATE` (`CODECOV_REVIEW.md:21`); T42 still OPEN (`OPEN_ITEMS.md:55`). Closes when the operator records Codecov as retired (and the App/plan decision) as T02's terminal disposition.

- [ ] CEG G01: required product verifier is no longer falsely attributed to
  Semgrep/Core; prove the sibling Odoo mapper integration or mark actual
  G01 not-run block. Never suppress to manufacture Core pass.
  > **Status: OPEN** — No fresh `Analyze (central Core)` result on CEG showing the sibling Odoo mapper proof running, and no recorded not-run block (B03 asks lane F1 for one). CEG canary #517 not re-run on PIN-ADVANCE-3 (`CLOSEOUT_RECEIPT.md:17`). Owner: CEG / rollout campaign.

- [ ] EIE Gitleaks: Dependabot PR exception explicitly documented and verified
  with native execution/skip status. An authorized premerge repair must verify
  trigger/job/actor predicates as well as secret availability; supplying a
  license alone is not closure. Post-merge is not counted as pre-merge.
  > **Status: OPEN** — Fix merged: EIE #366 (`e538bdfa`) runs the licence-free Gitleaks 8.24.3 binary on Dependabot events and labels the action skip `SKIPPED_BY_POLICY`. Missing: a hosted Dependabot PR run after the fix; every `gitleaks.yml` run since is by `cryptoxdog` (REST, last 10 runs).

- [ ] EIE GitGuardian: key missing and API failure cannot be classified as
  `EXECUTED_VERIFIED`; retained successful native evidence remains valid.
  > **Status: OPEN** — Fix merged: EIE #366 (`e538bdfa`) adds a `/v1/health` preflight that classifies a missing, rejected or unreachable key as `NOT_EXECUTED` and fails the job; witnesses in `tests/ci/test_secret_scan_truthfulness.py` (PR body). Retained native success observed after the fix: run 44894557872, job 136817337544, steps "Verify GitGuardian can scan" and "GitGuardian scan" success (REST). Missing: an observed execution of the negative witnesses (the PR body states "failing without the fix is not measured").

- [ ] CEG dependency-review: dependency-graph availability and actual review
  reported separately; a skipped PR cannot claim clean SCA result.
  > **Status: OPEN** — Fix merged: CEG #515 (`74f9cc38`) reports dependency-graph availability and review execution separately (from the 502 in run 44772844698). No post-fix run receipt showing the two fields was read.

- [x] Core Bandit/npm audit: profile/requiredness and skip reason explicit;
  no unconditional reenable without policy authority and coverage proof.
  > **Status: PASS** — Core `.github/workflows/security.yml` on `main` (REST read): header states bandit "advisory when a Python project is detected" and npm audit "not run unless the caller sets run-npm-audit: true; then required" (lines 20-22, 41-45); the bandit step reports completed / findings / did-not-complete as distinct notices (lines 387-415); npm audit requires `package-lock.json` when requested (lines 419-431). Made explicit by Core #285 (`c512c66b`, "report each scan's real outcome in security.yml (L2 T04)"); no unconditional re-enable.

- [ ] Codecov and Sonar coverage: one trusted immutable source/test pass per
  intended validation scope where supported; compare old/new test count,
  setup and wall time. No reduced rule/source/coverage parity.
  > **Status: OPEN** — Old/new test count, setup and wall time not compared; CG Sonar has not run since 2026-11-20 (T15). Core #289 (`c9d436a9`), EIE #371/#372 and CEG #521 wire coverage reuse, without a recorded before/after.

- [ ] Other provider inventory: CodeRabbit, Perplexity, Copilot, OpenSSF,
  Syft, license checks, Gitleaks, Dependabot, Mypy/Ruff/Biome, optional
  Trivy, paid tools. Each receives an owner, state, evidence and cost/unique
  value. Not-installed is not a PASS, unverified subscription is UNKNOWN.
  > **Status: OPEN** — Partial owner/state rows exist across `OPEN_ITEMS.md` (T26 Copilot, T27 CodeRabbit, T28 Perplexity, T41 GitGuardian, T42 Codecov) and `SEMGREP_REVIEW.md`; no single inventory covers OpenSSF, Syft, licence checks, Gitleaks, Dependabot, Mypy/Ruff/Biome, Trivy with owner, state, evidence and cost/unique value. Subscriptions remain UNKNOWN.

- [ ] First mandatory live integrated Core/SDK consumer remains Cursor,
  then secondary native tool canaries (EIE, CEG, Odoo) as currently scoped.
  > **Status: OPEN** — Cursor was the first live consumer canary (2026-11-20 run 44819081765; PASS on 2026-11-21, run 44876362790). Secondary: EIE recorded (runs 44874376220 and 44878546690; run 1 started 06:11:39Z, 25 min before the CG PASS evaluation run started at 06:36:45Z, REST); CEG not re-run on PIN-ADVANCE-3 (#517 open); Odoo not run (outside scope).

- [ ] All auth/feature changes occurred after G0 with applicable explicit
  operator authorization. Reuse authorization already supplied for the same
  action; G0 completion grants none. No secret values disclosed and no tool
  installation required merely to complete verification.
  > **Status: UNKNOWN** — No G0 close-out table was found, so ordering of vendor changes against G0 cannot be shown. Semgrep changes record operator authorization (`OPEN_ITEMS.md:49`, T37); the SonarCloud visibility and deletion change (T18, `OPEN_ITEMS.md:16`) records no authorization in the evidence read. Evidence files carry counts only for credentials (`OPEN_ITEMS.md` preamble); no secret disclosure was found.

## Proof summary

| Section | PASS | FAIL | OPEN | UNKNOWN | N/A (out of scope) | Total |
|---|---|---|---|---|---|---|
| Required evidence (first-consumer blocker, P0-P8) | 1 | 2 | 5 | 1 | 1 | 10 |
| Concrete tests | 0 | 0 | 6 | 0 | 0 | 6 |
| P12 CodeRabbit | 0 | 0 | 3 | 1 | 1 | 5 |
| P13 CodeQL and Sonar (incl. G0 precondition) | 0 | 1 | 5 | 1 | 1 | 8 |
| P10 Harvest | 2 | 0 | 5 | 0 | 0 | 7 |
| P11 Cursor-Governance canary (incl. close-out paragraph) | 2 | 1 | 2 | 0 | 0 | 5 |
| P9 ADRs and precedence | 4 | 0 | 2 | 0 | 0 | 6 |
| P14 Native tool truth (intro + 11 checklist items) | 1 | 0 | 10 | 1 | 0 | 12 |
| **Total** | **10** | **4** | **38** | **4** | **3** | **59** |

Checklist ticks: 1 of 11 (`Core Bandit/npm audit`). `PROOF.md` is not satisfied: X9 stays open until every OPEN, FAIL and UNKNOWN row above has a terminal disposition.

Evidence conflicts found while drafting (REST read 2026-11-21 versus the evidence files):

- `OPEN_ITEMS.md:43` says EIE #368 is open; it merged 2026-11-20T18:42:01Z (`4324e0df`).
- `HARVEST_LEDGER.md:126` says Core #312 is open and C1 not effective, and `:138` says CEG #524 is open; #312 merged 2026-11-21T08:16:54Z (`63ff7da5`) and #524 merged 2026-11-21T08:04:20Z (`e1eb4f2d`).
- Click-path 2 (`CLOSEOUT_RECEIPT.md:80`) says to switch CodeQL *Default setup* off; `code-scanning/default-setup` reports `not-configured`. The second CodeQL on Cursor-Governance PRs is GitHub Code Quality (`dynamic/github-code-quality/codeql`, T30).
- `CLOSEOUT_RECEIPT.md:36-37` cite runs 44875640013 and 44891625020 as canary passes; their run-level conclusion is `failure` and their verdict jobs (136761385630, 136814835426) are `success`. In 44875640013 both Cursor-Governance legs failed (row 27 masking).
- `OPEN_ITEMS.md:42` (T32) says CodeQL covers JavaScript in Cursor-Governance; the PR and nightly CodeQL runs analyze `python` only.
