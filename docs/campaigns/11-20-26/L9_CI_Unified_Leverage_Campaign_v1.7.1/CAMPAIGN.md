# Campaign contract

**ADR binding:** `ADRS.md` and `candidates/adr/` are the **prewritten**
architectural decisions. They are proposed, not admitted, and the agent must
not rename, redesign, relocate or dilute the material decisions in normal
execution. The ADR decision/owner matrix is upstream of the source-owner
contract edits and implementation. Existing canonical global semantics and
accepted SDK ADRs remain binding unless a duly admitted successor changes
their explicitly scoped obligations.


**Invariant binding:** `INVARIANTS.yaml` is the exact candidate statement ledger; `INVARIANTS.md` is its owner/negative-test map and `candidates/*.patch` are precise proposed changes for existing scoped owner contracts. All lanes are subordinate to these obligations; no agent may redefine their meaning as a convenience. No candidate is live authority until admitted by the target owner.

## A. Frozen intent / nonnegotiables

**Hard ordering:** inspect custom consumer rules and configuration deltas in a
*targeted* harvest before selecting shared defaults. Route each delta to its
existing upstream owner under `HARVEST.md`. Only reusable generic rules
become all-consumer rules; framework-specific checks are capability-selected;
product/domain rules remain source-owned and selectively invoked. After SDK/Core
implementation and promotion, run `CURSOR_CANARY.md` on the **actual**
`Quantum-L9/Cursor-Governance` consumer. Do not proceed to secondary canaries,
consumer cleanup or fleet rollout without the live acceptance result.

1. No routine per-repository copies or version pins for the promoted Core/SDK
   required runtime. Runtime inheritance replaces stamp churn only after Core's
   current drift contract is revised and validated. Preserve accepted native
   thin callers, their SHA pins/adoption updates, project bindings and existing
   managed native generators; CodeQL is the explicit current exception. These
   do not permit consumer overrides of Core/SDK policy or pins.
2. One authoritative governance policy, one version lock, deterministic
   capability selection, full language/framework coverage, evidence for all
   required outcomes. SDK evidence and policy decisions must not be conflated.
3. Do not silently drop a test, specialized rule, native scanner signal, or
   paid feature when removing legacy duplication. Prove parity or explicitly
   preserve the check with named ownership.
4. `Quantum-L9/.github` retains canonical semantics and organization ruleset
   authority. `l9-ci-core` orchestrates; `l9-ci-sdk` executes supported
   providers and normalizes results; `l9-assurance` retains its existing final
   verdict authority, where applicable. Avoid a new cross-cutting framework.
5. CodeQL is ALREADY LEVERAGED. Cursor-Governance PR #1067 is merged. Preserve
   the existing fast default-suite PR and deeper night analysis contracts.
   Do not redo or relocate CodeQL without a proved authority/feature gap.
   Correlate its native runs with the central coverage/evidence ledger.
6. Product-specific tests, compilers, special analysis, and local capability
   declarations remain owned by those products. Central orchestration may run
   them through the existing repository-execution ABI; it must not replace
   them with generic shortcuts.
7. Changes execute as PRs under the verified `make pr` interface; no merge,
   deployment, workflow disablement, or irreversible changes automatically.
8. An external tool's existence is not proof of paid entitlement, connected
   project, enabled feature, real execution, or added value.

## B. Target coverage

Core source owners:
- `Quantum-L9/.github`: organization semantics/rulesets and existing governed
  native configuration sources/generators, including CodeRabbit ADR-0020 and
  Dependabot. No new global law or copied Core/SDK CI distribution.
- `Quantum-L9/l9-ci-core`: required workflow, governance selection, toolchain
  lock, runtime config resolution, permissions, scheduling and canaries.
- `Quantum-L9/l9-ci-sdk`: capability inventory, provider SPI, rulepack
  composition, normalization, canonical coverage/failure semantics.
- Other existing native-provider owners (CodeQL, GitHub Actions, SonarQube
  Cloud, etc.) remain source owners unless independently resolved otherwise.

