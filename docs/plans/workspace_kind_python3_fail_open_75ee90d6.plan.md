---
name: workspace_kind.sh never classifies a workspace as ssot when python3 is absent
overview: "Fix at its source the baseline integration failure tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py::test_consumer_workspace_skips_the_governance_registry. ops/scripts/lib/workspace_kind.sh _workspace_kind_realpath shells out to python3; with no python3 on PATH both resolutions are empty, the comparison '' = '' holds, and classify_workspace_kind answers ssot for every workspace (fail-op..."
todos:
  - id: T1
    content: "Replace the python3 call in _workspace_kind_realpath with builtins (expand a leading ~, then `cd -P -- '$p' && pwd -P` for an existing directory, else echo the expanded path unchanged), and in classify_workspace_kind answer ssot only when ws_real is non-empty and equals gc_real."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Add one case to the existing test: prepend a bin dir whose python3 exits 127, then assert the consumer fixture stays consumer, the identity tree stays ssot_checkout and the live SSOT stays ssot."
    status: pending
    phase: execute
    depends_on: [T1]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: workspace_kind.sh never classifies a workspace as ssot when python3 is absent

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent_b69637a7.plan.md`
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
| plan_id | `plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| name | workspace_kind.sh never classifies a workspace as ssot when python3 is absent |
| overview | Fix at its source the baseline integration failure tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py::test_consumer_workspace_skips_the_governance_registry. ops/scripts/lib/workspace_kind.sh _workspace_kind_realpath shells out to python3; with no python3 on PATH both resolutions are empty, the comparison "" = "" holds, and classify_workspace_kind answers ssot for every workspace (fail-open: a consumer repository is treated as the governance SSOT). Replace the helper with shell builtins and refuse to equate two empty resolutions. The other baseline failures are out of scope: test_org_dotgithub single-reader was fixed by merged #814, and the three test_pr_gate_overlap_routing failures are ENVIRONMENT (the integration image lacks uv and the locked .venv that run_pr_gate.sh correctly fails closed on; CI and the host provide both). |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T01:36:44+00:00 |
| updated_at | 2026-11-05T01:36:44+00:00 |
| depth | `standard` |
| estimate | 1 small PR |

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
| captured_at | `2026-11-05T01:36:44+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/root/.l9/gov-worktrees/claude-code__baseline-five-failures` |
| branch | `agent/claude-code/baseline-five-failures` |
| commit_sha | `061fae50dbc1c1e57280b8f94f0a4df783f746d9` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Fix at its source the baseline integration failure tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py::test_consumer_workspace_skips_the_governance_registry. ops/scripts/lib/workspace_kind.sh _workspace_kind_realpath shells out to python3; with no python3 on PATH both resolutions are empty, the comparison "" = "" holds, and classify_workspace_kind answers ssot for every workspace (fail-open: a consumer repository is treated as the governance SSOT). Replace the helper with shell builtins and refuse to equate two empty resolutions. The other baseline failures are out of scope: test_org_dotgithub single-reader was fixed by merged #814, and the three test_pr_gate_overlap_routing failures are ENVIRONMENT (the integration image lacks uv and the locked .venv that run_pr_gate.sh correctly fails closed on; CI and the host provide both).

### Scope in

