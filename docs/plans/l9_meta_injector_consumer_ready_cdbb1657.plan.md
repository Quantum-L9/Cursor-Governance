---
name: l9-meta-injector — zero failures, zero warnings, installable and runnable from a consumer repository
overview: "Make Quantum-L9/l9-meta-injector green on every local and CI gate with no warnings, and prove by automated test that another repository can install it (GitHub Action, packed tarball, git dependency) and run its CLI (inventory, check) against itself, without weakening any existing contract or the fail-closed npm publication gate."
todos:
  - id: T1
    content: "Write the consumer-proof harness FIRST and watch it fail: extend scripts/test-packed-consumer.js to (a) install the packed tarball into a temp consumer that is a fresh git repo, run the installed bin `--help`, `inventory .`, and `check . --authority <fixture authority>`; (b) `npm install git+file://<temp bare clone>#HEAD` and run `inventory .`. Expected red today: (a) --help exits 1, (b) unknown — evidence for U4."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "ADR-078 (operator decision 2026-11-03, U1): repository-level facts (package_managers, governance_refs, adr_refs, package.name) exclude git-ignored paths, implemented by reusing the src/omit.ts gitignore matcher over the target's root .gitignore and .git/info/exclude (candidate B). Record candidate A (git ls-files) as rejected: it adds a git subprocess dependency to src/. Record the bounded gap: nested .gitignore files are not honoured. Append to docs/decision_log.md."
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Implement ADR-078 in src/repository_model.ts (and the shared enumeration it uses), rebuild dist/ in the same commit, and add regression REG-WU-078-a: a git-ignored pnpm-lock.yaml at the root yields package_managers == ['npm']; REG-WU-078-b: a tracked pnpm-lock.yaml still yields pnpm. Keep REG-WU-029-RC-033-e assertions unchanged."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "CLI usability for consumers: commit scripts/operation-cli.js with the executable bit (git update-index --chmod=+x); add `--help`/`-h` that prints usage and exits 0; keep ADR-022 relative-root refusal but make its error name the fix (`cd <repo> && l9-meta-injector inventory .`)."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T5
    content: "ADR-079 + package scripts. Evidence (Context7 /npm/cli/v10.9.9 package-json.md 'Git URLs as Dependencies'): a git dependency is cloned, has ALL dependencies installed, its scripts run and is re-packed whenever any of build, prepare, prepack, preinstall, install, postinstall is defined; npm advises repos shipping pre-built artifacts to define none of them. So: rename script `build` to `compile` and move the `prepack` gate chain into an explicit `release:check` run by prepublishOnly, selfpack, CI smoke and release.yml; update every caller (CI workflows, Makefile, action.yml, docs, AGENTS.md/CLAUDE.md command text via append) in the same commit. check:dist parity enforcement must remain on every path it covers today except the git-install lifecycle. Update docs/package-contract.json."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T6
    content: "Ship only runtime scripts: narrow package.json `files` from all of scripts/ to scripts/operation-cli.js plus the scripts/lib/ modules it requires; keep publication/release tooling (check-publication-readiness.js, check-release-candidate.js, which read docs/) out of the tarball. Update docs/public-api-contract.json if it enumerates shipped files; check:api and selfpack must stay green."
    status: pending
    phase: execute
    depends_on: [T5]
  - id: T7
    content: "Node floor honesty (U2): add a CI matrix that runs the packed-consumer proof (runtime only, no devDependencies) on Node 18, 20 and 22. If 18/20 pass, keep engines.node >=18 and document devEngines >=22.12 as contributor-only; if not, raise engines.node to the lowest passing floor in ADR-079."
    status: pending
    phase: execute
    depends_on: [T1, T5]
  - id: T8
    content: "CI job `consumer-proof`: check out a separate fixture repository directory, run the composite Action via `uses: ./meta-injector` against it in modes inventory and check (with authority input), assert success and an untouched fixture for dry-run. Pin every action by SHA; no continue-on-error; no copied org workflow or L9_CORE_REF."
    status: pending
    phase: execute
    depends_on: [T4, T5]
  - id: T9
    content: "Fix SonarCloud new-code findings: S2871 scripts/validation-report.js:74 (explicit compare fn, deterministic order); S4036 scripts/semantics-verify.js:43 (fixed absolute PATH via gitBinary resolution, as WU-069 already does); S8707 x5 tools/consolidation/folder_artifact_consolidator.py:97,110,114,123,141 (contain every CLI-supplied path under the declared root, reject escapes). Add a test for each behavioural change."
    status: pending
    phase: execute
    depends_on: []
  - id: T10
    content: "Refresh topology conformance evidence: run `node scripts/topology-conformance.js --update` against consumer main 2c2c628, review the diff (only revision and derived hashes may move), commit docs/topology-conformance.json."
    status: pending
    phase: execute
    depends_on: []
  - id: T11
    content: "Dependency warnings: converge Dependabot #117 (eslint 9.39.5 deprecated -> 10.13.0) and #116 (typescript-eslint 8.72.1) on their own branches via l9-pr-remediation (they own package.json/package-lock.json hunks; overlap gate). Decide #115 (@types/node 26 vs engines floor): add a dependabot ignore for @types/node majors above the engines floor, then close #115 with the reason."
    status: pending
    phase: execute
    depends_on: [T7]
  - id: T12
    content: "Docs truth: README install section (Action @v4 or @<sha>, packed tarball, git dependency; `cd <repo> && npx l9-meta-injector inventory .`), fix Action examples (add authority input; inventory/check instead of deprecated pipeline alias), complete the inputs table (authority, out, node-version; namespace applies to all modes; llm fails closed), append an AGENTS.md correction that distribution-owner approval cannot be waived."
    status: pending
    phase: execute
    depends_on: [T4, T5, T7]
  - id: T13
    content: "Close-out evidence: `npm run manifest:update`, regenerate CURRENT_VALIDATION_REPORT.md at the final head (currently stale at c24681b), CHANGELOG entry, then the full gate."
    status: pending
    phase: execute
    depends_on: [T3, T6, T8, T9, T10, T12]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: l9-meta-injector — zero failures, zero warnings, installable and runnable from a consumer repository

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository_5fe81d78.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| name | l9-meta-injector — zero failures, zero warnings, installable and runnable from a consumer repository |
| overview | Make Quantum-L9/l9-meta-injector green on every local and CI gate with no warnings, and prove by automated test that another repository can install it (GitHub Action, packed tarball, git dependency) and run its CLI (inventory, check) against itself, without weakening any existing contract or the fail-closed npm publication gate. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U2 |
| is_project | `false` |
| owner | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| created_at | 2026-11-03T13:48:08+00:00 |
| updated_at | 2026-11-03T13:48:08+00:00 |
| depth | `deep` |
| estimate | 1 PR, 13 todos; ends merge-ready, no release |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-03T13:48:08+00:00` |
| repository | `Quantum-L9/l9-meta-injector` |
| workspace | `/home/user/l9-meta-injector` |
| branch | `main` |
| commit_sha | `c352dbff2e0f5218c3815406fc2e1d2223a24a71` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make Quantum-L9/l9-meta-injector green on every local and CI gate with no warnings, and prove by automated test that another repository can install it (GitHub Action, packed tarball, git dependency) and run its CLI (inventory, check) against itself, without weakening any existing contract or the fail-closed npm publication gate.

### Scope in

- Quantum-L9/l9-meta-injector: src/, dist/ (rebuilt, same commit), tests/, scripts/, package.json, docs/decisions/ (new ADR-078, ADR-079), docs/decision_log.md, docs/package-contract.json, docs/public-api-contract.json, docs/topology-conformance.json, README.md, AGENTS.md (append-only correction), CHANGELOG.md, CURRENT_VALIDATION_REPORT.md, .github/workflows/ci.yml, .github/dependabot.yml, scripts/validation-report.js, scripts/semantics-verify.js, tools/consolidation/folder_artifact_consolidator.py
- Converging the open Dependabot PRs #116 and #117 and deciding #115 in this repository
- SonarCloud new-code findings on main c352dbf (1 CRITICAL BUG S2871, 1 MINOR VULNERABILITY S4036, 5 MAJOR VULNERABILITY S8707)
- Scheduled Topology conformance failure on main (stale docs/topology-conformance.json against consumer main 2c2c628)

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | SC1: `npm ci && npm run validate` exits 0 on a clean checkout even when a git-ignored stray lockfile (pnpm-lock.yaml) sits at the repo root — proof V1 and V2 | `quality_gate` | V1: `npm ci && npm run lint && npm run validate` → exit 0; vitest 180 files, 0 failed, 0 worker errors; V2: `touch pnpm-lock.yaml (git-ignored) && npx vitest run tests/repository_fact_scope.test.ts` → all pass including REG-WU-078-a and REG-WU-029-RC-033-e | `true` |
| SP-02 | SC2: ESLint reports 0 errors and 0 warnings, `tsc --noEmit` is clean, and `npm ci` prints no deprecation warning for a direct devDependency — proof V3 | `quality_gate` | V3: `npx eslint . --format json \| node -e "...sum warningCount+errorCount" && npx tsc --noEmit -p tsconfig.json && npm ci 2>&1 \| grep -c 'npm warn deprecated'` → 0, clean, 0 | `true` |
| SP-03 | SC3: an installed packed tarball runs `l9-meta-injector --help` (exit 0), `inventory .` and `check . --authority <fixture>` inside a fresh temporary git repository — proof V4 | `quality_gate` | V4: `npm run test:packed` → packed-consumer: OK including bin --help, inventory ., check . --authority in a temp git repo | `true` |
| SP-04 | SC4: `npm install git+file://<bare clone>#HEAD` succeeds in a temporary consumer and its installed bin runs `inventory .` — proof V5 | `quality_gate` | V5: `node scripts/test-packed-consumer.js --git-install` → git+file install succeeds and installed bin runs inventory . | `true` |
| SP-05 | SC5: CI job `consumer-proof` runs the composite Action from a checkout of a separate fixture repository and passes — proof V6 | `quality_gate` | V6: `CI job consumer-proof on the PR head` → success | `true` |
| SP-06 | SC6: every check-run on the PR head is green, including SonarCloud Code Analysis (0 new BUG/VULNERABILITY) and Topology conformance — proof V7 and V8 | `quality_gate` | V7: `gh api repos/Quantum-L9/l9-meta-injector/commits/<head>/check-runs` → every check-run conclusion success, SonarCloud Code Analysis included; V8: `node scripts/topology-conformance.js` → exit 0 against consumer main | `true` |
| SP-07 | SC7: `git status --porcelain --untracked-files=all` prints nothing after `npm run validate` — proof V9 | `quality_gate` | V9: `git status --porcelain --untracked-files=all` → empty output | `true` |
| SP-08 | SC8: `npm run check:publication` still reports BLOCKED until a distribution owner approves; no approval field is forged — proof V10 | `quality_gate` | V10: `npm run check:publication` → BLOCKED (fail-closed preserved) | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| source_ref | `plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind workspace /home/user/l9-meta-injector: branch main == origin/main @ c352dbf, clean tree, Node v22.23.4, npm 10.9.9` | single root, clean, current with origin/main | `true` |
| P1 | pre-validation (status `passed`) | `npm ci && npm run lint && npx tsc --noEmit -p tsconfig.json` | exit 0; ESLint 295 files 0 warnings 0 errors | `true` |
| P2 | pre-validation (status `failed`) | `npm run validate (after removing the pnpm-installed node_modules via npm ci)` | exit 0 | `true` |
| P3 | pre-validation (status `passed`) | `npm run -s check:api, check:authority, check:manifest, check:dist, selfpack, test:packed, check:release-candidate (each individually)` | each exit 0 | `true` |
| P4 | pre-validation (status `passed`) | `npm run check:publication` | BLOCKED by design (owner approval absent) | `true` |
| P5 | pre-validation (status `failed`) | `gh api check-runs for c352dbf; SonarCloud api/issues/search inNewCodePeriod BUG,VULNERABILITY` | all green | `true` |
| P6 | pre-validation (status `not_applicable`) | `.pre-commit-config.yaml hook catalog` | none configured in this repo (CLAUDE.md: CI commands are the authority) | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `src/`, `dist/`, `tests/`, `fixtures/consumer/`, `scripts/test-packed-consumer.js`, `scripts/operation-cli.js`, `scripts/lib/operation-dispatch.js`, `scripts/validation-report.js`, `scripts/semantics-verify.js`, `tools/consolidation/folder_artifact_consolidator.py`, `package.json`, `package-lock.json`, `docs/decisions/078-*.md`, `docs/decisions/079-*.md`, `docs/decision_log.md`, `docs/package-contract.json`, `docs/public-api-contract.json`, `docs/topology-conformance.json`, `docs/architecture.md`, `MANIFEST.json`, `README.md`, `AGENTS.md (append-only)`, `CHANGELOG.md`, `CURRENT_VALIDATION_REPORT.md`, `.github/workflows/ci.yml`, `.github/dependabot.yml`
- **write_deny:** `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `npm ci`, `npm run lint`, `npm run validate`, `npm run check:publication`, `git status --porcelain --untracked-files=all`, `npm ci && npm run lint && npm run validate`, `touch pnpm-lock.yaml (git-ignored) && npx vitest run tests/repository_fact_scope.test.ts`, `npx eslint . --format json \| node -e "...sum warningCount+errorCount" && npx tsc --noEmit -p tsconfig.json && npm ci 2>&1 \| grep -c 'npm warn deprecated'`, `npm run test:packed`, `node scripts/test-packed-consumer.js --git-install`, `CI job consumer-proof on the PR head`, `gh api repos/Quantum-L9/l9-meta-injector/commits/<head>/check-runs`, `node scripts/topology-conformance.js`, `.pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| allowed_services | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |

