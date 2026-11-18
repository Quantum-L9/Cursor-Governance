---
name: Fix five Test Suite failures on main
overview: "Make the full Test Suite green on main (23dc060e) by repairing the root cause of each of the five failures that have been red since at least 8b62bfb3, without weakening any gate, skipping any test, or loosening any assertion."
todos:
  - id: T1
    content: "Move the REST-only org template probe into org_dotgithub.py (rest_probe + `probe-rest <owner> <path>` CLI, exit 0 OK / 1 DENIED) and call it from gh_auth_probe.sh, keeping org_template_read a REST-only verdict"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Allowlist the Memory 3.0 OAuth resource identifier in memory-oauth-connector.yaml and memory-auth0-onboarding.yaml, citing CANONICAL_LAW §8.10 and ADR-100"
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Remove the redundant core.hooksPath=/dev/null from integrate.py git() and docker_git(); the scratch repos are fresh init/clone with GIT_CONFIG_GLOBAL=/dev/null and GIT_CONFIG_NOSYSTEM=1, so no hook is configured"
    status: pending
    phase: execute
    depends_on: []
  - id: T4
    content: "Make the live-repo resolver test correct for a checkout with no commits ahead (expect SOURCE:empty) and add a temp-repo test proving a branch with a commit ahead resolves to `comparison`"
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "Run the full CI test profile, then close session-debt item main-test-suite-5-failures with the run as evidence"
    status: pending
    phase: execute
    depends_on: [T1, T2, T3, T4]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Fix five Test Suite failures on main

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `fix_five_test_suite_failures_on_main_59d6a172.plan.md`
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
| plan_id | `plan.simple.fix_five_test_suite_failures_on_main.v1` |
| name | Fix five Test Suite failures on main |
| overview | Make the full Test Suite green on main (23dc060e) by repairing the root cause of each of the five failures that have been red since at least 8b62bfb3, without weakening any gate, skipping any test, or loosening any assertion. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| created_at | 2026-11-02T11:48:41+00:00 |
| updated_at | 2026-11-02T11:48:41+00:00 |
| depth | `standard` |
| estimate | 1 PR |

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
| captured_at | `2026-11-02T11:48:41+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/root/.l9/gov-worktrees/claude-code__main-test-suite-red` |
| branch | `agent/claude-code/main-test-suite-red` |
| commit_sha | `23dc060e4a5472cc043606a458195c0e25812c8d` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make the full Test Suite green on main (23dc060e) by repairing the root cause of each of the five failures that have been red since at least 8b62bfb3, without weakening any gate, skipping any test, or loosening any assertion.

### Scope in

