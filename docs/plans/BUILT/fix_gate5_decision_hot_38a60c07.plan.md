---
name: Lock the web-lead rehearsal to the controller receipt
overview: The production rehearsal must not fail a real hot classification because
  it expected the label HOT. The live controller returns decision hot and finishes
  a successful lead at state intake_created. That comparison is already on local Staging
  at 38a60c07. The remaining work is a static test so the string expected HOT cannot
  return. The later state=error Expected singleton res.users() failure is a...
todos:
- id: T1
  content: Add a pytest that reads tests/production-rehearsal/weblead_e2e.sh and fails
    if it contains expected HOT or compares decision to HOT. It passes only when the
    script compares decision to hot and requires state intake_created. Do not edit
    the webhook or the already-corrected comparison.
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Lock the web-lead rehearsal to the controller receipt

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `lock_the_web_lead_rehearsal_to_the_controller_receipt_b4387179.plan.md`
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
| plan_id | `plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| name | Lock the web-lead rehearsal to the controller receipt |
| overview | The production rehearsal must not fail a real hot classification because it expected the label HOT. The live controller returns decision hot and finishes a successful lead at state intake_created. That comparison is already on local Staging at 38a60c07. The remaining work is a static test so the string expected HOT cannot return. The later state=error Expected singleton res.users() failure is a product defect and is not this plan. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-06T19:11:16+00:00 |
| updated_at | 2026-11-06T19:11:16+00:00 |
| depth | `standard` |
| estimate | one small test |

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
| captured_at | `2026-11-06T19:11:16+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `Staging` |
| commit_sha | `38a60c07bbeaa99f49b804bcb1041a2e896460af` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

The production rehearsal must not fail a real hot classification because it expected the label HOT. The live controller returns decision hot and finishes a successful lead at state intake_created. That comparison is already on local Staging at 38a60c07. The remaining work is a static test so the string expected HOT cannot return. The later state=error Expected singleton res.users() failure is a product defect and is not this plan.

### Scope in

- tests/test_rehearsal_web_lead_receipt.py
- tests/production-rehearsal/weblead_e2e.sh
- tests/production-rehearsal/SPEC.md

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves tests/test_rehearsal_web_lead_receipt.py exits 0 and rejects the rehearsal text expected HOT | `quality_gate` | V1: `python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q` → exit 0; the test fails if weblead_e2e.sh contains expected HOT; V2: `.pre-commit-config.yaml` → ruff and the commit-stage hooks pass on tests/test_rehearsal_web_lead_receipt.py | `true` |
| SP-02 | V1 proves weblead_e2e.sh compares decision to hot and requires state intake_created | `quality_gate` | V1: `python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q` → exit 0; the test fails if weblead_e2e.sh contains expected HOT | `true` |
| SP-03 | V2 runs the .pre-commit-config.yaml catalog on the new test file | `quality_gate` | V2: `.pre-commit-config.yaml` → ruff and the commit-stage hooks pass on tests/test_rehearsal_web_lead_receipt.py | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| source_ref | `plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD` | branch Staging at 38a60c07, which already expects decision hot | `true` |
| P1 | pre-validation (status `passed`) | `read weblead_e2e.sh decision check and web_lead_api.py response_data` | script compares to hot; controller sets decision from lead.decision, whose selection value is hot | `true` |
| P2 | pre-validation (status `passed`) | `name .pre-commit-config.yaml as the hook catalog for the test file` | catalog exists; no origin/main lock and no new worktree | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/test_rehearsal_web_lead_receipt.py`
- **write_deny:** `plasticos_web_leads/`, `plasticos_crm_bridge/`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q`, `.pre-commit-config.yaml`
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

- decision value is hot
- success state is intake_created
- POST /api/v1/cognito-webhook remains the only admission call

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_rehearsal_web_lead_receipt.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests` | `assurance` | `decision value is hot`, `success state is intake_created`, `POST /api/v1/cognito-webhook remains the only admission call` | `plasticos_web_leads/`, `plasticos_crm_bridge/` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| source_execution_ref | `plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 exit 0) → do not publish a rehearsal script that again requires HOT |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the test file; leave 38a60c07 in place |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` — highest todo risk across 1 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `low` — a wrong assertion fails a real hot lead before the pipeline error is visible |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Add a pytest that reads tests/production-rehearsal/weblead_e2e.sh and fails if it contains expected HOT or compares decision to HOT. It passes only when the script compares decision to hot and requires state intake_created. Do not edit the webhook or the already-corrected comparison. | Cursor Build agent | `low` | S | `[]` | `tests/test_rehearsal_web_lead_receipt.py` |

**Critical path:** T1

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | the old expected HOT failure cannot be reintroduced without a red test | stacked publication with 38a60c07 |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 exit 0 | do not publish a rehearsal script that again requires HOT |

### Leverage

- **Ranked todos:** `T1`
- **Shared causes:** rehearsal asserted the display label HOT
- **Deletions / consolidations:** do not add a parallel decision normalizer in the rehearsal

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | the rehearsal receipt is owned by the controller and SPEC.md, which already names decision hot |
| tests/production-rehearsal/SPEC.md | `n_a` | — | 38a60c07 already states decision hot and state intake_created |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q` | exit 0; the test fails if weblead_e2e.sh contains expected HOT | `not_run` |
| E-V2 | SP-01, SP-03 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | ruff and the commit-stage hooks pass on tests/test_rehearsal_web_lead_receipt.py | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does the controller ever return the label HOT in decision?
- Would changing only the test leave expected HOT in weblead_e2e.sh?
- Is the res.users singleton the same defect as the HOT label check?

