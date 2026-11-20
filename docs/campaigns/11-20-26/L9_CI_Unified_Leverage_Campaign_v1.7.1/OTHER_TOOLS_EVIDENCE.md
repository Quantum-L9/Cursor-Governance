# Other CI and security tools: evidence-grounded failure and value census

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

**Read-only diagnosis, 2026-11-19 US Eastern / UTC runs 2026-11-20.** This inventory is an execution input, not a claim of all-fleet coverage. Sources were GitHub connector reads of named files at frozen branches and hosted PR workflow runs and logs. Every status is constrained to what that evidence establishes. Re-read exact heads at campaign kickoff and do not overwrite stacked work.

## Exact sampled source revisions

- `Quantum-L9/.github` main: `c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`.
- `Quantum-L9/l9-ci-core` main: `3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437`.
- `Quantum-L9/l9-ci-sdk` main: `ab8a25543bf99de4c932f1930841a1e5f2ef2f27`.
- `Quantum-L9/Cursor-Governance` main: `263216c13b5b4cac07f627675fb4f231e08317c8`.
- `Quantum-L9/Enrichment.Inference.Engine` main: `29d4eb54942e446a9ac917d2ebe2d9733a4e7aec`.
- `Quantum-L9/Cognitive.Engine.Graphs` main: `90a9863709537e4087646abf13d50830956df276`.
- `cryptoxdog/IB-Odoo_19` Staging: `0626d9493c877e5785ed7610c52d224fd7b738e6`.

## Inherited findings and risks: verify bindings before correction

These are observations recorded in the source pack, not fresh live checks by
this alignment revision. Preserve them as investigation inputs, then bind each
to its evaluated source before corrective work. A default-branch snapshot and a
hosted PR run are different evidence coordinates; the table below states where
the ZIP does not retain the full binding.