**Mandatory first live canary:**
- `Quantum-L9/Cursor-Governance`: real organization consumer, mixed source
  surfaces, four special Semgrep rules, established CodeQL behavior, PR ceremony.
  See `CURSOR_CANARY.md`; the campaign cannot pass before this run.

**Targeted harvest donors and subsequent secondary canaries:**
- `Quantum-L9/Enrichment.Inference.Engine`: Python and eight local rules.
- `Quantum-L9/Cognitive.Engine.Graphs`: overlapping eight rules and fixtures.
- `cryptoxdog/IB-Odoo_19` Staging: Odoo Python/XML and 36 observed rules,
  separately enforced GitHub owner, Sonar and open rule PR #553.

A lightweight path census may identify other customized donors; it does not
create a prerequisite to deeply harvest every repository.

Later: inventory and verify the entire eligible Quantum-L9 fleet. Do not
assume the fleet has exactly 60 repositories, or that the Quantum-L9 ruleset
binds the separate `cryptoxdog` owner.

## C. Workstream DAG and collision control

**v1.6.0 extension:** Stage 0 MUST consume `OTHER_TOOLS_EVIDENCE.md`,
`OTHER_TOOLS_EXECUTION.md` and `G0_OTHER_VENDOR_CHECK.md`. It treats P0 T01/T02
as falsified scan/coverage claims, and T03 as a real G01 product-proof failure.
G0 remains read-only, separate from approval to configure vendors. After initial
source inventory, run three disjoint technical concern lanes F1/F2/F3 as
specified. No new global invariant/ADR is authorized simply because a tool
malfunctioned; bind the existing owner contract/invariants first. Do not
obscure a native scanner failure behind a green GitHub workflow conclusion.

Stage 0: authority / current-state preflight, PR census, accepted interface
and tool baseline. The exact owner-specific ADRs in `candidates/adr/` and
corresponding SDK index patch MUST be reconciled and proposed at their true
source owners alongside the owner-specific invariant changes. The Core ADRs
record the already selected top-down control plane and a distinct adoption/trust
policy. SDK ADR 0020 records execution/capability/evidence architecture and
extends existing SDK ADR 0005/0016/0017 without rewriting accepted history.
Do not create a new global `.github` ADR for an implementation-specific CI
recipe, change Core/SDK boundaries, or treat any proposal as admitted.
The owner-specific invariants in `INVARIANTS.yaml` MUST
be tested and proposed at their exact owners as early Core and SDK PRs, prior
to migration or local scanner retirement. Do not send them to `.github`
merely for global visibility: reuse existing admitted L9 constitutional law.
The new 4.1.0 `policies/ORG_INVARIANTS.yaml` is self-labeled candidate; do
not use it as fresh canonical authorization. Verify this status at kickoff. Record current immutable SHA of every source owner, exact
canonical .github authority, actual repository rulesets and all existing PR
heads. Validate applicable projection/receipt rather than fabricate one.

In parallel AFTER Stage 0:

**Stage 0H: selective configuration and rule harvest (before shared promotion).**
Read `HARVEST.md`. Census the accessible fleet cheaply; deeply inspect genuine
configuration/rule deltas, starting with Cursor, EIE, CEG and Odoo. Record donor
and upstream revisions, exact target path/key, scope, canonical/derived owner,
one disposition, owner PR/change receipt, admission/promotion, effective config,
parity and rollback. Route to SDK/Lane 1, Core/Lane 2 or native/Lane 3 according
to the existing owner; retain product semantics and identities at their owner.
Generic rules may enter SDK, language/framework rules require proved scope,
and native configuration must not be forced into SDK. Inventory, publication,
promotion and effective inheritance are separate proof states. This is not a
60-repository deep audit, and a Semgrep-only candidate list does not close it.

