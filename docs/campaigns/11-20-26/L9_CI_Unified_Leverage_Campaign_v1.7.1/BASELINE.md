# Observed baseline and bounded unknowns

Source inspection date: 2026-11-19. These are input evidence, not tomorrow's
live target state. Recheck SHAs, PRs and native vendor settings at kickoff.

## Source revisions observed

- Organization authority `Quantum-L9/.github` main:
  `c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`
- Core `Quantum-L9/l9-ci-core` main:
  `3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437`
- SDK `Quantum-L9/l9-ci-sdk` main:
  `ab8a25543bf99de4c932f1930841a1e5f2ef2f27`
- Cursor-Governance main:
  `263216c13b5b4cac07f627675fb4f231e08317c8`
- EIE main:
  `29d4eb54942e446a9ac917d2ebe2d9733a4e7aec`
- CEG main:
  `90a9863709537e4087646abf13d50830956df276`
- Odoo Staging:
  `0626d9493c877e5785ed7610c52d224fd7b738e6`

## Existing architecture / primary evidence

### CodeQL and Sonar native-host evidence snapshot

- `CODEQL_SONAR_LEVERAGE.md` records the exact selected files, PR heads,
  hosted job IDs and native scan outcomes observed November 19-20, 2026.
- Cursor #1067 CodeQL run 44657558641: real upload; overlay cache MISS
  and fallback. Cursor #1067 Sonar run 44657558389: 8175 tests passed,
  coverage parsed and quality gate PASSED. This does not imply optimization.
- EIE #364 CodeQL run 44640276188 and Sonar run 44640276572:
  both completed; Sonar parsed Cobertura and gate PASSED; 3927 tests run
  in Sonar in addition to a separate repo-owned testing workflow.
- Cursor #1062 is OPEN, dispatch-only Sonar successor; a hosted `apply`
  result was not present on the inspected PR head. Odoo #552 is OPEN and
  addresses active production modules excluded by current Sonar scope.
- EIE `engine/` does not exist on inspected main (404), so its `--cov=engine`
  argument looks stale; this is not an omitted live `engine/` source claim.
- Vendor billing, effective Sonar dashboard mode, licensed Code Security
  features, active Sonar Advanced Security/SCA and dashboard project status
  are unverified without native account access.



- Central required workflow and no-copy activation:
  https://github.com/Quantum-L9/l9-ci-core/blob/main/docs/ACTIVATION.md
- Required organization ruleset source:
  https://github.com/Quantum-L9/.github/blob/main/rulesets/l9-canonical-ci-required.json
- Core owner split and source lock:
  https://github.com/Quantum-L9/l9-ci-core/blob/main/.l9/ownership.yaml
  https://github.com/Quantum-L9/l9-ci-core/blob/main/.github/actions/install-consumer-ci/toolchain-lock.json
- SDK provider boundary and capability detector:
  https://github.com/Quantum-L9/l9-ci-sdk/blob/main/AGENTS.md
  https://github.com/Quantum-L9/l9-ci-sdk/blob/main/l9_ci/capabilities/detector.py
- SDK Semgrep profiles:
  https://github.com/Quantum-L9/l9-ci-sdk/blob/main/l9_ci/rulesets/semgrep/profiles.yaml
- Cursor CodeQL reusable and config:
  https://github.com/Quantum-L9/Cursor-Governance/blob/main/.github/workflows/codeql-reusable.yml
  https://github.com/Quantum-L9/Cursor-Governance/blob/main/.github/codeql/codeql-config.yml
- Core has locked scanner versions (including Semgrep, Ruff, Mypy, Biome,
  Gitleaks, Bandit, pip-audit). Its org workflow runs Semgrep through SDK;
  currently Biome is Core-executed, while Ruff/Mypy/pytest are repo-executed.
  SDK `AGENTS.md` currently says Semgrep is its only active in-tree provider.
  Do not falsely report the other providers already integrated in SDK.
- Legacy Core `security.yml` has Gitleaks, Bandit, pip-audit and optional npm
  audit. It is not equivalent to the SDK Semgrep central gate.
- Cursor, EIE and CEG have separate CodeQL / Sonar or local analysis workflows.
  CEG includes Semgrep fixture tests and GitGuardian handling. Odoo runs
  custom Semgrep, legacy L9 analysis and separate secret scanning.
- Central current language selection is single-language; SDK capability model
  already observes multiple suffixes but integration must execute all required
  languages. Central Semgrep does not automatically include arbitrary consumer
  local .semgrep/ packs.

## Existing PRs observed

- `Cursor-Governance` #1067, merged, CodeQL default PR suite:
  https://github.com/Quantum-L9/Cursor-Governance/pull/1067
  Observed head `483e53a56899630bd45fe5dd30d3256ead205bdd`.