- ops/scripts/lib/workspace_kind.sh: _workspace_kind_realpath and the ssot comparison in classify_workspace_kind
- ops/scripts/tests/test_workspace_kind.sh: one regression case

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | classify_workspace_kind returns consumer for a non-governance directory when python3 is unavailable (PATH stub exiting 127), and still returns ssot for the SSOT and ssot_checkout for an identity tree (V1) | `quality_gate` | V1: `bash ops/scripts/tests/test_workspace_kind.sh` → all cases PASS, including the python3-absent case | `true` |
| SP-02 | the new test_workspace_kind.sh case fails against the current helper and passes after the fix (V1, checkpoint C1) | `quality_gate` | V1: `bash ops/scripts/tests/test_workspace_kind.sh` → all cases PASS, including the python3-absent case; V4: `shellcheck ops/scripts/lib/workspace_kind.sh ops/scripts/tests/test_workspace_kind.sh` → no new findings | `true` |
| SP-03 | tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py passes inside the integration container image (l9-cg-deps:06fee41, PATH=/usr/bin:/bin, no python3 there) where it failed before (V3) | `quality_gate` | V2: `TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py` → all pass on the host; V3: `docker run --rm --init --network none --read-only --user 30033:30033 -e HOME=/tmp -e TESTING=true -e PYTHONPATH=/workspace --tmpfs /tmp:rw,exec --mount type=bind,src=$PWD,dst=/workspace l9-cg-deps:06fee41 python -m pytest -q -p no:cacheprovider tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py` → the previously failing test passes in the integration image | `true` |
| SP-04 | no consumer of classify_workspace_kind changes behaviour on a host that has python3 (V1, V2) | `quality_gate` | V1: `bash ops/scripts/tests/test_workspace_kind.sh` → all cases PASS, including the python3-absent case; V2: `TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py` → all pass on the host | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| source_ref | `plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P1 | pre-validation (status `passed`) | `Reproduce: run test_pr_gate_pytest_workspace_scope.py in docker image l9-cg-deps:06fee41 with --init --network none, HOME=/tmp; observe 'python3: command not found' and classify -> ssot` | the test fails with assert 'registry' == 'skip' and the bash -x trace shows ws_real='' gc_real='' | `true` |
| P2 | pre-validation (status `pending`) | `On the host at main@061fae5: bash ops/scripts/tests/test_workspace_kind.sh and pytest tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py` | both pass (baseline green where python3 exists); hook catalog is .pre-commit-config.yaml (shellcheck, ruff) | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/scripts/lib/workspace_kind.sh`, `ops/scripts/tests/test_workspace_kind.sh`
- **write_deny:** `tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py`, `tests/ops/scripts/test_pr_gate_overlap_routing.py`, `ops/scripts/ensure_gov_python.sh`, `ops/scripts/run_pr_gate.sh`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `bash ops/scripts/tests/test_workspace_kind.sh`, `.pre-commit-config.yaml`, `TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py`, `docker run --rm --init --network none --read-only --user 30033:30033 -e HOME=/tmp -e TESTING=true -e PYTHONPATH=/workspace --tmpfs /tmp:rw,exec --mount type=bind,src=$PWD,dst=/workspace l9-cg-deps:06fee41 python -m pytest -q -p no:cacheprovider tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py`, `shellcheck ops/scripts/lib/workspace_kind.sh ops/scripts/tests/test_workspace_kind.sh`, `.pre-commit-config.yaml hooks on the changed files (via the make pr gate)`
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

- classify_workspace_kind output vocabulary ssot | ssot_checkout | consumer
- identity files decide ssot_checkout
- gate locked-interpreter fail-closed contract

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/lib/workspace_kind.sh` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/scripts/tests/test_workspace_kind.sh` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `ops/scripts/lib` | `control_plane` | `classify_workspace_kind output vocabulary ssot \| ssot_checkout \| consumer`, `identity files decide ssot_checkout`, `gate locked-interpreter fail-closed contract` | `tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py`, `tests/ops/scripts/test_pr_gate_overlap_routing.py`, `ops/scripts/ensure_gov_python.sh`, `ops/scripts/run_pr_gate.sh` |
| T2 | `ops/scripts/tests` | `assurance` | `classify_workspace_kind output vocabulary ssot \| ssot_checkout \| consumer`, `identity files decide ssot_checkout`, `gate locked-interpreter fail-closed contract` | `tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py`, `tests/ops/scripts/test_pr_gate_overlap_routing.py`, `ops/scripts/ensure_gov_python.sh`, `ops/scripts/run_pr_gate.sh` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| source_execution_ref | `plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (the new case FAILS when the test runs against the pre-fix helper (git show HEAD:ops/scripts/lib/workspace_kind.sh copied into a scratch tree) and PASSES after T1) → stop; the regression case does not discriminate |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the single commit; no state or data migration |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `bash ops/scripts/tests/test_workspace_kind.sh`
- re-run `.pre-commit-config.yaml`
- re-run `TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py`
- re-run `docker run --rm --init --network none --read-only --user 30033:30033 -e HOME=/tmp -e TESTING=true -e PYTHONPATH=/workspace --tmpfs /tmp:rw,exec --mount type=bind,src=$PWD,dst=/workspace l9-cg-deps:06fee41 python -m pytest -q -p no:cacheprovider tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py`
- re-run `shellcheck ops/scripts/lib/workspace_kind.sh ops/scripts/tests/test_workspace_kind.sh`
- re-run `.pre-commit-config.yaml hooks on the changed files (via the make pr gate)`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 2 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `medium` — every caller of classify_workspace_kind (run_pr_gate.sh, session_start_bootstrap.sh, ensure_workspace_wired.sh, check_governance_wiring.sh, setup_workspace_symlinks.sh, validate_governance_symlinks.sh, workspace_link_health.sh, cursor_plans_store.sh); on hosts with python3 the results are unchanged |
| architectural_boundaries_crossed | none |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Replace the python3 call in _workspace_kind_realpath with builtins (expand a leading ~, then `cd -P -- "$p" && pwd -P` for an existing directory, else echo the expanded path unchanged), and in classify_workspace_kind answer ssot only when ws_real is non-empty and equals gc_real. | Cursor Build agent | `medium` | S | `[]` | `ops/scripts/lib/workspace_kind.sh` |
| T2 | Add one case to the existing test: prepend a bin dir whose python3 exits 127, then assert the consumer fixture stays consumer, the identity tree stays ssot_checkout and the live SSOT stays ssot. | Cursor Build agent | `low` | S | `[T1]` | `ops/scripts/tests/test_workspace_kind.sh` |

**Critical path:** T1 → T2

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | classifier is interpreter-independent and fails closed to consumer | the container baseline loses its workspace-scope failure; consumer gates no longer run the governance registry on python3-less hosts |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T2 | the new case FAILS when the test runs against the pre-fix helper (git show HEAD:ops/scripts/lib/workspace_kind.sh copied into a scratch tree) and PASSES after T1 | stop; the regression case does not discriminate |

### Leverage

- **Ranked todos:** `T1`, `T2`
- **Shared causes:** optional-interpreter dependency in a fail-closed identity check
- **Deletions / consolidations:** removes the python3 subprocess from the helper

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md / ARCHITECTURE.md / README | `n_a` | — | behaviour-preserving fix of an internal helper; no documented contract changes |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-04 | `quality_gate_evidence` | command | `bash ops/scripts/tests/test_workspace_kind.sh` | all cases PASS, including the python3-absent case | `not_run` |
| E-V2 | SP-03, SP-04 | `quality_gate_evidence` | command | `TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py` | all pass on the host | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `docker run --rm --init --network none --read-only --user 30033:30033 -e HOME=/tmp -e TESTING=true -e PYTHONPATH=/workspace --tmpfs /tmp:rw,exec --mount type=bind,src=$PWD,dst=/workspace l9-cg-deps:06fee41 python -m pytest -q -p no:cacheprovider tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py` | the previously failing test passes in the integration image | `not_run` |
| E-V4 | SP-02 | `quality_gate_evidence` | command | `shellcheck ops/scripts/lib/workspace_kind.sh ops/scripts/tests/test_workspace_kind.sh` | no new findings | `not_run` |
| E-V5 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml hooks on the changed files (via the make pr gate)` | all hooks pass | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does any caller pass a path that does not exist yet and rely on realpath resolving symlinked parents? (python realpath resolves parents of a missing leaf; the builtin keeps the literal path)
- Does any caller pass a file rather than a directory?
- Is ~ ever passed unexpanded?

