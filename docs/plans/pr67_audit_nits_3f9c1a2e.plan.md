---
name: Close the PR #67 audit nits in l9-cognitive-runtime
overview: "Fix the three non-blocking audit findings on PR #67 that need no owner decision: route MCP pack resources and adapter templates through manifest-verified reads, fail closed on malformed adapter placeholder markers, and bind closure relevance to planned requirements"
todos:
  - id: T1
    content: "Serve MCP schema and kernel resources through pack.read_verified and add tamper and unlisted-file regression tests"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Add AdapterRenderer pack= verified mode: listed template via read_verified, unlisted on-disk template fails closed, absent template uses DEFAULT_TEMPLATE; pack and pack_root are mutually exclusive"
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Fail closed when template text still carries a {{ or }} marker after known tokens are removed; regression test with {{a{b}}}"
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "Extend closure check 4 so selected_because must be a non-empty subset of planned requirement ids; regression test with a forged unplanned binding"
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "Run the CLAUDE.md verify block and prove each new test fails on b87a5e79 sources"
    status: pending
    phase: execute
    depends_on: [T1, T2, T3, T4]
isProject: false
kind: simple
execute_via: cursor-build
status: current
kernel_pass:
  bound_path: docs/plans/pr67_audit_nits_3f9c1a2e.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-10-29T15:52:00Z
    body_sha256: "8d22e08466e439b764d5db17b3eb2d6769f77627e90166ae8042efe4d46620f9"
    deltas:
      - "T4 anchored to context_closure.py:218 with its test placed beside test_an_unbound_selected_item_is_detected_by_closure, reusing the _context/_plan/_requirement/law helpers"
      - "Success criterion 5 states that T2 fails on base by construction (pack= is absent at b87a5e79) instead of implying a behavioural fail-before"
      - "Template body filled: framing, baseline, preflight probes, envelope, side effects, architecture impact, rollback, DAG, evidence matrix, convergence"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-10-29T15:54:00Z
    body_sha256: "8d22e08466e439b764d5db17b3eb2d6769f77627e90166ae8042efe4d46620f9"
    deltas:
      - "Out-of-scope reason for the liveness twin aligned to evidence: validate_runtime_semantic_liveness (liveness.py:101) takes no requirement_plan"
      - "Preserved contract added: check name every_selected_item_has_relevance_binding stays in REQUIRED_CHECKS (context_closure.py:72), so a closure receipt is unchanged"
      - "Architecture recorded as settled: the fixes reuse RuntimePack.read_verified, AdapterRenderer and ContextClosureValidator; no new module or reader (GAR applied as an architecture-settled determination, not a full GAR runtime run)"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-10-29T15:56:00Z
    body_sha256: "8d22e08466e439b764d5db17b3eb2d6769f77627e90166ae8042efe4d46620f9"
    deltas:
      - "Repaired PLAN_DOCUMENT unknowns to the schema object shape (G_SCHEMA failure on first validation)"
      - "Validated: validate_plan_document.py PASS and section receipt PASS after re-render"
      - "Repaired the envelope deny list so it names no forbidden command form literally"
---

# PLAN: Close the PR #67 audit nits in l9-cognitive-runtime

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `close-the-pr-67-audit-nits-in-l9-cognitive-runtime_25c5dc47.plan.md`

## Objective (from PLAN_DOCUMENT)

Fix the three non-blocking audit findings on PR #67 that need no owner decision: route MCP pack resources and adapter templates through manifest-verified reads, fail closed on malformed adapter placeholder markers, and bind closure relevance to planned requirements

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | MCP kernels/{id} and schemas/{name} resources read through RuntimePack.read_verified: a post-load tampered or unlisted file raises instead of being served | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | AdapterRenderer(pack=RuntimePack) renders listed templates through read_verified; a tampered listed template or an unlisted on-disk template fails closed; pack_root mode is unchanged | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | A template containing a brace-bearing token such as {{a{b}}} fails closed with 'adapter template left placeholders unresolved'; every shipped template still renders | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | ContextClosureValidator check every_selected_item_has_relevance_binding fails when an item's selected_because names a requirement id absent from requirement_plan | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | Each new regression test fails on b87a5e79 sources (T2 fails by construction: pack= does not exist on base) and passes after the fix | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | ruff check, ruff format --check, mypy strict, and the full pytest suite pass in the worktree | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** src/l9_cognitive_runtime/mcp/__init__.py _read_pack_file, src/l9_cognitive_runtime/compiler/adapters.py AdapterRenderer template read and placeholder residue check, src/l9_cognitive_runtime/compiler/context_closure.py check 4, regression tests in tests/test_mcp_stdio.py, tests/test_gar_adapter_packet.py, tests/test_context_compiler.py

