# Acceptance, validation and rollout receipts

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

## Required evidence, not green theater

**First-consumer blocker:** `CURSOR_CANARY_PASS` from `CURSOR_CANARY.md` is a
mandatory prerequisite to secondary rollout and removal of redundant
consumer checks. `HARVEST.md` candidate dispositions must precede shared
configuration/rule promotion at the correct upstream owner. CI Core/SDK unit tests, a published PR,
and a simulated consumer are insufficient.

P0: every observed required check is actually governed. Record correct
organization ruleset target, correct working/source revision, enforced mode,
executed providers and permissions, plus any exceptions. `cryptoxdog` must
have separate, verified enforcement.

P1: detection is complete and accurate. Known-good mixed Python+TS repository
selects both. Framework/supply-chain capabilities select correctly. Deliberate
missing/invalid metadata and scanner failures yield incomplete/fail rather
than PASS. Document detectors' blind spots and known unsupported languages.

P2: real tool runs. Capture native executable version, SHA/digest where
available, exact central config/rulepack digest, file scope, normalized
findings/coverage, status, run link and exact repository SHA. A provider that
can only issue an advisory artifact cannot be presented as a blocking gate.
Separate the inspected source snapshot, PR head, actual analyzed/merge checkout,
and resolved reusable workflow/action revision. Missing coordinates remain
Unknown; a default-branch SHA cannot substitute for the code a hosted run used.

P3: parity. For every retired local check, test a known-bad case that fails
and a known-good case that passes in the central successor. Reproduce unique
consumer rule findings and preserve project tests. Compare historical live
runs before and after. No local workflow/config removal before parity.

P4: coverage across four canaries, then every eligible org repo. Publish
repo-by-repo coverage and policy ledger, not merely a percentage without
unscanned repository names. Include external owner separately. A new supported
repo proves Core/SDK runtime inheritance without routine copies/repins. Record
retained native callers and their required SHA-pin updates, managed native files,
project identities and product settings separately; do not claim these vanished.

P5: paid-tool leverage. Each tool must have actual tier/entitlement and native
project configuration proof, demonstrable unique value or explicitly
substantiated retirement decision, before/after scan cost and coverage where
measurable, and no unapproved vendor billing or permission changes. If native
access is unavailable, label optimization blocked by access and do not certify
complete spend optimization.

P6: no unauthorized changes. PRs published by target-verified `make pr`; no
manual raw pushes, branch protection bypass, merge, deployment or payments.
All open PR overlap reconciled by exact head and base SHA before writing.

P7: rollback. Preserve SHA of Core, SDK, org rulesets and native-provider
config before promotion. Central canary failure halts next rollout wave;
rollback is narrowly scoped to faulty owning release, never consumer-local
policy bypass. Verify rollback itself against the affected required checks.

P8: invariant closure. For EACH ID in `INVARIANTS.yaml`, show (a) exact
source-owner change/accepted existing law, (b) type/schema compatibility,
(c) known-bad witness that fails before/when tested, (d) known-good witness
that passes, (e) real enforcement observation, (f) revision-bound integrated
Core+SDK run, and (g) disposition (implemented, already satisfied, invalid,
blocked). Merely including a statement in YAML is not an enforcement receipt.
Global constitutional refs remain canonical at `.github`; campaign candidates
must not self-admit. No local check retirement if any relevant invariant's
negative witness or parity evidence remains missing.

## Concrete tests

- Capability selection fixtures (SDK-001, Core-003): Python-only, TypeScript-only, mixed,
  Odoo Python+XML, no supported code, malformed manifests, unsupported env.
- Provider failures (SDK-002, Core-003): missing executable, hash mismatch, registry/network
  failure, invalid custom rulepack, report parse failure, scanner timeout,
  missing token for externally required native scanner.
- Policy effects (Core-001, Core-006): blocking known-bad, approved advisory finding, true
  not_applicable, failing native project test, missing required run, known
  unowned exception, read-only PR vs native write-scope boundaries.
- Tool value: each proposed setting activates on the entitled project and
  changes actual coverage/precision/cost in a measurable manner, or is
  explicitly rejected as duplicative/ineffective.
- CI performance: PR-fast elapsed runtime and total job-minute deltas; no
  reduction in required findings or native tests.
- Default-branch and release: clean PR, push, nightly and release/profile
  evidence; no green-on-skip; integrity of rulepack and tool locks.

## P12: CodeRabbit activation and paid-utilization evidence

- Verify authenticated subscription tier, seats, GitHub App installation, native dashboard activation, and any usage-based billing settings separately for `Quantum-L9` and `cryptoxdog` where applicable. Billing and token state not visible from GitHub content remain UNKNOWN.
- Verify central `coderabbit` repository installation and effective configuration source using official PR configuration command, plus local `inheritance: true` where genuinely necessary. Keep domain-specific instructions owned locally.
- Verify an actual substantive or explicit no-action review on a Cursor-Governance PR, and a separate specialized-consumer review. A CodeRabbit skip/status comment never counts as executed review. Preserve CodeQL and normal CI.
- Reconcile Odoo #556 sub-10-star skip with real paid entitlement. Provide manual trigger only as fallback; do not claim automatic review from a manually invoked result.
- Record accepted unique findings, coverage and actual spend or BLOCKED_EXTERNAL_ACCOUNT. No purchase or overage switch is implied.