### Secrets

| Field | Value |
|-------|-------|
| access | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- ADR-022 contained CLI/Action dispatch: relative roots only
- TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only
- dist/ committed and in parity with src/ in the same commit
- check:publication fail-closed
- no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA
- TransportPacket is the only wire format for emitted packets

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/test-packed-consumer.js fixtures/consumer/authority.yaml tests/packed_consumer_cli.test.ts` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- docs/decisions/078-repository-facts-exclude-ignored-paths.md docs/decision_log.md` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- src/repository_model.ts src/omit.ts dist/repository_model.js dist/repository_model.d.ts dist/omit.js dist/omit.d.ts tests/repository_fact_scope.test.ts` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/operation-cli.js scripts/lib/operation-dispatch.js tests/operation_cli_help.test.ts` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- package.json docs/package-contract.json docs/decisions/079-consumer-install-paths.md docs/decision_log.md .github/workflows/ Makefile README.md` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- package.json docs/package-contract.json docs/public-api-contract.json` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .github/workflows/ci.yml package.json README.md` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .github/workflows/ci.yml fixtures/consumer/` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/validation-report.js scripts/semantics-verify.js tools/consolidation/folder_artifact_consolidator.py tests/validation_report.test.ts` | `false` |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- docs/topology-conformance.json` | `false` |
| T11 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .github/dependabot.yml` | `false` |
| T12 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- README.md AGENTS.md` | `false` |
| T13 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- CURRENT_VALIDATION_REPORT.md CHANGELOG.md MANIFEST.json` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T2 | `docs` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T3 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T4 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T5 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T6 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T7 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T8 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T9 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T10 | `docs` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T11 | `.github` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T12 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |
| T13 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `ADR-022 contained CLI/Action dispatch: relative roots only`, `TypeScript pipeline is the sole active engine; tools/consolidation stays reference-only`, `dist/ committed and in parity with src/ in the same commit`, `check:publication fail-closed`, `no copied org workflow, no L9_CORE_REF/L9_SDK_REF pin, no continue-on-error, actions pinned by SHA`, `TransportPacket is the only wire format for emitted packets` | `docs/package-publication-decision.json approval fields`, `accepted ADRs 001-077 (supersede with links only)`, `.github/workflows/release.yml tag logic`, `Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| source_execution_ref | `plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (harness output showing --help exit 1 and the git-install result before any fix) → stop; a harness that is green before the fix cannot discriminate (KP-011 tautological verification); C2 fails (REG-WU-078-a fails before T3 and passes after; full vitest 180 files 0 failed) → revert T3; reopen ADR-078 candidate selection; C3 fails (V4, V5, V6 green on the PR head) → do not request merge; consumers stay on @<sha>; C4 fails (V1-V10 recorded in CURRENT_VALIDATION_REPORT.md bound to the final head) → do not request merge |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | All changes land in one PR on a branch; revert the merge commit. No version bump and no tag movement in this plan (operator decision). |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `npm ci`
- re-run `npm run lint`
- re-run `npm run validate`
- re-run `npm run check:publication`
- re-run `git status --porcelain --untracked-files=all`
- re-run `npm ci && npm run lint && npm run validate`
- re-run `touch pnpm-lock.yaml (git-ignored) && npx vitest run tests/repository_fact_scope.test.ts`
- re-run `npx eslint . --format json | node -e "...sum warningCount+errorCount" && npx tsc --noEmit -p tsconfig.json && npm ci 2>&1 | grep -c 'npm warn deprecated'`
- re-run `npm run test:packed`
- re-run `node scripts/test-packed-consumer.js --git-install`
- re-run `CI job consumer-proof on the PR head`
- re-run `gh api repos/Quantum-L9/l9-meta-injector/commits/<head>/check-runs`
- re-run `node scripts/topology-conformance.js`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 13 todo(s) |
| uncertainty | `medium` — 5 unknown(s), 0 blocking |
| blast_radius | `high` — Every consumer of @v4 and of the TransportPacket repository facts (l9-constellation-topology ingests them): a wrong T3 changes package_managers/governance_refs facts across the constellation; a wrong T5/T6 ships a tarball missing runtime scripts. |
| architectural_boundaries_crossed | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| external_systems_touched | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| migration_required | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| unknown_dependency_count | `5` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Write the consumer-proof harness FIRST and watch it fail: extend scripts/test-packed-consumer.js to (a) install the packed tarball into a temp consumer that is a fresh git repo, run the installed bin `--help`, `inventory .`, and `check . --authority <fixture authority>`; (b) `npm install git+file://<temp bare clone>#HEAD` and run `inventory .`. Expected red today: (a) --help exits 1, (b) unknown — evidence for U4. | Cursor Build agent | `medium` | M | `[]` | `scripts/test-packed-consumer.js`, `fixtures/consumer/authority.yaml`, `tests/packed_consumer_cli.test.ts` |
| T2 | ADR-078 (operator decision 2026-11-03, U1): repository-level facts (package_managers, governance_refs, adr_refs, package.name) exclude git-ignored paths, implemented by reusing the src/omit.ts gitignore matcher over the target's root .gitignore and .git/info/exclude (candidate B). Record candidate A (git ls-files) as rejected: it adds a git subprocess dependency to src/. Record the bounded gap: nested .gitignore files are not honoured. Append to docs/decision_log.md. | Cursor Build agent | `medium` | S | `[]` | `docs/decisions/078-repository-facts-exclude-ignored-paths.md`, `docs/decision_log.md` |
| T3 | Implement ADR-078 in src/repository_model.ts (and the shared enumeration it uses), rebuild dist/ in the same commit, and add regression REG-WU-078-a: a git-ignored pnpm-lock.yaml at the root yields package_managers == ['npm']; REG-WU-078-b: a tracked pnpm-lock.yaml still yields pnpm. Keep REG-WU-029-RC-033-e assertions unchanged. | Cursor Build agent | `high` | M | `[T2]` | `src/repository_model.ts`, `src/omit.ts`, `dist/repository_model.js`, `dist/repository_model.d.ts`, `dist/omit.js`, `dist/omit.d.ts`, `tests/repository_fact_scope.test.ts` |
| T4 | CLI usability for consumers: commit scripts/operation-cli.js with the executable bit (git update-index --chmod=+x); add `--help`/`-h` that prints usage and exits 0; keep ADR-022 relative-root refusal but make its error name the fix (`cd <repo> && l9-meta-injector inventory .`). | Cursor Build agent | `low` | S | `[T1]` | `scripts/operation-cli.js`, `scripts/lib/operation-dispatch.js`, `tests/operation_cli_help.test.ts` |
| T5 | ADR-079 + package scripts. Evidence (Context7 /npm/cli/v10.9.9 package-json.md 'Git URLs as Dependencies'): a git dependency is cloned, has ALL dependencies installed, its scripts run and is re-packed whenever any of build, prepare, prepack, preinstall, install, postinstall is defined; npm advises repos shipping pre-built artifacts to define none of them. So: rename script `build` to `compile` and move the `prepack` gate chain into an explicit `release:check` run by prepublishOnly, selfpack, CI smoke and release.yml; update every caller (CI workflows, Makefile, action.yml, docs, AGENTS.md/CLAUDE.md command text via append) in the same commit. check:dist parity enforcement must remain on every path it covers today except the git-install lifecycle. Update docs/package-contract.json. | Cursor Build agent | `high` | M | `[T1]` | `package.json`, `docs/package-contract.json`, `docs/decisions/079-consumer-install-paths.md`, `docs/decision_log.md`, `.github/workflows/`, `Makefile`, `README.md` |
| T6 | Ship only runtime scripts: narrow package.json `files` from all of scripts/ to scripts/operation-cli.js plus the scripts/lib/ modules it requires; keep publication/release tooling (check-publication-readiness.js, check-release-candidate.js, which read docs/) out of the tarball. Update docs/public-api-contract.json if it enumerates shipped files; check:api and selfpack must stay green. | Cursor Build agent | `medium` | S | `[T5]` | `package.json`, `docs/package-contract.json`, `docs/public-api-contract.json` |
| T7 | Node floor honesty (U2): add a CI matrix that runs the packed-consumer proof (runtime only, no devDependencies) on Node 18, 20 and 22. If 18/20 pass, keep engines.node >=18 and document devEngines >=22.12 as contributor-only; if not, raise engines.node to the lowest passing floor in ADR-079. | Cursor Build agent | `medium` | S | `[T1, T5]` | `.github/workflows/ci.yml`, `package.json`, `README.md` |
| T8 | CI job `consumer-proof`: check out a separate fixture repository directory, run the composite Action via `uses: ./meta-injector` against it in modes inventory and check (with authority input), assert success and an untouched fixture for dry-run. Pin every action by SHA; no continue-on-error; no copied org workflow or L9_CORE_REF. | Cursor Build agent | `medium` | M | `[T4, T5]` | `.github/workflows/ci.yml`, `fixtures/consumer/` |
| T9 | Fix SonarCloud new-code findings: S2871 scripts/validation-report.js:74 (explicit compare fn, deterministic order); S4036 scripts/semantics-verify.js:43 (fixed absolute PATH via gitBinary resolution, as WU-069 already does); S8707 x5 tools/consolidation/folder_artifact_consolidator.py:97,110,114,123,141 (contain every CLI-supplied path under the declared root, reject escapes). Add a test for each behavioural change. | Cursor Build agent | `medium` | M | `[]` | `scripts/validation-report.js`, `scripts/semantics-verify.js`, `tools/consolidation/folder_artifact_consolidator.py`, `tests/validation_report.test.ts` |
| T10 | Refresh topology conformance evidence: run `node scripts/topology-conformance.js --update` against consumer main 2c2c628, review the diff (only revision and derived hashes may move), commit docs/topology-conformance.json. | Cursor Build agent | `low` | S | `[]` | `docs/topology-conformance.json` |
| T11 | Dependency warnings: converge Dependabot #117 (eslint 9.39.5 deprecated -> 10.13.0) and #116 (typescript-eslint 8.72.1) on their own branches via l9-pr-remediation (they own package.json/package-lock.json hunks; overlap gate). Decide #115 (@types/node 26 vs engines floor): add a dependabot ignore for @types/node majors above the engines floor, then close #115 with the reason. | Cursor Build agent | `medium` | S | `[T7]` | `.github/dependabot.yml` |
| T12 | Docs truth: README install section (Action @v4 or @<sha>, packed tarball, git dependency; `cd <repo> && npx l9-meta-injector inventory .`), fix Action examples (add authority input; inventory/check instead of deprecated pipeline alias), complete the inputs table (authority, out, node-version; namespace applies to all modes; llm fails closed), append an AGENTS.md correction that distribution-owner approval cannot be waived. | Cursor Build agent | `low` | S | `[T4, T5, T7]` | `README.md`, `AGENTS.md` |
| T13 | Close-out evidence: `npm run manifest:update`, regenerate CURRENT_VALIDATION_REPORT.md at the final head (currently stale at c24681b), CHANGELOG entry, then the full gate. | Cursor Build agent | `low` | S | `[T3, T6, T8, T9, T10, T12]` | `CURRENT_VALIDATION_REPORT.md`, `CHANGELOG.md`, `MANIFEST.json` |