- ops/scripts/org_dotgithub.py and ops/scripts/lib/gh_auth_probe.sh (REST probe ownership)
- ops/config/memory-egress-allowlist.json (two allowlist entries)
- skills/l9-pr-integration-testing/scripts/integrate.py (two redundant hook-disable flags)
- tests/ops/scripts/test_resolve_changed_files_merge_base.py (live-checkout assumption)
- tests for each change

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: no module outside ops/scripts/org_dotgithub.py calls the <owner>/.github REST route, and the org_template_read probe still reports a REST-only per-transport verdict | `quality_gate` | V1: `.venv/bin/python -m pytest -q ops/scripts/tests/test_org_dotgithub.py && bash ops/scripts/tests/test_gh_auth_probe.sh && .venv/bin/python -m pytest -q tests/ops/scripts/test_claude_bootstrap_receipt_revision.py` → all pass | `true` |
| SP-02 | V2: test_egress_boundary.py passes because the two Memory 3.0 OAuth audience files are allowlisted with a CANONICAL_LAW §8.10 reason, not because a forbidden token was removed from the scanner | `quality_gate` | V2: `.venv/bin/python -m pytest -q tests/ops/memory/test_egress_boundary.py && .venv/bin/python ops/scripts/validate_memory_egress_boundary.py --enforce` → all pass; findings_unlisted == 0 | `true` |
| SP-03 | V3: test_commit_verification_validator.py passes because integrate.py no longer emits core.hooksPath=/dev/null, with the integration skill's own tests still green | `quality_gate` | V3: `.venv/bin/python -m pytest -q tests/ops/scripts/test_commit_verification_validator.py tests/skills/l9_pr_integration_testing` → all pass | `true` |
| SP-04 | V4: test_resolve_changed_files_merge_base.py passes on a checkout with zero commits ahead of origin/main and still proves a real change set resolves to `comparison` | `quality_gate` | V4: `.venv/bin/python -m pytest -q tests/ops/scripts/test_resolve_changed_files_merge_base.py` → all pass on a zero-ahead checkout and on a branch with commits ahead | `true` |
| SP-05 | V5: run_python_test_suites.py --profile ci reports 0 failed | `quality_gate` | V5: `.venv/bin/python ops/scripts/run_python_test_suites.py --profile ci` → 0 failed | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.fix_five_test_suite_failures_on_main.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.fix_five_test_suite_failures_on_main.v1` |
| source_ref | `plan.simple.fix_five_test_suite_failures_on_main.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.fix_five_test_suite_failures_on_main.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P1 | pre-validation (status `passed`) | `.venv/bin/python -m pytest the five failing node ids on a worktree at origin/main 23dc060e` | same five failures reproduce locally with the CI messages | `true` |
| P2 | pre-validation (status `passed`) | `read Test Suite logs for 8b62bfb3, a6c139a6, 5871bf8c, 23dc060e` | the same five failures exist before #800/#802/#803 | `true` |
| P3 | pre-validation (status `passed`) | `bind workspace: agent/claude-code/main-test-suite-red at origin/main 23dc060e; hook catalog .pre-commit-config.yaml` | clean worktree on the current main head | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/scripts/org_dotgithub.py`, `ops/scripts/lib/gh_auth_probe.sh`, `ops/scripts/tests/test_org_dotgithub.py`, `ops/scripts/tests/test_gh_auth_probe.sh`, `ops/config/memory-egress-allowlist.json`, `skills/l9-pr-integration-testing/scripts/integrate.py`, `tests/skills/l9_pr_integration_testing/test_runner_contract.py`, `tests/ops/scripts/test_resolve_changed_files_merge_base.py`
- **write_deny:** `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `.venv/bin/python ops/scripts/run_python_test_suites.py --profile ci`, `.pre-commit-config.yaml`, `.venv/bin/python -m pytest -q ops/scripts/tests/test_org_dotgithub.py && bash ops/scripts/tests/test_gh_auth_probe.sh && .venv/bin/python -m pytest -q tests/ops/scripts/test_claude_bootstrap_receipt_revision.py`, `.venv/bin/python -m pytest -q tests/ops/memory/test_egress_boundary.py && .venv/bin/python ops/scripts/validate_memory_egress_boundary.py --enforce`, `.venv/bin/python -m pytest -q tests/ops/scripts/test_commit_verification_validator.py tests/skills/l9_pr_integration_testing`, `.venv/bin/python -m pytest -q tests/ops/scripts/test_resolve_changed_files_merge_base.py`
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