### Assumption failure conditions

- the selection value were HOT rather than hot
- Build rewrote triage to make the rehearsal pass

### Blast radius notes

- a wrong assertion fails a real hot lead before the pipeline error is visible

### Rollback constraints

- revert the test file; leave 38a60c07 in place

### Risks

| risk | mitigation |
|------|------------|
| Build treats the later res.users error as part of this plan and edits web_lead.py | scope out names that file and the singleton; T1 is a reader of the rehearsal script only |

## Out of scope

- plasticos_web_leads triage and the Expected singleton res.users() error
- a second admission path or a system-parameter bearer
- ERP and VanillaSoft rehearsal gates
- pushing or opening the pull request during planning
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
| source_ref | `plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1` |
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

- **required_evidence_refs:** E-V1, E-V2
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `open_blocker` | stop_reason | the HOT label check is already corrected at 38a60c07; the regression test is not written | planning convergence `partial` |

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
  plan_id: "plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1"
  name: "Lock the web-lead rehearsal to the controller receipt"
  overview: "The production rehearsal must not fail a real hot classification because it expected the label HOT. The live controller returns decision hot and finishes a successful lead at state intake_created. That comparison is already on local Staging at 38a60c07. The remaining work is a static test so the string expected HOT cannot return. The later state=error Expected singleton res.users() failure is a product defect and is not this plan."
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
  commit_sha: "38a60c07bbeaa99f49b804bcb1041a2e896460af"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "The production rehearsal must not fail a real hot classification because it expected the label HOT. The live controller returns decision hot and finishes a successful lead at state intake_created. That comparison is already on local Staging at 38a60c07. The remaining work is a static test so the string expected HOT cannot return. The later state=error Expected singleton res.users() failure is a product defect and is not this plan."
  success_properties:
    - id: "SP-01"
      property: "V1 proves tests/test_rehearsal_web_lead_receipt.py exits 0 and rejects the rehearsal text expected HOT"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-02"
      property: "V1 proves weblead_e2e.sh compares decision to hot and requires state intake_created"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-03"
      property: "V2 runs the .pre-commit-config.yaml catalog on the new test file"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/test_rehearsal_web_lead_receipt.py"]
    write_deny: ["plasticos_web_leads/", "plasticos_crm_bridge/"]
  commands:
    allow: ["python3 -m pytest tests/test_rehearsal_web_lead_receipt.py -q", ".pre-commit-config.yaml"]
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
rollback_contract_ref: "rollback.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1"
dependency_topology_ref: "dag.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1"
validation_evidence_refs: ["E-V1", "E-V2"]
stress_and_disconfirm:
  disconfirming_cases: ["Does the controller ever return the label HOT in decision?", "Would changing only the test leave expected HOT in weblead_e2e.sh?", "Is the res.users singleton the same defect as the HOT label check?"]
  assumption_failure_conditions: ["the selection value were HOT rather than hot", "Build rewrote triage to make the rehearsal pass"]
out_of_scope: ["plasticos_web_leads triage and the Expected singleton res.users() error", "a second admission path or a system-parameter bearer", "ERP and VanillaSoft rehearsal gates", "pushing or opening the pull request during planning"]
convergence_contract_ref: "conv.plan.simple.lock_the_web_lead_rehearsal_to_the_controller_receipt.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Add a pytest that reads tests/production-rehearsal/weblead_e2e.sh and fails if it contains expected HOT or compares decision to HOT. It passes only when the script compares decision to hot and requires state intake_created. Do not edit the webhook or the already-corrected comparison."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-06T19:21:17Z`
- conversation_id: `844a066e-f5ef-49d9-9116-466ce9f65ea7`
- generation_id: `0345379b-f0fe-4ec0-8584-f0e0e36941bd`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/844a066e-f5ef-49d9-9116-466ce9f65ea7/844a066e-f5ef-49d9-9116-466ce9f65ea7.jsonl`
- todos at build time:
- `T1`: completed
