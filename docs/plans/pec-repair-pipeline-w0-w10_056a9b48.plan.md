---
name: PEC repair pipeline W0-W10
overview: "W0-W7 built on this checkout (shadow graduation only). W8 v3 control plane, W9 RiskPacket/ImpactEngine, and W10 dogfood are pending — later plan, fresh origin/main SHA after this PR lands. Do not start them from this plan."
todos:
  - id: T-W0-stderr
    content: "Retain bounded worker stdout/stderr text on FAIL in the Claude adapter; keep digest fields"
    status: completed
    phase: execute
    depends_on: []
  - id: T-W0-sha
    content: "Align candidate identity with permission_renderer denials of git add and git commit"
    status: completed
    phase: execute
    depends_on: [T-W0-stderr]
  - id: T-W0-probe
    content: "Re-probe one 1-file local_write path at current HEAD via adapter tests; record turns, changed_files, stderr text"
    status: completed
    phase: execute
    depends_on: [T-W0-sha]
  - id: T-W1-characterize
    content: "Add characterization tests for journeys A-J that record route, stages reached, losses, and side effects without semantic fixes"
    status: completed
    phase: execute
    depends_on: [T-W0-stderr]
  - id: T-W1-fixtures
    content: "Land fixture corpus 01 through 14 plus semantic expectation format that is not a second Blueprint"
    status: completed
    phase: execute
    depends_on: [T-W1-characterize]
  - id: T-W1-shadow
    content: "Implement shadow compiler runner and comparator with dimensioned metrics and zero campaign execution side effects"
    status: completed
    phase: execute
    depends_on: [T-W1-fixtures]
  - id: T-W2-counterexamples
    content: "Freeze current failures as a machine-readable counterexample registry; mark desired-safe assertions as expected failures; no semantic product fixes in this wave"
    status: completed
    phase: execute
    depends_on: [T-W1-shadow]
  - id: T-W3-ingress
    content: "Unify human ingress so one-liner, ADR, Markdown, architecture-intent, and program-execution.intent.v1 enter without operator-chosen internal route; keep intent.py strict"
    status: completed
    phase: execute
    depends_on: [T-W2-counterexamples]
  - id: T-W4-fidelity
    content: "Add semantic materiality so lowercase prohibitions and constraints survive with provenance; keep uppercase MUST/MUST NOT as high-confidence anchors; retarget case-sensitivity tests to the new contract"
    status: completed
    phase: execute
    depends_on: [T-W3-ingress]
  - id: T-W5-microscope
    content: "Extend repo_truth with disposition IR (ALREADY_SATISFIED KEEP MERGE HARDEN CREATE DELETE_SUPERSEDED UNKNOWN) plus path and symbol evidence before task synthesis"
    status: completed
    phase: execute
    depends_on: [T-W4-fidelity]
  - id: T-W6-lowering
    content: "Synthesize tasks from obligation times owner times seam; unknown seam is a discovery dependency; require per-task writable paths; stop docs/program-execution TASK fallback"
    status: completed
    phase: execute
    depends_on: [T-W5-microscope]
  - id: T-W7-graduate
    content: "Prove golden journeys through shadow compile plus Blueprint validation with zero material-intent loss, false CREATE, authority widening, and manual IR edits; do not invoke the campaign runner"
    status: completed
    phase: execute
    depends_on: [T-W0-probe, T-W6-lowering]
  - id: T-W8-v3
    content: "PENDING later plan — v3 control-plane S1-S8 + REPLAN_CONTRACT on two planes. Requires a fresh origin/main SHA after this PR. Do not start from this Build."
    status: pending
    phase: execute
    depends_on: [T-W7-graduate]
  - id: T-W9-risk
    content: "PENDING later plan — RiskPacket / ImpactEngine / enforcement / outcome replan. Blocked on T-W8-v3 and U4 (l9-assurance not attached)."
    status: pending
    phase: execute
    depends_on: [T-W8-v3]
  - id: T-W10-dogfood
    content: "PENDING later plan — PEC dogfood of the messy RiskPacket objective. Blocked on T-W9-risk."
    status: pending
    phase: execute
    depends_on: [T-W9-risk]
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: "pec-repair-pipeline-w0-w10_056a9b48.plan.md"
  improve:
    kernel: kernels/Improve.md
    ran_at: "2026-08-29T21:05:00Z"
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Replaced renderer seed-only quality_gate proofs with per-wave structural and runtime evidence."
      - "Split W0 stderr retention from candidate-identity so the probe can name the remaining defect."
      - "Parked W8-W10 behind CP-W7 so RiskPacket cannot start from this Build."
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: "2026-08-29T21:06:00Z"
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Execute path is Cursor Build; campaign runner, Program Lock, and Controller lease stay out of this plan."
      - "Preserved Program Controller, REPLAN_CONTRACT, authorization, evidence, TransportPacket, and refuse_publication."
      - "Ingress stays before strict intent.py; no second compiler or runtime."
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: "2026-08-29T21:07:00Z"
    body_sha256: "c3b51c09cfb203f660337dbc7314f0d66334880fdbb4b148f2e1d1159761459f"
    deltas:
      - "Filled envelope, DAG, side-effect matrix, rollback, and evidence rows for every mutating todo."
      - "Named U1-U4 with probe or block resolutions; no inferred W0 outcome at stale SHA c3081ee."
      - "Removed unfilled template placeholders so status can be executable after sha bind."