- `Cursor-Governance` #1062, OPEN, PR scope and Sonar gating:
  https://github.com/Quantum-L9/Cursor-Governance/pull/1062
  Observed head `de0623e452ce179e85646b98eb387809794495e1`.
- `l9-ci-core` #281, OPEN, PR expense guard:
  https://github.com/Quantum-L9/l9-ci-core/pull/281
  Observed head `faeeda6998214bf11353ebbdc7499984bf921533`.
- `IB-Odoo_19` #552, OPEN, Sonar effective source scope:
  https://github.com/cryptoxdog/IB-Odoo_19/pull/552
  Observed head `f47b61835e94ad304364cbda62a5c9c4756c8f76`.
- `IB-Odoo_19` #553, OPEN, Semgrep SQL/taint and fixtures:
  https://github.com/cryptoxdog/IB-Odoo_19/pull/553
  Observed head `6f310453ff7836c45fdcdadce273ee0730b49ed4`.
- `IB-Odoo_19` #556, OPEN, scanner-config PR-fast classification:
  https://github.com/cryptoxdog/IB-Odoo_19/pull/556
  Observed head `3edfddd11a5d57d238234198d8135adeb55a00e7`.

## CodeRabbit configuration evidence (source inspected 2026-11-19)

- `Quantum-L9/.github` has a rendered `.coderabbit.yaml` and accepted ADR-0020 establishing a native vendor `Quantum-L9/coderabbit` central repository design; the intended repo was not retrievable through current GitHub connection, so its existence, private access and CodeRabbit app installation remain UNKNOWN.
- Cursor main root contains no `.coderabbit.yaml`; sampled PRs #1062/#1067 have no `coderabbitai[bot]` actor. This is not exhaustive proof of installation state.
- EIE, CEG and l9-repo-template local `.coderabbit.yaml` lack `inheritance: true`; EIE excludes `docs/**` from CodeRabbit paths.
- Odoo Staging local YAML also lacks inheritance and includes `enable_free_tier: true`; PR #556 CodeRabbit bot posted that automatic review is skipped because the repo has fewer than 10 stars, despite YAML enabling auto review. `cryptoxdog` is a distinct GitHub owner.
- These are code and PR observations, NOT authenticated billing/plan/dashboard facts. See `CODERABBIT_ACTIVATION.md` for acceptance.

## Bounded donor evidence (source inspected 2026-11-19)

- Cursor custom Semgrep 4 IDs: `.semgrep/l9-pr.yml`, blob
  `8e7552457ddf4a0acd630bdae94141299a1172f4`. Three memory transport or
  spawning rules are local; the process token rule is a conditional candidate,
  **not** a universal rule by default.
- EIE custom Semgrep 8 IDs: `.semgrep/semgrep-rules.yaml`, blob
  `753352355f0cde213c7b0f6244523cc3411e5d26`.
- CEG custom Semgrep 8 IDs: `.semgrep/semgrep-rules.yaml`, blob
  `b770b980b741761194b6998e209b13042f49ad87`; singleton and float
  patterns are visibly more precise than their EIE counterparts, but migration
  still requires actual positive and negative fixture comparison.
- Odoo custom Semgrep 36 IDs: `.semgrep/odoo-patterns.yml`, blob
  `48de124ecb33a465da140c3cd08adb5607997bb5`. Distinguish portable
  Odoo 19 checks from product-specific PlasticOS checks and open #553 changes.
- The above is a **targeted donor shortlist**, not proof that no other repos
  have custom configs. A cheap path census discovers additional hits.

## Unknown / not attested here

- Complete historical run-to-checkout and reusable workflow/action bindings
  where not retained in the pack; see `OTHER_TOOLS_EVIDENCE.md`. Pinned default
  source snapshots cannot be substituted for actual hosted-run revisions.
- Current paid plans and activated vendor features for GitHub security,
  SonarQube Cloud, Semgrep, GitGuardian, CodeRabbit, Codecov or others.
- Actual line/seat/credit bills, vendor API tokens and connected project
  permissions. Do not ask operator to paste secrets.
- Validated GAR observer projection receipt and current canonical closure.
  Load through source-owner authority resolution before execution.
- Whether other scanner PRs open after this snapshot alter this campaign.
- Real fleet size and every repository's protected branch / effective ruleset.
- Whether `cryptoxdog` has permission to invoke a cross-owner central
  required workflow and whether its rulesets enforce it.
- Live tool-value baselines and before/after performance metrics.

These unknowns are explicit Stage 0 evidence requests, not authorizations to
change scope or silently report success.