Lane 1 - SDK provider and capability closure
  Write owner: `l9-ci-sdk` only.
  - Publish proposed SDK ADR 0020 at `docs/adr/0020-all-applicable-capabilities-and-lossless-provider-evidence.md` and the provided ADR index amendment, with applicable tests and exact owner confirmation. Do not self-mark Accepted.
  - Admit SDK domain invariant candidate `L9-CI-SDK-001..005` through the
    existing SDK integration contract and runnable positive/negative tests.
    Use the exact frozen wording in INVARIANTS.yaml and scoped owner patch.
  - Build a capability inventory of languages, frameworks, lockfiles, Docker,
    CI environments, and supported provider preconditions. Detect ALL
    applicable languages and distinguish not_applicable, incomplete, failed.
  - Extend the existing provider registry/public API; migrate generic scanner
    configuration and rulepacks to versioned SDK package data with rule tests.
  - Consume `HARVEST.md` donor dispositions: compare EIE and CEG overlapping
    eight rule IDs by actual behavior and fixtures; separate Odoo framework
    patterns from PlasticOS-specific law and Cursor memory-path restrictions.
    Reuse precise rule behavior, not filenames, broad severity or path ignores.
  - Add or adapt SDK execution and normalization for CLI-capable scanner
    categories only where it eliminates actual duplication. For CodeQL and
    external SaaS, consume trustworthy native results via governed adapters.
  - Provide explicit invocation, coverage, provider failure and normalized
    output contracts to Lane 2. Do not overgeneralize the SPI.
  - Return each harvested SDK delta's owner PR, admission, promoted revision,
    effective runtime config and proof to the shared harvest ledger.

Lane 2 - Core governance and execution
  Write owner: `l9-ci-core` only. Interface freeze coordinated with Lane 1.
  - Publish proposed Core ADRs 0001 and 0002 and the Core ADR index from `candidates/adr/l9-ci-core/docs/adr/`, preserving the two distinct decisions and their existing owner contracts. Do not self-mark Accepted.
  - Admit Core domain invariant candidate `L9-CI-CORE-001..006` through
    Core's existing governance contract and executable proofs. Apply the
    exact owned statements, not new global constitutional copies.
  - Reuse current org-ci workflow, governance profiles and toolchain lock;
    do not distribute a second workflow into consumers.
  - Implement central runtime config resolution, language/framework matrix,
    provider eligibility, permissions, evidence retention and policy overlays.
  - Keep immutable pins and known configuration digests. Separate PR-fast,
    merge, nightly, release and supply-chain profiles, with safe run budgets.
  - Correct existing single-language selection and absence of automatic
    consumer-specialized rulepack inclusion. Never equate skipped with PASS.
  - Ensure the Core-owned stamp/repo-execution contract can accept inherited
    config without self-triggered drift failures.
  - Reconcile open Core PR #281 before changing PR expense logic. Preserve
    fast checks, avoid unconditional expensive full-suite fallback.
  - Deliver harvested Core defaults/profile deltas at existing source surfaces;
    record effective inheritance and coordinate SDK/native changes by owner.

Lane 3 - Native/paid-tool leverage and verified scanner coverage
  **Precondition G0**: `OPERATOR_VERIFY_FIRST.md` and the bounded
  `G0_OTHER_VENDOR_CHECK.md` extension. Read-only, one screen at a time; no
  new tests/scans, vendor-admin action or paid activation during G0.
  Paid entitlement Unknown does not block independent Core/SDK engineering.
  **Native CodeQL and Sonar architecture stays at its accepted owners.**
  The current CodeQL default PR/extended nightly split is a preservation
  contract, not a request to reimplement those scans in Core or SDK.

  Write scope: existing native provider owners only, separate PRs per owner.
  Evidence aggregation is read-only until authorized.
  Consume Stage 0H native-config deltas at their existing source/generator or
  native account, with effective-config proof. Preserve `.github` CodeRabbit
  and Dependabot generators, Cursor CodeQL ownership, native project identities
  and product instructions. Do not hand-edit a generated copy as its source.
  - CodeQL/Sonar: apply `CODEQL_SONAR_LEVERAGE.md`; verify actual PR/nightly
    receipts, scanner scope and coverage, quality gate and cost. Reconcile
    Cursor #1062 and Odoo #552. No static-config-only PASS.
  - CodeRabbit: apply `CODERABBIT_ACTIVATION.md`; verify subscription/installation
    and effective `.coderabbit.yaml` inheritance, demonstrate a real Cursor
    review, preserve local domain instructions. No fabricated review from bot
    status/skip comments.
  - Other providers: apply `OTHER_TOOLS_EVIDENCE.md` (T01-T14) and
    `OTHER_TOOLS_EXECUTION.md` (F1/F2/F3 lanes). CEG GitGuardian/Codecov
    false-green defects are P0; remediate at true owners with negative witness
    and native receipt. CEG G01 is a real unavailable product proof, not a
    Semgrep or central-gate defect.
  - Inventory vendor-native paid plans, available features, repo binding,
    quota and actual usage; ask for read-only owner account evidence when
    necessary. No purchase, secret exposure or enablement by assumption.
  - Every tool receives independently proven installation, actual execution,
    native accepted output, applicable source/language scope, findings,
    failures, cost and status; no skipped scan is counted as PASS.
  - Do not move native vendor credentials into untrusted PR runners, or
    confuse a plugin/account connection with scanner effectiveness.