## P13: CodeQL and SonarQube Cloud native-proof closure

**Precondition G0:** `OPERATOR_VERIFY_FIRST.md` read-only walkthrough is completed first. Evidence includes no mutations/scans, all three UI scope observations or explicit Unknowns, one-screen-at-a-time operator interaction, and CTO gap matrix. G0 is not proof that any subscription tier is active nor permission to configure. Configuration changes must have distinct operator approval.

- `CODEQL_SONAR_LEVERAGE.md` is the exact native-provider acceptance contract.
  Keep existing CodeQL architecture intact. Prove PR-default and scheduled
  nightly outcomes separately, multi-language selection, fail-closed unknown
  language detection and non-duplicate default setup. An overlay cache miss
  is an optimization gap, not a false security PASS.
- Record matched Sonar project, actual analyzed production file set,
  source/test exclusions, imported current-revision coverage, new-code
  quality-gate result and reviewed hotspots. Credential check alone is not a scan.
- Reconcile open Cursor #1062: `workflow_dispatch` mode=plan is not analysis;
  only a trusted Core-driven mode=apply on exact main SHA with a real Sonar
  result can replace the old native trigger. Stop native scanner retirement
  until that proof exists.
- Reconcile Odoo #552 as a candidate scope correction. No Sonar runtime
  observation was recovered for Odoo at the inspected head, and the separate
  `cryptoxdog` owner requires separate authorization.
- No duplicate deep test execution merely to produce identical coverage;
  prove test artifact identity and native coverage import before reusing it.
  Live Cursor 8175-test scan and EIE 3927-test scan are baseline expense signals.
- Confirm actual GitHub Code Security eligibility and Sonar subscription LOC,
  available AI CodeFix and optional Advanced Security add-on; no automatic
  AI-credit usage, purchase, gate escalation or admin toggle.
- Each native status has run URL, analyzed SHA, project or suite, exit result,
  findings/scope and evidence; unresolved credentials/account rights are
  `BLOCKED_EXTERNAL_ACCOUNT` rather than completed optimization.



## P10: targeted cross-tool configuration and rule harvest

