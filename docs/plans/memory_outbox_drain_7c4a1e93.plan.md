---
name: Memory outbox drain: give DESTINATION_SUBMITTED an owner
overview: "Close RC-3. Generated-data memory candidates are durably enqueued to a file outbox and land in PipelineState.DESTINATION_SUBMITTED, which is deliberately non-terminal, but no component in the repository ever reads that outbox or advances that state. Add the single missing consumer inside the existing DeliveryWorker, reusing the existing transports, retry policy, receipt chain and state machine,..."
todos:
  - id: todo-01-baseline-preflight
    content: "Lock the baseline and re-run CP-01..CP-05. Record the observed live outbox path and the observed transport availability into the plan's evidence section. Stop and replan on baseline drift."
    status: pending
    phase: execute
    depends_on: []
  - id: todo-02-unify-outbox-path
    content: "Resolve AI-002 duplicate location. ingest.py writes $L9_RUNTIME_ROOT/generated-data/outbox/memory while DeliveryWorkerConfiguration.memory_outbox and graphiti_memory._MEMORY_OUTBOX_DIR default to environment/agents/generated-data/.runtime/memory-outbox. Add one canonical resolver (memory_outbox_root()) in environment/agents/runtime_paths.py, make the adapter constant and the dataclass default resolve through it, and have the drain read exactly that. If any candidate files exist at the legacy location, the drain must adopt them once and log the adoption; it must not silently ignore them."
    status: pending
    phase: execute
    depends_on: [todo-01-baseline-preflight]
  - id: todo-03-implement-drain
    content: "Add DeliveryWorker.drain_memory_outbox(actor, limit) plus a --drain CLI flag. For each candidate file in the canonical outbox: look up its job, require current state DESTINATION_SUBMITTED, record a delivery_attempt with the existing idempotency_key, deliver through select_transport() (HttpJsonTransport or CommandTransport — never FileOutboxTransport, which would be a self-loop), then advance to DESTINATION_ACCEPTED on a real acceptance receipt, DESTINATION_REJECTED on a permanent rejection, RETRY_WAIT under the existing RetryPolicy on a transient failure, and DEAD_LETTERED at the policy ceiling. Remove the outbox file only after the terminal transition commits. Call recalculate_campaign_state so a fully drained campaign can finally reach completed. Fail closed: with no live transport configured, record the failed attempt and leave the job in DESTINATION_SUBMITTED."
    status: pending
    phase: execute
    depends_on: [todo-02-unify-outbox-path]
  - id: todo-04-drain-on-next-delivery
    content: "Give the drain a trigger without adding a scheduler. At the start of DeliveryWorker.run_batch, opportunistically drain a bounded number of outbox candidates before selecting new jobs, so ordinary pipeline activity clears the backlog. Keep the bound explicit and configurable, and make the opportunistic drain non-fatal: a drain failure must never fail the delivery run that triggered it."
    status: pending
    phase: execute
    depends_on: [todo-03-implement-drain]
  - id: todo-05-surface-backlog
    content: "Now that a drain exists, complete the change TASK-05 deliberately deferred. Extend campaign_summary.build_summary()'s memory section with measured outbox_backlog_count and outbox_oldest_candidate_age_seconds, following the existing None -> UNKNOWN convention for anything not measured. Do not infer persistence from enqueue. render_brief must show backlog distinctly from submitted."
    status: pending
    phase: execute
    depends_on: [todo-03-implement-drain]
  - id: todo-06-tests
    content: "Add drain tests: (a) success advances SUBMITTED -> ACCEPTED and removes the file; (b) unconfigured or unreachable transport leaves SUBMITTED, records a failed attempt, marks nothing accepted; (c) a second drain of the same candidate is idempotent; (d) transient failure routes to RETRY_WAIT and the policy ceiling routes to DEAD_LETTERED; (e) legacy-location candidates are adopted, not ignored; (f) campaign reaches completed only after drain. Then update test_enqueued_is_not_reported_as_persisted in the hardening E2E: it currently characterises the unfixed gap and must be rewritten to assert the drained end state rather than deleted."
    status: pending
    phase: execute
    depends_on: [todo-03-implement-drain, todo-04-drain-on-next-delivery, todo-05-surface-backlog]
  - id: todo-07-converge
    content: "Run the repo's fast checks and the affected suites, update docs/handoffs/PE_SWARM_MEMORY_REMEDIATION_FINDINGS.md to move RC-3 from ESCALATED to CLOSED with the evidence, then converge to a green PR. Do not merge."
    status: pending
    phase: execute
    depends_on: [todo-06-tests]