**Critical path:** T1 → T5 → T4 → T8 → T13

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | consumer-proof harness exists and fails for the documented reasons | T4, T5, T7, T8 have a falsifying test |
| M2 | repository facts ignore git-ignored files; local validate green with a stray ignored lockfile | SC1 |
| M3 | tarball and git installs run the CLI in a foreign repo; Action runs from a foreign checkout in CI | SC3, SC4, SC5 |
| M4 | SonarCloud, conformance, and dependency warnings cleared | SC2, SC6 |
| M5 | evidence regenerated; PR green and merge-ready | merge under operator authorization; release stays a separate operator decision |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | harness output showing --help exit 1 and the git-install result before any fix | stop; a harness that is green before the fix cannot discriminate (KP-011 tautological verification) |
| C2 | M2 | REG-WU-078-a fails before T3 and passes after; full vitest 180 files 0 failed | revert T3; reopen ADR-078 candidate selection |
| C3 | M3 | V4, V5, V6 green on the PR head | do not request merge; consumers stay on @<sha> |
| C4 | M5 | V1-V10 recorded in CURRENT_VALIDATION_REPORT.md bound to the final head | do not request merge |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T5`, `T4`, `T8`, `T6`, `T7`, `T9`, `T10`, `T11`, `T12`, `T13`
- **Shared causes:** consumer use was never exercised outside this repository (T1 feeds T4, T5, T6, T7, T8); observation treats every file on disk as repository truth (T2, T3)
- **Deletions / consolidations:** drop publication/release tooling from the shipped tarball (T6); retire the README's deprecated `pipeline` examples in favour of inventory/check (T12)

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| README.md | `update` | `T12` | — |
| AGENTS.md | `update` | `T12` | — |
| CLAUDE.md | `n_a` | — | verify-before-push commands and CI topology unchanged except the added consumer-proof job, which AGENTS.md/README document |
| INVARIANTS.md | `n_a` | — | no invariant is relaxed; ADR-078/079 add constraints recorded in docs/decisions |
| docs/architecture.md + MANIFEST.json | `update` | `T13` | — |
| docs/decisions + docs/decision_log.md | `update` | `T2`, `T5` | — |
| CHANGELOG.md | `update` | `T13` | — |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `npm ci && npm run lint && npm run validate` | exit 0; vitest 180 files, 0 failed, 0 worker errors | `not_run` |
| E-V2 | SP-01 | `quality_gate_evidence` | command | `touch pnpm-lock.yaml (git-ignored) && npx vitest run tests/repository_fact_scope.test.ts` | all pass including REG-WU-078-a and REG-WU-029-RC-033-e | `not_run` |
| E-V3 | SP-02 | `quality_gate_evidence` | command | `npx eslint . --format json \| node -e "...sum warningCount+errorCount" && npx tsc --noEmit -p tsconfig.json && npm ci 2>&1 \| grep -c 'npm warn deprecated'` | 0, clean, 0 | `not_run` |
| E-V4 | SP-03 | `quality_gate_evidence` | command | `npm run test:packed` | packed-consumer: OK including bin --help, inventory ., check . --authority in a temp git repo | `not_run` |
| E-V5 | SP-04 | `quality_gate_evidence` | command | `node scripts/test-packed-consumer.js --git-install` | git+file install succeeds and installed bin runs inventory . | `not_run` |
| E-V6 | SP-05 | `quality_gate_evidence` | command | `CI job consumer-proof on the PR head` | success | `not_run` |
| E-V7 | SP-06 | `quality_gate_evidence` | command | `gh api repos/Quantum-L9/l9-meta-injector/commits/<head>/check-runs` | every check-run conclusion success, SonarCloud Code Analysis included | `not_run` |
| E-V8 | SP-06 | `quality_gate_evidence` | command | `node scripts/topology-conformance.js` | exit 0 against consumer main | `not_run` |
| E-V9 | SP-07 | `quality_gate_evidence` | command | `git status --porcelain --untracked-files=all` | empty output | `not_run` |
| E-V10 | SP-08 | `quality_gate_evidence` | command | `npm run check:publication` | BLOCKED (fail-closed preserved) | `not_run` |
| E-V11 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | N/A: l9-meta-injector configures no pre-commit framework; CI commands (V1, V7) are the authority per CLAUDE.md | `not_run` (not_applicable) |

## Stress and disconfirm

### Disconfirming cases

- Would the plan still be green if a consumer has no git binary (tarball install into a non-git directory)?
- Can T3 hide a real lockfile that a consumer tracks but also lists in .gitignore by mistake (tracked-but-ignored)?
- Does moving gates out of prepack let a broken dist/ reach a git consumer?
- Could the harness pass because it runs inside this repository's own tree rather than a foreign one?
- Is SonarCloud red caused by tools/consolidation, which CLAUDE.md calls historical reference, so deleting it would be the real fix?

### Assumption failure conditions

- npm's git fetcher does not run prepack for packages with committed dist/ (U4) — if false, T5 changes shape
- dist/ runs on Node 18 — if false, engines.node must rise (T7)
- the stale conformance record is consumer drift, not a producer regression — if the --update diff touches anything but revision-derived fields, stop and investigate

### Blast radius notes

- Every consumer of @v4 and of the TransportPacket repository facts (l9-constellation-topology ingests them): a wrong T3 changes package_managers/governance_refs facts across the constellation; a wrong T5/T6 ships a tarball missing runtime scripts.

### Rollback constraints

- All changes land in one PR on a branch; revert the merge commit. No version bump and no tag movement in this plan (operator decision).

### Risks

| risk | mitigation |
|------|------------|
| T3 changes constellation-visible repository facts | ADR-078 first; REG-WU-078-a/b pin both directions; topology conformance (V8) re-proves the consumer accepts the packets |
| T5 lifecycle change weakens dist/ parity enforcement | check:dist stays in npm run validate, CI smoke, prepublishOnly and release.yml; only the git-install lifecycle path stops invoking it |
| Dependabot eslint 10 major breaks eslint.config.js | converged on its own PR (#117) with npm run lint as the gate, not folded into this branch |
| the local governance provisioner keeps installing with pnpm and re-breaks the environment | run `npm ci` before every local gate; governance fix tracked separately (session-debt session-deps-pnpm-override) |

## Out of scope

- npm registry publication: docs/package-publication-decision.json requires distribution-owner approval and approved_version; CLAUDE.md forbids marking publication evidence verified without external proof
- Cursor-Governance environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh:528-531 (runs pnpm on npm repos): different repository; recorded as session-debt `session-deps-pnpm-override`, separate PR
- Relaxing ADR-022 relative-root containment of the CLI and Action (absolute roots stay refused)
- Any change in l9-constellation-topology (the consumer); its PR #33 is separate
- Manually moving the `v4` tag; release.yml owns tags
- Version bump / v4.2.1 release and v4 tag movement (operator decision 2026-11-03: stop at merge-ready PR)
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| source_ref | `plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7, E-V8, E-V9, E-V10, E-V11
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7, E-V8, E-V9, E-V10, E-V11

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Exclude git-ignored files from repository-level facts (ADR-078), and via candidate A (git ls-files) or B (reuse omit.ts over .gitignore + .git/info/exclude)? — RESOLVED 2026-11-03 by operator: exclude via .gitignore (candidate B); nested .gitignore is a documented bounded gap | `accept_bounded` |
| `unknown` | U2 | Does dist/ run on Node 18 and 20 so engines.node >=18 is honest? — T7 keeps or raises the floor; T11 @types/node ignore bound | `probe` |
| `unknown` | U3 | Approve releasing v4.2.1 (advances the v4 tag consumers pin)? — RESOLVED 2026-11-03 by operator: no version bump in this PR; stop at merge-ready; README documents @<sha> pinning until a separate release decision | `accept_bounded` |
| `unknown` | U4 | Which lifecycle scripts does npm run for a git dependency that has committed dist/ and a prepack script? — RESOLVED 2026-11-03 via Context7 /npm/cli/v10.9.9: build/prepare/prepack/preinstall/install/postinstall each trigger the full git-dependency build flow; T5 removes `build` and `prepack` script names | `accept_bounded` |
| `unknown` | U5 | npm registry publication approval — none in this plan; check:publication stays BLOCKED | `accept_bounded` |
| `open_blocker` | stop_reason | plan validated; U1/U3 operator-bound, U4 resolved from npm docs; U2 (Node 18/20 runtime floor) is probed by the T7 CI matrix — no Node 18/20 runtime in this container | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1"
  name: "l9-meta-injector — zero failures, zero warnings, installable and runnable from a consumer repository"
  overview: "Make Quantum-L9/l9-meta-injector green on every local and CI gate with no warnings, and prove by automated test that another repository can install it (GitHub Action, packed tarball, git dependency) and run its CLI (inventory, check) against itself, without weakening any existing contract or the fail-closed npm publication gate."
  status: "draft"
  is_project: false
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/l9-meta-injector"
  commit_sha: "c352dbff2e0f5218c3815406fc2e1d2223a24a71"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make Quantum-L9/l9-meta-injector green on every local and CI gate with no warnings, and prove by automated test that another repository can install it (GitHub Action, packed tarball, git dependency) and run its CLI (inventory, check) against itself, without weakening any existing contract or the fail-closed npm publication gate."
  success_properties:
    - id: "SP-01"
      property: "SC1: `npm ci && npm run validate` exits 0 on a clean checkout even when a git-ignored stray lockfile (pnpm-lock.yaml) sits at the repo root — proof V1 and V2"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-02"
      property: "SC2: ESLint reports 0 errors and 0 warnings, `tsc --noEmit` is clean, and `npm ci` prints no deprecation warning for a direct devDependency — proof V3"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-03"
      property: "SC3: an installed packed tarball runs `l9-meta-injector --help` (exit 0), `inventory .` and `check . --authority <fixture>` inside a fresh temporary git repository — proof V4"
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-04"
      property: "SC4: `npm install git+file://<bare clone>#HEAD` succeeds in a temporary consumer and its installed bin runs `inventory .` — proof V5"
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
    - id: "SP-05"
      property: "SC5: CI job `consumer-proof` runs the composite Action from a checkout of a separate fixture repository and passes — proof V6"
      evidence_type: "quality_gate"
      proof: ["V6"]
      blocking: true
    - id: "SP-06"
      property: "SC6: every check-run on the PR head is green, including SonarCloud Code Analysis (0 new BUG/VULNERABILITY) and Topology conformance — proof V7 and V8"
      evidence_type: "quality_gate"
      proof: ["V7", "V8"]
      blocking: true
    - id: "SP-07"
      property: "SC7: `git status --porcelain --untracked-files=all` prints nothing after `npm run validate` — proof V9"
      evidence_type: "quality_gate"
      proof: ["V9"]
      blocking: true
    - id: "SP-08"
      property: "SC8: `npm run check:publication` still reports BLOCKED until a distribution owner approves; no approval field is forged — proof V10"
      evidence_type: "quality_gate"
      proof: ["V10"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1"
execution_envelope:
  filesystem:
    write_allow: ["src/", "dist/", "tests/", "fixtures/consumer/", "scripts/test-packed-consumer.js", "scripts/operation-cli.js", "scripts/lib/operation-dispatch.js", "scripts/validation-report.js", "scripts/semantics-verify.js", "tools/consolidation/folder_artifact_consolidator.py", "package.json", "package-lock.json", "docs/decisions/078-*.md", "docs/decisions/079-*.md", "docs/decision_log.md", "docs/package-contract.json", "docs/public-api-contract.json", "docs/topology-conformance.json", "docs/architecture.md", "MANIFEST.json", "README.md", "AGENTS.md (append-only)", "CHANGELOG.md", "CURRENT_VALIDATION_REPORT.md", ".github/workflows/ci.yml", ".github/dependabot.yml"]
    write_deny: ["docs/package-publication-decision.json approval fields", "accepted ADRs 001-077 (supersede with links only)", ".github/workflows/release.yml tag logic", "Quantum-L9/.github semantics (cite via .l9/meta-authority.yaml, never copy)"]
  commands:
    allow: ["npm ci", "npm run lint", "npm run validate", "npm run check:publication", "git status --porcelain --untracked-files=all", "npm ci && npm run lint && npm run validate", "touch pnpm-lock.yaml (git-ignored) && npx vitest run tests/repository_fact_scope.test.ts", "npx eslint . --format json | node -e \"...sum warningCount+errorCount\" && npx tsc --noEmit -p tsconfig.json && npm ci 2>&1 | grep -c 'npm warn deprecated'", "npm run test:packed", "node scripts/test-packed-consumer.js --git-install", "CI job consumer-proof on the PR head", "gh api repos/Quantum-L9/l9-meta-injector/commits/<head>/check-runs", "node scripts/topology-conformance.js", ".pre-commit-config.yaml"]
  network:
    mode: "unknown — not declared in PLAN_DOCUMENT; resolve before status `executable`"
  secrets:
    access: "unknown — not declared in PLAN_DOCUMENT; resolve before status `executable`"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T5"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T8"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T9"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T10"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T11"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T12"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T13"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1"
dependency_topology_ref: "dag.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6", "E-V7", "E-V8", "E-V9", "E-V10", "E-V11"]
stress_and_disconfirm:
  disconfirming_cases: ["Would the plan still be green if a consumer has no git binary (tarball install into a non-git directory)?", "Can T3 hide a real lockfile that a consumer tracks but also lists in .gitignore by mistake (tracked-but-ignored)?", "Does moving gates out of prepack let a broken dist/ reach a git consumer?", "Could the harness pass because it runs inside this repository's own tree rather than a foreign one?", "Is SonarCloud red caused by tools/consolidation, which CLAUDE.md calls historical reference, so deleting it would be the real fix?"]
  assumption_failure_conditions: ["npm's git fetcher does not run prepack for packages with committed dist/ (U4) — if false, T5 changes shape", "dist/ runs on Node 18 — if false, engines.node must rise (T7)", "the stale conformance record is consumer drift, not a producer regression — if the --update diff touches anything but revision-derived fields, stop and investigate"]
