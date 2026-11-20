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

## Promotions, grouped by upstream owner

### Core (`Quantum-L9/l9-ci-core`), lane L2

| # | Component | Donors | Disposition | Target | State |
|---|---|---|---|---|---|
| C1 | Consumer security scans (gitleaks, pip-audit, bandit advisory). Core `security.yml` is `workflow_call`-only and only Core calls it, so no consumer CI runs it | all four (each carries its own copy; CG has none in CI) | promote_global | `org-ci.yml` calls `security.yml` for consumers | Assigned L2, priority 1 |
| C2 | Toolchain alignment check made blocking (advisory today at `org-ci.yml:348-350`); per-repo guards drift | CEG `tests/unit/test_core_toolchain_pins.py` (stale), all repos drift | promote_global | Core `check-toolchain-alignment` | Assigned L2, priority 2 |
| C3 | Conflict-marker scan | CG `l9-lint-test.yml:173-189` | promote_global | repository verification step | Assigned L2, priority 3 |
| C4 | Nightly deep dispatch for consumers; CG missing from `deep-entrypoints.json`; apply closed | CG `sonarcloud.yml`, EIE deep plan, CEG deep plan, IB nightly | promote_global (scheduling) | `deep-entrypoints.json` + apply step | Assigned L2, priority 4; apply needs the operator's GitHub App |
| C5 | Supply-chain lane: dependency-review, licence allow/deny, SBOM, GPL/AGPL audit | CG, CEG, EIE (divergent copies) | promote_global (mechanism); exemptions retain_domain | Core `supply_chain` event class | Assigned L2, priority 5 |
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
| S1 | Odoo 19 framework pack: `check_odoo19_xml` (with tests), `check_odoo19_hooks`, circular deps, orphan model refs, ACL completeness, package init, XML ref deps, about 17 generic `check_odoo_patterns.sh` checks, cron lock pairing | IB-Odoo_19 | promote_framework | new SDK framework pack (none exists: `packs.yaml:25-26`) | Blocked on the operator's licence grant from cryptoxdog, or a clean-room rewrite |
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