isProject: false
kind: simple
execute_via: cursor-build
---

# PLAN: Memory outbox drain: give DESTINATION_SUBMITTED an owner

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Work in the current checkout. Do not run `make campaign`.
> **Suggested filename:** `memory-outbox-drain-give-destination-submitted-an-owner_86de98a7.plan.md`

## Objective (from PLAN_DOCUMENT)

Close RC-3. Generated-data memory candidates are durably enqueued to a file outbox and land in PipelineState.DESTINATION_SUBMITTED, which is deliberately non-terminal, but no component in the repository ever reads that outbox or advances that state. Add the single missing consumer inside the existing DeliveryWorker, reusing the existing transports, retry policy, receipt chain and state machine, and unify the two divergent outbox locations under one canonical owner. Introduce no new store, queue, service, scheduler, or memory writer.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | A memory candidate enqueued to the canonical outbox is delivered to Graphiti by a named owner, and its job advances DESTINATION_SUBMITTED -> DESTINATION_ACCEPTED with a real destination receipt. | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | A drain attempt against an unreachable or unconfigured transport leaves the job in DESTINATION_SUBMITTED, records a failed delivery_attempt, and never marks DESTINATION_ACCEPTED. | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | Repeated drains of the same candidate are idempotent: the second pass reports deduplicated or already_delivered and performs no second non-idempotent write. | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | Exactly one canonical filesystem location holds memory-route candidates; the divergent second location is removed or aliased to the canonical resolver, and both writers and the drain resolve it through one function. | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | campaign_summary.py reports outbox backlog and oldest-candidate age as measured values, distinguishable from healthy submission, following the existing None -> UNKNOWN convention. | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | A campaign whose only memory delivery was outbox-enqueued can reach campaigns.state == completed after a successful drain, instead of remaining active forever. | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | No new state store, queue, service, scheduler, coordination protocol, or memory writer is introduced. | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** environment/agents/generated-data/orchestration/delivery_worker.py — add outbox drain owned by the existing worker, environment/agents/generated-data/adapters/graphiti_memory.py — outbox path resolution and drain-side read helper, environment/agents/runtime_paths.py — one canonical memory-outbox resolver, environment/agents/generated-data/ingress/ingest.py — use the canonical resolver, environment/program-execution/integrations/subagent-generated-data/campaign_summary.py — backlog and staleness reporting, tests for drain success, drain failure, idempotency, and path unification, extension of environment/program-execution/tests/hardening/test_real_campaign_e2e.py where it currently characterises the unfixed gap

**Out:**
- Non-memory route outboxes written by RouteOutboxTransport (<route>-outbox) — same class of defect, different destination systems, separate plan
- ops/graphiti/distill_queue — a distinct S3-backed session-transcript pipeline, confirmed non-overlapping in TASK-01
- Any change to Graphiti server-side ingestion semantics
- Adding a scheduler, daemon, cron, or GitHub Actions runner for the drain
- Changing the deliberate decision at ingest.py:105-107 that a missing live transport must still durably enqueue
- Widening the generated-data pipeline's authority or publication boundary

## Critical path (seed)

todo-01-baseline-preflight → todo-02-unify-outbox-path → todo-03-implement-drain → todo-06-tests → todo-07-converge

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Medium. The change is confined to the generated-data delivery component plus one summary module, and adds a forward transition to a state that is currently a dead end, so existing terminal outcomes are unaffected. The realistic failure mode is a drain that marks ACCEPTED without a receipt, which would convert a visible stall into invisible data loss — worse than today. CK-02 exists specifically to block that.
- Rollback: Every change is additive and revertible by scoped git restore of the listed files. The drain is opt-in at the call site, so reverting todo-04 alone disables automatic draining while leaving the CLI. No data migration occurs: candidate files are only removed after a committed terminal transition, so an aborted drain leaves the outbox intact.