---
# PLAN: PEC repair pipeline W0-W10

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **PLAN_DOCUMENT:** `WIP/8-29-26/PEC/PLAN_DOCUMENT.pec-repair-pipeline.v1.json`
> **Pipeline SSOT:** `WIP/8-29-26/PEC/PEC-repair-pipeline.md`
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** W0–W7 already built. Do **not** start W8–W10 from this plan.

## Build outcome (2026-08-29)

W0–W7 landed as commit `c794ac30` (parked across `/ff`; republish from current `origin/main`). 203 targeted PE tests passed on that tree. Campaign runner was not invoked.

| Wave | Status | Honest residual |
|------|--------|-----------------|
| W0 | **built** | FAIL receipts keep bounded redacted text + digests. Probe is the adapter fixture (13-turn FAIL), not a live hosted worker. Candidate identity is controller HEAD; worker still cannot `git add`/`commit`. |
| W1 | **built** | `compiler/tests/conformance/` fixtures 01–14 + shadow runner. No `~/.l9/programs` write. |
| W2 | **built** | `counterexamples.yaml` records AT-002–008 as closed-by-later-wave, not as live xfails. |
| W3 | **built, partial** | `--check-input` / `compile_intent_ingress` compiles `program-execution.intent.v1`. `SUPPORTED_KINDS` still omits it so `classify_campaign_input` / `make campaign` still refuse execute. Conversion is no longer the only operator path. |
| W4 | **built** | Lowercase `don't` / `must` survive. Bare conversational `never` is not a signal (golden architecture SRC-0002). |
| W5 | **built, thin** | `classify_dispositions` is path/symbol evidence, not a full microscope. Unknown stays UNKNOWN. |
| W6 | **built** | No `docs/program-execution/<TASK>.md` fallback. Unknown seam is inspection-only. Blocking unknown IDs were not emitted (Blueprint validator rejected unresolved `UNK-SEAM-*`). |
| W7 | **built, shadow only** | Golden journeys: material-intent loss, false CREATE, authority widening = 0. **`make campaign` was not run.** Spine execute/Lock/repeatability (10 clean shadow+execute runs) is still pending. |
| W8 | **pending — later plan** | v3 two-plane reconstruction. Needs a new baseline SHA after this PR lands. |
| W9 | **pending — later plan** | RiskPacket / ImpactEngine. Also blocked on U4 (`l9-assurance` not attached). |
| W10 | **pending — later plan** | PEC dogfood of the messy Risk objective. Blocked on W9. |

Revisit W8–W10 only in a new plan bound to the post-merge `origin/main` SHA. Do not reopen this plan to start them.

## Execute via Cursor Build

