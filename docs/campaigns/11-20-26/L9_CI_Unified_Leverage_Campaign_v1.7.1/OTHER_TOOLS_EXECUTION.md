# CTO/LCTO execution contract: scanner honesty, coverage reuse and paid-tool leverage

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

This is the **prewritten execution design** for the inherited tool findings in `OTHER_TOOLS_EVIDENCE.md`, subject to its source/run binding limits and current-source verification. It does not add a new canonical authority, another CI orchestrator, an alternate `make pr`, an assurance verdict source, or authorization to modify SaaS accounts. Preserve frozen architecture/ADRs/11 owner-specific invariants. Repository changes are PR-only by exact authorized write owner; native account changes follow G0 and applicable explicit authorization. G0's read-only activity does not block independent authorized engineering or its necessary validation.

## Phase A: prove present reality before edits (read-only; no new scans)

CTO must inventory every active/paid tool in this group, including: Semgrep, CodeQL, SonarQube Cloud, CodeRabbit, GitGuardian, Gitleaks, Codecov, Ruff, Mypy, Biome, Bandit, pip-audit/npm-audit, GitHub Dependabot/dependency graph/dependency-review, GitHub secret scanning if enabled, Syft/CycloneDX/SPDX SBOM, license checks, OpenSSF Scorecard, Trivy, and any other observed scanners/reviewers (e.g. Perplexity). **Absence in sampled source is not proof of absence in fleet.**

For each tool and scope, enumerate these evidence dimensions individually (never one green boolean):

1. Vendor/product + owner of policy, implementation and native account.
2. Feature/paid tier/consumed seats, usage quota, expected monthly charges (UNKNOWN until native account evidence).
3. Installation: GitHub App/secret/token and project connection, safe run permissions.
4. Event and trust: PR, merge, push, nightly, scheduled, forks; what really ran.
5. Source/material coverage: languages, manifests, lockfiles, Docker contexts, artifact roots, rulepacks, exclusions; how many relevant targets.
6. Native proof: exact PR SHA, run/job, invoked/failed/skipped, results received by vendor, scanner-native count, QG status, coverage artifact digest.
7. Outcome: candidate `EXECUTED_VERIFIED`, `EXECUTED_FAILED`, `NOT_EXECUTED`, `SKIPPED_BY_POLICY`, `UNKNOWN` (these are reporting labels only; NOT a new canonical state algebra).
8. Findings/ROI: actionable unique findings, false positives, overlap, remediation effort, total test minutes/scanner compute minutes, API charges.
9. Existing policy source and whether required/advisory/shadow/disabled. Never silently convert a setting.
10. Disposition: retain, repair, promote, consolidate after parity, retire after authorization, or blocked with owner/next proof.

One tool can have `workflow_conclusion=success` and `native_outcome=EXECUTED_FAILED`; this is exactly T01 and T02. The campaign must report both. The release evidence cannot erase the discrepancy.

## Phase B: bounded parallel owner lanes, no writes before independent owner/source inspection

### Lane F1, CEG source owner: secret scan and Codecov false greens (P0)

**Write owner:** `Quantum-L9/Cognitive.Engine.Graphs`; access to Core/SDK `.github` is read-only unless specifically authorized. Start with `.github/workflows/ci-quality.yml` and native run evidence from PR #508. Two separate PR concerns may run in parallel only on disjoint files/branches; otherwise use one bounded PR.

- **T01 GitGuardian**: bind the exact container/version and inspect both CI-context propagation and the wrapper's error classification. The inherited run records `secret scan ci should only be used in a CI environment` with a masked API key present; a missing key is not the supported diagnosis. Prove clean scan, missing CI context, unavailable scanner, successful container pull followed by scanner failure, and detected synthetic test secret. Preserve the native outcome through wrapper and aggregate. The ZIP does not preserve the exact catch implementation; rebind it before attributing a specific mechanism. Honor existing required/advisory mode; no generic catch, exit-zero or warning may impersonate execution.
- **T02 Codecov (including T14)**: operator/vendor account check for connected project and acceptable auth method. Existing `fail_ci_if_error: false` means failed upload can return success; fix native upload path and provenance, or explicitly record Codecov disabled/advisory while preserving local test coverage. Do not invent `CODECOV_TOKEN` value, change global public token requirement, or enable a paid tier without operator action. Actual vendor-accepted upload at exact PR SHA, coupled to existing test artifact, is mandatory before claiming Codecov value. T14 is supporting detail of this defect and uses the same correction and closure receipt; it requires no duplicate PR.
- **T07 false green**: CEG `quality-gate` aggregate currently treats both jobs as successful despite native exceptions. Preserve distinct technical outcomes; require a fixture that a failed/unauthorized native result cannot be marked as an executed control. No new global status primitive.
- **T03 exception**: do NOT suppress CEG G01 or treat green Semgrep as green required CI. Resolve at CEG integration proof owner, or record blocked when sibling Odoo proof cannot run; test matrix needs a real proof environment or a clear valid unavailable outcome, not a modified PASS assertion.

### Lane F2, native secrets/supply-chain owners (read, then bounded candidates)

**Source owners:** EIE, CEG, Cursor and Core individually; no single cross-repo bulk fix. Preserve EIE's Gitleaks hard-gate success and both scanners' distinct strengths until benefit/coverage evidence resolves redundancy.