## Convergence (seed)

- status: partial
- next_skill: Build (current checkout)
- stop_reason: Plan is execution-ready. U1 is bounded by design (the fail-closed path is required regardless of transport availability) and does not block execution. U2, U3 and U4 are probes scheduled inside todo-01 and todo-02 and are resolved before the first irreversible change at todo-03.
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Memory outbox drain: give DESTINATION_SUBMITTED an owner

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, press **Build** and work in the **current checkout**. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.memory.outbox_drain.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` *(frontmatter `isProject`)* |
| owner | generated-data delivery (DeliveryWorker) |
| created_at | `2026-08-27` |
| updated_at | `2026-08-27` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | path or ADR that owns architecture for this change |
| plan_class | `bounded_execution_contract` \| `migration_plan` \| `retirement_plan` \| `remediation_plan` \| `deployment_plan` \| `refactor_plan` \| `integration_plan` \| `recovery_plan` \| `custom` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build on the current checkout; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-27T05:20:00Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | absolute or `$(pwd)` convention |
| ssot_clone | if applicable |
| branch | `claude/cursor-governance-remediate-kpzvnr` |
| commit_sha | `f4265dcc58ff8ebee7896a1a89c9f298c9e8e5c8` |
| dirty | `false` |
| artifact_hashes | `{ "path": "sha256:…" }` |
| allowed_local_dirt | optional path list |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` \| `require_clean_tree` \| `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

One paragraph: residual defect or feature; system bound; non-negotiable preserved contracts.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline still matches locked SHA at start | `repository_state` | `git rev-parse HEAD` == locked SHA | true |
| SP-02 | Declared behavior/structure holds after mutation | `runtime_behavior` \| `structural` \| `filesystem` | exact command + expected marker (not exit-0 alone) | true |
| SP-03 | Quality gate / PR gate PASS on changed files | `quality_gate` | e.g. `make pr-check` → PASS | true |

`evidence_type` ∈ `filesystem` \| `runtime_behavior` \| `structural` \| `quality_gate` \| `repository_state` \| `network_observation` \| `proof_receipt` \| `human_confirmation`

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → fill path or inline id below.

| Field | Value |
|-------|-------|
| preflight_id | `preflight.<plan_id>` |
| source_ref | this plan_id |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | baseline section / receipt path |
| baseline_verified | |
| drift_detected | |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | equals locked commit_sha | true |
| CP-02 | `command_available` | tool X present | version / path | true |
| CP-03 | `filesystem_write` | may_modify paths writable | write probe or ACL | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `path/or/glob/...`
- **write_deny:** `protected/...`, secrets, unrelated trees
- **delete_allow:** *(optional)*

### Commands

- **allow:** listed validation / mutate commands
- **deny:** force-push, hard-reset, secret exfil, out-of-scope installs

### Network

| Field | Value |
|-------|-------|
| mode | `none` \| `read_only` \| `named_services_only` \| `existing_tunnel_only` \| `bounded_external_write` |
| allowed_services | *(if named_services_only / bounded)* |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` \| `read_only_named` \| `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005).

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| todo-01-baseline-preflight | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| todo-02-mutate | `filesystem_mutation` | `safe_with_dedupe` \| `unsafe_blind_repeat` \| `non_idempotent` | `manual_only` \| `retry_once` \| `bounded_retry` | restore scoped paths / revert | false |
| todo-03-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |
| todo-04-converge | `network_write` \| `none` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

`side_effects` ∈ `none` \| `filesystem_read` \| `filesystem_mutation` \| `destructive_filesystem_mutation` \| `network_read` \| `network_write` \| `database_read` \| `database_write` \| `external_state_mutation` \| `human_approval`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| todo-02-mutate | e.g. memory / ops / adapters | `control_plane` \| `data_plane` \| `chassis` \| `ops` \| `runtime` \| `policy` \| `assurance` \| `memory` \| `graph` \| `docs` \| `external_system` | ADR / schema / skill that owns it | redesign X; touch Y; invent Z |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.<plan_id>` |
| source_execution_ref | this plan_id |
| supported | `true` \| `false` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` \| `revert_commit` \| `none` | scoped to write_allow |
| data | `none` \| `restore_snapshot` \| `compensating_transaction` \| `manual_recovery` | |
| external_state | `none` \| `corrective_append_only_record` \| `manual_recovery` | never claim false reversibility |
| local_state | `none` \| `git_restore_scoped_paths` \| `manual_recovery` | |

### Irreversible operations

- *(enumerate; PLAN-SCHEMA-010)* none | …

### Rollback verification

- command / proof that rollback restored invariants

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` \| `medium` \| `high` \| `critical` |
| uncertainty | `low` \| `medium` \| `high` \| `critical` |
| blast_radius | `low` \| `medium` \| `high` \| `critical` |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `0` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | |
| categories | `delete` \| `migrate_then_delete` \| `keep` \| `replace` \| `skip` |
| checksum_required | `true` |
| destructive_gate_required_for | `migrate_then_delete` |

