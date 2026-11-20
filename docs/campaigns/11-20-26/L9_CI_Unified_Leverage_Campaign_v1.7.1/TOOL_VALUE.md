> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

> **v1.6.0 live-source audit**: Read `OTHER_TOOLS_EVIDENCE.md`,
> `OTHER_TOOLS_EXECUTION.md` and `G0_OTHER_VENDOR_CHECK.md` before operating
> any other tool below. The previous general advice is subordinate to the
> recorded P0 false-green outcomes, actual product proof failure and owner
> write boundaries. No dashboard or paid-feature change during G0.

# Tool value and configuration mandate

## Goal

Maximize unique, actionable coverage from existing tools and paid entitlements
while minimizing duplicate findings, scanner latency, human review burden and
CI cost. Do not treat more alerts as more value. Configure tools at their actual
authoritative owners and verify on a real PR or default-branch run.

## Audit every active and paid tool

Collect: vendor; product/project identity; billing owner and actual tier;
paid seats / LOC / credits / run allowance if available; entitlement proof;
assigned repositories; analyzed source/branches; configured features; actual
run links and outcome; security findings and false positives; time and cost;
nearest overlapping tool; owner; next action; proof status and blockers.

Entitlement evidence must come from authenticated vendor/native account views
or authoritative contracts. A public repo workflow is not billing evidence.
Do not print secrets, expose vendor tokens or make external purchases.
If account access is missing, leave a focused proof request and continue other
independent work. Never mark paid optimization complete without this proof.

## Provider-specific value configuration

Vendor tier/feature examples below are inherited snapshot research, not current
rights or prices. Revalidate official terms and native account state at execution.
Use `HARVEST.md` for configuration-delta routing and upstream delivery proof;
this tool inventory does not transfer native ownership to Core/SDK.

### Semgrep

- Centralize portable rulepacks; preserve high-value custom rules and Odoo
  domain invariants. Compare SDK baseline/community, EIE/CEG generic rules,
  Cursor security rules and Odoo SQL/Odoo19/XML rules by detected behavior.
- Validate rules with both positive and negative tests and representative
  production files. Turn on supported taint/interfile features ONLY if the
  verified product/plan includes them and they materially improve findings.
- Record effective scanned paths and ignore reasons. Make new-code PR checks
  fast; retain comprehensive scheduled analysis. Preserve rule identity and
  explain advisory vs blocking at Core policy, not per-repo YAML.
- Pin executable AND rule contents; mutable remote registry names alone are
  not immutable security coverage evidence.

### CodeQL (preserve existing work)

**Mandatory native optimization checks:** `CODEQL_SONAR_LEVERAGE.md` is
source- and run-bound. Prove no silent success on GitHub language-API failure,
actual all-language participation, real PR+nightly scans, cache HIT for claimed
overlay acceleration, and unique actionable alerts. GitHub CodeQL is free
for public repos but private code scanning may require paid Code Security;
AI Scan/agentic fixes may consume additional AI credits. Do not default-enable
paid features.



- Treat merged Cursor-Governance PR #1067 and the existing reusable/native
  CodeQL architecture as an established baseline. Do not reconstruct it.
- Verify PR default suite, overnight security-extended, per-language build
  selection, overlay viability, native upload permissions, supported license
  features and cost. Confirm new CodeQL results are correlated with central
  policy/evidence; do not downgrade coverage or move write scopes to Core PR.
- Any genuinely missing feature should be a narrow follow-up to its current
  owner, not a large CodeQL refactor inside the CI consolidation.

### SonarQube Cloud / SonarCloud

**Mandatory paid-platform optimization checks:** inspect verified native
source coverage/exclusions, project subscription LOC, new-code Quality Gate
and profile, PR decoration, vulnerability and hotspot status, current-SHA
Cobertura import, and native `SONAR_TOKEN` access. Reuse product-owned coverage
instead of re-running deep tests in a scanner job where provenance allows.
Reconcile existing Cursor #1062 and Odoo #552 PRs. AI CodeFix may be available
on Team/Enterprise if activated; Advanced Security/SCA is an Enterprise add-on.
No subscription or external admin changes are authorized automatically.



