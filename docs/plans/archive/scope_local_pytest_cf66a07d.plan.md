---
name: Scope local pytest to the published diff
overview: "Narrow local make pr pytest to test files in the diff and tests whose source contains a changed path or dotted module. Keep GitHub ci.yml on pytest tests/. When V1 through V4 pass, commit only the may_modify paths. Do not run make pr, git push, or gh pr create. The governing cause remains select_tests in scripts/pr_check_scope.py. One owner stays. No second gate, skip switch, pass cache, or pyt..."
todos:
  - id: T1
    content: "Narrow tokens_for to the repo-relative path, the suffix-stripped path, and the dotted module for Python. Delete the bare stem, the addon directory token, the quoted-directory scan, and the plasticos_* glob. Update the pr_check_scope.py docstring and the pr_check_run.sh header comment."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Rewrite tests/test_pr_check_scope.py so an addon README selects nothing, seed.xml selects only the test that quotes that path, scripts/helper.py selects only a fixture that quotes scripts/helper.py, docs/x.md selects nothing, and load.py does not select a word-only hit. Keep tests=all for the harness, PR_CHECK_SCOPE=full, an empty diff, an unknown base, and a scope-script failure."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "On PR_SMOKE_BYPASS, call make pr-check while the bypass variable is still set. Assert the publication test log contains make pr-check and does not contain a bare make test goal. PR_CHECK_SKIP_SMOKE=1 still refuses."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Append one AGENTS.md correction dated 2026-11-05 stating the narrow local pytest rule and that ci.yml still runs pytest tests/. Leave the 2026-10-22 paragraph in place."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T5
    content: "Run ruff on the edited Python, then pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py, then pre-commit on the edited paths using .pre-commit-config.yaml. Confirm .github/workflows/ci.yml has no diff."
    status: pending
    phase: execute
    depends_on: [T2, T3, T4]
  - id: T7
    content: "After the selector change and V1 through V4 pass, invoke .cursor-commands/kernels/Validate & Repair.md on the finished may_modify files. Implement every confirmed fix that kernel requires inside those files. Do not edit .cursor-commands. Do not run make pr."
    status: pending
    phase: execute
    depends_on: [T5]
  - id: T6
    content: "After the Validate and Repair fixes are in the tree, commit only the may_modify paths with one conventional commit. Do not run make pr, git push, or gh pr create."
    status: pending
    phase: execute
    depends_on: [T7]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Scope local pytest to the published diff

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build** on the current branch, complete the todos, run Validate and Repair on the finished files, implement its confirmed fixes, then commit only the may_modify paths. Do not run `make pr`, `git push`, or `gh pr create`. Do not run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `scope_local_pytest_to_the_published_diff_db7393cc.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan and execute on the current workspace branch.

- Do not run `make pr`, `git push`, or `gh pr create`.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree as a planning or publication step.
- After V1 through V4 pass: invoke Validate and Repair on the finished may_modify files and implement every confirmed fix it requires.
- Then commit only the may_modify paths.
- The finish reply names that commit. A pull request is out of scope.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| name | Scope local pytest to the published diff |
| overview | Narrow local make pr pytest to test files in the diff and tests whose source contains a changed path or dotted module. Keep GitHub ci.yml on pytest tests/. When V1 through V4 pass, commit only the may_modify paths. Do not run make pr, git push, or gh pr create. The governing cause remains select_tests in scripts/pr_check_scope.py. One owner stays. No second gate, skip switch, pass cache, or pytest-xdist. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T16:56:12+00:00 |
| updated_at | 2026-11-05T16:56:12+00:00 |
| depth | `standard` |
| estimate | one focused change set |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build on the current branch; Validate and Repair before one local commit; do not run make pr |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-05T16:56:12+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `docs/brs-documents-logistics-ownership` |
| commit_sha | `7edbcce1967af5cca89a2d2f4f00b891a109ce34` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Narrow local make pr pytest to test files in the diff and tests whose source contains a changed path or dotted module. Keep GitHub ci.yml on pytest tests/. When V1 through V4 pass, commit only the may_modify paths. Do not run make pr, git push, or gh pr create. The governing cause remains select_tests in scripts/pr_check_scope.py. One owner stays. No second gate, skip switch, pass cache, or pytest-xdist.

### Scope in

- scripts/pr_check_scope.py tokens_for and select_tests, plus the module docstring
- scripts/pr_check_run.sh header comment only, so it matches the narrower rule
- scripts/git_push_with_pr.sh PR_SMOKE_BYPASS branch, so it calls make pr-check
- tests/test_pr_check_scope.py assertions that lock today's broad match
- tests/test_make_pr_publication.py smoke-bypass assertion
- AGENTS.md append-only correction dated 2026-11-05

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: the scoped pytest run exits 0, and a bare filename stem such as load.py does not select a test. | `quality_gate` | V1: `python3 -m pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py -q` → exit 0, and the load.py case rejects a word-only match | `true` |
| SP-02 | V2: ruff check and ruff format --check both exit 0. | `quality_gate` | V2: `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py && ruff format --check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py` → both commands exit 0 | `true` |
| SP-03 | V3: pre-commit exits 0. | `quality_gate` | V3: `pre-commit run --config .pre-commit-config.yaml --files scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` → exit 0 | `true` |
| SP-04 | V4: the CI workflow diff is empty. | `quality_gate` | V4: `git diff -- .github/workflows/ci.yml` → empty diff | `true` |
| SP-05 | V5: one local commit contains the allowed paths and git status for those paths is empty. | `quality_gate` | V5: `git log -1 --name-only && git status --porcelain -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` → HEAD commit lists each may_modify path and git status for those paths is empty | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.scope_local_pytest_to_the_published_diff.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| source_ref | `plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| PV1 | pre-validation (status `passed`) | `Read scripts/pr_check_scope.py select_tests and tokens_for` | Bare stem, addon name, quoted directory, and TREE_WALK_RE are the four broad matches | `true` |
| PV2 | pre-validation (status `passed`) | `Read scripts/pr_check_run.sh tests case and Makefile test-scoped` | The runner consumes the receipt and does not choose files itself | `true` |
| PV3 | pre-validation (status `passed`) | `Read scripts/git_push_with_pr.sh smoke bypass branch` | PR_SMOKE_BYPASS currently runs make audit audit-baseline test | `true` |
| PV4 | pre-validation (status `passed`) | `Read .github/workflows/ci.yml pure-python-tests` | The merge job runs pytest tests/ | `true` |
| PV5 | pre-validation (status `passed`) | `python3 "$HOME/.cursor-governance/skills/l9-plan/scripts/route_plan.py" --risk medium --evidence sufficient --json` | depth standard and omit_gates empty | `true` |
| PV6 | pre-validation (status `passed`) | `Read .l9/memory/plan-prefetch.json` | conflicts CLEAN, 62 records, no selector conflict | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `scripts/pr_check_scope.py`, `scripts/pr_check_run.sh`, `scripts/git_push_with_pr.sh`, `tests/test_pr_check_scope.py`, `tests/test_make_pr_publication.py`, `AGENTS.md`
- **write_deny:** `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py -q`, `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py`, `pre-commit run --config .pre-commit-config.yaml --files scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md`, `git diff -- .github/workflows/ci.yml`, `git log -1 --name-only && git status --porcelain -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md`, `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py && ruff format --check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | none |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- ci.yml pure-python-tests remains pytest tests/
- tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure
- audit and smoke decisions stay in pr_check_scope.plan
- make pr remains the only publication command in the repo, and this change set does not run it
- finish is one local commit of the may_modify paths

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/pr_check_scope.py scripts/pr_check_run.sh` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_pr_check_scope.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/git_push_with_pr.sh tests/test_make_pr_publication.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- AGENTS.md` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/pr_check_scope.py tests/test_pr_check_scope.py tests/test_make_pr_publication.py scripts/git_push_with_pr.sh` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `scripts` | `assurance` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T2 | `tests` | `assurance` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T3 | `repository root` | `ops` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T4 | `repository root` | `docs` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T5 | `repository root` | `assurance` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T7 | `repository root` | `assurance` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |
| T6 | `repository root` | `ops` | `ci.yml pure-python-tests remains pytest tests/`, `tests=all for harness files, PR_CHECK_SCOPE=full, empty diff, unknown base, and scope-script failure`, `audit and smoke decisions stay in pr_check_scope.plan`, `make pr remains the only publication command in the repo, and this change set does not run it`, `finish is one local commit of the may_modify paths` | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml`, `.cursor-commands` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.scope_local_pytest_to_the_published_diff.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| source_execution_ref | `plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (tokens_for no longer adds path.stem or the addon directory, and select_tests no longer calls TREE_WALK_RE or _dir_pattern) → Stop before editing tests. Restore the previous select_tests if a fail-closed tests=all path was removed.; C2 fails (V1 V2 V3 V4 all exit 0) → Stop. Fix the failing contract. Do not commit and do not publish.; C4 fails (Validate and Repair was run on the finished may_modify files, and every confirmed fix it required in those files is implemented) → Do not commit while a confirmed finding in the allowed files is still open.; C3 fails (git log -1 shows one commit of the may_modify paths, those paths are clean, and no pull request was opened) → If make pr, git push, or gh pr create ran, stop and report that. Do not open a pull request to undo it. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the feature-branch commits. scripts/pr_check_scope.py, the two test modules, the smoke-bypass branch, and the AGENTS.md correction return together. ci.yml was never edited. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py -q`
- re-run `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py`
- re-run `pre-commit run --config .pre-commit-config.yaml --files scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md`
- re-run `git diff -- .github/workflows/ci.yml`
- re-run `git log -1 --name-only && git status --porcelain -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md`
- re-run `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py && ruff format --check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 7 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — Every later make pr on this repo runs a smaller local pytest set. A regression whose test does not name the changed path waits for GitHub ci.yml. Audit, audit-baseline, gitleaks, and install-smoke are unchanged. |
| architectural_boundaries_crossed | `local make pr gate versus GitHub ci.yml merge verdict` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.scope_local_pytest_to_the_published_diff.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Narrow tokens_for to the repo-relative path, the suffix-stripped path, and the dotted module for Python. Delete the bare stem, the addon directory token, the quoted-directory scan, and the plasticos_* glob. Update the pr_check_scope.py docstring and the pr_check_run.sh header comment. | Cursor Build agent | `medium` | M | `[]` | `scripts/pr_check_scope.py`, `scripts/pr_check_run.sh` |
| T2 | Rewrite tests/test_pr_check_scope.py so an addon README selects nothing, seed.xml selects only the test that quotes that path, scripts/helper.py selects only a fixture that quotes scripts/helper.py, docs/x.md selects nothing, and load.py does not select a word-only hit. Keep tests=all for the harness, PR_CHECK_SCOPE=full, an empty diff, an unknown base, and a scope-script failure. | Cursor Build agent | `medium` | M | `[T1]` | `tests/test_pr_check_scope.py` |
| T3 | On PR_SMOKE_BYPASS, call make pr-check while the bypass variable is still set. Assert the publication test log contains make pr-check and does not contain a bare make test goal. PR_CHECK_SKIP_SMOKE=1 still refuses. | Cursor Build agent | `medium` | S | `[T1]` | `scripts/git_push_with_pr.sh`, `tests/test_make_pr_publication.py` |
| T4 | Append one AGENTS.md correction dated 2026-11-05 stating the narrow local pytest rule and that ci.yml still runs pytest tests/. Leave the 2026-10-22 paragraph in place. | Cursor Build agent | `low` | S | `[T1]` | `AGENTS.md` |
| T5 | Run ruff on the edited Python, then pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py, then pre-commit on the edited paths using .pre-commit-config.yaml. Confirm .github/workflows/ci.yml has no diff. | Cursor Build agent | `low` | S | `[T2, T3, T4]` | `scripts/pr_check_scope.py`, `tests/test_pr_check_scope.py`, `tests/test_make_pr_publication.py`, `scripts/git_push_with_pr.sh` |
| T7 | After the selector change and V1 through V4 pass, invoke .cursor-commands/kernels/Validate & Repair.md on the finished may_modify files. Implement every confirmed fix that kernel requires inside those files. Do not edit .cursor-commands. Do not run make pr. | Cursor Build agent | `medium` | M | `[T5]` | `scripts/pr_check_scope.py`, `scripts/pr_check_run.sh`, `scripts/git_push_with_pr.sh`, `tests/test_pr_check_scope.py`, `tests/test_make_pr_publication.py`, `AGENTS.md` |
| T6 | After the Validate and Repair fixes are in the tree, commit only the may_modify paths with one conventional commit. Do not run make pr, git push, or gh pr create. | Cursor Build agent | `low` | S | `[T7]` | `scripts/pr_check_scope.py`, `scripts/pr_check_run.sh`, `scripts/git_push_with_pr.sh`, `tests/test_pr_check_scope.py`, `tests/test_make_pr_publication.py`, `AGENTS.md` |

