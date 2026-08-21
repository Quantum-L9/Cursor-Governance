---
name: "PE crack remediation: campaign compile, pec gates, honest PASS"
status: superseded
built: true
overview: "Close the load-bearing Program Execution cracks so campaign source compiles through a repo-owned schema and compiler, pec refuses unvalidated draft locks by default, Cursor/ChatGPT cannot substitute PASS, and Make/conformance gate those contracts. Do not admit bounded-replanning-v1, do not mutate its immutable CAMPAIGN_SOURCE.yaml, do not add a DeepSeek PE provider, and do not land on the dirty feature branch."
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
    content: "Add campaign-source.v2 JSON Schema covering the live CAMPAIGN_SOURCE dialect and a fixture that validates all four registered campaign files"
    status: cancelled
    phase: execute
    depends_on: [T0]
    side_effect_ref: SE-T1
    evidence_property_refs: [SP-02]
  - id: T2
    content: "Add a repo-owned compiler that remaps campaign-source fields onto Blueprint v2 including authorities to AUTHORITY_REGISTRY, rewrites MANIFEST.yaml, and forces program_control local_write false without editing campaign source bytes"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T2
    evidence_property_refs: [SP-02, SP-06]
  - id: T3
    content: "Make pec bootstrap call instantiated validate_blueprint before write_program_lock; add --admission-draft that cannot mark tasks ready"
    status: cancelled
    phase: execute
    depends_on: [T2]
    side_effect_ref: SE-T3
    evidence_property_refs: [SP-04]
  - id: T4
    content: "Replace untyped empty-object Blueprint schema properties with types taken from live blueprint-template YAML instances"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T4
    evidence_property_refs: [SP-02]
  - id: T5
    content: "Map optional host result status into CanonicalProviderResult; missing or non-PASS host status MUST become FAIL or BLOCKED, never PASS"
    status: cancelled
    phase: execute
    depends_on: [T0]
    side_effect_ref: SE-T5
    evidence_property_refs: [SP-05]
  - id: T6
    content: "Bind campaign target adapter tokens git and git_repo_adapter in the campaign schema only; document that pec reconcile uses repository_id, not a worker adapter"
    status: cancelled
    phase: execute
    depends_on: [T1, T2]
    side_effect_ref: SE-T6
    evidence_property_refs: [SP-02]
  - id: T7
    content: "Append campaign compile/validate, pec controller tests, validate_manifest, and COMPILE_ALLOWLIST into Make PE targets without deleting existing Makefile lines"
    status: cancelled
    phase: execute
    depends_on: [T2, T3, T5]
    side_effect_ref: SE-T7
    evidence_property_refs: [SP-03]
  - id: T8
    content: "Correct campaign honesty in README only: leftover campaigns archival/inconclusive; receipt producer and path mismatches called out; do not rewrite receipt JSON or campaign source bytes"
    status: cancelled
    phase: execute
    depends_on: [T1]
    side_effect_ref: SE-T8
    evidence_property_refs: [SP-06]
  - id: T9
    content: "Record Claude backend_mode and model_hint as probe evidence only; keep DeepSeek out of the PE provider registry; T16 owns the executable-vs-path probe split"
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
    content: "Retitle PE ARCHITECTURE.md as Program Execution and document the compile then validate then bootstrap path in README"
    status: cancelled
    phase: execute
    depends_on: [T2, T3, T10]
    side_effect_ref: SE-T11
    evidence_property_refs: [SP-02]
  - id: T12
    content: "Prove the stack: campaign compile fixture, immutable source digest, pec admission-draft negative test, Cursor FAIL mapping, Make PE targets, make pr-check"
    status: cancelled
    phase: validate
    depends_on: [T4, T6, T7, T8, T9, T11, T14, T15, T16, T17]
    evidence_property_refs: [SP-01, SP-02, SP-03, SP-04, SP-05, SP-06, SP-07, SP-08]
  - id: T13
    content: "Align program-lock.schema.json with normalize_blueprint writer fields do_not_build and current_state; verify_program_lock MUST run JSON Schema"
    status: cancelled
    phase: execute
    depends_on: [T3]
    side_effect_ref: SE-T13
    evidence_property_refs: [SP-07]
  - id: T14
    content: "Enforce Blueprint DO_NOT_BUILD prohibited paths at pec verify, not only Source Contract writable_paths"
    status: cancelled
    phase: execute
    depends_on: [T13]
    side_effect_ref: SE-T14
    evidence_property_refs: [SP-07]
  - id: T15
    content: "Reject source-contract rollback strings that match REPLACE_WITH placeholder text at register time"
    status: cancelled
    phase: execute
    depends_on: [T3]
    side_effect_ref: SE-T15
    evidence_property_refs: [SP-04]
  - id: T16
    content: "Split Cursor and Claude probes into structural vs transport; path-only checks MUST NOT emit PASS or READY when transport is file-drop or claude is absent"
    status: cancelled
    phase: execute
    depends_on: [T5]
    side_effect_ref: SE-T16
    evidence_property_refs: [SP-08]
  - id: T17
    content: "Append program-execution-core-validate and validate_thin_providers to peer-execution CI and peer-execution-conformance; ignore __pycache__ in pair and adapter validators"
    status: cancelled
    phase: execute
    depends_on: [T7]
    side_effect_ref: SE-T17
    evidence_property_refs: [SP-03]