- CANONICAL_LAW §8.10 memory egress boundary
- l9-commit-verification-integrity contract
- org_dotgithub single-reader rule
- per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/org_dotgithub.py ops/scripts/lib/gh_auth_probe.sh ops/scripts/tests/test_org_dotgithub.py ops/scripts/tests/test_gh_auth_probe.sh` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/config/memory-egress-allowlist.json` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-pr-integration-testing/scripts/integrate.py tests/skills/l9_pr_integration_testing/test_runner_contract.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/ops/scripts/test_resolve_changed_files_merge_base.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .l9/autonomy/session-debt.json` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `ops/scripts` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `CANONICAL_LAW §8.10 memory egress boundary`, `l9-commit-verification-integrity contract`, `org_dotgithub single-reader rule`, `per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)` | `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/` |
| T2 | `ops/config` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `CANONICAL_LAW §8.10 memory egress boundary`, `l9-commit-verification-integrity contract`, `org_dotgithub single-reader rule`, `per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)` | `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/` |
| T3 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `CANONICAL_LAW §8.10 memory egress boundary`, `l9-commit-verification-integrity contract`, `org_dotgithub single-reader rule`, `per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)` | `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/` |
| T4 | `tests/ops/scripts` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `CANONICAL_LAW §8.10 memory egress boundary`, `l9-commit-verification-integrity contract`, `org_dotgithub single-reader rule`, `per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)` | `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/` |
| T5 | `.l9/autonomy` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `CANONICAL_LAW §8.10 memory egress boundary`, `l9-commit-verification-integrity contract`, `org_dotgithub single-reader rule`, `per-transport GitHub capability verdicts (DEGRADED_MODE_CONTRACT)` | `ops/scripts/validate_memory_egress_boundary.py`, `ops/config/commit-verification-contract.json`, `ops/scripts/resolve_changed_files.sh`, `.github/workflows/` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.fix_five_test_suite_failures_on_main.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.fix_five_test_suite_failures_on_main.v1` |
| source_execution_ref | `plan.simple.fix_five_test_suite_failures_on_main.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1, V2, V3, V4 pass; integration skill tests pass; test_gh_auth_probe.sh passes) → stop and re-diagnose the failing item; do not loosen the assertion; C2 fails (V5 passes) → classify any new failure (product/test/fixture/environment/flake) before touching it |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the single fix commit; each todo touches disjoint files |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `.venv/bin/python ops/scripts/run_python_test_suites.py --profile ci`
- re-run `.pre-commit-config.yaml`
- re-run `.venv/bin/python -m pytest -q ops/scripts/tests/test_org_dotgithub.py && bash ops/scripts/tests/test_gh_auth_probe.sh && .venv/bin/python -m pytest -q tests/ops/scripts/test_claude_bootstrap_receipt_revision.py`
- re-run `.venv/bin/python -m pytest -q tests/ops/memory/test_egress_boundary.py && .venv/bin/python ops/scripts/validate_memory_egress_boundary.py --enforce`
- re-run `.venv/bin/python -m pytest -q tests/ops/scripts/test_commit_verification_validator.py tests/skills/l9_pr_integration_testing`
- re-run `.venv/bin/python -m pytest -q tests/ops/scripts/test_resolve_changed_files_merge_base.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 5 todo(s) |
| uncertainty | `medium` — 2 unknown(s), 0 blocking |
| blast_radius | `medium` — governance gates that run on every PR and on main; a wrong allowlist entry or probe change misreports egress or GitHub capability on every surface |
| architectural_boundaries_crossed | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| external_systems_touched | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| migration_required | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| unknown_dependency_count | `2` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.fix_five_test_suite_failures_on_main.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.fix_five_test_suite_failures_on_main.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Move the REST-only org template probe into org_dotgithub.py (rest_probe + `probe-rest <owner> <path>` CLI, exit 0 OK / 1 DENIED) and call it from gh_auth_probe.sh, keeping org_template_read a REST-only verdict | Cursor Build agent | `medium` | S | `[]` | `ops/scripts/org_dotgithub.py`, `ops/scripts/lib/gh_auth_probe.sh`, `ops/scripts/tests/test_org_dotgithub.py`, `ops/scripts/tests/test_gh_auth_probe.sh` |
| T2 | Allowlist the Memory 3.0 OAuth resource identifier in memory-oauth-connector.yaml and memory-auth0-onboarding.yaml, citing CANONICAL_LAW §8.10 and ADR-100 | Cursor Build agent | `medium` | S | `[]` | `ops/config/memory-egress-allowlist.json` |
| T3 | Remove the redundant core.hooksPath=/dev/null from integrate.py git() and docker_git(); the scratch repos are fresh init/clone with GIT_CONFIG_GLOBAL=/dev/null and GIT_CONFIG_NOSYSTEM=1, so no hook is configured | Cursor Build agent | `medium` | S | `[]` | `skills/l9-pr-integration-testing/scripts/integrate.py`, `tests/skills/l9_pr_integration_testing/test_runner_contract.py` |
| T4 | Make the live-repo resolver test correct for a checkout with no commits ahead (expect SOURCE:empty) and add a temp-repo test proving a branch with a commit ahead resolves to `comparison` | Cursor Build agent | `low` | S | `[]` | `tests/ops/scripts/test_resolve_changed_files_merge_base.py` |
| T5 | Run the full CI test profile, then close session-debt item main-test-suite-5-failures with the run as evidence | Cursor Build agent | `low` | S | `[T1, T2, T3, T4]` | `.l9/autonomy/session-debt.json` |

**Critical path:** T2 → T1 → T3 → T4 → T5

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | each of the five tests passes in isolation | full-suite run |
| M2 | full CI profile reports 0 failed | publish via make pr |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1, V2, V3, V4 pass; integration skill tests pass; test_gh_auth_probe.sh passes | stop and re-diagnose the failing item; do not loosen the assertion |
| C2 | M2 | V5 passes | classify any new failure (product/test/fixture/environment/flake) before touching it |

### Leverage