W0–W7 are done. Do not press Build to start W8–W10.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.pec.repair-pipeline.v1` |
| name | PEC repair pipeline W0-W10 |
| overview | W0-W7 built (shadow); W8-W10 pending later plan + fresh SHA |
| schema_version | `1.0.0` |
| status | `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | `2026-08-29` |
| updated_at | `2026-08-29` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `WIP/8-29-26/PEC/PEC-repair-pipeline.md` |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Cursor Build on current checkout. Compiler/runtime PE module only. No second controller. W8-W10 are follow-on inside this DAG but gated by CP-W7. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-29T21:02:00Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `main` |
| commit_sha | `74f8622617db907941587679a18b93cf3e5d7b50` |
| dirty | `true` |
| artifact_hashes | `{ "WIP/8-29-26/PEC/PEC-repair-pipeline.json": "file", "WIP/8-29-26/PEC/PLAN_DOCUMENT.pec-repair-pipeline.v1.json": "file" }` |
| allowed_local_dirt | `WIP/**`, `docs/plans/**`, untracked plans JSON |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

Re-verify `git rev-parse HEAD` at Build start. If it differs from `74f8622617db907941587679a18b93cf3e5d7b50`, stop and replan. Do not treat this SHA as an origin/main lock.

## Objective

### Mission

PEC runtime law is already strong (`refuse_publication`, Program Lock, authorization, evidence, REPLAN_CONTRACT). The remaining defect is the front half: worker FAILs are undiagnosable, human intent still requires picking an internal schema, lowercase prohibitions can vanish, grounding cannot KEEP vs CREATE, and lowering follows document sections. This Build executes W0-W7 of `PEC-repair-pipeline.md` as scoped code changes plus a shadow harness. W8-W10 stay in the DAG but must not start until W7 metrics are zero.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | HEAD at Build start equals captured commit_sha unless dirt is only allowed_local_dirt | `repository_state` | `git rev-parse HEAD` | true |
| SP-02 | FAIL receipts include bounded stderr/stdout text; digest fields remain | `structural` | `provider.py` stores text on FAIL; `test_driver.py` asserts | true |
| SP-03 | candidate identity matches git add/commit denials | `structural` | permission_renderer and controller/peer_execution agree; probe log names turns and changed_files | true |
| SP-04 | Shadow harness exists; fixtures 01-14; no campaign execution side effect | `filesystem` | `compiler/tests/conformance/` + shadow_runner; git status under `~/.l9/programs` unchanged by the runner | true |
| SP-05 | `program-execution.intent.v1` is a live ingress kind; operator is not told conversion is the only path | `structural` | `SUPPORTED_KINDS` includes it or a normalizer feeds it before reject | true |
| SP-06 | lowercase prohibition retains provenance; case-sensitivity tests retargeted not deleted to hide loss | `runtime_behavior` | pytest conformance fixture 04 plus `test_architecture_intent.py` | true |
| SP-07 | Dispositions exist before lowering; tasks name writable paths | `structural` | repo_truth disposition IR; architecture_to_campaign has no docs/program-execution fallback | true |
| SP-08 | W7 metrics: material_intent_loss, false_create_where_canonical_exists, authority_widening, manual IR edits are 0 | `proof_receipt` | shadow comparator report | true |
| SP-09 | Hook catalog for changed files is `.pre-commit-config.yaml`; campaign runner not invoked | `quality_gate` | named catalog; no `run_campaign.py` in the Build shell history for this plan | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `preflight.plan.pec.repair-pipeline.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.pec.repair-pipeline.v1` |
| source_ref | `plan.pec.repair-pipeline.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline section |
| baseline_verified | pending at Build start |
| drift_detected | pending |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD && git branch --show-current` | SHA recorded; current checkout; no origin/main lock line written | true |
| CP-02 | `pipeline_ssot` | `test -f WIP/8-29-26/PEC/PEC-repair-pipeline.md` | remaining-work markdown present | true |
| CP-03 | `filesystem_write` | write_allow paths exist and are repo-tracked PE trees | `test -d environment/program-execution/compiler` | true |
| CP-04 | `pytest_interpreter` | `.venv/bin/python -m pytest --version` | locked interpreter runs | true |

## Execution envelope

Mutations outside this envelope are forbidden.

### Filesystem