isProject: false
---
# PLAN: PE crack remediation: campaign compile, pec gates, honest PASS

> **SUPERSEDED** by `.cursor/plans/pe_crack_remediation_760ee9d3.plan.md` (microscope-audit delta, 2026-08-14). Do not execute this file.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Machine SSOT:** `.cursor/plans/pe_crack_remediation_v1.json` (`validate_plan_document.py` PASS; hex `760ee9d3`)
> **Supersedes:** `.cursor/plans/pe_crack_remediation_4c064022.plan.md` (microscope-audit delta T13–T17). Earlier: `4a0fefbe`.
> **Schema:** `canonical.schema.plan_document.v1`
> **Dual-artifact status law:** JSON `convergence.status=partial` because V1–V5 are pending. Markdown `status=executable` means the *plan contract* is ready to project through PE+autonomy. It does **not** mean implementation evidence has passed.
> **Execute:** **[@environment/program-execution](environment/program-execution/)** then subordinate **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Landing:** new branch from `origin/main` (`KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`). MUST NOT land on `fix/ci-required-contexts-wip-only`.

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

Program leases are authoritative. Autonomy leases MUST NOT outlive the Program lease. MUST NOT invent a second scheduler. MUST NOT auto-init `.l9/autonomy/campaigns/*.json` from pec.

### Pipeline steps

1. **Attach** [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md).
2. **T0 first:** create a clean worktree / new branch from `origin/main` @ `1aba3592b094f8bd424479264e725ade585c018e`. MUST refuse the dirty `fix/ci-required-contexts-wip-only` checkout.
3. **Project this plan → Blueprint artifacts** under `$HOME/.l9/programs/pe-crack-remediation-v1/` — MUST NOT mutate sealed `environment/program-execution/core/` templates in place except through the Task Cards below.

   | Plan section | PE Blueprint / Controller artifact |
   |--------------|-------------------------------------|
   | metadata / objective | `PROGRAM.yaml` / program identity `pe-crack-remediation-v1` |
   | immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA `1aba3592…` |
   | execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
   | execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
   | capability_preflight | Controller reconcile + gate probes before claim |
   | property_evidence_matrix | Task Card `validation` / evidence catalog refs |
   | rollback | Task Card `rollback` + recovery receipts |
   | convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt |

4. **Validate + bootstrap Controller** for *this overlay* (not bounded-replanning admission):

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

   After T3, this overlay Blueprint MUST be `accepted` for its own Task Cards, **or** use `--admission-draft` for inspect only. MUST NOT flip `bounded-replanning-v1` to `accepted`.