- **Ranked todos:** `T2`, `T1`, `T3`, `T4`, `T5`
- **Shared causes:** gates on main were red before these merges and PR CI runs only changed-file subsets, so the full-suite failures never blocked a PR
- **Deletions / consolidations:** remove the duplicated <owner>/.github REST call from gh_auth_probe.sh; remove two redundant core.hooksPath flags

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| docs/DEGRADED_MODE_CONTRACT.md | `n_a` | — | the org_template_read probe keeps its REST-only meaning; only the module that issues the call moves |
| AGENTS.md / CANONICAL_LAW.md | `n_a` | — | no law changes; the allowlist reason cites existing §8.10 |
| skills/l9-pr-integration-testing/SKILL.md | `n_a` | — | scratch-repo isolation behavior is unchanged; only a redundant flag is removed |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest -q ops/scripts/tests/test_org_dotgithub.py && bash ops/scripts/tests/test_gh_auth_probe.sh && .venv/bin/python -m pytest -q tests/ops/scripts/test_claude_bootstrap_receipt_revision.py` | all pass | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest -q tests/ops/memory/test_egress_boundary.py && .venv/bin/python ops/scripts/validate_memory_egress_boundary.py --enforce` | all pass; findings_unlisted == 0 | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest -q tests/ops/scripts/test_commit_verification_validator.py tests/skills/l9_pr_integration_testing` | all pass | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest -q tests/ops/scripts/test_resolve_changed_files_merge_base.py` | all pass on a zero-ahead checkout and on a branch with commits ahead | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `.venv/bin/python ops/scripts/run_python_test_suites.py --profile ci` | 0 failed | `not_run` |
| E-V6 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | changed-file hooks PASS in the make pr gate | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Is memory.quantumaipartners.com/mcp a raw provider route that §8.10 still forbids, rather than the native MCP audience it authorizes?
- Could a hook fire in integrate.py's scratch repos once the flag is gone (templateDir, repo-local config, docker image config)?
- Does anything read org_template_read as 'template readable by any transport' rather than 'REST works'?
- Is SOURCE:empty on a zero-ahead checkout the resolver's correct answer, or the false-PASS regression the test guards?

### Assumption failure conditions

- the egress validator flags memory.quantumaipartners.com because §8.10 does not cover OAuth audiences
- git clone into a fresh dir applies hooks from a template directory despite GIT_CONFIG_GLOBAL=/dev/null
- a merge-base failure on the CI checkout is being reported as empty

### Blast radius notes

- governance gates that run on every PR and on main; a wrong allowlist entry or probe change misreports egress or GitHub capability on every surface

### Rollback constraints

- revert the single fix commit; each todo touches disjoint files

### Risks

| risk | mitigation |
|------|------------|
| allowlisting a forbidden token hides a real provider side door | entry is path-scoped to the two audience files, cites §8.10 and ADR-100, and leaves the token forbidden everywhere else |
| the probe change alters what install.sh records in the bootstrap receipt | keep REST-only semantics and the OK/DENIED/UNKNOWN vocabulary; test_gh_auth_probe.sh T6/T7 and test_claude_bootstrap_receipt_revision.py must stay green |
| removing the hook flag lets a hook run against untrusted PR code | verify before editing that the scratch repos carry no hooksPath and no non-sample hooks; add a test asserting none |

## Out of scope