| ID | Priority | Affected owner and source | Observed reality | Required disposition and proof |
|---|---|---|---|---|
| T01 | P0 | CEG `.github/workflows/ci-quality.yml`, GitGuardian `secrets-scan` job | The hosted job on PR #508 emitted `Error: secret scan ci should only be used in a CI environment` and `GitGuardian container failed to start; skipping scan (infra)`, yet the job succeeded. A present masked key did NOT mean the scan succeeded. | Fix at CEG native workflow or reuse vetted owner mechanism, explicitly pass required CI detection context to container if demonstrated, and fail/label operational failure according to governed requiredness. Negative fixture missing CI environment and actual new-secret fixture must demonstrate failure. Record GitGuardian receipt or verified non-applicability, not success by warning. |
| T02 | P0 | CEG `.github/workflows/ci-quality.yml`, Codecov upload | On CEG PR #508 Codecov uploader said `Upload queued for processing failed: {"message":"Token required - not valid tokenless upload"}`. Action concluded success with `fail_ci_if_error: false` and empty `INPUT_CODECOV_TOKEN`. | Read Codecov account repository and auth policy; repair with authorized secret or authorized native OIDC/tokenless policy if supported. Require an accepted Codecov upload linked to exact commit/PR before claiming dashboard coverage. Auth/server failure must not count as coverage PASS. Do not place token in fork PR untrusted context. |
| T03 | P1 | CEG `l9-ci-core` required workflow on PR #508, `run-repository-verification` | SDK Semgrep technical gate passed, but required repository verification failed because `make test` exited 2. The product test `tests/unit/test_plasticos_buyer_identity.py` explicitly failed `G01 consumer proof is NOT_RUN: the sibling Odoo mapper is absent`. | Treat as a genuine product/integration proof gap, NOT Core or Semgrep false-red. Product owner determines safe integration fixture/environ or necessary authorized dependency. Never suppress expected test just to turn green. Preserve required gate. |
| T04 | P1 | Core `.github/workflows/security.yml` | Legacy v1 reusable workflow's `bandit` check uses `|| echo` (advisory despite a scanner error); `run-npm-audit` defaults false; Python detection conditional. Core required `org-ci.yml` currently has Semgrep and separately Biome, not proof that security.yml ran for every consumer. | Explicit per-profile applicability/requiredness and truthful outcome labeling. Use existing Core policy to choose advisory vs blocking; do not silently promote Bandit or npm-audit fleet-wide, and do not equate compatibility workflow with org-enforced coverage. |
| T05 | P1 | EIE `.github/workflows/gitleaks.yml` | Gitleaks SHA-pinned hard gate, but `dependabot[bot]` PRs skip scan with license isolation as the recorded rationale, relying on post-merge push scan. | Verify scope/exception authority, trigger/job/actor predicates and license availability. A safe authorized license path alone does not remove an unchanged skip; require actual Dependabot premerge execution or record the residual gap. Post-merge is not pre-merge. |
| T06 | P1 | EIE `.github/workflows/gitguardian.yml` | Token-absent path emits notice and skips scan, potentially green. Unlike CEG, sampled EIE PR #364 GitGuardian step actually executed successfully. | Keep good evidence; promote missing/expired token to clear `not_executed` or policy-refused state, not reported scan pass. Compare unique value and paid-seat/API limits vs Gitleaks. |
| T07 | P1 | CEG `.github/workflows/ci-quality.yml` | GitGuardian and Codecov failures are independent of aggregate `Quality Gate` success on sampled PR #508. Quality Gate combines job conclusions, not scanner-native proof. | Prove synthetic/real simulated failure paths cause aggregate status consistent with policy. Never use `needs.<job>.result=success` as proof that external service accepted upload or scan. |
| T08 | P1 | CEG `.github/workflows/supply-chain.yml` | `dependency-review` checks API availability and skips with warning when dependency graph unavailable. Hosted supply-chain workflow PR #508 passed; effective skipped-vs-executed review was not individually proven. | Produce status and API access receipt, preserve no-change contract; do not misrepresent skip as vulnerability-free. Validate actual dependency graph configuration. |
| T09 | P1 | EIE `.github/workflows/sonarcloud.yml` + Cursor `.github/workflows/sonarcloud.yml` | EIE PR #364 runs thousands of tests before native Sonar scan; Cursor PR #1067 ran 8,175 tests plus 22 more and Sonar and was green, while separate product test workflow also runs. Cursor PR #1062 proposes dispatch-only deep Sonar. | Reconcile PR #1062 and Core #281 before touching suite; generate coverage exactly once per relevant event/source, reuse authenticated exact-commit artifact where compatible; keep quality gate and prevent an unproven coverage gap. PR expense guard cannot declare fixture success a live receipt. |
| T10 | P1 | EIE `sonar-project.properties` + Odoo `sonar-project.properties`, `.sonarcloud.properties` | EIE declares `sonar.sources=app`, while coverage command measures `app` and `engine`; no top-level `engine/` in inspected EIE main tree. Odoo Staging currently excludes several active PlasticOS modules, with fix proposed in Odoo PR #552. | EIE: reconcile actual source roots, do not invent phantom engine/. Odoo: reconcile #552 exact head and prove live scanner scope. Avoid dual-run Sonar automatic + CI modes. See `CODEQL_SONAR_LEVERAGE.md`. |
| T11 | P2 | CEG `.github/workflows/ci-quality.yml` + other CI runners | CEG coverage job runs `pytest` independently to feed Codecov; EIE, Cursor likewise re-run tests in native Sonar jobs. | Inventory actual suite identity, head, coverage XML, trust, and costs. Reuse exact immutable artifact once only when provenance/security permit, not blindly across forks or revisions. |
| T12 | P2 | `.github` rendered Dependabot and consumer copies | Org `.github` owns `ops/render-dependabot.js` seed; EIE/CEG/Cursor have managed dependabot.yml. Core selects specific pinned tools; consumer ignores prevent unconstrained updates. Odoo Staging had no accessible `.github/dependabot.yml` in sampled tree. | Verify installed GitHub dependency alerts, version updates, ecosystem coverage, ignored major-only security fixes and auto-merge posture in UI. No blanket repinning or duplicate manager. Odoo outside Quantum-L9 org scope. |
| T13 | P2 | EIE `.github/workflows/perplexity-code-review.yml` | Separate LLM review path exists; scoped workflow trigger/paid provider usage and unique review value not established by file existence. | Audit actual dispatch history, cost, permissions, overlapping CodeRabbit/Copilot comments before deciding whether it earns runtime. Disable or retire only with explicit authorization and comparable review parity, never merely based on overlap. |
| T14 | Linked to T02 | CEG `.github/workflows/ci-quality.yml`, Codecov action | Supporting detail of T02: `fail_ci_if_error: false` and empty uploader token in the same observed run. | Share T02 owner, correction, priority and terminal receipt; do not count another defect or create another PR. Preserve explicit required/advisory/disabled policy and accepted-upload proof. |