- Confirm tier, project binding, automatic-vs-CI analysis mode, analyzed
  branch/PR, New Code definition, quality profile/gate, source exclusions,
  test and coverage ingestion, duplication, hotspots, PR decoration, and
  confirmed token presence without revealing the token.
- Treat Odoo #552 source-scope fix and Cursor-Governance #1062 Sonar trigger/
  PR-expense behavior as in-flight. Avoid adding unbounded paid scans to
  every PR. Include the actual add-on code, not phantom ignored roots.
- Optimize clean-code/new-code signals; reconcile duplicate rule findings
  with CodeQL and Semgrep without disabling a unique security gate.

### Secrets: Gitleaks and GitGuardian where deployed

- Inventory historical/full scan vs PR scan, token validity/scope, custom
  ignore allowlists and expiration, synthetic known-secret fixtures and alert
  delivery. Test a real valid entitlement and a known-bad detection.
- Establish which provides unique leak validation, historical coverage or
  remediation workflow. If both are retained, document the distinct job each
  performs. Never suppress a real secret merely to green a PR.

### CodeRabbit or other paid AI review

- Follow `CODERABBIT_ACTIVATION.md` for current evidence and a bounded owner-based activation sequence. The current repo snapshot shows inconsistent local inheritance and an Odoo #556 bot notice that automatic review was skipped for a less-than-10-stars repository. Reconcile entitlement, installation, activation, and actual review separately. Vendor config is not a Core/SDK scanner provider.

- Confirm paid entitlement and use, supported project review settings, PR
  scopes, context/rules, review volume, noisy repetitions, actual correctness
  discoveries and follow-up automation. Prevent duplicate comments already
  covered by required linters/scanners. Preserve independent architectural
  and domain-aware review where it finds defects scanners cannot.
- Do not count generated comments or review tokens as engineering value.

### Codecov or native coverage services

- Verify ingest from real test suites, exact revision and flags, patch coverage
  and trend thresholds, proper project filtering and retained artifacts.
- Prefer differentiated coverage gaps to duplicate tests or brittle global
  thresholds that do not reflect production risk. Capture actual service tier.

### Ruff, Biome, Mypy and type/format tools

- Core owns tool version; SDK should own eligible portable execution. Use
  centrally inherited lint/format defaults; preserve product-specific typing
  semantics, targets and documented exceptions. Make Ruff and Biome the
  noncompeting primary formatter for their supported language boundaries.
- Confirm lint/format/type checks actually run, files included, cache value,
  deterministic failure evidence, and no unnecessary duplicate local job.

### Dependency / supply-chain tooling

- Audit pip-audit, npm audit and any ACTUALLY INSTALLED SCA/SBOM/container
  scanners. Bind findings to real lockfiles, reachable artifacts and package
  resolution where supported. Document advisory/blocked vulnerability policy,
  exceptions with owner and expiration, freshness and incremental PR cost.
- Do not purchase or add Snyk/Trivy/other tools only to create nominal breadth.
  Identify unique missing coverage first.

### Tests and CI compute

- Product owns test selection. Preserve compile/schema/unit/integration and
  platform-specific checks; run only relevant tests fast on PR when scope is
  known. Unknown scope must not silently downgrade to zero tests.
- Confirm Core PR expense changes in #281 before changing scheduling. Use
  cache and parallelism only with reproducible clean-run proof; retain full
  trustworthy coverage on appropriate event profiles. Charge savings against
  observed runner minutes, not optimistic estimates.

## Value scorecard

For each tool, report measurable before/after whenever feasible:

1. Required coverage: applicable code and branches scanned / applicable code.
2. Unique verified high-severity findings, and percentage with actionable fix.
3. False-positive ratio and duplicate finding ratio relative to other tools.
4. Change detection latency, PR added wall time and CI runner minutes.
5. Paid consumption: actual bill/credits/seat utilization per period, when
   authenticated evidence exists; otherwise Unknown.
6. Cost per unique validated high-risk finding or prevented regression,
   labeled Unknown when denominator or attribution cannot be established.
7. Features entitled vs actually enabled; each beneficial unused feature
   gets an explicit action, owner and acceptance test.
8. Change-risk and rollback effect of promoting an existing advisory check.

Recommend keep / configure / consolidate / remove only when unique evidence
justifies it. Never erase a complementary signal solely because its cost is
visible and a competitor's is not.