## Gated write pipeline *(optional — irreversible or external writes)*

- **gates (ordered):** …
- **dedupe_before_non_idempotent_write:** `true`
- **bounded_write_count:**
- **receipt_required:** `true`

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| RG-01 | regenerator path / script | disable or retarget | prove artifact not recreated |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.<plan_id>` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| todo-01-baseline-preflight | agent | assurance | [] | baseline_receipt, preflight_receipt |
| todo-02-mutate | agent | *(layer)* | [todo-01-baseline-preflight] | mutated paths |
| todo-03-prove | agent | assurance | [todo-02-mutate] | validation_evidence refs |
| todo-04-converge | agent | control_plane | [todo-03-prove] | convergence receipt / PR |

**Critical path:** `todo-01-baseline-preflight` → `todo-02-mutate` → `todo-03-prove` → `todo-04-converge`

**Forbidden edges:** *(none, or list cycles / illegal orderings)*

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | locked SHA | `not_run` |
| EV-SP-02 | SP-02 | `property_evidence` \| `structural_evidence` \| `runtime_behavior_evidence` | … | … | marker / structure | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Assumption A false → …
- Probe/environment differs from baseline capture → …

### Assumption failure conditions

- Dirty tree overlaps `write_allow` under `stop_if_dirty_overlaps_may_modify`
- Blocking success property fails after mutation
- Unknown dependency discovered mid-flight (PLAN-SCHEMA-013)

### Blast radius notes

- …

### Rollback constraints

- No force-push / history rewrite
- External append-only systems → compensating record only

## Out of scope

- Adjacent features / refactors not listed in envelope
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | … | … |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.<plan_id>` |
| source_ref | this plan_id |
| current_state | `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `false` until preflight + DAG + envelope filled |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking SP-* evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** `EV-SP-01`, `EV-SP-02`, `EV-SP-03`
- **observed_evidence_refs:** *(fill during execution)*
- **missing_evidence:** *(fill)*

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | | | |
| unknown | U1 | | ask / measure / lock — do not infer away |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build** and work in the current checkout — do not free-form execute |
| execute_via | Cursor Build on the current checkout |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.memory.outbox_drain.v1
  name: Short plan title
  overview: "…"
  status: executable
  is_project: false
  created_at: 2026-08-27
architect_framing:
  planning_ssot: …
  plan_class: bounded_execution_contract
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: org/repo
  commit_sha: f4265dcc58ff8ebee7896a1a89c9f298c9e8e5c8
  dirty: false
  artifact_hashes: {}
  overlap_policy: stop_if_dirty_overlaps_may_modify
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: …
  success_properties:
    - id: SP-01
      property: …
      evidence_type: repository_state
      proof: …
      blocking: true
capability_preflight_ref: preflight.plan.domain.slug.v1
execution_envelope:
  filesystem:
    write_allow: []
    write_deny: []
  commands:
    allow: []
    deny: []
  network:
    mode: none
  secrets:
    access: none
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: rollback.plan.domain.slug.v1
complexity_and_uncertainty:
  complexity: low
  uncertainty: low
  blast_radius: low
  architectural_boundaries_crossed: 0
  external_systems_touched: 0
  migration_required: false
  unknown_dependency_count: 0
dependency_topology_ref: dag.plan.domain.slug.v1
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: conv.plan.domain.slug.v1
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: current checkout
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: todo-01-baseline-preflight
    content: …
    status: pending
```