- **write_allow:** `environment/program-execution/adapters/claude-code/**`, `environment/program-execution/compiler/**`, `environment/program-execution/scripts/campaign_input.py`, `environment/program-execution/peer_execution/**`, `environment/program-execution/core/program-execution-controller-template/scripts/pec/**`, `environment/program-execution/conformance/**`, `WIP/8-29-26/PEC/PEC-repair-pipeline.md`, `WIP/8-29-26/PEC/PEC-repair-pipeline.json`, `ARCHITECTURE.md`
- **write_deny:** `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile`, `ops/autonomy/surface_profile.yaml`, `environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml`, `environment/program-execution/core/shared/EVIDENCE_MODEL.yaml`, `environment/program-execution/campaigns/pe-v3-hardening/CAMPAIGN_SOURCE.yaml`, `WIP/8-29-26/PEC/_archive/**`, secrets, unrelated trees
- **delete_allow:** untracked conformance scratch files created by this Build only

### Commands

- **allow:** `git status`, `git diff`, `git log`, scoped `git add`/`git commit` on write_allow, `.venv/bin/python -m pytest` on named PE test paths, `Read`/`Edit`/`Write` inside write_allow
- **deny:** campaign runner (`run_campaign.py`, `make campaign`), `pec.py` bootstrap/claim/render, force-push, hard-reset, admin-merge, secret exfil, `pre-commit install`

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | |

W0 probe is adapter tests and local CLI, not a live hosted worker unless already on this machine. Do not open GitHub PRs.

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`

This plan does not merge. Publish is out of envelope.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T-W0-stderr | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore provider.py | false |
| T-W0-sha | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | restore permission_renderer and controller | false |
| T-W0-probe | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | restore tests | false |
| T-W1-characterize | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | delete new test file | false |
| T-W1-fixtures | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | delete conformance fixtures | false |
| T-W1-shadow | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | restore cli.py; delete shadow_runner | false |
| T-W2-counterexamples | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | delete counterexamples.yaml | false |
| T-W3-ingress | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | restore campaign_input.py | false |
| T-W4-fidelity | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | restore architecture_* and tests | false |
| T-W5-microscope | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | restore repo_truth.py | false |
| T-W6-lowering | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | restore architecture_to_campaign.py synthesizer.py | false |
| T-W7-graduate | `filesystem_read` | `safe_to_repeat` | `retry_once` | none | false |
| T-W8-v3 | `filesystem_mutation` | `non_idempotent` | `manual_only` | restore pec package; do not start this todo until CP-W7 | true |
| T-W9-risk | `filesystem_mutation` | `non_idempotent` | `manual_only` | restore contracts.py; blocked on U4 | true |
| T-W10-dogfood | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | delete dogfood fixture | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T-W0-stderr | peer execution adapter | `runtime` | Claude adapter receipts | second log SSOT; dropping digest |
| T-W0-sha | peer execution adapter | `control_plane` | permission_renderer + pec candidate identity | granting git push; granting gh |
| T-W1-shadow | PE compiler | `control_plane` | compiler CLI | executing a campaign; writing ~/.l9/programs |
| T-W3-ingress | campaign front door | `control_plane` | campaign_input.py | loosening intent.py; second router |
| T-W4-fidelity | PE compiler | `policy` | architecture_intent materiality | deleting case tests to hide loss |
| T-W5-microscope | PE compiler | `control_plane` | repo_truth.py | replacing repo_truth; fake CREATE |
| T-W6-lowering | PE compiler | `control_plane` | architecture_to_campaign.py | docs-path write fallback |
| T-W8-v3 | PEC controller | `control_plane` | REPLAN_CONTRACT | starting before CP-W7; rewriting pe-v3-hardening source |
| T-W9-risk | assurance + PEC | `assurance` | l9-assurance + contracts.py | RiskPacket router; second auth/evidence |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback.plan.pec.repair-pipeline.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.pec.repair-pipeline.v1` |
| source_execution_ref | `plan.pec.repair-pipeline.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking SP fail; envelope breach; campaign runner invoked |

### Strategies

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | restore write_allow; revert local commits on this checkout |
| data | `none` | no databases |
| external_state | `none` | this plan must not create campaign runtimes |
| local_state | `git_restore_scoped_paths` | delete untracked conformance files if wrong |

### Irreversible operations

- T-W8-v3 and T-W9-risk if started: control-plane semantics can poison later receipts. Do not start them from this Build until CP-W7.

### Rollback verification

- `git diff -- environment/program-execution` empty of unintended paths
- `python3 -m pytest environment/program-execution/compiler/tests -q` on restored tree

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `critical` |
| uncertainty | `high` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `2` |
| external_systems_touched | `0` |
| migration_required | `false` |
| unknown_dependency_count | `4` |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dag.plan.pec.repair-pipeline.v1`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.pec.repair-pipeline.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges (Build todos, not Controller Task Cards)

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T-W0-stderr | agent | runtime | [] | FAIL text receipts |
| T-W0-sha | agent | control_plane | [T-W0-stderr] | aligned candidate identity |
| T-W0-probe | agent | assurance | [T-W0-sha] | probe log |
| T-W1-characterize | agent | assurance | [T-W0-stderr] | journeys A-J tests |
| T-W1-fixtures | agent | assurance | [T-W1-characterize] | fixtures 01-14 |
| T-W1-shadow | agent | control_plane | [T-W1-fixtures] | shadow_runner + metrics |
| T-W2-counterexamples | agent | assurance | [T-W1-shadow] | counterexamples.yaml |
| T-W3-ingress | agent | control_plane | [T-W2-counterexamples] | unified ingress |
| T-W4-fidelity | agent | policy | [T-W3-ingress] | lowercase retention |
| T-W5-microscope | agent | control_plane | [T-W4-fidelity] | disposition IR |
| T-W6-lowering | agent | control_plane | [T-W5-microscope] | seam-based tasks |
| T-W7-graduate | agent | assurance | [T-W0-probe, T-W6-lowering] | W7 metric receipt |
| T-W8-v3 | agent | control_plane | [T-W7-graduate] | blocked until CP-W7 |
| T-W9-risk | agent | assurance | [T-W8-v3] | blocked until U4 |
| T-W10-dogfood | agent | control_plane | [T-W9-risk] | blocked until T-W9-risk |