**Critical path:** T1 → T2 → T3 → T4 → T5 → T7 → T6

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | select_tests returns only path-named and self-changed test modules | T2 and T3 can lock the new contract |
| M2 | Contract tests and the smoke bypass agree with the narrow rule | T5 proof |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T1 | tokens_for no longer adds path.stem or the addon directory, and select_tests no longer calls TREE_WALK_RE or _dir_pattern | Stop before editing tests. Restore the previous select_tests if a fail-closed tests=all path was removed. |
| C2 | T5 | V1 V2 V3 V4 all exit 0 | Stop. Fix the failing contract. Do not commit and do not publish. |
| C4 | T7 | Validate and Repair was run on the finished may_modify files, and every confirmed fix it required in those files is implemented | Do not commit while a confirmed finding in the allowed files is still open. |
| C3 | T6 | git log -1 shows one commit of the may_modify paths, those paths are clean, and no pull request was opened | If make pr, git push, or gh pr create ran, stop and report that. Do not open a pull request to undo it. |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`, `T5`, `T7`, `T6`
- **Shared causes:** one over-broad select_tests causes the 89-module local wave and the smoke-bypass full suite
- **Deletions / consolidations:** delete bare filename stems from tokens_for; delete the addon directory token; delete _dir_pattern selection; delete TREE_WALK_RE selection; delete the smoke-bypass call to make test

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `update` | `T4` | The 2026-10-22 correction describes the broad reader rule. Append a superseding correction. Leave that paragraph in place. |
| CLAUDE.md | `n_a` | — | CLAUDE.md points at AGENTS.md and does not restate the pytest selector. |
| INVARIANTS.md | `n_a` | — | No invariant id changes. The merge suite stays intact. |
| .github/workflows/ci.yml | `n_a` | — | The full pytest tests/ job remains the merge verdict. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py -q` | exit 0, and the load.py case rejects a word-only match | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py && ruff format --check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py` | both commands exit 0 | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` | exit 0 | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `git diff -- .github/workflows/ci.yml` | empty diff | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `git log -1 --name-only && git status --porcelain -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md` | HEAD commit lists each may_modify path and git status for those paths is empty | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does a test that imports the changed module by dotted path still get selected?
- Does tests=all still happen for tests/conftest.py, pyproject.toml, requirements files, PR_CHECK_SCOPE=full, an empty diff, and a scope-script failure?
- Does make pr-nosmoke still launch pytest tests/ after the bypass calls make pr-check?
- Is a regression whose test does not name the changed path accepted as a CI-only catch?
- Does any execute sentence still order make pr after the operator required a local commit and no publication?