**Out:**
- Audit nit 3 (CLI raw-size pre-read bound): conflicts with the RU-16 documented rule that file formatting neither admits nor refuses a payload; owner decision required
- liveness.py check 19 twin of the relevance binding: validate_runtime_semantic_liveness (liveness.py:101) receives no requirement_plan, so plan membership cannot be checked there
- l9-pr-digest tooling defects in Cursor-Governance
- CONTEXT_COMPILER_SEMANTICS_VERSION bump (compiled output is unchanged)
- Edits to PR #67 branch history

## Critical path (seed)

T2 → T3 → T5

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: MCP resource reads, adapter projection for hosts, and context closure for every compile; a wrong T4 would fail every compile closed
- Rollback: revert the stacked PR or the individual unit commit; no data, migration, or external state

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: plan validated; UNK-01 is excluded scope awaiting owner decision
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Close the PR #67 audit nits in l9-cognitive-runtime

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every `n/a` is an instance slot. Backtick tokens are the closed vocabulary for that field. Replace each parameter before status becomes `executable`. Leave no sample instance in a delivered plan.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **Rename to:** `<snake_case_name>_<8hex>.plan.md` before execute.
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
| plan_id | `plan.l9-cognitive-runtime.pr67-audit-nits.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `in_progress` — `draft` \| `preflight_blocked` \| `executable` \| `in_progress` \| `validation_failed` \| `converged` \| `superseded` |
| is_project | *(frontmatter `isProject`)* |
| owner | `claude-code` |
| created_at | `2026-10-29T15:40:00Z` |
| updated_at | `2026-10-29T16:05:00Z` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `docs/plans/pr67_audit_nits_3f9c1a2e.plan.json` |
| plan_class | `remediation_plan` — `bounded_execution_contract` \| `migration_plan` \| `retirement_plan` \| `remediation_plan` \| `deployment_plan` \| `refactor_plan` \| `integration_plan` \| `recovery_plan` \| `custom` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-10-29T15:40:00Z` |
| repository | `Quantum-L9/l9-cognitive-runtime` |
| workspace | `/home/user/l9-cr-pr67-nits` |
| ssot_clone | `/root/.cursor-governance` |
| branch | `agent/claude-code/pr67-audit-nits (from origin/agent/claude-code/correctness-remediation)` |
| commit_sha | `b87a5e795cc55f63b4af667ecccaec03be48f9d3` — full 40-char SHA (PLAN-SCHEMA-001) |
| dirty | `true` — `true` \| `false` |
| artifact_hashes | `n/a` |
| allowed_local_dirt | `AGENTS.md, CLAUDE.md formatter-ownership block and .vscode/ written by worktree_add_wired.sh; never staged` |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` — `stop_if_dirty_overlaps_may_modify` \| `require_clean_tree` \| `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

`Close the three PR #67 audit nits that need no owner decision, stacked on PR #67`

### Success properties