- Changing ops/scripts/validate_memory_egress_boundary.py forbidden tokens or enforce mode
- Changing the commit-verification contract or adding a breakglass
- Changing resolve_changed_files.sh behavior
- Open PRs #798 and #801
- The stale ~/.claude/skills and ~/.cursor/plans symlinks into old task worktrees
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.fix_five_test_suite_failures_on_main.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.fix_five_test_suite_failures_on_main.v1` |
| source_ref | `plan.simple.fix_five_test_suite_failures_on_main.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Does org_dotgithub.gh_api shell out to `gh api` so the stubbed gh in test_gh_auth_probe.sh still controls the probe? — if not, T1's shell test needs a different stub | `probe` |
| `unknown` | U2 | Does the l9-pr-integration-testing Docker image set a system or global core.hooksPath? — if it does, removing the flag in docker_git() needs an isolation fix instead | `probe` |
| `open_blocker` | stop_reason | plan validated; root causes reproduced and located; implementation and validations V1-V6 not yet run | planning convergence `partial` |

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
  plan_id: "plan.simple.fix_five_test_suite_failures_on_main.v1"
  name: "Fix five Test Suite failures on main"
  overview: "Make the full Test Suite green on main (23dc060e) by repairing the root cause of each of the five failures that have been red since at least 8b62bfb3, without weakening any gate, skipping any test, or loosening any assertion."
  status: "draft"
  is_project: false
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "23dc060e4a5472cc043606a458195c0e25812c8d"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make the full Test Suite green on main (23dc060e) by repairing the root cause of each of the five failures that have been red since at least 8b62bfb3, without weakening any gate, skipping any test, or loosening any assertion."
  success_properties:
    - id: "SP-01"
      property: "V1: no module outside ops/scripts/org_dotgithub.py calls the <owner>/.github REST route, and the org_template_read probe still reports a REST-only per-transport verdict"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: test_egress_boundary.py passes because the two Memory 3.0 OAuth audience files are allowlisted with a CANONICAL_LAW §8.10 reason, not because a forbidden token was removed from the scanner"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3: test_commit_verification_validator.py passes because integrate.py no longer emits core.hooksPath=/dev/null, with the integration skill's own tests still green"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4: test_resolve_changed_files_merge_base.py passes on a checkout with zero commits ahead of origin/main and still proves a real change set resolves to `comparison`"
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-05"
      property: "V5: run_python_test_suites.py --profile ci reports 0 failed"
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.fix_five_test_suite_failures_on_main.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/scripts/org_dotgithub.py", "ops/scripts/lib/gh_auth_probe.sh", "ops/scripts/tests/test_org_dotgithub.py", "ops/scripts/tests/test_gh_auth_probe.sh", "ops/config/memory-egress-allowlist.json", "skills/l9-pr-integration-testing/scripts/integrate.py", "tests/skills/l9_pr_integration_testing/test_runner_contract.py", "tests/ops/scripts/test_resolve_changed_files_merge_base.py"]
    write_deny: ["ops/scripts/validate_memory_egress_boundary.py", "ops/config/commit-verification-contract.json", "ops/scripts/resolve_changed_files.sh", ".github/workflows/"]
  commands:
    allow: [".venv/bin/python ops/scripts/run_python_test_suites.py --profile ci", ".pre-commit-config.yaml", ".venv/bin/python -m pytest -q ops/scripts/tests/test_org_dotgithub.py && bash ops/scripts/tests/test_gh_auth_probe.sh && .venv/bin/python -m pytest -q tests/ops/scripts/test_claude_bootstrap_receipt_revision.py", ".venv/bin/python -m pytest -q tests/ops/memory/test_egress_boundary.py && .venv/bin/python ops/scripts/validate_memory_egress_boundary.py --enforce", ".venv/bin/python -m pytest -q tests/ops/scripts/test_commit_verification_validator.py tests/skills/l9_pr_integration_testing", ".venv/bin/python -m pytest -q tests/ops/scripts/test_resolve_changed_files_merge_base.py"]
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
rollback_contract_ref: "rollback.plan.simple.fix_five_test_suite_failures_on_main.v1"
dependency_topology_ref: "dag.plan.simple.fix_five_test_suite_failures_on_main.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6"]
stress_and_disconfirm:
  disconfirming_cases: ["Is memory.quantumaipartners.com/mcp a raw provider route that §8.10 still forbids, rather than the native MCP audience it authorizes?", "Could a hook fire in integrate.py's scratch repos once the flag is gone (templateDir, repo-local config, docker image config)?", "Does anything read org_template_read as 'template readable by any transport' rather than 'REST works'?", "Is SOURCE:empty on a zero-ahead checkout the resolver's correct answer, or the false-PASS regression the test guards?"]
  assumption_failure_conditions: ["the egress validator flags memory.quantumaipartners.com because §8.10 does not cover OAuth audiences", "git clone into a fresh dir applies hooks from a template directory despite GIT_CONFIG_GLOBAL=/dev/null", "a merge-base failure on the CI checkout is being reported as empty"]
out_of_scope: ["Changing ops/scripts/validate_memory_egress_boundary.py forbidden tokens or enforce mode", "Changing the commit-verification contract or adding a breakglass", "Changing resolve_changed_files.sh behavior", "Open PRs #798 and #801", "The stale ~/.claude/skills and ~/.cursor/plans symlinks into old task worktrees"]
convergence_contract_ref: "conv.plan.simple.fix_five_test_suite_failures_on_main.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Move the REST-only org template probe into org_dotgithub.py (rest_probe + `probe-rest <owner> <path>` CLI, exit 0 OK / 1 DENIED) and call it from gh_auth_probe.sh, keeping org_template_read a REST-only verdict"
    status: "pending"
  - id: "T2"
    content: "Allowlist the Memory 3.0 OAuth resource identifier in memory-oauth-connector.yaml and memory-auth0-onboarding.yaml, citing CANONICAL_LAW §8.10 and ADR-100"
    status: "pending"
  - id: "T3"
    content: "Remove the redundant core.hooksPath=/dev/null from integrate.py git() and docker_git(); the scratch repos are fresh init/clone with GIT_CONFIG_GLOBAL=/dev/null and GIT_CONFIG_NOSYSTEM=1, so no hook is configured"
    status: "pending"
  - id: "T4"
    content: "Make the live-repo resolver test correct for a checkout with no commits ahead (expect SOURCE:empty) and add a temp-repo test proving a branch with a commit ahead resolves to `comparison`"
    status: "pending"
  - id: "T5"
    content: "Run the full CI test profile, then close session-debt item main-test-suite-5-failures with the run as evidence"
    status: "pending"
```