5. **Admit exact task scope** — Source Contract ⊂ Task Card ceiling; then `claim` → `prepare` → `render-contract`.
6. **Map Program task → autonomy campaign** via `environment/program-execution/integrations/autonomy-control-plane/`.
7. **Orchestrate under [@autonomy](commands/autonomy.md)** — Protocols A–D.
8. **L4 local autonomy:** local commits only until `ops/autonomy/l4_local.py authorize-release` → scoped push/PR → `l9-pr-remediation`. Launching this plan through PE+`/autonomy` **or** clicking Build **is** merge authorization for this stack after green+mergeable (older PRs first).
9. **Record + verify + handoff** — `pec.py record-attempt` → `verify` → `export-handoff`.

### Adapter routing

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
plan_ref: .cursor/plans/pe_crack_remediation_760ee9d3.plan.md
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
  - mutate_bounded_replanning_campaign_source
  - rewrite_source_integrity_receipt
  - add_deepseek_pe_provider
  - auto_init_autonomy_campaign_packets
  - overwrite_makefile_existing_lines
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
| T8 | TASK-007 | W2 | [T1] | true | `path:environment/program-execution/campaigns/*/README.md` | `honesty` | `pes.w2.task007` | `work` | `cursor-foreground` |
| T3 | TASK-008 | W3 | [T2] | true | `path:environment/program-execution/core/program-execution-controller-template/scripts/pec/` | `pec-gate` | `pes.w3.task008` | `work` | `cursor-foreground` |
| T6 | TASK-009 | W3 | [T1, T2] | true | `path:environment/program-execution/core/shared/schemas/campaign-source.schema.json` | `adapter-token` | `pes.w3.task009` | `work` | `cursor-foreground` |
| T10 | TASK-010 | W3 | [T3] | true | `path:environment/program-execution/peer_execution/autonomy/bootstrap.py` | `dual-plane` | `pes.w3.task010` | `work` | `cursor-foreground` |
| T7 | TASK-011 | W4 | [T2, T3, T5] | true | `path:Makefile` | `make-pe` | `pes.w4.task011` | `work` | `cursor-foreground` |
| T11 | TASK-012 | W4 | [T2, T3, T10] | true | `path:environment/program-execution/ARCHITECTURE.md` | `docs` | `pes.w4.task012` | `work` | `cursor-foreground` |
| T12 | TASK-013 | W5 | [T4, T6, T7, T8, T9, T11, T14, T15, T16, T17] | false | `evidence:plan.program-execution.crack-remediation.v1` | `validate` | `pes.w5.task013` | `work` | `ci-generic-shell` |
| T13 | TASK-014 | W3 | [T3] | true | `path:…/schemas/program-lock.schema.json` | `lock-schema` | `pes.w3.task014` | `work` | `cursor-foreground` |
| T14 | TASK-015 | W4 | [T13] | true | `path:…/pec/controller.py` | `dnb-verify` | `pes.w4.task015` | `work` | `cursor-foreground` |
| T15 | TASK-016 | W3 | [T3] | true | `path:…/pec/contracts.py` | `rollback-placeholder` | `pes.w3.task016` | `work` | `cursor-foreground` |
| T16 | TASK-017 | W2 | [T5] | true | `path:environment/program-execution/adapters/` | `probe-honesty` | `pes.w2.task017` | `work` | `cursor-foreground` |
| T17 | TASK-018 | W4 | [T7] | true | `path:.github/workflows/peer-execution.yml` | `ci-pe` | `pes.w4.task018` | `work` | `cursor-foreground` |

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A. Autonomy MUST NOT bypass wave order.

