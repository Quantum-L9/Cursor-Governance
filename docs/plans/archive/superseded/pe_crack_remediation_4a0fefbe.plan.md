---
name: "PE crack remediation: campaign compile, pec gates, honest PASS"
status: superseded
built: true
overview: "Close the load-bearing Program Execution cracks so campaign source compiles through a repo-owned schema and compiler, pec refuses unvalidated draft locks by default, Cursor/ChatGPT cannot substitute PASS, and Make/conformance actually gate those contracts. Do not admit or accept bounded-replanning-v1, do not add a DeepSeek PE provider, and do not mix this landing onto the current dirty feature branch."
todos:
  - id: built-marker
    content: Marked built after execution; session-start audit should skip
    status: cancelled
  - id: T0
    content: "Open a clean worktree from origin/main; lock full SHA; refuse the dirty fix/ci-required-contexts-wip-only checkout as the landing tree"
    status: cancelled
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: T1
    content: "Add campaign-source.v2 JSON Schema covering the live CAMPAIGN_SOURCE dialect and a fixture gate for the four registered campaigns"
    status: cancelled
    phase: execute
    depends_on: [T0]
    side_effect_ref: SE-T1
    evidence_property_refs: [SP-02]
  - id: T2
    content: "Add a repo-owned compiler that remaps campaign-source fields onto Blueprint v2 and rewrites MANIFEST.yaml"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T2
    evidence_property_refs: [SP-02]
  - id: T3
    content: "Make pec bootstrap fail-closed unless validate_blueprint instantiated PASSes; add explicit --admission-draft that cannot mark tasks ready"
    status: cancelled
    phase: execute
    depends_on: [T2]
    side_effect_ref: SE-T3
    evidence_property_refs: [SP-04]
  - id: T4
    content: "Replace empty-object Blueprint schema properties for waves, current-state, observability, do-not-build, cutover, and source-traceability with typed required shapes"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T4
    evidence_property_refs: [SP-02]
  - id: T5
    content: "Map Cursor and ChatGPT host result status into CanonicalProviderResult; missing or non-PASS host status cannot become PASS"
    status: cancelled
    phase: execute
    depends_on: [T0]
    side_effect_ref: SE-T5
    evidence_property_refs: [SP-05]
  - id: T6
    content: "Bind target adapter tokens in the campaign schema (git vs git_repo_adapter) and document that pec reconcile uses repository_id, not a worker adapter"
    status: cancelled
    phase: execute
    depends_on: [T1, T2]
    side_effect_ref: SE-T6
    evidence_property_refs: [SP-02]
  - id: T7
    content: "Wire campaign compile/validate, pec controller tests, and validate_manifest into Make PE targets by appending only"
    status: cancelled
    phase: execute
    depends_on: [T2, T3, T5]
    side_effect_ref: SE-T7
    evidence_property_refs: [SP-03]
  - id: T8
    content: "Correct campaign honesty: TASK-007 local_write false; integrity receipt producer not controller-admission; leftover campaigns labeled archival/inconclusive"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T8
    evidence_property_refs: [SP-06]
  - id: T9
    content: "Record Claude backend_mode and model_hint as probe evidence only; keep DeepSeek out of the PE provider registry"
    status: cancelled
    phase: execute
    depends_on: [T0]
    side_effect_ref: SE-T9
    evidence_property_refs: [SP-02]
  - id: T10
    content: "Add a read-only dual-plane status line so pec status and autonomy bootstrap each name the other plane without writing campaign packets"
    status: cancelled
    phase: execute
    depends_on: [T3]
    side_effect_ref: SE-T10
    evidence_property_refs: [SP-02]
  - id: T11
    content: "Retitle PE ARCHITECTURE.md as Program Execution and document the compile→validate→bootstrap path in README"
    status: cancelled
    phase: execute
    depends_on: [T2, T3, T10]
    side_effect_ref: SE-T11
    evidence_property_refs: [SP-02]
  - id: T12
    content: "Prove the stack: campaign compile fixture, pec admission-draft negative test, Cursor FAIL mapping, Make PE targets, make pr-check"
    status: cancelled
    phase: validate
    depends_on: [T4, T6, T7, T8, T9, T11]
    evidence_property_refs: [SP-02, SP-03, SP-04, SP-05]