Lane 4 - Existing PR and specialized-policy reconciliation
  Initial owner: source inspection only; mutation owns one designated repo
  each, with no shared writes to Core or SDK.
  - Revalidate status/head/diff of Cursor-Governance #1067 (merged), #1062;
    Core #281; Odoo #552/#553/#556. Discover other open scanner PRs.
  - Do not overwrite existing PR work, independently reproduce their fixes,
    or claim unmerged changes exist on default branch.
  - Extract Odoo-specific Semgrep rules and Sonar source coverage after PR
    disposition, preserve framework-specific semantics, fixtures, exceptions.
  - Inspect Cursor, EIE, CEG duplicate local scans before planning removal.
  - Resolve access and enforcement limitations for `cryptoxdog` separately.

**Native provider and economics verification before migration:** for every
present tool report actual execution, native acceptance, requiredness,
paid entitlement, coverage denominator, overlapping findings, and cost.
The source-bound known-bad fixtures in `OTHER_TOOLS_EXECUTION.md` are the
minimum prevention proof for CEG GitGuardian and Codecov. Preserve vendor
trust/secret boundaries and publication through each correct repo owner.

Stage 1 integration: Core/SDK ADR decisions and invariant candidate changes must be
reviewable in their owner PRs and enforceable with negative witnesses BEFORE
the successor runtime is accepted. Owner admission and integrated enforcement
are separate proof steps. SDK-Core public contract; pinned SDK source, invocation,
provider evidence, profile selection, read-only execution. No central policy
or consumer cleanup is accepted on static assertions alone.

Stage 2A MANDATORY live consumer gate:

**Native integration preconditions**: CodeQL PR and nightly claims require actual
native evidence; Cursor CodeQL cache HIT is an efficiency objective, not
a security-gate prerequisite. Cursor #1062 dispatch-only Sonar successor
requires actual Core apply plus a native Sonar quality gate before its
new mode can replace the prior scanner coverage; a local PR success or
`mode=plan` does not count. Do not block unrelated Core/SDK PR engineering on
a vendor-dashboard entitlement Unknown.

 **Cursor-Governance first**. After
Core+SDK integration is promoted through the actual central workflow source,
run the complete `CURSOR_CANARY.md` against the real Cursor consumer. Prove
required-workflow targeting, exact head evaluation, inherited config, all
applicable providers, four special-rule dispositions, known-good/known-bad
fixtures, true failures, unchanged CodeQL/native tests, and no policy bypass.
No consumer duplication is retired and no fleet rollout starts without
`CURSOR_CANARY_PASS`. An unmerged owner PR or synthetic SDK test is not the
live acceptance receipt.

Stage 2B secondary canaries: EIE, CEG and Odoo Staging, using their specific
harvested rules/fixtures and the separately owned `cryptoxdog` governance.
Preserve checks until parity. Secondary tests do not substitute for Stage 2A.

Stage 3 fleet rollout: inventory every eligible repo, group by detected
capabilities and trust tier, use staged canaries, publish minimum necessary
consumer cleanup PRs. Only then delete duplicate local workflows/configs,
updating any references/contracts that required them. External owner work is
separately authorized and attested. Avoid all-at-once blocking policy flips.

Stage 4 closeout: PROOF.md receipts, documented residual blockers and
rollbacks; no fabricated fleet-wide PASS. Publish per-source-owner PRs through
verified `make pr`, track dependent PR stacks, and preserve actual merge order.