**Critical path:** T-W0-stderr → T-W1-characterize → T-W1-fixtures → T-W1-shadow → T-W2-counterexamples → T-W3-ingress → T-W4-fidelity → T-W5-microscope → T-W6-lowering → T-W0-sha → T-W0-probe → T-W7-graduate

**Forbidden edges:** T-W8-v3 before T-W7-graduate; T-W9-risk before T-W8-v3; campaign runner from any node; T-W3-ingress loosening intent.py

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse | `git rev-parse HEAD` | Build SHA was `74f86226`; `/ff` parked `c794ac30` | `passed_then_parked` |
| EV-SP-02 | SP-02 | `structural_evidence` | inspect + pytest | adapter `test_driver.py` | FAIL path includes stderr text | `passed` |
| EV-SP-03 | SP-03 | `structural_evidence` | inspect | permission_renderer + controller + worker instruction | denials and null SHA agree | `passed` |
| EV-SP-04 | SP-04 | `filesystem_evidence` | pytest | `compiler/tests/conformance` | fixtures 01-14; shadow no side effect | `passed` |
| EV-SP-05 | SP-05 | `structural_evidence` | inspect | `compile_intent_ingress` / `--check-input` | compile path live; `SUPPORTED_KINDS` still omits execute | `partial` |
| EV-SP-06 | SP-06 | `runtime_behavior_evidence` | pytest | `test_architecture_intent.py` + fixture 04 | lowercase prohibition retained | `passed` |
| EV-SP-07 | SP-07 | `structural_evidence` | inspect | no docs/program-execution fallback | absent | `passed` |
| EV-SP-08 | SP-08 | `proof_receipt` | shadow report | golden journeys | four counts 0; execute spine not run | `partial` |
| EV-SP-09 | SP-09 | `quality_gate_evidence` | catalog | `.pre-commit-config.yaml` | no campaign runner in this Build | `passed` |

## Stress and disconfirm

### Disconfirming cases

- T-W0-probe at current HEAD already PASSes with edits and stderr → T-W0-stderr shrinks to tests-only; do not rebuild the adapter.
- Adding PROGRAM_INTENT_V1 to SUPPORTED_KINDS without a compile adapter recreates the dead-end as a later crash → W3 has not unified ingress.
- Lowercase retention treats every sentence as normative → coverage drowns; stop and add a materiality threshold.
- W7 declared done while the Build agent invoked the campaign runner → plan violated; stop.
- repo_truth cannot name a canonical owner and lowering still emits CREATE write paths → stop; disposition must be UNKNOWN.

### Assumption failure conditions