- Perform a lightweight path/config index, then deep-inspect only real custom
  candidates. Known donors: Cursor (4 rules), EIE (8), CEG (8 overlapping),
  Odoo Staging (36, with #553 pending at baseline).
- Every considered rule/config delta receives `already_satisfied`, `promote_global`,
  `promote_language`, `promote_framework`, `retain_domain`,
  `retire_duplicate` or `defer_unknown`, with exact donor/upstream revision,
  source/generator owner, target path/native key and scope. Behavioral changes
  need good/bad and non-target witnesses; service-owned settings need effective
  config/native receipts appropriate to the change, not fabricated fixtures.
- Cover each observed configured tool using `HARVEST.md` owner routing. Prove
  SDK rule, Core profile, native CodeQL, CodeRabbit source/rendered inheritance,
  Dependabot generation, Sonar/native settings and retained product semantics
  reach their proper owners wherever those deltas exist. No invented candidate
  is required for a tool without a real delta.
- Record owner PR/change receipt, admission, actual promotion, effective
  inherited config/digest and execution proof separately. A published candidate
  or Semgrep-only inventory cannot close the cross-tool delivery obligation.
- Before retirement, bind exact successor, relevant canary/parity and preceding
  known-good owner configuration, with scoped rollback and validation. Working
  checks remain when delivery, native access or proof is blocked. Never promote
  secret values, customer data or product/account identity as shared defaults.
- Prove non-target repositories do **not** receive Odoo/PlasticOS/memory
  specialty rules. The SDK baseline remains mandatory everywhere applicable.
- Do not equate "60 repos" with "60 deep harvest targets". Fleet required-check
  coverage is separately verified in the rollout stage.

## P11: mandatory Cursor-Governance live canary

- Actual `Quantum-L9/Cursor-Governance` repo and exact evaluated head,
  effective org required-workflow ruleset, promoted Core+SDK runtime and real
  `Analyze (central Core)` job, not SDK-only fixtures or a static workflow diff.
- Independently verify every required language/provider and custom-rule scope,
  inherited config/pins, adverse provider failure, tamper resistance,
  known-good/bad witnesses, native CodeQL and product test preservation.
- Compare live baseline and successor findings/runtimes and keep existing
  local enforcement until parity is proven. Report `CURSOR_CANARY_PASS` or
  `CURSOR_CANARY_BLOCKED` with concrete evidence, owner and failed clause.
- `CURSOR_CANARY_BLOCKED` halts **secondary rollout, fleet rollout, and
  consumer cleanup**, not all independent in-scope engineering or PR publication.
  No local bypass/waiver is a substitute for an upstream correction.

Produce a single readable closeout with: accepted decisions, PR links and
head SHAs, exact rulesets/revisions, canary and fleet coverage ledger,
rulepack tests, true/false fixture proof, tool ROI matrix, spend unknowns,
rollout status, and every finding marked fixed, already satisfied, invalid,
or blocked with owner/next action. PR published is NOT fleet rollout complete.
No claims that tests, live rulesets, entitlements or canaries passed without
real outputs. If any required objective remains blocked, state the frontier
plainly and keep the campaign open.

## P9: ADR placement, decision closure and precedence

- Every new ADR is proposed **at its owner**, not simply referenced in the campaign. Core 0001 and 0002 must be published as owner documents with their index; SDK 0020 must be published with an index entry and the applicable ADR 0005/0016/0017 amendment notes. No existing accepted ADR may be rewritten or silently superseded.
- For each ADR record owner, exact target path, preflight base SHA, authorizing decision/status, matching scoped invariant IDs, prohibited alternatives, code/contract realization PR and tested acceptance evidence. Proposal publication alone does not make it Accepted, implemented, effective or fleet-enforced.
- Test the top-down precedence: organization required-workflow ruleset -> Core governance/versions/permissions -> SDK provider facts/technical gates, while product-native semantics remain with the product and native SaaS trust scopes remain with their authorized owner. Evidence must flow back with source/revision identity.
- Reject simulated pass when a second language, mandatory rule, product-specific test or required native result is absent. Verify that the current CodeQL owner and native PR/nightly profiles remain intact.
- Verify unambiguous live owner references, ADR index links, new target paths and schema compatibility. Core has no existing `docs/adr` ledger at the inspected revision, so its proposed first two ADR numbers are deliberately provisional; if a new live ADR has appeared, resolve the collision without modifying its accepted meaning.
- No global constitutional ADR is required merely to repeat `L9-OWNER-001`, `L9-MONOTONIC-001`, `L9-UNKNOWN-001` or existing `.github` ADR-010. Change global law only if a genuinely new cross-domain obligation is independently established and separately authorized.


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

- [ ] CEG GitGuardian: native CI-mode scanning succeeds on a real authorized
  event. Witnesses cover missing CI context, unavailable scanner, a successful
  container pull followed by scanner failure, detected synthetic test secret,
  and clean scan. Preserve the actual outcome and authorized required/advisory
  mode; neither wrapper classification nor aggregate may impersonate execution.
  Prior observed https://github.com/Quantum-L9/Cognitive.Engine.Graphs/actions/runs/44655221257
  (job 136019664092) had workflow success but native scan failure.
- [ ] CEG Codecov: new accepted exact-revision upload (vendor or independently
  verifiable accepted-upload receipt); missing token/failed upload cannot be
  represented as accepted coverage. Prior same run job 136019663740 returned
  `Token required - not valid tokenless upload` with an overall success.
- [ ] CEG G01: required product verifier is no longer falsely attributed to
  Semgrep/Core; prove the sibling Odoo mapper integration or mark actual
  G01 not-run block. Never suppress to manufacture Core pass.
- [ ] EIE Gitleaks: Dependabot PR exception explicitly documented and verified
  with native execution/skip status. An authorized premerge repair must verify
  trigger/job/actor predicates as well as secret availability; supplying a
  license alone is not closure. Post-merge is not counted as pre-merge.
- [ ] EIE GitGuardian: key missing and API failure cannot be classified as
  `EXECUTED_VERIFIED`; retained successful native evidence remains valid.
- [ ] CEG dependency-review: dependency-graph availability and actual review
  reported separately; a skipped PR cannot claim clean SCA result.
- [ ] Core Bandit/npm audit: profile/requiredness and skip reason explicit;
  no unconditional reenable without policy authority and coverage proof.
- [ ] Codecov and Sonar coverage: one trusted immutable source/test pass per
  intended validation scope where supported; compare old/new test count,
  setup and wall time. No reduced rule/source/coverage parity.
- [ ] Other provider inventory: CodeRabbit, Perplexity, Copilot, OpenSSF,
  Syft, license checks, Gitleaks, Dependabot, Mypy/Ruff/Biome, optional
  Trivy, paid tools. Each receives an owner, state, evidence and cost/unique
  value. Not-installed is not a PASS, unverified subscription is UNKNOWN.
- [ ] First mandatory live integrated Core/SDK consumer remains Cursor,
  then secondary native tool canaries (EIE, CEG, Odoo) as currently scoped.
- [ ] All auth/feature changes occurred after G0 with applicable explicit
  operator authorization. Reuse authorization already supplied for the same
  action; G0 completion grants none. No secret values disclosed and no tool
  installation required merely to complete verification.
