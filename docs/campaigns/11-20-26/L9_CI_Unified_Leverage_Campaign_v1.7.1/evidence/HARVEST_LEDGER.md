# Harvest ledger (Stage 0H)

Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`. Single writer: the CTO session (`09_EXECUTION_BINDING.md:155-156`).
Dispositions follow `HARVEST.md`. A disposition here admits nothing and retires nothing. Retirement of a
consumer copy waits for the promoted successor plus a parity receipt on that consumer's canary.

## Sources

Read-only census on 2026-11-20 by four CTO research agents, one per donor, against:

| Repository | Ref | Head |
|---|---|---|
| Quantum-L9/Cursor-Governance | main | `605bb681` |
| Quantum-L9/Enrichment.Inference.Engine | main | `8f46df4d` |
| Quantum-L9/Cognitive.Engine.Graphs | main | `e66fa5ef` |
| cryptoxdog/IB-Odoo_19 | Staging | `25fd3282` |
| Quantum-L9/l9-ci-core (comparison) | main | `75a521f8` |
| Quantum-L9/l9-ci-sdk (comparison) | main | `015db807` |

Semgrep rules are ledgered separately in SDK `docs/harvest/semgrep-donor-ledger.yaml` (59 rows: 6 promoted
into SDK `python-portable` as 4 rules, 8 already satisfied, 14 retain_domain, 31 defer_unknown). This
ledger covers everything else: workflows, gates, scripts, hooks, coverage and lint configuration.

Runtimes are job wall-clock from one sampled run per repository and are indicative only.

## Per-PR cost today (indicative)

| Repository | Local CI per PR | `Analyze (central Core)` | Duplicated by Core or inside the repo |
|---|---|---|---|
| EIE | 37 jobs, about 707 s | about 120 s | about 185 s duplicates Core; gitleaks runs 3 times, dependency-review 3 times, constitution verify 3 times |
| CEG | about 30 jobs, about 413 s (PR) / 605 s (main) | 166 s | ruff, format and mypy run 5 times; contract_scanner 4 times; Scorecard, SBOM and dependency-review twice each |
| IB-Odoo_19 | 6 parallel jobs, about 3 min | not run (user-owned repository, outside org rulesets) | gitleaks, Actions pin checks and `l9-analysis.yml` duplicate Core |
| Cursor-Governance | 5 required local checks plus supply chain, CodeQL and others | runs `make setup validate check test` | ruff, format and uv-lock duplicate Core repo-check |

## Row completeness

This is the Stage 0H index: one row per distinct promotion candidate, with donor, disposition, target
and state. Rows C1 to C5, promoted during this campaign, carry the full `HARVEST.md` fields and a
delivery receipt in "Promoted rows" below (re-bound 2026-11-21 against Core `main` `4aa7f2b`). Every
other row is backlog for the rollout campaign: its index disposition stands, and its remaining
`HARVEST.md` fields (donor path and blob SHA, behaviour and scope, good/bad and non-target witnesses,
delivery reference and admission, retirement and rollback) are **Unknown** until its owner lane picks it
up and fills them in this file, in the same PR as the delivery, before promotion. No consumer copy is
retired from a row that lacks a parity receipt. Census evidence (file and line) for the backlog rows is
in the four census reports summarized in the CTO session transcript of 2026-11-20 and is re-bound by
the owner lane at its head.

## Promotions, grouped by upstream owner

### Core (`Quantum-L9/l9-ci-core`), lane L2

| # | Component | Donors | Disposition | Target | State |
|---|---|---|---|---|---|
| C1 | Consumer security scans (gitleaks, pip-audit, bandit advisory). Core `security.yml` is `workflow_call`-only and only Core calls it, so no consumer CI runs it | all four (each carries its own copy; CG has none in CI) | promote_global | `org-ci.yml` calls `security.yml` for consumers | Step one merged (Core #298); step two open (Core #312). Full fields below |
| C2 | Toolchain alignment check made blocking (advisory today at `org-ci.yml:348-350`); per-repo guards drift | CEG `tests/unit/test_core_toolchain_pins.py` (stale), all repos drift | promote_global | Core `check-toolchain-alignment` | Delivered advisory (Core #295, #302; operator: advisory, not blocking). Full fields below |
| C3 | Conflict-marker scan | CG `l9-lint-test.yml:173-189` | promote_global | repository verification step | Delivered (Core #300). Full fields below |
| C4 | Nightly deep dispatch for consumers; CG missing from `deep-entrypoints.json`; apply closed | CG `sonarcloud.yml`, EIE deep plan, CEG deep plan, IB nightly | promote_global (scheduling) | `deep-entrypoints.json` + apply step | Merged (Core #290, #299); not effective until the App is installed and an apply run dispatches. Full fields below |
| C5 | Supply-chain lane: dependency-review, licence allow/deny, SBOM, GPL/AGPL audit | CG, CEG, EIE (divergent copies) | promote_global (mechanism); exemptions retain_domain | Core `supply_chain` event class | Step one merged (Core #304, #309); consumer wiring not on Core `main`. Full fields below |
| C6 | Fail-slow parallel tiers with one fail-closed aggregator | IB `ci.yml:431-455`, CEG quality-gate | promote_global | org-ci consumer fan-in | Candidate |
| C7 | PR changed-scope selector (Core already refuses PR full-suite fallback and fails `PR_SCOPE_UNKNOWN`, but has no selector) | IB `ci/pr_fast_scope.py`, CG Test Suite scope job | promote_global (contract) + promote_language (Python AST selector) | Core contract, SDK selector | Candidate; IB code needs licence grant |
| C8 | Change-policy companion rules and select-gates engine exposed to consumers (exists Core-local in `tools/l9_repo/change_policy.py`) | EIE constitution gate, EIE contract control, C-13 lockstep | promote_global | Core consumer contract (needs a Core ADR) | Candidate |
| C9 | Contract-manifest reference checker (`verify_contracts`) vs Core `contract_wiring.py` | CEG, EIE (same tool) | promote_global (engine); manifests retain_domain | Core consumer contract | Candidate; equivalence UNKNOWN |
| C10 | Coverage-floor requiredness (C-15 71% runs only in an unscheduled deep plan) | EIE, CEG | promote_global (requiredness); value retain_domain | Core governance defaults | Candidate |
| C11 | `uv lock --check` and lock-integrity test | CEG `test_uv_lock.py`, EIE sdk-channel | promote_language | Core python profile | Candidate |
| C12 | Root-file append-only validator (stdlib only, config-driven) | CG, IB has a config | promote_global | Core action or org-ci step | Candidate |
| C13 | Workflow-integrity lint for consumers (Core `check_workflow_integrity.py` runs on Core only); catches false greens such as EIE docs-sync's subshell counter and `\|\| echo` fail-opens | EIE `tests/ci`, CEG `check_action_refs.py`, IB Actions kernel, CG pin validator | promote_global; local copies retire_duplicate | Core consumer step, or SDK `l9-yaml-governance.yml` | Candidate |
| C14 | Scan truthfulness (EXECUTED_CLEAN / FINDINGS / FAILED / NOT_EXECUTED; preflight before claiming a scan) | EIE gitleaks/GitGuardian, CEG `tools/scanner_outcomes.py` | promote_global | Core security.yml (partial today) + SDK evidence contracts | Candidate |
| C15 | Test classifying-marker guard (`-m unit` cannot silently drop tests) and "at least one test passed" guard | CEG `tests/conftest.py:122-150`, EIE Repo.mk JUnit check | promote_language | Core repo-test contract | Candidate |

### SDK (`Quantum-L9/l9-ci-sdk`), lane L1

| # | Component | Donors | Disposition | Target | State |
|---|---|---|---|---|---|
| S1a | Odoo 19 XML deprecations (`<tree>`, `attrs=`, `states=`, `t-esc`, search `string=`, decoration-secondary, alert role, `active_id`) | IB `ci/check_odoo19_xml.py` (+ `ci/test_check_odoo19_xml.py`), `scripts/check_odoo_patterns.sh` #12-#16, #19, #20 | promote_framework | SDK Odoo framework pack (none exists: `packs.yaml:25-26`) | Blocked: licence grant or clean-room rewrite |
| S1b | Odoo 19 hook writes (`groups_id` / users in hooks) | IB `ci/check_odoo19_hooks.py` | promote_framework | SDK Odoo pack | Blocked: licence |
| S1c | Removed decorators and depends (`@api.one`/`@api.multi`, `@api.depends("id")`), `env.get` misuse, empty `__init__`, cron `numbercall`, `res.groups` `category_id`, unescaped `&`, nested eval quotes, icon without title | IB `scripts/check_odoo_patterns.sh` #2-#7, #11, #21, #24 | promote_framework | SDK Odoo pack | Blocked: licence |
| S1d | Module dependency graph: circular deps, XML ref module declared in depends | IB `ci/check_circular_deps.py`, `ci/check_xml_module_ref_deps.py` | promote_framework | SDK Odoo pack | Blocked: licence |
| S1e | Model integrity: orphan model refs, ACL completeness, package `__init__` integrity | IB `ci/check_orphan_model_refs.py`, `ci/check_acl_completeness.py`, `ci/check_package_init.py` | promote_framework | SDK Odoo pack | Blocked: licence |
| S1f | Cron advisory-lock pairing (CRON1xx/2xx; CRON3xx stays domain) | IB `tools/cron_invariant_check.py` (pre-commit only, not in CI) | promote_framework | SDK Odoo pack | Blocked: licence; also not yet in IB CI |
| S2 | Neo4j/Cypher interpolation lint (AST classifier; sanitizer and sink names externalized) | CEG `tools/cypher_lint.py` | promote_framework | SDK framework pack | Candidate |
| S3 | Contract-ID rule-table scanner engine | CEG `tools/contract_scanner.py` (rules retain_domain; SEC/ERR generic rules promote_language) | promote_global (engine) | SDK provider | Candidate |
| S4 | Finding tier policy (unknown HIGH fails closed; touched vs inherited; reasoned review markers) | EIE `tools/audit_engine.py` | promote_global | SDK baseline comparator + gate evaluator | Candidate |
| S5 | Baseline fingerprint ratchet | IB `scripts/audit/baseline_utils.py` | already_satisfied (SDK `l9_ci/baseline` is stronger); IB copy retire_duplicate after an adapter | — | No promotion needed |

### `Quantum-L9/.github`

| # | Component | Donors | Disposition | State |
|---|---|---|---|---|
| G1 | PR size gate | CEG, EIE (`setFailed` removed there, so advisory) | promote_global to `governance-pr` gates | Candidate |
| G2 | Markdown link check | CEG docs-code-sync, EIE docs-sync (false green) | promote_global | Candidate |
| G3 | Branch hygiene report | CG | promote_global | Candidate |
| G4 | Release drafter | CEG, EIE | promote_global (low) | Candidate |

### Stays with its owner (retain_domain), recorded so it is not lost at cutover

CG: governance-self-check, repo-hygiene rules, root-file protection data, memory cross-repo proof,
Claude preservation, identity and projection verification, `make pr` ceremony, overlap check, PR body
composer, CodeQL reusable owner (HARVEST:36). EIE: payload contract compiler, KB schema, C-13 file set,
coverage value 71, Sonar keys. CEG: audit harness (boundary doc), DomainSpec and design-pack validation,
FILE_REGISTRY, 24 contract rule tables, deep-plan suite. IB-Odoo_19: PlasticOS checks (naming,
no-local-intelligence, BAN001, state guard, dev-tools fence), Odoo runtime gates (install-smoke,
test-env fixture; need Enterprise and Docker).

## Promoted rows: full `HARVEST.md` fields (C1 to C5)

Re-bound 2026-11-21, about 07:50Z, by lane HARVEST-FIELDS (X7). Each Core claim below was checked against
the merged Core commit (message and diff) on Core `main` `4aa7f2b` (#325). The org-ci actions pin
`284a5eb6f55828ab37f992c783aa3ed2273f3213` (#323) contains every merge cited here (`git merge-base
--is-ancestor`). The consumer run receipt is Cursor-Governance PR #1112, head `6ef0ae35`,
[run 44876362790 / job 136761824478](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44876362790/job/136761824478),
`Analyze (central Core)` at actions `284a5eb6`. "Merged" means the Core PR is on Core `main`;
"effective" means org-ci delivers it to consumers at its current pin; "observed" means a consumer run
shows it. These are different states and are recorded separately. EIE (`8f46df4d`) and IB-Odoo_19
(`25fd3282`) donor paths were not re-bound in this lane: their blob SHAs are Unknown (owner: the
rollout campaign; next proof: `git rev-parse <head>:<path>` at the census head).

### C1: consumer security scans

| Field | Value |
|---|---|
| Donor | CEG `main` `e66fa5ef`, `.github/workflows/ci.yml` blob `afdae3e3` job `security` (gitleaks CLI over PR and push ranges with `.gitleaks.toml` blob `740ad2d9`; `pip-audit --desc \|\| echo`, so non-blocking; bandit; dependency-review). Cursor-Governance `605bb681`: none in CI, only `ops/scripts/run_pr_security.sh` inside `make pr`. EIE and IB-Odoo_19 copies: path and blob Unknown |
| Behavior | Core `security.yml` (#298): gitleaks applies a repository `.gitleaks.toml` on top of the Core preset rules (a runtime copy gains `useDefault = true` when the config has no `[extend]`; an `[extend]` path, or a config that drops the defaults, is refused rather than scanned with fewer rules); event scope is base..head for a pull request or merge group, before..after for a push, otherwise full history, and an unresolvable range is refused before the scan; pip-audit audits `requirements.txt` or the `pyproject.toml` project, not the runner; bandit is advisory when a Python project is detected. Events: pull request, merge group, push. Languages: any (gitleaks), Python (pip-audit, bandit) |
| Ownership | Semantic owner Core. Source: `Quantum-L9/l9-ci-core/.github/workflows/security.yml`. Requiredness: org-ci `security` job enforced inside the required `Analyze (central Core)` context (#312). Consumer allowlists in `.gitleaks.toml` stay with the consumer (retain_domain) |
| Evidence | Core `tests/workflows/test_security_consumer_scope.py` (+317 lines in #298) covers event ranges, config extension and refusal; Core runs it on itself (`self-security.yml`). Consumer good/bad witness: **Unknown**, since no consumer runs it until #312 merges (next proof: a planted secret failing `Analyze (central Core)` on a canary PR, and a clean PR passing) |
| Disposition | promote_global |
| Delivery | Step one: Core #298, merged `14396e9` (2026-11-20 23:24Z). Step two: Core #312, open, head `ef108215`; it adds the org-ci `security` job pinned at `security.yml@14396e9` and an `Enforce security scan (secrets, dependency audit)` step in the required job. Effective: **not yet**, because org-ci on Core `main` `4aa7f2b` has no consumer security job. Observed: none |
| Retirement and recovery | No consumer copy is eligible. CEG's `security` job stays until #312 merges and a CEG run shows parity (secret found, clean pass). Rollback scope after #312: the org-ci `security` job and its enforce step; known-good is org-ci at Core `main` `4aa7f2b` |

### C2: toolchain alignment

| Field | Value |
|---|---|
| Donor | CEG `e66fa5ef`, `tests/unit/test_core_toolchain_pins.py` blob `ae93a287` (a hand-kept list of Core tools, stale against Core's lock). Every repository's own local pins (OPEN_ITEMS T48) |
| Behavior | Core `check-toolchain-alignment` (#295) reads every declaration surface (`requires-python`, `.python-version`, workflow `python-version` / `PYTHON_VERSION`, workflow `pip install` pins, `setup-uv` / `UV_VERSION`, gitleaks versions including a shell `GITLEAKS_VERSION=`, nested `*requirements*.txt` and `*-bootstrap.txt`) against `install-consumer-ci/toolchain-lock.json`; a `requires-python` that admits an older minor is drift. org-ci (#302) reports each drifting declaration as a `file:line` warning plus a summary line and never fails the job. Events: every org-ci event; all consumers |
| Ownership | Core: `.github/actions/check-toolchain-alignment`, the lock above, and the org-ci steps `Report toolchain alignment (advisory)` and `Report toolchain alignment drift (advisory)` |
| Evidence | Core `tests/governance/test_core_toolchain_alignment.py` (Core scans itself) and `tests/workflows/test_org_ci_toolchain_drift_report.py`. Real consumer: the receipt run logs `check-toolchain-alignment: aligned (41 declaration(s))` and `Toolchain drift (advisory): aligned, 0 declaration(s)`. Drift witness on a consumer: **Unknown** (no drifting consumer run observed in this lane) |
| Disposition | promote_global, delivered **advisory**. The index target "made blocking" was superseded by the operator decision of 2026-11-20 about 22:20Z (OPEN_ITEMS: housekeeping never blocks); #302's first commit made it blocking and its second made it advisory |
| Delivery | Core #295 merged `8667d53` (2026-11-20 22:09Z); Core #302 merged `b8d3e31` (2026-11-21 01:35Z). Effective at actions pin `284a5eb6`. Observed on Cursor-Governance in the receipt run. Consumer-side: CEG #524 (`ci/align-core-toolchain-lock`, head `46665232`, open, ready to merge) replaces CEG's hand list with `scripts/check_core_toolchain.py`, which reads Core's `core-owned-tools.json` and lock |
| Retirement and recovery | CEG's hand list goes with CEG #524 (not yet merged). Other repositories' local guards: Unknown, rollout campaign. Rollback: a dedicated Core revert of #295 and #302, released through the usual two-step pin advance (Core AGENTS.md §16) and validated by Core's alignment tests and one consumer `Analyze (central Core)` run. Moving the shared actions pin back before `8667d53` would also drop C3 and C5, so it is not the rollback. The check is advisory, so no merge outcome depends on it |

### C3: conflict-marker scan

| Field | Value |
|---|---|
| Donor | Cursor-Governance `605bb681`, `.github/workflows/l9-lint-test.yml` blob `cd04a29a`, lines 173-189 (`git grep -E '^(<<<<<<<\|=======$\|>>>>>>>)'` with archive and reports excludes; a push tripwire, not a merge blocker) |
| Behavior | Core `run-repository-verification` (#300) scans tracked text files for git's complete conflict block (`<<<<<<<`, an optional diff3 `\|\|\|\|\|\|\|`, `=======`, `>>>>>>>`, at column 0) before any contract decision and records a contract failure in both modes, with or without a contract. A lone `=======` or an indented sample is not reported; binary files and `.l9/runtime` are not scanned; an unreadable file list is an infrastructure failure, never clean. Blocking (it protects working code). Events: every org-ci event |
| Ownership | Core: `.github/actions/run-repository-verification/run.py` |
| Evidence | Core `tests/repo_execution/test_repository_verification_conflict_markers.py` (+157 lines) holds the good/bad cases; #300 records clean runs on Core, Cursor-Governance, CEG, EIE, IB-Odoo_19 and `.github`. Receipt run: `run-repository-verification@284a5eb6` executed on Cursor-Governance and passed. Non-target: unlike the donor's grep, a lone `=======` line no longer fires. Consumer known-bad: **Unknown** (none planted on a consumer) |
| Disposition | promote_global |
| Delivery | Core #300 merged `7e11e2b` (2026-11-21 01:35Z). Effective at actions pin `284a5eb6`. Observed on Cursor-Governance in the receipt run |
| Retirement and recovery | Cursor-Governance's `l9-lint-test.yml` step is eligible only after a parity receipt (a planted conflict block failing `Analyze (central Core)`); owner CG-CUTOVER. Rollback: a dedicated Core revert of #300, released through the two-step pin advance and validated by `test_repository_verification_conflict_markers.py` and one consumer run; the shared actions pin is not moved back, since that would drop C2 and C5 |

### C4: nightly deep dispatch

| Field | Value |
|---|---|
| Donor | Cursor-Governance `605bb681`, `.github/workflows/sonarcloud.yml` blob `85dc4dc4` (no scheduler, OPEN_ITEMS T15); CEG `e66fa5ef`, `.github/workflows/deep-plan.yml` blob `b3d00c38`; EIE `.github/workflows/ci.yml` and IB-Odoo_19 nightly: blob Unknown |
| Behavior | Core #290: the nightly plan reads the committed registry projection and `.github/nightly/deep-entrypoints.json` (no network); `nightly-deep.yml` skips when `main`'s HEAD already has a successful scheduled run; `tools/nightly_apply.py` dispatches ELIGIBLE entrypoints with a bounded `nd1-` dispatch key, once per change. Core #299: `org-nightly-dispatch.yml` gains an apply job (schedule, or dispatch with `mode=apply`) that mints an `l9-nightly-dispatch` App installation token (`actions:write`, `contents:read`, admitted repositories only; never a PAT), and admits Cursor-Governance's `sonarcloud.yml` (`cursor-governance-deep/v1`, scheduling `dispatch`) beside CEG `deep-plan.yml` and EIE `ci.yml` |
| Ownership | Core: `org-nightly-dispatch.yml`, `tools/nightly_dispatch.py`, `tools/nightly_apply.py`, `.github/nightly/deep-entrypoints.json`, `docs/nightly-deep-consumer-contract.md`. Native: the GitHub App installation (operator). Consumers own their deep workflows (retain_domain) |
| Evidence | Core `tests/workflows/test_nightly_apply.py` ("exactly the dispatch workflow opens apply, with an App-minted token, never a PAT") and `test_org_nightly_dispatch.py`. Real dispatch: **none observed**. Cursor-Governance `sonarcloud.yml` runs (REST, 2026-11-21 about 07:50Z) are all `pull_request`, latest 44772875111 on 2026-11-20 16:23Z; no `workflow_dispatch` run exists. #299 records that Cursor-Governance's run-name does not yet follow the contract |
| Disposition | promote_global (scheduling) |
| Delivery | Core #290 merged `9830f9d` (2026-11-20 19:48Z); Core #299 merged `8584d13` (2026-11-20 22:44Z). Effective: **not yet**. The code is merged on Core `main`, but without the App installation the apply job cannot dispatch any consumer entrypoint. Pending: the App installation and a first successful apply run. Next proof: a `workflow_dispatch` run of Cursor-Governance `sonarcloud.yml` carrying an `nd1-` key from Core's apply job (OPEN_ITEMS T15, X4) |
| Retirement and recovery | Nothing retires on Cursor-Governance, which has no schedule. CEG and EIE scheduled CodeQL and supply-chain runs retire only after `CURSOR_CANARY_PASS` and a per-consumer receipt (the consumer contract). Rollback: remove the apply job, or withhold the App token; the plan stays credential-free |

### C5: supply-chain lane

| Field | Value |
|---|---|
| Donor | Cursor-Governance `605bb681`, `.github/workflows/supply-chain.yml` blob `80349462`; CEG `e66fa5ef`, `.github/workflows/supply-chain.yml` blob `6d6aec9b` plus the `ci.yml` (blob `afdae3e3`) dependency-review and `sbom` jobs; EIE copy: blob Unknown |
| Behavior | Core `run-supply-chain` (#304): on a pull request it runs only when a dependency file changes (change set `HEAD^1..HEAD` of the merge commit, no event value reaches git), and always on schedule, dispatch and push; it runs dependency review (PR), installs the locked runtime dependencies into an isolated environment, writes a CycloneDX SBOM with Syft, and judges every licence against Core `default-policy.json` plus an optional consumer `.l9/supply-chain-policy.json`. #309 adds Core-owned `repositories/<owner>__<name>.json`, merged additively; every exemption carries a reason; a Core-denied licence stays denied. Denied or not-allowed fails; undetermined is reported; an empty SBOM fails closed |
| Ownership | Core: `.github/actions/run-supply-chain/` (`action.yml`, `supply_chain.py`, `default-policy.json`, `repositories/*.json`). Exemptions are retain_domain data held by Core: Cursor-Governance (`l9-graphite-memory`), CEG and EIE (`constellation-node-sdk`) |
| Evidence | Core `tests/actions/test_run_supply_chain.py` (+407 lines in #304, +119 in #309); Core runs the lane on itself (`self-supply-chain.yml`). #304 states the verdicts on Core and three canaries were unchanged by its refactor, but cites no run IDs, so those runs are **Unknown**. Consumer run: none |
| Disposition | promote_global (mechanism); exemptions retain_domain |
| Delivery | Step one: Core #304 merged `f10471b` (2026-11-20 23:50Z) and #309 merged `5032702` (2026-11-21 00:29Z). Step two, org-ci running `run-supply-chain` for consumers: **not on Core `main` `4aa7f2b`** (org-ci declares the `supply_chain` event class but has no step calling the action); its pull request is Unknown. Effective: no. Observed: none |
| Retirement and recovery | No consumer copy is eligible; Cursor-Governance and CEG `supply-chain.yml` stay. Rollback: not applicable until step two exists |

## Not promoted: backlog for the rollout campaign

C6 to C15, S1a to S4, and G1 to G4 were not promoted during this campaign. Each keeps the disposition in
its index row and moves, as written, to the rollout campaign's backlog. S5 needs no promotion
(already_satisfied; the IB-Odoo_19 copy is retire_duplicate after an adapter). The retain_domain list
above stays with its owners. Each backlog row's remaining fields are Unknown until its owner lane takes it.

## Defects the census found (CI-config evidence, not product findings)

| Defect | Where | Routed to |
|---|---|---|
| Biome job calls an SDK workflow deleted on SDK main (5fd1e3f); runs only from an old pin | CG `l9-lint-test-node.yml:50`, CEG same file | CG-CUTOVER (CG); CEG consolidation |
| Bot PRs opened with `GITHUB_TOKEN` never get CI | CG and CEG `lint-autofix.yml` | CG-CUTOVER (CG); CEG lane |
| `on-org-update.yml` calls a script that does not exist | CG | CG-CUTOVER |
| Version authority contradicted in code ("SDK wins") | CG `ops/scripts/run_pr_security.sh:5-7` | CG-CUTOVER |
| docs-sync can never fail (counter incremented in a piped subshell) | EIE `docs-sync.yml:55-77` | EIE lane |
| docs-consistency checks files that do not exist, so it always passes | EIE | EIE lane |
| PR size check says BLOCKED but cannot fail | EIE `pr-review-enforcement.yml` | G1 |
| `.gitleaks.toml` does not extend default rules | EIE | C1 adoption |
| Unpinned actions, one third-party (`softprops/action-gh-release@v1`) missed by the repo's own pin check | IB `release.yml:109` and four other workflows | G2 lane (IB toolchain PR) |
| Odoo XML checker's own tests are outside pytest `testpaths`, so they probably never run | IB `ci/test_check_odoo19_xml.py` | G2 lane |
| Deep-plan coverage floor has no scheduler (apply closed) | EIE, CEG | C4 |

## Cutover

Campaign scope (operator decision, 2026-11-20): cut over **Cursor-Governance** only, prove it with
`CURSOR_CANARY_PASS`, and leave the organization ready to roll out. Rolling out to other repositories is
not part of this campaign. Cutover items for Cursor-Governance are owned by lane CG-CUTOVER and depend on
C1 to C5. The other donors' rows above are the starting backlog for the rollout campaign.