**Stop / do not execute when:** JSON plan missing; Program Lock drift; dirty landing tree; attempt to set `bounded-replanning-v1` `definition_status=accepted`; attempt to edit that campaign's `CAMPAIGN_SOURCE.yaml` or `source-integrity-receipt.json`; attempt to add a DeepSeek PE provider; Makefile deletion of existing lines.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.program-execution.crack-remediation.v1` |
| name | PE crack remediation: campaign compile, pec gates, honest PASS |
| schema_version | `1.0.0` |
| status | `executable` (plan contract). JSON convergence remains `partial` until V1–V5 pass. |
| is_project | `false` |
| owner | Cursor-Governance / Program Execution |
| created_at | `2026-08-14` |
| updated_at | `2026-08-14` |
| machine_ssot | `.cursor/plans/pe_crack_remediation_v1.json` |
| depth | `deep` |
| improve_kernel | `kernels/Improve.md` v3.0 applied to prior plan `4a0fefbe` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `environment/program-execution/` + ADRs 0017–0022 + 2026-08-14 PE folder crack audit |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Close unbound campaign dialect, pec draft-lock, and substituted PASS. Honesty for TASK-007 is a compiler rewrite. Compile allowlist lives outside immutable seeds. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-14T18:43:00-04:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `/Users/ib-mac/.cursor-governance` |
| branch | `fix/pe-crack-remediation-v1` (create at execute) |
| commit_sha | `1aba3592b094f8bd424479264e725ade585c018e` |
| dirty | current workspace `true`; **landing tree MUST be clean** |
| artifact_hashes | `{ "environment/program-execution/campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml": "sha256:7a71ede7fc3dd0272ceed5ce4cbaf62a5d66769f75b0fe21689d7eb6f8168619" }` |
| allowed_local_dirt | none on the landing worktree |
| overlap_policy | `require_clean_tree` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Program Execution has an unbound campaign-source dialect (four `CAMPAIGN_SOURCE.yaml` files, zero schema, zero in-repo compiler), pec bootstrap that locks unvalidated drafts (`normalize_blueprint` then `write_program_lock`), and Cursor/ChatGPT providers that emit `CanonicalProviderResult.status="PASS"` whenever a result file exists. Close those cracks. Preserve thin-adapter law, ADR-0020, `autonomous_merge: false`, `definition_status=draft` for bounded-replanning-v1, and `metadata.source_is_immutable: true`.

### Locked compiler remap table (T2 MUST implement)