### Assumption failure conditions

- A second pytest file list is added in the Makefile or in ci.yml
- The bare stem or plasticos_* glob is left in place beside the new rule
- A previous pytest pass is reused as evidence that the new diff is green

### Blast radius notes

- Every later make pr on this repo runs a smaller local pytest set. A regression whose test does not name the changed path waits for GitHub ci.yml. Audit, audit-baseline, gitleaks, and install-smoke are unchanged.

### Rollback constraints

- Revert the feature-branch commits. scripts/pr_check_scope.py, the two test modules, the smoke-bypass branch, and the AGENTS.md correction return together. ci.yml was never edited.

### Risks

| risk | mitigation |
|------|------------|
| A pure-Python test covers a changed file without quoting its path, so make pr will not run it. | CI still runs pytest tests/. The contract test locks the path rule so the omission is visible. |
| make pr already skips the pre-push phantom-enum and manifest-contract hooks, and the narrow rule will not add them back. | Those two modules stay in ci.yml. The user accepted CI as the full suite. |
| This branch touches seven addons, so tests that quote those paths still run and the bar can stay long. | Proof is the contract tests, not a small receipt on this wide diff. |

## Out of scope

- .github/workflows/ci.yml full pytest tests/ job
- Makefile test and test-scoped recipes
- .pre-commit-config.yaml hook list
- .cursor-commands and Cursor-Governance make pr-check
- plasticos_* manifests and module version bumps
- install-smoke trigger rules
- a PR_CHECK_SKIP_TESTS switch, a pytest pass cache, and pytest-xdist
- make pr, git push, and gh pr create for this change set
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.scope_local_pytest_to_the_published_diff.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.scope_local_pytest_to_the_published_diff.v1` |
| source_ref | `plan.simple.scope_local_pytest_to_the_published_diff.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | How many of the 89 modules on the current seven-addon diff quote a changed path and will remain on the local bar? — Does not change the rule. It only changes how long this particular branch stays in pytest. | `accept_bounded` |
| `open_blocker` | stop_reason | PLAN_DOCUMENT structure is complete. V1 through V5 stay pending until Build edits the selector, runs Validate and Repair on that diff, and commits it. Doctrine forbids converged while those checks are pending. Publication is out of scope. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build** on the current branch, run Validate and Repair, then commit the may_modify paths — do not run make pr |
| execute_via | Cursor Build on the current branch; Validate and Repair; one local commit; do not run make pr |
| next_skill | Build, Validate and Repair, then one local commit; do not make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.scope_local_pytest_to_the_published_diff.v1"
  name: "Scope local pytest to the published diff"
  overview: "Narrow local make pr pytest to test files in the diff and tests whose source contains a changed path or dotted module. Keep GitHub ci.yml on pytest tests/. When V1 through V4 pass, commit only the may_modify paths. Do not run make pr, git push, or gh pr create. The governing cause remains select_tests in scripts/pr_check_scope.py. One owner stays. No second gate, skip switch, pass cache, or pytest-xdist."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "7edbcce1967af5cca89a2d2f4f00b891a109ce34"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Narrow local make pr pytest to test files in the diff and tests whose source contains a changed path or dotted module. Keep GitHub ci.yml on pytest tests/. When V1 through V4 pass, commit only the may_modify paths. Do not run make pr, git push, or gh pr create. The governing cause remains select_tests in scripts/pr_check_scope.py. One owner stays. No second gate, skip switch, pass cache, or pytest-xdist."
  success_properties:
    - id: "SP-01"
      property: "V1: the scoped pytest run exits 0, and a bare filename stem such as load.py does not select a test."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: ruff check and ruff format --check both exit 0."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3: pre-commit exits 0."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4: the CI workflow diff is empty."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-05"
      property: "V5: one local commit contains the allowed paths and git status for those paths is empty."
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.scope_local_pytest_to_the_published_diff.v1"
execution_envelope:
  filesystem:
    write_allow: ["scripts/pr_check_scope.py", "scripts/pr_check_run.sh", "scripts/git_push_with_pr.sh", "tests/test_pr_check_scope.py", "tests/test_make_pr_publication.py", "AGENTS.md"]
    write_deny: [".github/workflows/ci.yml", "Makefile", ".pre-commit-config.yaml", ".cursor-commands"]
  commands:
    allow: ["python3 -m pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py -q", "ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py", "pre-commit run --config .pre-commit-config.yaml --files scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md", "git diff -- .github/workflows/ci.yml", "git log -1 --name-only && git status --porcelain -- scripts/pr_check_scope.py scripts/pr_check_run.sh scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py AGENTS.md", "ruff check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py && ruff format --check scripts/pr_check_scope.py scripts/git_push_with_pr.sh tests/test_pr_check_scope.py tests/test_make_pr_publication.py"]
  network:
    mode: "none"
  secrets:
    access: "none"
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
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.scope_local_pytest_to_the_published_diff.v1"
dependency_topology_ref: "dag.plan.simple.scope_local_pytest_to_the_published_diff.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5"]
stress_and_disconfirm:
  disconfirming_cases: ["Does a test that imports the changed module by dotted path still get selected?", "Does tests=all still happen for tests/conftest.py, pyproject.toml, requirements files, PR_CHECK_SCOPE=full, an empty diff, and a scope-script failure?", "Does make pr-nosmoke still launch pytest tests/ after the bypass calls make pr-check?", "Is a regression whose test does not name the changed path accepted as a CI-only catch?", "Does any execute sentence still order make pr after the operator required a local commit and no publication?"]
  assumption_failure_conditions: ["A second pytest file list is added in the Makefile or in ci.yml", "The bare stem or plasticos_* glob is left in place beside the new rule", "A previous pytest pass is reused as evidence that the new diff is green"]