out_of_scope: ["npm registry publication: docs/package-publication-decision.json requires distribution-owner approval and approved_version; CLAUDE.md forbids marking publication evidence verified without external proof", "Cursor-Governance environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh:528-531 (runs pnpm on npm repos): different repository; recorded as session-debt `session-deps-pnpm-override`, separate PR", "Relaxing ADR-022 relative-root containment of the CLI and Action (absolute roots stay refused)", "Any change in l9-constellation-topology (the consumer); its PR #33 is separate", "Manually moving the `v4` tag; release.yml owns tags", "Version bump / v4.2.1 release and v4 tag movement (operator decision 2026-11-03: stop at merge-ready PR)"]
convergence_contract_ref: "conv.plan.simple.l9_meta_injector_zero_failures_zero_warnings_installable_and_runnable_from_a_consumer_repository.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Write the consumer-proof harness FIRST and watch it fail: extend scripts/test-packed-consumer.js to (a) install the packed tarball into a temp consumer that is a fresh git repo, run the installed bin `--help`, `inventory .`, and `check . --authority <fixture authority>`; (b) `npm install git+file://<temp bare clone>#HEAD` and run `inventory .`. Expected red today: (a) --help exits 1, (b) unknown — evidence for U4."
    status: "pending"
  - id: "T2"
    content: "ADR-078 (operator decision 2026-11-03, U1): repository-level facts (package_managers, governance_refs, adr_refs, package.name) exclude git-ignored paths, implemented by reusing the src/omit.ts gitignore matcher over the target's root .gitignore and .git/info/exclude (candidate B). Record candidate A (git ls-files) as rejected: it adds a git subprocess dependency to src/. Record the bounded gap: nested .gitignore files are not honoured. Append to docs/decision_log.md."
    status: "pending"
  - id: "T3"
    content: "Implement ADR-078 in src/repository_model.ts (and the shared enumeration it uses), rebuild dist/ in the same commit, and add regression REG-WU-078-a: a git-ignored pnpm-lock.yaml at the root yields package_managers == ['npm']; REG-WU-078-b: a tracked pnpm-lock.yaml still yields pnpm. Keep REG-WU-029-RC-033-e assertions unchanged."
    status: "pending"
  - id: "T4"
    content: "CLI usability for consumers: commit scripts/operation-cli.js with the executable bit (git update-index --chmod=+x); add `--help`/`-h` that prints usage and exits 0; keep ADR-022 relative-root refusal but make its error name the fix (`cd <repo> && l9-meta-injector inventory .`)."
    status: "pending"
  - id: "T5"
    content: "ADR-079 + package scripts. Evidence (Context7 /npm/cli/v10.9.9 package-json.md 'Git URLs as Dependencies'): a git dependency is cloned, has ALL dependencies installed, its scripts run and is re-packed whenever any of build, prepare, prepack, preinstall, install, postinstall is defined; npm advises repos shipping pre-built artifacts to define none of them. So: rename script `build` to `compile` and move the `prepack` gate chain into an explicit `release:check` run by prepublishOnly, selfpack, CI smoke and release.yml; update every caller (CI workflows, Makefile, action.yml, docs, AGENTS.md/CLAUDE.md command text via append) in the same commit. check:dist parity enforcement must remain on every path it covers today except the git-install lifecycle. Update docs/package-contract.json."
    status: "pending"
  - id: "T6"
    content: "Ship only runtime scripts: narrow package.json `files` from all of scripts/ to scripts/operation-cli.js plus the scripts/lib/ modules it requires; keep publication/release tooling (check-publication-readiness.js, check-release-candidate.js, which read docs/) out of the tarball. Update docs/public-api-contract.json if it enumerates shipped files; check:api and selfpack must stay green."
    status: "pending"
  - id: "T7"
    content: "Node floor honesty (U2): add a CI matrix that runs the packed-consumer proof (runtime only, no devDependencies) on Node 18, 20 and 22. If 18/20 pass, keep engines.node >=18 and document devEngines >=22.12 as contributor-only; if not, raise engines.node to the lowest passing floor in ADR-079."
    status: "pending"
  - id: "T8"
    content: "CI job `consumer-proof`: check out a separate fixture repository directory, run the composite Action via `uses: ./meta-injector` against it in modes inventory and check (with authority input), assert success and an untouched fixture for dry-run. Pin every action by SHA; no continue-on-error; no copied org workflow or L9_CORE_REF."
    status: "pending"
  - id: "T9"
    content: "Fix SonarCloud new-code findings: S2871 scripts/validation-report.js:74 (explicit compare fn, deterministic order); S4036 scripts/semantics-verify.js:43 (fixed absolute PATH via gitBinary resolution, as WU-069 already does); S8707 x5 tools/consolidation/folder_artifact_consolidator.py:97,110,114,123,141 (contain every CLI-supplied path under the declared root, reject escapes). Add a test for each behavioural change."
    status: "pending"
  - id: "T10"
    content: "Refresh topology conformance evidence: run `node scripts/topology-conformance.js --update` against consumer main 2c2c628, review the diff (only revision and derived hashes may move), commit docs/topology-conformance.json."
    status: "pending"
  - id: "T11"
    content: "Dependency warnings: converge Dependabot #117 (eslint 9.39.5 deprecated -> 10.13.0) and #116 (typescript-eslint 8.72.1) on their own branches via l9-pr-remediation (they own package.json/package-lock.json hunks; overlap gate). Decide #115 (@types/node 26 vs engines floor): add a dependabot ignore for @types/node majors above the engines floor, then close #115 with the reason."
    status: "pending"
  - id: "T12"
    content: "Docs truth: README install section (Action @v4 or @<sha>, packed tarball, git dependency; `cd <repo> && npx l9-meta-injector inventory .`), fix Action examples (add authority input; inventory/check instead of deprecated pipeline alias), complete the inputs table (authority, out, node-version; namespace applies to all modes; llm fails closed), append an AGENTS.md correction that distribution-owner approval cannot be waived."
    status: "pending"
  - id: "T13"
    content: "Close-out evidence: `npm run manifest:update`, regenerate CURRENT_VALIDATION_REPORT.md at the final head (currently stale at c24681b), CHANGELOG entry, then the full gate."
    status: "pending"
```