| Campaign-source field | Blueprint v2 field | Rule |
|-----------------------|--------------------|------|
| `selected_option_id` | `selected_option` | rename |
| `blocking_task_ids` | `blocks` | rename |
| `predecessor_wave_ids` | `depends_on` | rename |
| `git_repo_adapter` | `git` | campaign token only; MUST NOT add a registry worker |
| `program.contracts` extra keys (e.g. `new_replan_contract`) | omit | schema allows only `pair` / `blueprint` / `controller_minimum` |
| likelihood `possible` | `medium` | enum cover |
| `execution_kind=program_control` AND `local_write=true` | `local_write=false` | validate_blueprint law; do this in the compiler, not the seed |
| `authorities[]` (`owner`, `authority_type`, `scope`) | `AUTHORITY_REGISTRY.responsibilities[]` | map onto required Blueprint keys; missing required keys MUST error, not invent owners |
| evidence `planned` / `revision=UNKNOWN` | unchanged | instantiated validate MUST still FAIL |

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Landing HEAD equals locked origin/main SHA at start | `repository_state` | `git rev-parse HEAD` == `1aba3592b094f8bd424479264e725ade585c018e`; worktree clean | true |
| SP-02 | Schema + compiler exist; template-mode PASS on compiled bounded-replanning-v1 | `structural` | four-file fixture + V2 compile/validate | true |
| SP-03 | Make PE targets and `make pr-check` PASS; leftover campaigns not compiled | `quality_gate` | V4 + V5; allowlist contains only `bounded-replanning-v1` | true |
| SP-04 | pec bootstrap refuses draft/unvalidated Blueprints unless `--admission-draft` | `runtime_behavior` | V3 nonzero; draft flag → `ready: []` | true |
| SP-05 | Cursor/ChatGPT missing or non-PASS host status cannot become canonical PASS | `runtime_behavior` | unit tests: missing→BLOCKED; FAIL→FAIL | true |
| SP-06 | Immutable seed unchanged; compiled TASK-007 `local_write=false`; honesty is README-only | `filesystem` | source digest `7a71ede7…`; receipt JSON bytes unchanged | true |
| SP-07 | Program lock writer output validates against `program-lock.schema.json`; verify enforces DO_NOT_BUILD | `structural` | T13/T14 tests; `do_not_build` and `current_state` are schema properties | true |
| SP-08 | Cursor/Claude path-only probes are not PASS/READY | `runtime_behavior` | T16 tests; missing `claude` or file-drop transport → BLOCKED | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`  
`instance_binding:` `preflight.plan.program-execution.crack-remediation.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.program-execution.crack-remediation.v1` |
| source_ref | `plan.program-execution.crack-remediation.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `1aba3592b094f8bd424479264e725ade585c018e` |
| baseline_verified | planning-time `origin/main` resolved; reverify at T0 |
| drift_detected | current workspace dirty on another branch — expected |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git fetch origin && git rev-parse origin/main` | equals locked SHA or stop_and_replan | true |
| CP-02 | `command_available` | `python3`, `make`, `git` | all on PATH | true |
| CP-03 | `filesystem_write` | write_allow on the *new* worktree | landing tree clean and writable | true |
| CP-04 | `schema_gap_still_present` | glob campaign-source schema + compile script | both absent at T0 | true |
| CP-05 | `cursor_result_contract` | read `foreground_transport.py` `collect()` | any object; no status required (U2 locked) | true |
| CP-06 | `immutable_seed` | `shasum -a 256 …/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml` | `7a71ede7fc3dd0272ceed5ce4cbaf62a5d66769f75b0fe21689d7eb6f8168619` | true |

Planning P0–P5: **passed**. Re-run CP-01/CP-03/CP-06 on the landing tree before first mutation.

## Execution envelope

### Filesystem

- **write_allow:**
  - `environment/program-execution/` except the two deny paths below
  - `Makefile` (append-only; root-file-protection `additive_only` / `canonical`)
  - `$HOME/.l9/programs/pe-crack-remediation-v1/` (runtime; not git)
  - `$HOME/.l9/blueprints/` compiled trees (runtime; not git)
- **write_deny:**
  - `environment/program-execution/campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml`
  - `environment/program-execution/campaigns/bounded-replanning-v1/source-integrity-receipt.json`
  - `CANONICAL_LAW.md`, `pyproject.toml` existing keys, `ops/hooks/session_start_bootstrap.sh`
  - `WIP/`, `.env.local`, legal evidence
  - ADR-0020 decision text
  - `EXECUTION_ADAPTER_REGISTRY.yaml` adding `git` / `git_repo_adapter` / DeepSeek workers
- **delete_allow:** none in git. Disposable: `$HOME/.l9/blueprints/_compile_bounded_replanning.py` after T2.

### Commands

- **allow:** `git` (non-destructive), `python3` pec/validate/compile/tests, `make program-execution-*`, `make pr-check`, `make pr` only after L4 `authorize-release`, `ops/autonomy/l4_local.py`
- **deny:** force-push, hard-reset, admin-merge, secret exfil, scanner weakening, faking `accepted`, rewriting campaign source bytes

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `origin` git (after L4 release), GitHub API for scoped PR |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`

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
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore campaign READMEs | false |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore claude provider/README | false |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore pec status + bootstrap.py | false |
| T11 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore ARCHITECTURE/README | false |
| T12 | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |

T8 MUST NOT change campaign YAML or receipt JSON. T2 owns TASK-007 honesty.

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | campaign source | `policy` | new `campaign-source.schema.json` | required fields absent from the four live files |
| T2 | compile | `control_plane` | Blueprint v2 + `validate_blueprint.py` | keep `$HOME/.l9` ad-hoc compiler; edit seed YAML |
| T3 | pec admission | `control_plane` | controller.v2 | lock drafts as admitted; fake `accepted` |
| T4 | Blueprint schemas | `policy` | blueprint-template schemas | invent required keys not present in live YAML |
| T5 | thin adapters | `runtime` | thin-adapter law | substitute PASS; thicken adapters |
| T6 | campaign tokens | `policy` | campaign-source schema | add `git` worker to adapter registry |
| T7 | Make PE gates | `ops` | Makefile additive_only | delete/overwrite existing Makefile lines |
| T8 | campaign docs | `docs` | `source_is_immutable` | rewrite receipt or seed |
| T9 | Claude probe | `runtime` | ADR-0020 | register DeepSeek as a PE provider |
| T10 | dual-plane | `control_plane` | autonomy-control-plane | auto-init campaign packets |
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
| trigger_conditions | baseline drift; blocking SP fail; envelope breach; leftover campaigns compiled; Cursor PASS mapping inverted; source digest changed |