## New invariant authority preflight (checked 2026-11-19)

- Canonical `semantics/invariants.yaml` registered by `semantics/canonical_sources.yaml` at
  `Quantum-L9/.github@c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`.
  Reused IDs are enumerated in `INVARIANTS.yaml`; no new global ID is asserted.
- `.github/policies/ORG_INVARIANTS.yaml` version 4.1.0 explicitly states
  `This revision is a candidate. It is not an owner admission.` Its
  apparent `policy_state: active` entries do not overturn that provenance.
  `Cursor-Governance/ORG_INVARIANTS.yaml` is marked a consumer mirror; do not
  independently mutate it or equate it with the constitutional source.
- Core proposed owner: `.l9/governance-contract.yaml` at
  `Quantum-L9/l9-ci-core@3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437`.
- SDK proposed owner: `.l9/integration-contract.yaml` at
  `Quantum-L9/l9-ci-sdk@ab8a25543bf99de4c932f1930841a1e5f2ef2f27`.
  SDK `INVARIANTS.md` already has INV-001..INV-014; retain these.
- The candidates propose new fields in existing repo-owned contracts. Their
  admissibility under current target validators is unknown until target PR
  tests execute; this pack does not claim those proposals merged or enforced.

## ADR source inventory, 2026-11-19 inspection

- Core's inspected Git tree at `3579bdc19a7f36973e4f0fe516ea5aa6c5ab9437` had **no** `docs/adr/` ledger. This campaign proposes two Core owner ADRs and a minimal index, rather than inventing a preexisting Core ADR number.
- SDK `docs/adr/README.md` lists ADRs through `0019-rule-precision-saas-and-usage-counts.md` at `ab8a25543bf99de4c932f1930841a1e5f2ef2f27`. SDK ADR 0005 defines provider SPI; ADR 0016 adopts centrally required organization CI; ADR 0017 cedes organization tool-version selection to Core and explicitly requires a new ADR if the SDK adds a Biome provider. SDK 0020 is an additive proposed decision, **not** an executable provider promotion.
- Global `.github/docs/adr/ADR-010-ownership-boundaries-no-recipes.md` is Accepted at the inspected pinned authority `c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`; it counsels against provider-specific or repository-specific global semantic recipes. The existing global invariants are reused by ID. No new constitutional ADR is justified for this CI implementation architecture.
- Proposed decision texts and effective source-owner targets are in `ADRS.md` / `candidates/adr/`; their compatibility and future acceptance need target-owner PR evaluation, not assertions from this ZIP.


## v1.6.0 other-tool evidence supplement

**Grounded sampled sources:** exact repos/SHAs and hosted PR run IDs appear in
`OTHER_TOOLS_EVIDENCE.md`. The CEG PR #508 `Quality Gates` job concluded success
although GitGuardian failed to start a valid `secret scan ci` in its Docker
context and Codecov rejected an unauthenticated upload. In the same PR, Core's
required verification failed on explicit `G01 consumer proof is NOT_RUN` because
Odoo mapper fixture absent. These are different concern owners and must not be
collapsed into a Semgrep failure. EIE PR #364 native GitGuardian/Gitleaks ran
successfully on the sampled PR, but EIE's Gitleaks Dependabot event skips.
Core v1 compatibility `security.yml` explicitly treats Bandit as advisory and
npm-audit as opt-in. All-fleet paid entitlements, actual vendor billing, source
coverage and full-fleet scan execution remain UNKNOWN without native proof.

## Live recheck, 2026-11-20 (v1.7.1)

Everything above is the 2026-11-19 snapshot and is kept as history. The current heads and pull-request
states are in `09_EXECUTION_BINDING.md`, "Live recheck". In short:

- Unchanged: `.github` `c788b991`, `l9-ci-core` `3579bdc1`, `l9-ci-sdk` `ab8a2554`.
- Moved: Cursor-Governance `main` `a95562c9`, EIE `main` `e1a61f78`, CEG `main` `b2150980`,
  IB-Odoo_19 `Staging` `341e45f4`.
- Merged since the snapshot: Cursor-Governance #1062; IB-Odoo_19 #552, #553, #556; CEG #508; EIE #364.
- Still open: `l9-ci-core` #281.
- Newly relevant open pull requests: CEG #514, EIE #365, `.github` #274, Cursor-Governance #1073.
- Odoo custom Semgrep is 39 rule IDs at blob `e92848dc`, not 36.
- The EIE, CEG and Cursor-Governance rule files are unchanged: blobs `75335235`, `b770b980`,
  `8e755245`.

Heads are rechecked again in the bootstrap sitting. A lane branches from the tip it fetches.