T07 is the separate aggregate-outcome obligation dependent on T01/T02. T14 is
retained for traceability but consolidated into T02. T09/T11 share the coverage
reuse lane while retaining their distinct source/suite observations.

## Hosted evidence anchors

- CEG PR #508: https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/508
  - Quality Gates https://github.com/Quantum-L9/Cognitive.Engine.Graphs/actions/runs/44655221257; GitGuardian job 136019664092; Codecov job 136019663740; successful aggregate `Quality Gate` job 136022337648.
  - Required Core https://github.com/Quantum-L9/Cognitive.Engine.Graphs/actions/runs/44655221269; job 136019665966; Semgrep gate PASS but repo verification FAIL due explicit G01 NOT_RUN.
- EIE PR #364: https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/364
  - Gitleaks https://github.com/Quantum-L9/Enrichment.Inference.Engine/actions/runs/44640276422; GitGuardian https://github.com/Quantum-L9/Enrichment.Inference.Engine/actions/runs/44640276899; Supply Chain https://github.com/Quantum-L9/Enrichment.Inference.Engine/actions/runs/44640276323.
- Cursor-Governance PR #1067: https://github.com/Quantum-L9/Cursor-Governance/pull/1067; Sonar run https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44657558389; actual 8,175 passed/15 skipped/364 subtests and coverage XML, Sonar QG passed.
- Cursor-Governance PR #1062: https://github.com/Quantum-L9/Cursor-Governance/pull/1062 (unmerged at observed head `de0623e452ce179e85646b98eb387809794495e1`; must refresh).
- Core #281 and Odoo #552/#553/#556 are open PRs at earlier source review; refresh exact heads before relying on any outcome.

## Confidence and precedence

The ZIP retains pinned source snapshots and historical run/job links with
reported log observations. It does not retain raw logs or every run-to-source
binding. The reported CEG G01 failure remains a historical product-proof
observation, not a fresh diagnosis of current Core or product code. Do not
attribute a run to a later default-branch config/action revision merely because
the file has the same name. Rebind before implementation.

| Hosted evidence | PR/source-head coordinate retained in this ZIP | Evaluated/analyzed checkout | Resolved workflow/action revision |
|---|---|---|---|
| CEG #508 Quality Gates `44655221257` and Required Core `44655221269` | PR number retained; exact PR head UNKNOWN | UNKNOWN; retrieve run metadata and checkout logs | UNKNOWN; retrieve reusable workflow and action resolution |
| EIE #364 secrets/supply chain `44640276422`, `44640276899`, `44640276323` | PR number retained; exact PR head UNKNOWN | UNKNOWN | UNKNOWN |
| EIE #364 CodeQL `44640276188` and Sonar `44640276572` | PR number retained; exact PR head UNKNOWN | UNKNOWN | UNKNOWN |
| Cursor #1067 CodeQL `44657558641` and Sonar `44657558389` | `BASELINE.md` records PR head `483e53a56899630bd45fe5dd30d3256ead205bdd`; not proof of the analyzed checkout | UNKNOWN until per-run binding is recovered | UNKNOWN |
| Cursor #1062 CodeQL `44663728259` | Recorded PR snapshot `de0623e452ce179e85646b98eb387809794495e1`; do not infer every run used that head | UNKNOWN until per-run binding is recovered | UNKNOWN |

These Unknowns limit causal attribution and must be resolved for the affected
change/receipt; they do not erase the historical observations. This is a sample,
not a fleet census. Synthetic failure proof, current native dashboard receipts,
billing, ruleset enforcement, entitlement, monthly spend and current secrets
configuration remain UNKNOWN until the applicable execution-stage verification.

Vendor docs useful only as remediation candidates, not substitute runtime proof:
- GitGuardian `ggshield secret scan ci`: https://docs.gitguardian.com/ggshield-docs/reference/secret/scan/ci (CI context is required; failures and `--exit-zero` semantics must be reviewed).
- GitGuardian guide for earlier ggshield CI detection issue: https://docs.gitguardian.com/ggshield-docs/integrations/cicd-integrations/harness-ci (example of `CI=true` context fix, not direct proof for GitHub container).
- Codecov token policy: https://docs.codecov.com/docs/codecov-tokens (protected/private branch and organization settings determine token need).