One row per property. `evidence_type` ∈ `filesystem` | `runtime_behavior` | `structural` | `quality_gate` | `repository_state` | `network_observation` | `proof_receipt` | `human_confirmation`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP1 | MCP kernel/schema resources refuse tampered or unlisted files | runtime_behavior | new test_mcp_stdio cases | true |
| SP2 | AdapterRenderer(pack=) verifies templates; pack_root mode unchanged | runtime_behavior | new test_gar_adapter_packet cases + existing RG-008a/b | true |
| SP3 | brace-bearing placeholder marker fails closed; shipped templates render | runtime_behavior | new RG case + existing render tests | true |
| SP4 | closure refuses selected_because outside requirement_plan | runtime_behavior | new test_context_compiler case | true |
| SP5 | ruff, ruff format, mypy strict, full pytest green | quality_gate | CLAUDE.md verify block | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.pr67_audit_nits_3f9c1a2e`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.pr67_audit_nits_3f9c1a2e` |
| source_ref | `pr67_audit_nits_3f9c1a2e` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.pr67_audit_nits_3f9c1a2e` |
| baseline_verified | `true` |
| drift_detected | `false` |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| PR1 | frozen deps | uv sync --extra dev --frozen --no-install-project --no-build | exit 0 | true |
| PR2 | sealed pack coverage | build_deployment_pack + list provenance.file_digests | schemas/, kernels/, adapters/*.md listed | true |
| PR3 | baseline head | git log -1 --format=%H in the worktree | b87a5e795cc55f63b4af667ecccaec03be48f9d3 | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `src/l9_cognitive_runtime/mcp/__init__.py, src/l9_cognitive_runtime/compiler/adapters.py, src/l9_cognitive_runtime/compiler/context_closure.py, tests/test_mcp_stdio.py, tests/test_gar_adapter_packet.py, tests/test_context_compiler.py`
- **write_deny:** `cli.py, models/context.py, runtime/, MANIFEST.json, uv.lock, .github/`
- **delete_allow:** `none`

### Commands

- **allow:** `uv run --no-sync --no-build ruff|mypy|pytest; scoped git add/commit; gmp_executor.py start|finalize; l4_local.py begin|authorize-release; PR_REMEDIATE=0 make pr`
- **deny:** `history rewrite, branch switching in the primary clone, any Program Execution campaign target`

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` — `none` \| `read_only` \| `named_services_only` \| `existing_tunnel_only` \| `bounded_external_write` |
| allowed_services | `github.com Quantum-L9/l9-cognitive-runtime only: git push of agent/claude-code/pr67-audit-nits and one PR open/update via make pr; gh api reads` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` — `none` \| `read_only_named` \| `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan:** never from Build or `make pr`. The stacked PR merges only after its parent PR #67, green and mergeable, through the human-authorized merge path (`rules/48-make-pr-remediation`, `rules/88-l4-local-autonomy`). Program Execution is retired and is not a prerequisite.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per `T1-T5`.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | filesystem_mutation | safe_to_repeat | none | git_restore_scoped_paths | false |
| T2 | filesystem_mutation | safe_to_repeat | none | git_restore_scoped_paths | false |
| T3 | filesystem_mutation | safe_to_repeat | none | git_restore_scoped_paths | false |
| T4 | filesystem_mutation | safe_to_repeat | none | git_restore_scoped_paths | false |
| T5 | filesystem_read | safe_to_repeat | retry_once | none | false |

`side_effects` ∈ `none` | `filesystem_read` | `filesystem_mutation` | `destructive_filesystem_mutation` | `network_read` | `network_write` | `database_read` | `database_write` | `external_state_mutation` | `human_approval`

`idempotency` ∈ `safe_to_repeat` | `safe_with_dedupe` | `unsafe_blind_repeat` | `non_idempotent`

`retry` ∈ `none` | `manual_only` | `retry_once` | `bounded_retry`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | MCP read-only server | runtime | RuntimePack.read_verified (pack/loader.py) | no new reader; no write path |
| T2 | adapter projection | runtime | INV-CTX-031 projection fidelity | no change to pack_root behaviour |
| T3 | adapter projection | runtime | INV-CTX-031 projection fidelity | no template edits |
| T4 | context closure | runtime | ContextClosureValidator REQUIRED_CHECKS | no check rename; no semantics version bump |
| T5 | verification | assurance | pr-check.yml | no gate weakening |

`layer` ∈ `control_plane` | `data_plane` | `chassis` | `ops` | `runtime` | `policy` | `assurance` | `memory` | `graph` | `docs` | `external_system`

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.pr67_audit_nits_3f9c1a2e` |
| source_execution_ref | `pr67_audit_nits_3f9c1a2e` |
| supported | `true` — `true` \| `false` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | `any gate red after merge` |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | `git_restore_scoped_paths` \| `revert_commit` \| `none` |
| data | `none` | `none` \| `restore_snapshot` \| `compensating_transaction` \| `manual_recovery` |
| external_state | `none` | `none` \| `corrective_append_only_record` \| `manual_recovery` |
| local_state | `git_restore_scoped_paths` | `none` \| `git_restore_scoped_paths` \| `manual_recovery` |

### Irreversible operations

- `none` (PLAN-SCHEMA-010)

### Rollback verification

- `full pytest green after revert`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` — `low` \| `medium` \| `high` \| `critical` |
| uncertainty | `low` — `low` \| `medium` \| `high` \| `critical` |
| blast_radius | `medium` — `low` \| `medium` \| `high` \| `critical` |
| architectural_boundaries_crossed | `none` |
| external_systems_touched | `none` |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | `n/a` |
| categories | `n/a` — `delete` \| `migrate_then_delete` \| `keep` \| `replace` \| `skip` |
| checksum_required | `n/a` |
| destructive_gate_required_for | `n/a` |

## Gated write pipeline *(optional — irreversible or external writes)*