- **T04**: Core v1 compatibility `security.yml` has advisory Bandit and npm audit opt-in false. Confirm whether actually used by org required workflow and whether omitted tool categories are detected by SDK. Do not rewrite accepted migration semantics because a scanner is capable of failing. Report actual coverage denominator and requiredness per profile.
- **T05**: EIE Dependabot-triggered Gitleaks skips with license isolation as its recorded rationale; current cause and exception authority need verification. Inspect trigger/job/actor skip predicates and vendor/app license behavior on a hosted Dependabot PR. An available license alone cannot make an unchanged skip path execute. Choose an authorized, proven premerge path or explicit approved residual exception. Post-merge scanning does not close premerge risk.
- **T06**: EIE GitGuardian skipped-with-notice path exists, although sampled native scan succeeded. Test missing/expired token and API failure; ensure outcome never claims execution when skipped. Retain independent value only when justified by unique incidents or central scanning needs.
- **T08**: CEG dependency-review can skip for unavailable dependency graph. Inspect actual GitHub feature availability, upload state and vendor-native result. An unavailable graph must be visible and must not count as a clean dependency review.
- **T12**: Dependabot org-seeded file is already managed by `.github`. Identify alerts and open PR capability; discover missing ecosystems/major-only vulnerabilities. Never duplicate `dependabot.yml` generation in Core or SDK, repin Core-owned tools from consumers, or silently auto-merge security dependencies.
- **Supply chain**: align SBOM file scope to actually locked dependencies/images, provenance/digest, source commit, exported SPDX/CycloneDX format, artifact retention, and license policy at existing owner. Do not install a second SBOM generator just to increase provider count.

### Lane F3, quality, tests and AI reviewers (cost-first)

**Owners:** native consumer test suites and vendor review integrations. Core owns scheduling/profiles. SDK owns normalizers/adapters only if contractually supported. No new orchestration plane.

- **T09/T11**: consolidate repeat test executions only after comparing exact tests and immutable coverage artifact provenance. Cursor PR #1062 may eliminate PR deep suite; Core #281 may enforce PR cost budget. Reuse those changes, do not duplicate. Sonar native can run lighter with trusted same-commit coverage report if its semantics accept it. A coverage upload that fails is not test failure, and a passing test suite is not a coverage upload receipt.
- **T10**: inspect actual source roots, ignored code, and exclusions. EIE `sonar.sources=app` is not automatically wrong: the top-level `engine/` directory was absent at sampled main; `--cov=engine` may refer to import module or outdated target. Prove actual scan file list before editing. Odoo #552 proposes material source scope correction; don't independently redo it.
- **CEG quality**: Mypy command uses `--ignore-missing-imports --exclude chassis`; document whether intentional, unused, or a real type-check blind spot with representative fixtures before broadening. Codecov's result must not be confused with local pytest PASS.
- **T13**: audit EIE Perplexity paid review, CodeRabbit, Copilot reviewers for real PR execution, decision quality, latency, cost and overlap. Reuse existing `CODERABBIT_ACTIVATION.md`. If no unique value, propose retirement as a separate authorized provider change, not hidden CI cleanup.
- **Actions hygiene**: minimize broad workflow-level permissions, record stale action runtimes, pin issuer/third-party SHA at owning source; no vendor token on untrusted fork PR. Central `l9-ci-core` remains the version owner for its provider/toolchain.

## Phase C: integration and rollout, constrained by existing campaign gates

1. Source-owner PRs may be built in parallel if truly disjoint; don't assume branch, Make targets or publication command from docs. Verify Cursor-Governance `make pr` SSOT current source before publication and follow existing campaign permission constraints.
2. `CURSOR_CANARY_PASS` remains mandatory first central Core/SDK live consumer proof. It is not replaced by CEG or EIE remediation. Separate positive/negative scanner fixtures and native CI receipts are required.
3. Source-owner false-green fixes can precede canary when independent. No fleet rollout or consumer scanner deletion until parity and first canary.
4. PR-fast must not run deep duplicate suites; any proposed performance improvement supplies old and new duration/run counts and preserves quality/security evidence.
5. Native account/billing changes: operator-guided G0 and separate approval. Missing entitlement blocks the specific activation, not all source owner PRs.
6. End with `KEEP / FIX / PROMOTE / CONSOLIDATE / RETIRE_CANDIDATE / BLOCKED` matrix by tool, exact owner, current outcome, proof URL and next owner action. Existence of an integration is not success; a passing workflow is not an accepted scan.

Feed every reusable rule/config delta and its owner change into the shared
`HARVEST.md` ledger. F1/F2/F3 and campaign Lanes 1/2/3 are concern groupings,
not permission for parallel writers to the same repo/file set. T07's aggregate
proof depends on T01/T02 outcomes; T14 closes with T02. All T01-T14 IDs remain
traceable to an explicit terminal disposition.

## Non-goals and guardrails

No bulk 60-repo configuration rewrite, no new marketplace purchases or renewals, no experimental paid-tier feature toggle, no disabled required checks, no unilateral merge, no scanner auto-fix commit to main, no blanket `continue-on-error`, no secrets disclosure, no vendor admin mutations based solely on this campaign. Domain-specific rules stay with their source owners. Native CodeQL advanced/default setup and two-suite architecture stay intact unless actual proof reveals a strictly scoped defect.