out_of_scope: [".github/workflows/ci.yml full pytest tests/ job", "Makefile test and test-scoped recipes", ".pre-commit-config.yaml hook list", ".cursor-commands and Cursor-Governance make pr-check", "plasticos_* manifests and module version bumps", "install-smoke trigger rules", "a PR_CHECK_SKIP_TESTS switch, a pytest pass cache, and pytest-xdist", "make pr, git push, and gh pr create for this change set"]
convergence_contract_ref: "conv.plan.simple.scope_local_pytest_to_the_published_diff.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: Validate and Repair, then a local commit; do not run make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Narrow tokens_for to the repo-relative path, the suffix-stripped path, and the dotted module for Python. Delete the bare stem, the addon directory token, the quoted-directory scan, and the plasticos_* glob. Update the pr_check_scope.py docstring and the pr_check_run.sh header comment."
    status: "pending"
  - id: "T2"
    content: "Rewrite tests/test_pr_check_scope.py so an addon README selects nothing, seed.xml selects only the test that quotes that path, scripts/helper.py selects only a fixture that quotes scripts/helper.py, docs/x.md selects nothing, and load.py does not select a word-only hit. Keep tests=all for the harness, PR_CHECK_SCOPE=full, an empty diff, an unknown base, and a scope-script failure."
    status: "pending"
  - id: "T3"
    content: "On PR_SMOKE_BYPASS, call make pr-check while the bypass variable is still set. Assert the publication test log contains make pr-check and does not contain a bare make test goal. PR_CHECK_SKIP_SMOKE=1 still refuses."
    status: "pending"
  - id: "T4"
    content: "Append one AGENTS.md correction dated 2026-11-05 stating the narrow local pytest rule and that ci.yml still runs pytest tests/. Leave the 2026-10-22 paragraph in place."
    status: "pending"
  - id: "T5"
    content: "Run ruff on the edited Python, then pytest tests/test_pr_check_scope.py tests/test_make_pr_publication.py, then pre-commit on the edited paths using .pre-commit-config.yaml. Confirm .github/workflows/ci.yml has no diff."
    status: "pending"
  - id: "T7"
    content: "After the selector change and V1 through V4 pass, invoke .cursor-commands/kernels/Validate & Repair.md on the finished may_modify files. Implement every confirmed fix that kernel requires inside those files. Do not edit .cursor-commands. Do not run make pr."
    status: "pending"
  - id: "T6"
    content: "After the Validate and Repair fixes are in the tree, commit only the may_modify paths with one conventional commit. Do not run make pr, git push, or gh pr create."
    status: "pending"
```