- **gates (ordered):** `n/a`
- **dedupe_before_non_idempotent_write:** `n/a`
- **bounded_write_count:** `n/a`
- **receipt_required:** `n/a`

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| `n/a` | `n/a` | `n/a` | `n/a` |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.pr67_audit_nits_3f9c1a2e` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T1 | claude-code | runtime | [] | mcp/__init__.py + tests |
| T2 | claude-code | runtime | [] | compiler/adapters.py + tests |
| T3 | claude-code | runtime | [T2] | compiler/adapters.py + tests |
| T4 | claude-code | runtime | [] | compiler/context_closure.py + tests |
| T5 | claude-code | assurance | [T1, T2, T3, T4] | gate evidence |

**Critical path:** `T2 -> T3 -> T5`

**Forbidden edges:** `none`

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E1 | SP1 | runtime_behavior_evidence | pytest | pytest tests/test_mcp_stdio.py | pass on head, fail on b87a5e79 src | passed |
| E2 | SP2 | runtime_behavior_evidence | pytest | pytest tests/test_gar_adapter_packet.py | pass on head, fail on b87a5e79 src | passed |
| E3 | SP3 | runtime_behavior_evidence | pytest | pytest tests/test_gar_adapter_packet.py | pass on head, fail on b87a5e79 src | passed |
| E4 | SP4 | runtime_behavior_evidence | pytest | pytest tests/test_context_compiler.py | pass on head, fail on b87a5e79 src | passed |
| E5 | SP5 | quality_gate_evidence | CLAUDE.md verify block | ruff/mypy/pytest | exit 0 | passed |

`evidence_kind` ∈ `repository_state_evidence` | `property_evidence` | `structural_evidence` | `runtime_behavior_evidence` | `quality_gate_evidence`

`evidence_status` ∈ `not_run` | `passed` | `failed`

## Stress and disconfirm

### Disconfirming cases

- `a sealed-pack MCP resource names a file the manifest omits; a compiler-built context binds an item to a non-plan reason`

### Assumption failure conditions

- `tests/test_deployment_pack.py or any compile closure test fails after the change` (PLAN-SCHEMA-013)

### Blast radius notes

- `T4 runs on every compile; a wrong subset check fails every compile closed`

### Rollback constraints

- `none; pure code change`

## Out of scope

- `see Scope (from PLAN_DOCUMENT) out list`
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `n/a` |

| priority | change | why |
|----------|--------|-----|
| `n/a` | `n/a` | `n/a` |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.pr67_audit_nits_3f9c1a2e` |
| source_ref | `pr67_audit_nits_3f9c1a2e` |
| current_state | `partial` — `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `true` |

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

- **required_evidence_refs:** `E1-E5`
- **observed_evidence_refs:** `E1-E5 passed on 7c9f676 (Quantum-L9/l9-cognitive-runtime#68): 495 passed; 8 new tests fail on b87a5e79 src`
- **missing_evidence:** `merge of parent #67, then #68`

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | UNK-01 | audit nit 3 raw-size pre-read bound conflicts with RU-16 formatting-neutral ingress | ask owner; excluded from this plan |

`blocker_kind` ∈ `open_blocker` | `unknown`

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `C1 after M1` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.<domain>.<slug>.v1
  name: <plan_title>
  overview: <overview>
  status: <status>
  is_project: false
  created_at: <created_at>
architect_framing:
  planning_ssot: <planning_ssot>
  plan_class: <plan_class>
  redesign_allowed: <redesign_allowed>
  follow_on_schema_evolution_separate: <follow_on_schema_evolution_separate>
immutable_baseline:
  repository: <repository>
  commit_sha: <commit_sha>
  dirty: <dirty>
  artifact_hashes: {}
  overlap_policy: <overlap_policy>
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: <mission>
  success_properties:
    - id: <success_property_id>
      property: <property>
      evidence_type: <evidence_type>
      proof: <proof>
      blocking: <blocking>
capability_preflight_ref: <capability_preflight_ref>
execution_envelope:
  filesystem:
    write_allow: [<write_allow>]
    write_deny: [<write_deny>]
  commands:
    allow: [<commands_allow>]
    deny: [<commands_deny>]
  network:
    mode: <network_mode>
  secrets:
    access: <secrets_access>
    redaction_required: <redaction_required>
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: <rollback_contract_ref>
complexity_and_uncertainty:
  complexity: <complexity>
  uncertainty: <uncertainty>
  blast_radius: <blast_radius>
  architectural_boundaries_crossed: <architectural_boundaries_crossed>
  external_systems_touched: <external_systems_touched>
  migration_required: <migration_required>
  unknown_dependency_count: <unknown_dependency_count>
dependency_topology_ref: <dependency_topology_ref>
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: <convergence_contract_ref>
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: <todo_id>
    content: <todo_content>
    status: pending
```