### Strategies

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | feature-branch commits only; no force-push |
| data | `none` | |
| external_state | `none` | no campaign packet writes |
| local_state | `manual_recovery` | `$HOME/.l9` disposable; git seeds are not |

### Irreversible operations

- None authorized. Source-byte mutation is forbidden, not reversible-by-receipt-rewrite.

### Rollback verification

- Feature branch abandoned vs `origin/main`
- `shasum` of bounded-replanning `CAMPAIGN_SOURCE.yaml` still `7a71ede7…`
- pec `--admission-draft` still available if default refuse is too tight

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `3` |
| external_systems_touched | `0` during local execute; `1` (GitHub) after L4 release |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`

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
| T2 | agent | control_plane | [T1] | compiler + remap table + TASK-007 rewrite |
| T4 | agent | policy | [T1] | typed Blueprint schemas from live YAML |
| T8 | agent | docs | [T1] | README honesty only |
| T3 | agent | control_plane | [T2] | pec bootstrap gate + `--admission-draft` |
| T6 | agent | policy | [T1, T2] | git token bind; no registry worker |
| T10 | agent | control_plane | [T3] | read-only dual-plane status |
| T7 | agent | ops | [T2, T3, T5] | appended Make PE gates + COMPILE_ALLOWLIST |
| T11 | agent | docs | [T2, T3, T10] | ARCHITECTURE/README path |
| T12 | agent | assurance | [T4, T6, T7, T8, T9, T11] | V1–V5 evidence |

**Critical path:** `T0` → `T1` → `T2` → `T3` → `T13` → `T7` → `T12`  
**Joins:** `T5` is parallel after T0 and precedes T7 and T16. `T13` follows T3. `T17` follows T7.

**Forbidden edges:** T3 before T2; T7 before T3/T5; T8 editing YAML/receipt; T6 adding a git worker; T10 writing autonomy campaign JSON; any mutation on `fix/ci-required-contexts-wip-only`.

### Waves

- **W0:** T0
- **W1:** T1, T5, T9
- **W2:** T2, T4, T8
- **W3:** T3, T6, T10
- **W4:** T7, T11
- **W5:** T12

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse | `git rev-parse HEAD` | `1aba3592b094f8bd424479264e725ade585c018e` | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | schema + compile | V1 + V2 | four campaigns parse; template PASS | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | Make + pr-check | V4 + V5 | all PASS; allowlist = bounded-replanning-v1 | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | negative bootstrap | V3 | nonzero without `--admission-draft` | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | provider unit tests | cursor/chatgpt tests | missing→BLOCKED; FAIL→FAIL | `not_run` |
| EV-SP-06 | SP-06 | `filesystem_evidence` | digest + compiled YAML | `shasum` + inspect compiled TASK-007 | digest `7a71ede7…`; `local_write: false` | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- pec already blocks ready tasks on planned evidence → **accepted:** default refuse + `--admission-draft` for inspect (U1).
- schema requires new campaign fields → **accepted:** T1 MUST be a cover of the live four files; no new required keys.
- Cursor result JSON has no status → **locked:** optional `status`; missing/non-PASS → BLOCKED/FAIL (U2).
- Make compiles every campaign directory → **accepted:** `campaigns/COMPILE_ALLOWLIST.yaml` outside seeds; day-one id `bounded-replanning-v1` (U3).
- T4 types tighter than live blueprint-template YAML → **accepted:** type from live instances; no invented required keys.

### Assumption failure conditions

- `origin/main` SHA drifts → stop_and_replan
- Dirty landing tree overlaps `write_allow` → stop
- Source digest changes → stop; revert
- `validate_blueprint --mode instantiated` starts accepting `draft` → stop
- Makefile existing lines deleted → stop (root-file-protection)

### Blast radius notes

PE admission, every pec bootstrap, Cursor/ChatGPT receipts, Make PE CI, four campaign seeds, Blueprint template validation.

### Rollback constraints

- No force-push / history rewrite
- `$HOME/.l9` disposable; git campaign seeds are not
- Do not delete the existing `$HOME/.l9/programs/bounded-replanning-v1` lock; document it as non-admitted

## Out of scope

- Accepting or faking `program.definition_status=accepted` for bounded-replanning-v1
- Mutating `CAMPAIGN_SOURCE.yaml` or `source-integrity-receipt.json` for that campaign
- Collecting EVID-001–008 or implementing Replan Revision
- Adding a DeepSeek PE provider or changing ADR-0020
- Re-executing leftover INCONCLUSIVE campaigns
- `WIP/`, legal evidence, `fix/ci-required-contexts-wip-only`
- `CANONICAL_LAW.md`, `pyproject.toml` existing keys, sessionStart rewrite
- Adding `git` / `git_repo_adapter` workers to the adapter registry
- Auto-init of `.l9/autonomy/campaigns/*.json`
- Force-push, hard-reset, admin-merge, `autonomous_merge`, secret commits

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | Collect EVID-001–008 and admit bounded-replanning-v1 | Admission is a different program |
| P2 | Compile leftover campaigns after archival cleanup | U3 excludes them from day-one CI |
| P3 | Host-required Cursor status field | T5 works with optional status |
| P4 | `pec relock` CLI | Documented; not implemented; new-workspace recovery remains |
| P5 | Rename `peer_execution.autonomy` to end the root `autonomy` import collision | Distinct from “no second scheduler”; package rename is follow-on |
| P6 | Implement `program-execution.replan.v1` | Bounded-replanning admission program, not this overlay |
| P7 | Reconcile workspace vs `$HOME/.cursor-governance` dual-clone tip | Operational; T0 lands from `origin/main` |
| P8 | Retire `environment/program-execution-campaigns/` / `l9-unified-campaign-compiler` | Orphan pack outside MANIFEST |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.program-execution.crack-remediation.v1` |
| source_ref | `plan.program-execution.crack-remediation.v1` |
| current_state | `execution_ready` |
| implementation_ready | `true` for plan projection; V1–V5 `not_run` |

### Gates

- **executable_when:** baseline locked; probes pass; DAG acyclic; envelope complete; unknowns accepted-bounded
- **complete_when:** SP-01..SP-06 `passed`; source digest unchanged; out_of_scope respected
- **blocking_conditions:** dirty landing branch; source mutation; pec still locks drafts after T3; substituted PASS remains; Makefile overwrite; leftover campaigns compiled

### Evidence

- **required_evidence_refs:** `EV-SP-01` … `EV-SP-06`
- **observed_evidence_refs:** P0–P5 passed; U2 locked against `foreground_transport.py`; `source_is_immutable: true`
- **missing_evidence:** V1–V5

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | Default pec refuse vs warn-only | `accept_bounded` — default refuse + `--admission-draft` |
| unknown | U2 | Cursor result JSON status | `accept_bounded` — optional; missing/non-PASS → BLOCKED/FAIL |
| unknown | U3 | CI compile set | `accept_bounded` — `COMPILE_ALLOWLIST.yaml`; day-one `bounded-replanning-v1` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | Attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); T0 new branch from origin/main |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| broader_work_requires_separate_contract | `true` |
| next_skill | `l9-ynp` |

## Machine stub

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.program-execution.crack-remediation.v1
  status: executable
  is_project: false
  created_at: 2026-08-14
immutable_baseline:
  repository: Quantum-L9/Cursor-Governance
  commit_sha: 1aba3592b094f8bd424479264e725ade585c018e
  overlap_policy: require_clean_tree
  on_drift: stop_and_replan
execution_envelope:
  autonomous_merge: false
  secrets:
    access: none
    redaction_required: true
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  slash: /autonomy
  skill: l9-bounded-autonomy
  mention_autonomy: "@autonomy"
  adapter_default: cursor-foreground
```