isProject: false
---
# PLAN: PE crack remediation: campaign compile, pec gates, honest PASS

> **SUPERSEDED** by `.cursor/plans/pe_crack_remediation_4c064022.plan.md` (Improve-kernel regeneration, 2026-08-14). Do not execute this file.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Machine SSOT:** `.cursor/plans/pe_crack_remediation_v1.json` (`validate_plan_document.py` PASS; hex `4a0fefbe`)
> **Schema:** `canonical.schema.plan_document.v1` (status: `executable`)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Landing:** new branch from `origin/main` (`KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`). Do not land on `fix/ci-required-contexts-wip-only`.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected.

## Execute via @environment/program-execution + autonomy (required)

**Authority order (fail-closed — see `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md  (intent / envelope / DAG / success properties)
        │ project
        ▼
@environment/program-execution   HOW work executes (authoritative)
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act?  (packet, lanes, PR poll) — owns_program_state: false
        │
        ▼
Peer Execution Core -> thin provider
  (Cursor: cursor-foreground | cursor-background;
   Claude: claude-code-direct)
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease. Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet. Do **not** auto-init `.l9/autonomy/campaigns/*.json` from pec.

### Pipeline steps

1. **Attach** [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md).
2. **T0 first:** create a clean worktree / new branch from `origin/main` @ `1aba3592b094f8bd424479264e725ade585c018e`. Refuse the dirty `fix/ci-required-contexts-wip-only` checkout.
3. **Project this plan → Blueprint artifacts** under `$HOME/.l9/programs/pe-crack-remediation-v1/` — never mutate sealed `environment/program-execution/core/` templates in place except through the Task Cards in this plan (those edits are the product):

   | Plan section | PE Blueprint / Controller artifact |
   |--------------|-------------------------------------|
   | metadata / objective | `PROGRAM.yaml` / program identity `pe-crack-remediation-v1` |
   | immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA `1aba3592…` |
   | execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
   | execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
   | capability_preflight | Controller reconcile + gate probes before claim |
   | property_evidence_matrix | Task Card `validation` / evidence catalog refs |
   | rollback | Task Card `rollback` + recovery receipts |
   | convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

4. **Validate + bootstrap Controller** after T2 exists (compiled Blueprint for *this* overlay, not bounded-replanning admission):

```bash
python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py bootstrap \
  --workspace "$HOME/.l9/programs/pe-crack-remediation-v1/runtime" \
  --blueprint "$HOME/.l9/programs/pe-crack-remediation-v1/blueprint"
python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py reconcile \
  --workspace "$HOME/.l9/programs/pe-crack-remediation-v1/runtime" \
  --repository cursor-governance="$(pwd)"
python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py status \
  --workspace "$HOME/.l9/programs/pe-crack-remediation-v1/runtime"
python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py next \
  --workspace "$HOME/.l9/programs/pe-crack-remediation-v1/runtime"
```

   Until T3 lands, default pec still locks drafts. After T3, this overlay's own Blueprint must be `accepted` for its Task Cards (this plan), **or** use `--admission-draft` only for inspect. Do **not** flip `bounded-replanning-v1` to `accepted`.

5. **Admit exact task scope** — draft/register Source Contract ⊂ Task Card ceiling; then `claim` → `prepare` → `render-contract`. Worker receives **only** Rendered Contract + Worker Brief + worktree.
6. **Map Program task → autonomy campaign** via `environment/program-execution/integrations/autonomy-control-plane/`. Set each mutating Task Card `autonomy_action_id` (`pes.w<n>.<task>`).
7. **Orchestrate under [@autonomy](commands/autonomy.md)** — Protocols A–D; packet aligned to Program Lock digest + declared branch. Spawn ready `work` Tasks; main continues.
8. **L4 local autonomy** inside the Program lease: local commits only until `ops/autonomy/l4_local.py authorize-release` → scoped push/PR → `l9-pr-remediation` Converge. Launching this plan through PE+`/autonomy` **or** clicking Build **is** merge authorization for this stack after green+mergeable (bottom-up older PRs first).
9. **Record + verify + handoff** — `pec.py record-attempt` → `verify` → `export-handoff`. Graphiti PICKUP on close is observability only.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-generic-shell` then `make pr-check` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-2026-08-14-pe-crack-remediation
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: .cursor/plans/pe_crack_remediation_4a0fefbe.plan.md
plan_id: plan.program-execution.crack-remediation.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pe-crack-remediation-v1
  program_lock_digest: <sha256 from Controller>
  blueprint_ref: $HOME/.l9/programs/pe-crack-remediation-v1/blueprint
  runtime_ref: $HOME/.l9/programs/pe-crack-remediation-v1/runtime
  provider_ref: cursor-foreground
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [fix/pe-crack-remediation-v1]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch
  - inspect_ci_and_comments
forbidden_inside_packet:
  - widen_blueprint_or_task_card_ceiling
  - mutate_without_program_lease
  - outlive_program_lease
  - merge_outside_l4_plan_build_stack
  - force_push
  - admin_merge
  - expand_scope
  - commit_secrets
  - weaken_tests_for_green
  - direct_graphiti_task_claim
  - fake_program_definition_status_accepted
  - add_deepseek_pe_provider
  - auto_init_autonomy_campaign_packets
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| T0 | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.task001` | `work` | `cursor-foreground` |
| T1 | TASK-002 | W1 | [T0] | true | `path:environment/program-execution/core/shared/schemas/` | `schema` | `pes.w1.task002` | `work` | `cursor-foreground` |
| T5 | TASK-003 | W1 | [T0] | true | `path:environment/program-execution/adapters/` | `honest-pass` | `pes.w1.task003` | `work` | `cursor-foreground` |
| T9 | TASK-004 | W1 | [T0] | true | `path:environment/program-execution/adapters/claude-code/` | `probe-meta` | `pes.w1.task004` | `work` | `cursor-foreground` |
| T2 | TASK-005 | W2 | [T1] | true | `path:environment/program-execution/scripts/compile_campaign_source.py` | `compiler` | `pes.w2.task005` | `work` | `cursor-foreground` |
| T4 | TASK-006 | W2 | [T1] | true | `path:environment/program-execution/core/program-execution-blueprint-template/schemas/` | `bp-schema` | `pes.w2.task006` | `work` | `cursor-foreground` |
| T8 | TASK-007 | W2 | [T1] | true | `path:environment/program-execution/campaigns/` | `honesty` | `pes.w2.task007` | `work` | `cursor-foreground` |
| T3 | TASK-008 | W3 | [T2] | true | `path:environment/program-execution/core/program-execution-controller-template/scripts/pec/` | `pec-gate` | `pes.w3.task008` | `work` | `cursor-foreground` |
| T6 | TASK-009 | W3 | [T1, T2] | true | `path:environment/program-execution/core/shared/schemas/campaign-source.schema.json` | `adapter-token` | `pes.w3.task009` | `work` | `cursor-foreground` |
| T10 | TASK-010 | W3 | [T3] | true | `path:environment/program-execution/peer_execution/autonomy/bootstrap.py` | `dual-plane` | `pes.w3.task010` | `work` | `cursor-foreground` |
| T7 | TASK-011 | W4 | [T2, T3, T5] | true | `path:Makefile` | `make-pe` | `pes.w4.task011` | `work` | `cursor-foreground` |
| T11 | TASK-012 | W4 | [T2, T3, T10] | true | `path:environment/program-execution/ARCHITECTURE.md` | `docs` | `pes.w4.task012` | `work` | `cursor-foreground` |
| T12 | TASK-013 | W5 | [T4, T6, T7, T8, T9, T11] | false | `evidence:plan.program-execution.crack-remediation.v1` | `validate` | `pes.w5.task013` | `work` | `ci-generic-shell` |

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A (ready `work` Tasks in one message). Autonomy must not bypass wave order or Program Lock drift checks.

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint for *this overlay* not bound; Program Lock drift; capability preflight blocked; dirty landing tree; attempt to set `bounded-replanning-v1` `definition_status=accepted`; attempt to add a DeepSeek PE provider.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.program-execution.crack-remediation.v1` |
| name | PE crack remediation: campaign compile, pec gates, honest PASS |
| overview | Close C1/C2/H1–H12 load-bearing PE cracks. Do not admit bounded-replanning-v1. Do not add a DeepSeek PE provider. New branch from origin/main only. |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` |
| owner | Cursor-Governance / Program Execution |
| created_at | `2026-08-14` |
| updated_at | `2026-08-14` |
| machine_ssot | `.cursor/plans/pe_crack_remediation_v1.json` |
| depth | `deep` (router: `--risk high --evidence sufficient`) |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `environment/program-execution/` + ADRs 0017–0022 + 2026-08-14 PE folder crack audit |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Close unbound campaign dialect, pec draft-lock, and substituted PASS. No second scheduler. No DeepSeek provider. No fake `accepted`. Execute via @environment/program-execution + subordinate @autonomy. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-14T18:38:00-04:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `/Users/ib-mac/.cursor-governance` |
| branch | `fix/pe-crack-remediation-v1` (create at execute; do not use current dirty branch) |
| commit_sha | `1aba3592b094f8bd424479264e725ade585c018e` |
| dirty | current workspace `true` (legal/WIP + `fix/ci-required-contexts-wip-only`); **landing tree must be clean** |
| artifact_hashes | `{ "environment/program-execution/campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml": "sha256:7a71ede7fc3dd0272ceed5ce4cbaf62a5d66769f75b0fe21689d7eb6f8168619" }` |
| allowed_local_dirt | none on the landing worktree |
| overlap_policy | `require_clean_tree` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

Current checkout `fix/ci-required-contexts-wip-only` is **not** the landing tree. T0 is a hard stop.

## Objective

### Mission

Program Execution currently has an unbound campaign-source dialect (four `CAMPAIGN_SOURCE.yaml` files, zero schema, zero in-repo compiler), pec bootstrap that locks unvalidated drafts, and Cursor/ChatGPT providers that emit `CanonicalProviderResult.status="PASS"` whenever a result file exists. Close those cracks so campaign source is a typed compiled contract, pec refuses unvalidated admission by default, worker receipts cannot lie, and Make/conformance gate the new contracts. Preserve thin-adapter law, ADR-0020 (DeepSeek deferred as a PE provider), `autonomous_merge: false`, and `definition_status=draft` for bounded-replanning-v1.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Landing HEAD equals locked origin/main SHA at start | `repository_state` | `git rev-parse HEAD` == `1aba3592b094f8bd424479264e725ade585c018e` on the new branch; worktree clean of legal/WIP | true |
| SP-02 | Campaign-source schema + compiler + typed Blueprint schemas exist and compile bounded-replanning-v1 to template PASS | `structural` | schema validates all four `CAMPAIGN_SOURCE.yaml`; `compile_campaign_source.py` + `validate_blueprint.py --mode template` PASS | true |
| SP-03 | Make PE targets and `make pr-check` PASS on the new-branch change set | `quality_gate` | `make program-execution-core-validate && make program-execution-adapters && make program-execution-conformance && make pr-check` → PASS | true |
| SP-04 | pec bootstrap refuses draft/unvalidated Blueprints unless `--admission-draft`; draft flag cannot mark tasks ready | `runtime_behavior` | bootstrap without flag exits nonzero on draft Blueprint; with flag prints `definition_status=draft` and `ready: []` | true |
| SP-05 | Cursor/ChatGPT missing or non-PASS host status cannot become canonical PASS | `runtime_behavior` | unit test: missing status → BLOCKED; host FAIL → FAIL; never PASS | true |
| SP-06 | Campaign honesty: TASK-007 `local_write: false`; receipt producer ≠ `controller-admission`; leftover campaigns labeled archival | `filesystem` | grep/receipt fields after T8; new receipt if YAML bytes change | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`  
`instance_binding:` `preflight.plan.program-execution.crack-remediation.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.program-execution.crack-remediation.v1` |
| source_ref | `plan.program-execution.crack-remediation.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline / `1aba3592b094f8bd424479264e725ade585c018e` |
| baseline_verified | planning-time `origin/main` resolved; reverify at T0 |
| drift_detected | current workspace dirty and on a different branch — expected; landing tree must not inherit it |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git fetch origin && git rev-parse origin/main` | equals `1aba3592b094f8bd424479264e725ade585c018e` or stop_and_replan with new SHA | true |
| CP-02 | `command_available` | `python3`, `make`, `git` | all on PATH | true |
| CP-03 | `filesystem_write` | write_allow paths writable on the *new* worktree | landing tree clean and writable | true |
| CP-04 | `schema_gap_still_present` | glob campaign-source schema + compile script | zero schema for `l9.program-execution.campaign-source.v2`; no in-repo compiler (planning P3 passed) | true |
| CP-05 | `cursor_result_contract` | read `foreground_transport.py` `collect()` | returns any object; no status field required today (U2 locked) | true |

Planning pre-validation P0–P3: **passed**. Re-run CP-01/CP-03 on the landing tree before first mutation.

## Execution envelope

Mutations outside this envelope are forbidden.

### Filesystem

- **write_allow:**
  - `environment/program-execution/`
  - `Makefile` (append-only; root-file-protection `additive_only`)
  - `$HOME/.l9/programs/pe-crack-remediation-v1/` (runtime; not git)
  - `$HOME/.l9/blueprints/` compiled trees (runtime; not git)
- **write_deny:**
  - `CANONICAL_LAW.md`
  - `pyproject.toml` existing keys
  - `ops/hooks/session_start_bootstrap.sh`
  - `WIP/`
  - `.env.local` and any secret files
  - `docs/decisions/ADR-0020-provider-neutral-inference-routing-deepseek-deferred.md` decision text
  - `environment/program-execution/campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml` `definition_status: accepted`
  - legal evidence trees
  - `environment/program-execution/registry/EXECUTION_ADAPTER_REGISTRY.yaml` adding `git` / `git_repo_adapter` / DeepSeek as workers
- **delete_allow:** none in git. Disposable: `$HOME/.l9/blueprints/_compile_bounded_replanning.py` after T2.

### Commands

- **allow:** `git` (non-destructive), `python3` pec/validate/compile/tests, `make program-execution-*`, `make pr-check`, `make pr` only after L4 `authorize-release`, `ops/autonomy/l4_local.py`
- **deny:** force-push, hard-reset, admin-merge, secret exfil, `gh pr merge` outside L4 stack, scanner weakening, faking `accepted`

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `origin` git (after L4 release), GitHub API for scoped PR |

Mid-execution push is denied until `authorize-release`.

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

No DeepSeek/Anthropic/GitHub token work in this overlay.

### Autonomous merge

`autonomous_merge:` `false`  
**Merge for this plan** only after PE verify/handoff + @autonomy join on this L4 plan/PE stack, green+mergeable. Outside that stack → denied.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T0 | `filesystem_read` | `safe_to_repeat` | `none` | abandon unused worktree | false |
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore schema/test paths | false |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore compiler paths | false |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore pec controller/cli | false |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore Blueprint schemas | false |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore provider.py files | false |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore schema/compiler/README | false |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert appended Makefile lines only | false |
| T8 | `filesystem_mutation` | `non_idempotent` | `manual_only` | new receipt; keep old digest in notes | false |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore claude provider/README | false |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore pec status + bootstrap.py | false |
| T11 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore ARCHITECTURE/README | false |
| T12 | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |

T8 is the only byte-sensitive campaign-seed edit. If `CAMPAIGN_SOURCE.yaml` bytes change, write a **new** integrity receipt with `producer=campaign-honesty-edit` and keep the old digest in notes. Do not rewrite history.

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | program-execution campaign source | `policy` | new `campaign-source.schema.json` beside shared PE contracts | invent a second campaign dialect |
| T2 | program-execution compile | `control_plane` | Blueprint v2 + `validate_blueprint.py` | keep `$HOME/.l9` ad-hoc compiler as SSOT |
| T3 | pec admission | `control_plane` | controller.v2 + `validate_blueprint.py` instantiated | lock drafts as admitted; fake `accepted` |
| T4 | Blueprint schemas | `policy` | blueprint-template schemas | leave material fields as `{}` |
| T5 | thin adapters | `runtime` | `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml` | substitute PASS; thicken adapters |
| T6 | campaign target tokens | `policy` | campaign-source schema | add `git` worker to `EXECUTION_ADAPTER_REGISTRY.yaml` |
| T7 | Make PE gates | `ops` | Makefile PE targets; root-file-protection additive_only | overwrite/delete existing Makefile keys |
| T8 | campaign seeds | `assurance` | campaign integrity receipts | set `definition_status=accepted` |
| T9 | Claude probe metadata | `runtime` | ADR-0020 | register DeepSeek as a PE provider |
| T10 | dual-plane observability | `control_plane` | COMPATIBILITY / autonomy-control-plane | auto-init autonomy campaign packets |
| T11 | PE docs | `docs` | PE README/ARCHITECTURE | retitle as a second product |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`  
`instance_binding:` `rollback.plan.program-execution.crack-remediation.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.program-execution.crack-remediation.v1` |
| source_execution_ref | `plan.program-execution.crack-remediation.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking SP fail; envelope breach; leftover campaigns fail CI compile; Cursor PASS mapping inverted |

### Strategies

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | revert feature-branch commits only; no force-push |
| data | `none` | no production data |
| external_state | `none` | no campaign packet writes |
| local_state | `manual_recovery` | `$HOME/.l9` runtimes are disposable; git seeds are not |

### Irreversible operations

- None in git history (no force-push).
- T8 receipt re-stamp is append-honest: old digest retained in notes; not a history rewrite.

### Rollback verification

- `git rev-parse HEAD` on the abandoned feature branch vs `origin/main`
- pec `--admission-draft` remains available if default refuse is too tight
- Cursor unit test still fails closed on missing status (or providers restored)

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `3` (campaign dialect, pec admission, adapter receipts) |
| external_systems_touched | `0` during local execute; `1` (GitHub) after L4 release |
| migration_required | `false` |
| unknown_dependency_count | `0` (U1/U2/U3 accepted-bounded) |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`  
`instance_binding:` `dag.plan.program-execution.crack-remediation.v1`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.program-execution.crack-remediation.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T0 | agent | assurance | [] | clean worktree; locked SHA |
| T1 | agent | policy | [T0] | campaign-source.schema.json + four-file fixture |
| T5 | agent | runtime | [T0] | honest Cursor/ChatGPT PASS mapping + tests |
| T9 | agent | runtime | [T0] | Claude probe metadata only |
| T2 | agent | control_plane | [T1] | compile_campaign_source.py + tests |
| T4 | agent | policy | [T1] | typed Blueprint schemas |
| T8 | agent | assurance | [T1] | honesty edits + new receipt if bytes change |
| T3 | agent | control_plane | [T2] | pec bootstrap gate + `--admission-draft` |
| T6 | agent | policy | [T1, T2] | git token bind; no registry worker |
| T10 | agent | control_plane | [T3] | read-only dual-plane status |
| T7 | agent | ops | [T2, T3, T5] | appended Make PE gates |
| T11 | agent | docs | [T2, T3, T10] | ARCHITECTURE/README path |
| T12 | agent | assurance | [T4, T6, T7, T8, T9, T11] | V1–V5 evidence |

**Critical path:** `T0` → `T1` → `T2` → `T3` → `T5` → `T7` → `T12`  
(T5 is parallel to T1 after T0; it joins the critical path at T7.)

**Forbidden edges:** T3 before T2; T7 before T3/T5; T8 setting `accepted`; T6 adding a git worker; T10 writing autonomy campaign JSON; any mutation on `fix/ci-required-contexts-wip-only`.

### Waves

- **W0:** T0
- **W1:** T1, T5, T9
- **W2:** T2, T4, T8
- **W3:** T3, T6, T10
- **W4:** T7, T11
- **W5:** T12

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | `1aba3592b094f8bd424479264e725ade585c018e` at branch start | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | schema + compile | V1 + V2 commands | four campaigns parse; template PASS | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | Make + pr-check | V4 + V5 | all PASS | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | negative bootstrap | V3 | nonzero without `--admission-draft`; draft ready=[] | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | provider unit tests | cursor/chatgpt `test_provider.py` | missing→BLOCKED; FAIL→FAIL | `not_run` |
| EV-SP-06 | SP-06 | `filesystem_evidence` | receipt + YAML fields | inspect T8 outputs | `local_write: false`; producer ≠ `controller-admission` | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- If pec already blocks ready tasks on planned evidence, default bootstrap refuse could add an operator loop → **accepted:** keep `--admission-draft` for W0 inspect; default path still refuse (U1).
- If campaign-source schema is written to the live four files, tightening TASK-007 or adapter enums invalidates historical integrity receipts → **accepted:** T8 re-stamps with `producer=campaign-honesty-edit` and keeps the old digest in notes.
- If Cursor result JSON has no status field, requiring status could break every foreground fixture → **locked:** `ForegroundTransport.collect` returns any object and never reads status. T5 maps **optional** `status`; missing or non-PASS → BLOCKED/FAIL, never PASS (U2).
- If Make compiles all four campaigns in CI, leftover INCONCLUSIVE campaigns fail unrelated PRs → **accepted:** CI compile only campaigns marked `compile: true` (U3). Day-one: `bounded-replanning-v1` only.

### Assumption failure conditions

- `origin/main` SHA drifts from `1aba3592…` → stop_and_replan; lock the new full SHA
- Dirty tree overlaps `write_allow` on the landing worktree → stop
- `validate_blueprint --mode instantiated` starts accepting `draft` → stop; do not weaken the validator
- Cursor host protocol later requires a different status key → remap in T5 tests; do not restore substituted PASS
- Makefile append is rejected by root-file-protection → keep append-only; do not rewrite the file

### Blast radius notes

PE admission, every pec bootstrap, Cursor/ChatGPT worker receipts, Make PE CI, and four registered campaign seeds. A bad compiler or schema can freeze future campaign landings. A bad PASS mapping can fail-close legitimate Cursor completions or, if inverted, restore silent success.

### Rollback constraints

- No force-push / history rewrite
- `$HOME/.l9` disposable; git campaign seeds are not
- Do not delete the existing `$HOME/.l9/programs/bounded-replanning-v1` lock; document it as non-admitted

## Out of scope

- Accepting or faking `program.definition_status=accepted` for bounded-replanning-v1
- Collecting EVID-001 through EVID-008 or implementing Replan Revision
- Adding a DeepSeek Program Execution provider or changing ADR-0020
- Merging or re-executing leftover INCONCLUSIVE campaigns (intent-compiler, devpack, ecosystem-fix)
- `WIP/` overlay, legal evidence, current dirty branch `fix/ci-required-contexts-wip-only`
- `CANONICAL_LAW.md`, `pyproject.toml` existing keys, sessionStart hook rewrite, memory-bank recreation
- Force-push, hard-reset, admin-merge, `autonomous_merge`, secret commits
- Adding `git` / `git_repo_adapter` as workers in `EXECUTION_ADAPTER_REGISTRY.yaml`
- Auto-init of `.l9/autonomy/campaigns/*.json` from pec (second scheduler)

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | Collect EVID-001–008 and admit bounded-replanning-v1 | Admission is a different program; this overlay only makes admission honest |
| P2 | Optional later: compile leftover campaigns after archival cleanup | U3 excludes them from day-one CI |
| P3 | Cursor host-protocol status field as a required transport contract | T5 works with optional status; a host-side required field is a separate contract |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`  
`instance_binding:` `conv.plan.program-execution.crack-remediation.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.program-execution.crack-remediation.v1` |
| source_ref | `plan.program-execution.crack-remediation.v1` |
| current_state | `execution_ready` |
| implementation_ready | `true` (plan law holds; V1–V5 evidence still `not_run`) |

### Gates

- **executable_when:**
  - baseline SHA locked (`1aba3592…`) + reverified at T0
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns (U1/U2/U3 accepted-bounded)
- **complete_when:**
  - all blocking SP-01..SP-06 evidence `passed`
  - rollback contract still valid
  - out_of_scope respected (no `accepted` fake; no DeepSeek provider; no dirty-branch mix)
- **blocking_conditions:**
  - landing on `fix/ci-required-contexts-wip-only`
  - pec bootstrap still locks drafts without `--admission-draft` after T3
  - Cursor/ChatGPT still substitute PASS
  - Makefile overwrite (root-file-protection fail)
  - leftover campaigns compiled in CI without `compile: true`

### Evidence

- **required_evidence_refs:** `EV-SP-01` … `EV-SP-06`
- **observed_evidence_refs:** planning P0–P3 passed; U2 locked against `foreground_transport.py`
- **missing_evidence:** V1–V5 (implementation)

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | Default pec refuse vs warn-only | `accept_bounded` — default refuse + `--admission-draft` for inspect |
| unknown | U2 | Cursor result JSON status field | `accept_bounded` — optional `status`; missing/non-PASS → BLOCKED/FAIL |
| unknown | U3 | Which campaigns compile in CI | `accept_bounded` — only `compile: true`; day-one `bounded-replanning-v1` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | Attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); T0 new branch from origin/main; do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| broader_work_requires_separate_contract | `true` |
| next_skill | `l9-ynp` |

## Machine stub

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.program-execution.crack-remediation.v1
  name: PE crack remediation: campaign compile, pec gates, honest PASS
  status: executable
  is_project: false
  created_at: 2026-08-14
immutable_baseline:
  repository: Quantum-L9/Cursor-Governance
  commit_sha: 1aba3592b094f8bd424479264e725ade585c018e
  dirty: true  # current workspace; landing tree must be clean
  overlap_policy: require_clean_tree
  on_drift: stop_and_replan
execution_envelope:
  autonomous_merge: false
  network:
    mode: named_services_only
  secrets:
    access: none
    redaction_required: true
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  controller: environment/program-execution/core/program-execution-controller-template
  blueprint: environment/program-execution/core/program-execution-blueprint-template
  autonomy_provider: root-autonomy-control-plane
  adapter_default: cursor-foreground
  slash: /autonomy
  skill: l9-bounded-autonomy
  mention_autonomy: "@autonomy"
```