- SaaS reviewer activation is a native-provider check, NOT a second SDK execution plane. CodeRabbit setup is governed by existing `.github` ADR-0020 and the vendor account; do not add new global law or replace local domain instructions. A UI/integration blocker is reported explicitly without blocking independent Core/SDK code changes.

## D. Decision rules

- Harvest classification and consumer canary acceptance are governed by
  `HARVEST.md` and `CURSOR_CANARY.md`, not ad hoc downstream judgment.
- Only high-confidence general rules enter global SDK baseline. A domain
  rule may remain product-owned while Core/SDK execute it through a scoped,
  traceable binding; that is compatible with no routine CI configuration.
- Required fleet rollout is blocked until the exact live Cursor head has
  passed the promoted Core/SDK required job with negative-fixture parity.

- Do not make every installed tool blocking by default. Preserve current
  governance semantics; evaluate severity, scope, maturity, value and
  cost before centrally promoting new mandatory gates.
- Prevent consumers from disabling central requirements or shadowing Core
  with local tool versions AFTER proven parity and safe migration.
- No new bespoke configuration language, ruleset router, service, runner,
  governance YAML, or receipt when existing Core/SDK machinery suffices.
- Generic rule: SDK; event/requiredness: Core; org semantics: .github;
  product-specific rule intent: product, with centrally versioned transport
  or reference when actually portable; native vendor features: native owner.
- A feature whose paid status, coverage or execution cannot be proven is
  Unknown, not inactive, enabled or successful by assumption.

## E. Deliverables

1. Core and SDK source-owner ADR and invariant PRs matching `ADRS.md`,
   `candidates/adr/`, `INVARIANTS.yaml` and the exact candidate contract patches;
   each ADR, invariant, index link, and cross-owner boundary must be disposed.
   Include schema-valid patches and positive/negative tests; no duplicated
   constitutional law, silent Accepted status or speculative execution claim.

2. Reproducible fleet capability/tool inventory and cross-tool harvest ledger
   by donor/upstream revision, true owner, disposition, delivery, effective
   inheritance, parity and rollback. An unresolved required promotion remains
   blocked, not completed by listing a recommendation.
3. SDK provider/rulepack coverage PRs and tests.
4. Core runtime-config / governance PRs and tests.
5. Per-tool entitlement, utilization, ROI and gap matrix with live run links.
   Include source-owner defect register T01-T14, exact native acceptance
   receipts, CEG false-green remediations, role of each scanner, no unproven
   fleet-wide pass, and cost savings from test/scan reuse.
   Include exact CodeQL/Sonar feature rights, source and coverage parity,
   existing native run baselines, duplicate-run elimination and scanner
   quality-gate evidence per `CODEQL_SONAR_LEVERAGE.md`.
6. CodeQL preservation/verification and existing PR disposition ledger.
7. Four-repo canary proof and full eligible-fleet enforcement proof.
8. Minimum consumer cleanup PRs, no redundant config churn.
9. Regression witness suite and precise residual blocker/rollback ledger.

## F. v1.7.1 execution binding

`09_EXECUTION_BINDING.md` resolves this contract against the live repositories and host and outranks
the sentences it names. For execution:

- Lanes 1 to 4 above and F1 to F3 in `OTHER_TOOLS_EXECUTION.md` are concern groupings. The writer map
  is the binding's lane table: L1 (SDK), L2 (Core), F1 (CEG), F2 (EIE), N1 (Cursor-Governance), H1
  (IB-Odoo_19), and G1, S0 and I1 in the CTO session. One writer per repository.
- "Verified `make pr`" means the command in the binding's Publication table for that repository.
- Cursor-Governance #1062 and IB-Odoo_19 #552, #553 and #556 are merged. Where this file says to
  reconcile them as open, verify the merged change's live effect instead.
- Stage 2A needs the operator's merges and Core's SDK pin advance. Wave 1 therefore ends at
  ready-to-merge pull requests and `CURSOR_CANARY_BLOCKED` with reason `BLOCKED_ON_PROMOTION`.