- Dirty tree overlaps write_allow under `stop_if_dirty_overlaps_may_modify`
- Blocking success property fails after mutation
- Unknown dependency discovered mid-flight (U4 for W9)
- Worker 13-turn FAIL no longer reproduces (U1) — retarget W0, do not invent a new defect

### Blast radius notes

Wrong ingress or lowering can fabricate tasks that overwrite live PE control-plane files. Wrong permission change can let workers git commit. Starting W8/W9 early can duplicate Controller/replan/auth. Weakening architecture_intent tests hides semantic loss.

### Rollback constraints

- No force-push / history rewrite
- No campaign runtime to compensate; do not create one

## Out of scope

- Adjacent features / refactors not listed in envelope
- Architecture redesign
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Environment-experience pack, Perplexity host overlay, PE memory cutover, draft execution schema family
- Rewriting pe-v3-hardening CAMPAIGN_SOURCE.yaml
- Follow-on schema/platform evolution except as listed under Follow-on

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | W8 v3 two-plane reconstruction | **Later plan.** Bind to `origin/main` SHA after this W0–W7 PR merges. Two planes. Do not rewrite `pe-v3-hardening` source. |
| P1 | W9 RiskPacket in l9-assurance then PEC | **Later plan.** Also U4: `l9-assurance` is not attached. |
| P2 | W10 PEC dogfood of messy Risk objective | **Later plan.** Needs W9. |
| P2 | Host overlays (merge queue, preview leases) | parked in pipeline |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `conv.plan.pec.repair-pipeline.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.pec.repair-pipeline.v1` |
| source_ref | `plan.pec.repair-pipeline.v1` |
| current_state | `partial` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline recorded (current checkout SHA, not an origin/main lock)
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - W8-W10 blockers explicit
- **complete_when:**
  - SP-01 through SP-09 evidence `passed` for W0-W7
  - T-W8 T-W9 T-W10 still unstarted or a later plan owns them
  - rollback contract still valid
  - out_of_scope respected
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property
  - campaign runner invoked

### Evidence

- **required_evidence_refs:** `EV-SP-01 through EV-SP-09`
- **observed_evidence_refs:** `EV-SP-02 EV-SP-03 EV-SP-04 EV-SP-06 EV-SP-07 EV-SP-09` passed; `EV-SP-05 EV-SP-08` partial
- **missing_evidence:** W7 execute spine (`make campaign`); W8–W10 entirely; U4 for W9

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | 13-turn empty-edit FAIL measured at c3081ee | probe at current HEAD |
| unknown | U2 | worker-commit grant vs controller-owned candidate identity | probe after T-W0-stderr |
| unknown | U3 | conformance directory home | accept_bounded `compiler/tests/conformance/` |
| unknown | U4 | l9-assurance not attached | block T-W9-risk |
| open_blocker | T-W8-v3 | Do not start until T-W7-graduate blocking properties pass | CP-W7 |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `partial` — do not start W8 from this plan |
| minimum_safe_next_action | Publish this W0–W7 PR. Open a **new** plan for W8–W10 only after it lands; bind that plan to the new `origin/main` SHA |
| execute_via | later plan — not this Cursor Build |
| broader_work_requires_separate_contract | `true` |

## Checkpoints (Build must stop)

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| CP-W0 | T-W0-probe | FAIL receipt text; identity agrees; probe log | Do not start W7 worker-dependent claims |
| CP-W1 | T-W1-shadow | shadow compiles a fixture with no worktree mutation | Do not start T-W3-ingress |
| CP-W4 | T-W4-fidelity | lowercase fixture retained; tests retargeted | Restore tests; do not hide loss |
| CP-W7 | T-W7-graduate | SP-08 zeros; campaign runner not invoked | Do not start T-W8-v3 |

## Machine stub

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.pec.repair-pipeline.v1
  name: PEC repair pipeline W0-W10
  status: partial
  is_project: false
  created_at: 2026-08-29
immutable_baseline:
  repository: Quantum-L9/Cursor-Governance
  commit_sha: 74f8622617db907941587679a18b93cf3e5d7b50
  dirty: true
  overlap_policy: stop_if_dirty_overlaps_may_modify
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: current checkout
  authority_order:
    - plan_document
    - cursor_build
```