### Assumption failure conditions

- If a missing GLOBAL_COMMANDS path previously equalled a workspace only through parent-symlink resolution, ssot detection would change; both sides are compared after identical treatment, so equality of two real directories is unchanged

### Blast radius notes

- every caller of classify_workspace_kind (run_pr_gate.sh, session_start_bootstrap.sh, ensure_workspace_wired.sh, check_governance_wiring.sh, setup_workspace_symlinks.sh, validate_governance_symlinks.sh, workspace_link_health.sh, cursor_plans_store.sh); on hosts with python3 the results are unchanged

### Rollback constraints

- revert the single commit; no state or data migration

### Risks

| risk | mitigation |
|------|------------|
| macOS /tmp -> /private/tmp: a lexical path would not equal a resolved one | cd -P / pwd -P resolves symlinks for existing directories, the same idiom ensure_gov_python.sh already relies on |
| a missing SSOT path now compares literally instead of via realpath of its parents | a missing SSOT cannot equal an existing workspace in either version; ssot requires both to be real directories |

## Out of scope

- tests/ops/scripts/test_pr_gate_overlap_routing.py: ENVIRONMENT, the gate's locked-interpreter contract (ensure_gov_python.sh) is correct to fail closed without uv
- ops/scripts/tests/test_org_dotgithub.py single-reader: fixed by #814
- integration image or Core toolchain changes (uv, wheel cache): would be new provisioning, excluded by the operator
- ops/autonomy/resolve_execution_gate.py: Python mirror of the identity test, unaffected
- any change to the test under repair (it encodes the correct contract)
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
| source_ref | `plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1` |
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
| `open_blocker` | stop_reason | plan validated; implementation not yet run | planning convergence `partial` |

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
  plan_id: "plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1"
  name: "workspace_kind.sh never classifies a workspace as ssot when python3 is absent"
  overview: "Fix at its source the baseline integration failure tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py::test_consumer_workspace_skips_the_governance_registry. ops/scripts/lib/workspace_kind.sh _workspace_kind_realpath shells out to python3; with no python3 on PATH both resolutions are empty, the comparison \"\" = \"\" holds, and classify_workspace_kind answers ssot for every workspace (fail-open: a consumer repository is treated as the governance SSOT). Replace the helper with shell builtins and refuse to equate two empty resolutions. The other baseline failures are out of scope: test_org_dotgithub single-reader was fixed by merged #814, and the three test_pr_gate_overlap_routing failures are ENVIRONMENT (the integration image lacks uv and the locked .venv that run_pr_gate.sh correctly fails closed on; CI and the host provide both)."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "061fae50dbc1c1e57280b8f94f0a4df783f746d9"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Fix at its source the baseline integration failure tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py::test_consumer_workspace_skips_the_governance_registry. ops/scripts/lib/workspace_kind.sh _workspace_kind_realpath shells out to python3; with no python3 on PATH both resolutions are empty, the comparison \"\" = \"\" holds, and classify_workspace_kind answers ssot for every workspace (fail-open: a consumer repository is treated as the governance SSOT). Replace the helper with shell builtins and refuse to equate two empty resolutions. The other baseline failures are out of scope: test_org_dotgithub single-reader was fixed by merged #814, and the three test_pr_gate_overlap_routing failures are ENVIRONMENT (the integration image lacks uv and the locked .venv that run_pr_gate.sh correctly fails closed on; CI and the host provide both)."
  success_properties:
    - id: "SP-01"
      property: "classify_workspace_kind returns consumer for a non-governance directory when python3 is unavailable (PATH stub exiting 127), and still returns ssot for the SSOT and ssot_checkout for an identity tree (V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "the new test_workspace_kind.sh case fails against the current helper and passes after the fix (V1, checkpoint C1)"
      evidence_type: "quality_gate"
      proof: ["V1", "V4"]
      blocking: true
    - id: "SP-03"
      property: "tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py passes inside the integration container image (l9-cg-deps:06fee41, PATH=/usr/bin:/bin, no python3 there) where it failed before (V3)"
      evidence_type: "quality_gate"
      proof: ["V2", "V3"]
      blocking: true
    - id: "SP-04"
      property: "no consumer of classify_workspace_kind changes behaviour on a host that has python3 (V1, V2)"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/scripts/lib/workspace_kind.sh", "ops/scripts/tests/test_workspace_kind.sh"]
    write_deny: ["tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py", "tests/ops/scripts/test_pr_gate_overlap_routing.py", "ops/scripts/ensure_gov_python.sh", "ops/scripts/run_pr_gate.sh"]
  commands:
    allow: ["bash ops/scripts/tests/test_workspace_kind.sh", ".pre-commit-config.yaml", "TESTING=true .venv/bin/python -m pytest -q tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py tests/ops/scripts/test_workspace_link_health.py", "docker run --rm --init --network none --read-only --user 30033:30033 -e HOME=/tmp -e TESTING=true -e PYTHONPATH=/workspace --tmpfs /tmp:rw,exec --mount type=bind,src=$PWD,dst=/workspace l9-cg-deps:06fee41 python -m pytest -q -p no:cacheprovider tests/ops/scripts/test_pr_gate_pytest_workspace_scope.py", "shellcheck ops/scripts/lib/workspace_kind.sh ops/scripts/tests/test_workspace_kind.sh", ".pre-commit-config.yaml hooks on the changed files (via the make pr gate)"]
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
rollback_contract_ref: "rollback.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1"
dependency_topology_ref: "dag.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5"]
stress_and_disconfirm:
  disconfirming_cases: ["Does any caller pass a path that does not exist yet and rely on realpath resolving symlinked parents? (python realpath resolves parents of a missing leaf; the builtin keeps the literal path)", "Does any caller pass a file rather than a directory?", "Is ~ ever passed unexpanded?"]
  assumption_failure_conditions: ["If a missing GLOBAL_COMMANDS path previously equalled a workspace only through parent-symlink resolution, ssot detection would change; both sides are compared after identical treatment, so equality of two real directories is unchanged"]
out_of_scope: ["tests/ops/scripts/test_pr_gate_overlap_routing.py: ENVIRONMENT, the gate's locked-interpreter contract (ensure_gov_python.sh) is correct to fail closed without uv", "ops/scripts/tests/test_org_dotgithub.py single-reader: fixed by #814", "integration image or Core toolchain changes (uv, wheel cache): would be new provisioning, excluded by the operator", "ops/autonomy/resolve_execution_gate.py: Python mirror of the identity test, unaffected", "any change to the test under repair (it encodes the correct contract)"]
convergence_contract_ref: "conv.plan.simple.workspace_kind_sh_never_classifies_a_workspace_as_ssot_when_python3_is_absent.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Replace the python3 call in _workspace_kind_realpath with builtins (expand a leading ~, then `cd -P -- \"$p\" && pwd -P` for an existing directory, else echo the expanded path unchanged), and in classify_workspace_kind answer ssot only when ws_real is non-empty and equals gc_real."
    status: "pending"
  - id: "T2"
    content: "Add one case to the existing test: prepend a bin dir whose python3 exits 127, then assert the consumer fixture stays consumer, the identity tree stays ssot_checkout and the live SSOT stays ssot."
    status: "pending"
```
