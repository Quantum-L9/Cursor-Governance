---
name: SEO-Bot T7-T12 assurance follow-on
overview: "Land Campaign 7-SEO T7–T12 in Quantum-L9/SEO-Bot on a new branch from origin/main. One SEO-Bot PR. Do not mix into Cursor-Governance PR 201. Do not weaken gates."
todos:
  - id: W0
    content: "Create a new SEO-Bot branch from origin/main (ff-only tip). Re-verify P0-P6 on that SHA. Do not use the producer branch. Do not mix Cursor-Governance WIP."
    status: pending
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: T7
    content: "Insert one ownership rule pattern .vscode/** owner agent-operations classification configuration beside the existing .claude/** rule. Do not untrack .vscode."
    status: pending
    phase: execute
    depends_on: [W0]
    side_effect_ref: SE-T7
    evidence_property_refs: [SP-02]
  - id: T8
    content: "Run npm run manifest:generate and commit both MANIFEST.json and the regenerated MANIFEST.md."
    status: pending
    phase: execute
    depends_on: [T7]
    side_effect_ref: SE-T8
    evidence_property_refs: [SP-03]
  - id: T9
    content: "Add packageManager npm@10.9.7 to package.json. Prove Corepack with npm ci. Do not switch the repo to pnpm or yarn."
    status: pending
    phase: execute
    depends_on: [W0]
    side_effect_ref: SE-T9
    evidence_property_refs: [SP-04]
  - id: T10
    content: "Change the env-contract schemaKeys regex in gate-registry.ts from z\\. to z\\s*\\. so multiline TRUST_PROXY is counted."
    status: pending
    phase: execute
    depends_on: [W0]
    side_effect_ref: SE-T10
    evidence_property_refs: [SP-05]
  - id: T11
    content: "Add CLIENT_SITE_GITHUB_TOKEN and CLIENT_SITE_VERCEL_DEPLOY_HOOK to infrastructureOnly. Keep those names in .env.example. Do not rename them to GITHUB_TOKEN."
    status: pending
    phase: execute
    depends_on: [W0]
    side_effect_ref: SE-T11
    evidence_property_refs: [SP-06]
  - id: T12
    content: "Run npm run manifest:check && npm run verify:assurance. Require preflight PASS, zero BLOCKED, Overall PASS. Never loosen assertions."
    status: pending
    phase: validate
    depends_on: [T8, T9, T10, T11]
    evidence_property_refs: [SP-07]
  - id: W-prove
    content: "Run make pr-check in SEO-Bot (tsc, vitest, biome). Fix only in-scope regressions. Do not weaken scanners."
    status: pending
    phase: validate
    depends_on: [T12]
    evidence_property_refs: [SP-08]
  - id: W-publish
    content: "After L4 kernels and authorize-release, publish with PR_REMEDIATE=0 make pr from the SEO-Bot feature branch against origin/main. Do not merge."
    status: pending
    phase: converge
    depends_on: [W-prove]
    side_effect_ref: SE-W-publish
    evidence_property_refs: [SP-09]
isProject: false
---

# PLAN: SEO-Bot T7-T12 assurance follow-on

> **PLAN_DOCUMENT:** `~/.cursor/plans/seo_bot_assurance_t7_t12.plan.json` — `validate_plan_document.py` **PASS** (2026-08-17)
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate). Do **not** free-form mutate from this markdown alone.
> **This is a follow-on Build**, not Cursor-Governance PR 201.

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

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease. Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile scripts from this template as a second scheduler.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT="$HOME/.cursor/plans/seo-bot-t7-t12-assurance-follow-on_31ca5f92.plan.md"
```

Target workspace at execute: `/Users/macm2/SEO-Bot` (or a wired worktree of `Quantum-L9/SEO-Bot`). Create the feature branch from **SEO-Bot `origin/main`**, not from Cursor-Governance.

If the runner is not used, the same envelope still binds: W0 → T7–T11 → T12 → `make pr-check` → L4 kernels → `PR_REMEDIATE=0 make pr`.

| Plan section | Runner-owned Blueprint / Controller artifact |
|--------------|-------------------------------------|
| metadata / objective | `PROGRAM.yaml` / program identity |
| immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA |
| execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
| execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
| capability_preflight | Controller reconcile + gate probes before claim |
| property_evidence_matrix | Task Card `validation` / evidence catalog refs |
| rollback | Task Card `rollback` + recovery receipts |
| convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

If the runner exits nonzero, stop and report. Do not continue with a second scheduler.

### Adapter routing

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-github-actions` / `ci-generic-shell` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-2026-08-17-seo-t7-t12
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: /Users/macm2/.cursor/plans/seo-bot-t7-t12-assurance-follow-on_31ca5f92.plan.md
plan_id: plan.seo-bot.t7-t12-assurance.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-seo-bot-t7-t12-assurance
  provider_ref: cursor-foreground
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [feat/seo-bot-t7-t12-assurance]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch   # only after L4 release_authorized
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
  - touch_cursor_governance_pr_201
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| W0 | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.baseline` | `work` | `cursor-foreground` |
| T7 | TASK-002 | W1 | [W0] | true | `path:manifest/ownership.yaml` | `mutate` | `pes.w1.t7` | `work` | routed |
| T9 | TASK-003 | W1 | [W0] | true | `path:package.json` | `mutate` | `pes.w1.t9` | `work` | routed |
| T10 | TASK-004 | W1 | [W0] | true | `path:scripts/validation/gate-registry.ts` | `mutate` | `pes.w1.t10` | `work` | routed |
| T11 | TASK-005 | W1 | [W0] | true | `path:scripts/validation/gate-registry.ts` | `mutate` | `pes.w1.t11` | `work` | routed |
| T8 | TASK-006 | W1 | [T7] | true | `path:MANIFEST.json` | `mutate` | `pes.w1.t8` | `work` | routed |
| T12 | TASK-007 | W2 | [T8, T9, T10, T11] | false | `evidence:assurance` | `validate` | `pes.w2.t12` | `work` | `ci-*` / foreground |
| W-prove | TASK-008 | W2 | [T12] | false | `evidence:pr-check` | `validate` | `pes.w2.prove` | `work` | foreground |
| W-publish | TASK-009 | W3 | [W-prove] | true | `pr:seo-bot` / `branch:feat/seo-bot-t7-t12-assurance` | `converge` | `pes.w3.publish` | `work` | `github-*` |

**Stop / do not execute when:** Program Lock drift; capability preflight blocked; DAG cyclic; envelope breach; verify:assurance BLOCKED only on T13–T15 (open a separate plan).

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.seo-bot.t7-t12-assurance.v1` |
| name | SEO-Bot T7-T12 assurance follow-on |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | `2026-08-17` |
| updated_at | `2026-08-17` |
| depth | `standard` (`route_plan.py --risk medium --evidence partial`) |
| json_ssot | `~/.cursor/plans/seo_bot_assurance_t7_t12.plan.json` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | Campaign 7-SEO brief T7–T12 + live `origin/main` inspection (this plan wins where they diverge) |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Fix SEO-Bot assurance blockers in place. Do not invent a parallel pipeline. Do not copy Claude Code as gold-standard. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-17T17:12:00-04:00` |
| repository | `Quantum-L9/SEO-Bot` |
| workspace | `/Users/macm2/SEO-Bot` |
| ssot_clone | n/a (consumer repo) |
| branch_at_capture | `claude/campaign-7-seo-build-intelligence-producer` (dirty; **not** the landing branch) |
| commit_sha | `cfb3d3691b270f726ab8d6b75dafdcf9fae1682b` (`origin/main` at plan time) |
| dirty | `true` on the producer checkout; landing tree must be clean at `origin/main` |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

**Landing rule:** new branch `feat/seo-bot-t7-t12-assurance` from `origin/main` (ff-only). Do not patch the producer branch. Do not land in Cursor-Governance.

### Live ground truth vs Campaign 7-SEO brief

| ID | Brief said | Live `origin/main` (`cfb3d369…`) | Plan action |
|----|------------|----------------------------------|-------------|
| T7 | `.vscode/**` unowned because `*` is `[^/]*` | Confirmed. `globToRegExp` `*` → `[^/]*`. No `.vscode/**` rule. `.vscode/extensions.json` and `settings.json` **are tracked**. Hash stamps gitignored. | Add one `.vscode/**` rule. Keep tracked (U3 `accept_bounded`). |
| T8 | `MANIFEST.json` missing; generate throws until T7 | `MANIFEST.md` present; `MANIFEST.json` **absent**. `generate.ts` writes both. | Generate after T7; commit both. |
| T9 | `"packageManager": "npm@10.9.7"` | Key **absent**. Gate: `startsWith("npm@10.")`. | Add pin; prove with `npm ci`. |
| T10 | `z\.` → `z\s*\.` | Confirmed. `TRUST_PROXY: z\n  .string()`. Old regex **47** keys, misses `TRUST_PROXY`. New regex **48**. | One-line regex replace. |
| T11 | Rename `CLIENT_SITE_*` to what code reads | **Brief is stale.** `.env.example` already has `GITHUB_TOKEN=` and `VERCEL_DEPLOY_HOOK=` matching `config.ts` and `site-deployment.ts`. `CLIENT_SITE_*` are extra per-client `env://` placeholders, only in `.env.example`, not in `src/` or `.github/`, not in `infrastructureOnly`. | Add both `CLIENT_SITE_*` names to `infrastructureOnly`. **Do not rename.** |
| T12 | `manifest:check` + `verify:assurance` Overall PASS | Not run this session (U-T12-RESIDUAL = probe at execute). | Fail-closed; never loosen. |

## Objective

### Mission

Close the SEO-Bot-side Campaign 7-SEO assurance gaps (T7–T12) so `manifest:generate` / `manifest:check` and `verify:assurance` can PASS on a clean `origin/main` descendant. Cursor-Governance Waves 0–2 (shared Infisical plane, PR 201) stay out of this tree. Product hydrate remains `@quantum-l9/infisical-config`.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Execute starts at locked `origin/main` SHA (or stop_and_replan) | `repository_state` | `git rev-parse origin/main` then `HEAD` on the new branch | true |
| SP-02 | `.vscode/extensions.json` has exactly one ownership match | `structural` | `npm run manifest:generate` exits 0; no `Unowned` / multi-match | true |
| SP-03 | `MANIFEST.json` committed and matches generate | `filesystem` | file exists; `npm run manifest:check` exit 0 | true |
| SP-04 | Corepack npm 10.x pin works | `runtime_behavior` | `package.json` has `packageManager` starting `npm@10.`; `npm ci` exit 0 | true |
| SP-05 | `TRUST_PROXY` is a schema key | `structural` | regex `z\s*\.`; 48 keys including `TRUST_PROXY` | true |
| SP-06 | `CLIENT_SITE_*` explained; Zod names unchanged | `structural` | both in `infrastructureOnly`; `GITHUB_TOKEN` / `VERCEL_DEPLOY_HOOK` still in example and Zod | true |
| SP-07 | Assurance green without loosened assertions | `quality_gate` | `npm run verify:assurance` → preflight PASS, 0 BLOCKED, Overall PASS | true |
| SP-08 | SEO-Bot publish gate green | `quality_gate` | `make pr-check` PASS | true |
| SP-09 | One unmerged SEO-Bot PR | `proof_receipt` | `PR_REMEDIATE=0 make pr` URL; merge not performed | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.seo-bot.t7-t12-assurance.v1` |
| blocking | `true` |
| immutable_baseline_ref | `cfb3d3691b270f726ab8d6b75dafdcf9fae1682b` |
| baseline_verified | re-check at W0 |
| drift_detected | unknown until W0 |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git fetch origin main && git rev-parse origin/main` | equals locked SHA or stop_and_replan | true |
| CP-02 | `command_available` | `node -v` and `npm -v` | Node 22.x; npm 10.x or Corepack can activate 10.9.7 | true |
| CP-03 | `filesystem_write` | SEO-Bot worktree writable | `may_modify` paths writable; CG tree not the write root | true |
| CP-04 | `ownership_gap` | read `manifest/ownership.yaml` | still no `.vscode/**` (else T7 becomes verify-only) | true |

## Execution envelope

### Filesystem

- **write_allow:** `manifest/ownership.yaml`, `MANIFEST.json`, `MANIFEST.md`, `package.json`, `package-lock.json`, `scripts/validation/gate-registry.ts`, `.env.example`
- **write_deny:** Cursor-Governance (including PR 201), Website-Bot, llm-router source, Infisical/AWS registries, `scripts/validation` assertion expected-value tables used to fake PASS, producer branch files, secrets, `validation/runs/` (gitignored evidence only)

### Commands

- **allow:** `git` (non-destructive + scoped commit), `npm run manifest:generate`, `npm run manifest:check`, `npm run verify:assurance`, `npm ci`, `make pr-check`, `PR_REMEDIATE=0 make pr`, L4 `l4_local.py` in the SEO-Bot worktree via governance clone
- **deny:** force-push, hard-reset, `gh pr merge`, vault writes, raw `git push` / `gh pr create` (path rule: `make pr` only), scanner weakening

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `github.com` / `api.github.com` after L4 release (publish only); npm registry for `npm ci` |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only` |
| redaction_required | `true` |
| notes | Do not paste Infisical UA or PAT. SEO-Bot product hydrate stays `@quantum-l9/infisical-config`. |

### Autonomous merge

`autonomous_merge:` `false`

This plan ends **green + merge-ready**. Merge only if the user later invokes `/l9-pr-remediation` or sets `L9_MERGE_AUTHORIZED`. An L4 release receipt does not authorize merge.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| W0 | `repository_state` | `safe_to_repeat` | `none` | abandon unused branch | false |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore `manifest/ownership.yaml` | false |
| T8 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | delete uncommitted MANIFEST pair / restore | false |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert `package.json` / lockfile | false |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore regex line | false |
| T11 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | restore `infrastructureOnly` set | false |
| T12 | `filesystem_read` | `safe_to_repeat` | `retry_once` | none (runs gitignored) | false |
| W-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | none | false |
| W-publish | `network_write` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T7 | SEO-Bot manifest ownership | `assurance` | `scripts/manifest/inventory.ts` `resolveOwnership` | catch-all `**` that double-matches; untracking `.vscode` |
| T8 | generated inventory | `assurance` | `scripts/manifest/generate.ts` | hand-written JSON that `check` cannot reproduce |
| T9 | toolchain pin | `ops` | `preflight.package-manager` | pnpm/yarn; npm 11 pin |
| T10 / T11 | env-contract | `assurance` | `gate-registry.ts` preflight.env-contract | renaming `CLIENT_SITE_*` onto `GITHUB_TOKEN`; loosening key counts |
| T12 | assurance profile | `assurance` | `verify:assurance` ci profile | weakening BLOCKED/Overall |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.seo-bot.t7-t12-assurance.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking SP fail; envelope breach; T12 BLOCKED only on T13–T15 |

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` / `revert_commit` | scoped to write_allow; close unmerged PR |
| data | `none` | no DB migration |
| external_state | `manual_recovery` | close GitHub PR if opened; no vault writes |
| local_state | `git_restore_scoped_paths` | MANIFEST pair is regenerable |

**Irreversible operations:** none.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` |
| uncertainty | `medium` (U-T12-RESIDUAL) |
| blast_radius | `low` (SEO-Bot assurance + Corepack pin) |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `1` (GitHub PR open only) |
| migration_required | `false` |
| unknown_dependency_count | `1` (`U-T12-RESIDUAL`) |

## Execution DAG

`graph_type:` directed_acyclic_graph

```text
W0
 ├─ T7 → T8 ─┐
 ├─ T9 ──────┤
 ├─ T10 ─────┼─→ T12 → W-prove → W-publish
 └─ T11 ─────┘
```

**Critical path:** `W0 → T7 → T8 → T12 → W-prove → W-publish`

**Forbidden edges:** T8 before T7; publish before T12/W-prove; any edge into Cursor-Governance PR 201.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | command | expected_positive | status |
|-------------|---------------|---------------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | `git rev-parse HEAD` | locked or re-planned SHA | `not_run` |
| EV-SP-02 | SP-02 | `runtime_behavior_evidence` | `npm run manifest:generate` | exit 0 | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | `npm run manifest:check` | exit 0 | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | `npm ci` | exit 0; `packageManager` `npm@10.` | `not_run` |
| EV-SP-05 | SP-05 | `structural_evidence` | inspect `gate-registry.ts` + config | `TRUST_PROXY` in schemaKeys | `not_run` |
| EV-SP-06 | SP-06 | `structural_evidence` | inspect `infrastructureOnly` + `.env.example` | `CLIENT_SITE_*` explained; Zod names intact | `not_run` |
| EV-SP-07 | SP-07 | `quality_gate_evidence` | `npm run verify:assurance` | Overall PASS, 0 BLOCKED | `not_run` |
| EV-SP-08 | SP-08 | `quality_gate_evidence` | `make pr-check` | PASS | `not_run` |
| EV-SP-09 | SP-09 | `proof_receipt` | `PR_REMEDIATE=0 make pr` | SEO-Bot PR URL; unmerged | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- `origin/main` already grew `MANIFEST.json` or `packageManager` → T8/T9 become verify-only; do not force a churn commit.
- `.vscode/**` plus another rule double-matches → generate throws on >1 match; keep exactly one matching rule for those paths (`*` cannot match slashes).
- Live Vercel env uses `CLIENT_SITE_*` as the **only** site-deploy names → still add to `infrastructureOnly`; do **not** rename onto `GITHUB_TOKEN` (those keys already exist). Changing code to read `CLIENT_SITE_*` is out of scope.
- CI image cannot activate `npm@10.9.7` → pin the `npm@10.x` the image already ships; stay on `npm@10.`.
- `verify:assurance` BLOCKED only on T13–T15 → stop; separate plan. Do not loosen T12.

### Assumption failure conditions

- Dirty producer tree used as the write root
- Envelope breach into Cursor-Governance
- Blocking success property fails after mutation

### Blast radius notes

SEO-Bot only. Wrong T11 rename collides with existing `GITHUB_TOKEN` example keys. Wrong Corepack pin fails `npm ci`. Double-match ownership bricks generate.

### Rollback constraints

No force-push / history rewrite. Close the unmerged PR if needed.

## Out of scope

- Cursor-Governance PR 201 / Waves 0–2
- Campaign 7-SEO T1–T6 (Claude-cloud / CG credential path)
- T13 llm-router pin, T14 seam proof, T15 Website-Bot PCC
- Website-Bot, LLM-Router source, PE-PE 1, producer PR 56
- Infisical or AWS vault writes; second GitHub PAT; pasting secrets into Claude cloud
- Weakening assurance / biome / vitest / tsc
- Untracking `.vscode`
- Merging from this plan

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | T13 llm-router pin | Campaign 7-SEO leftover; not required to start T7–T12 |
| P2 | T14 seam proof / T15 Website-Bot PCC | Cross-repo; own plan |
| P3 | Vercel project-env name audit | Only if U-VERCEL-ENV later shows a real name split |

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.seo-bot.t7-t12-assurance.v1` |
| current_state | `execution_ready` |
| implementation_ready | `true` for user Build (planning PASS; code not started) |

### Gates

- **executable_when:** baseline locked; envelope complete; T11 live correction recorded; U3 / U-VERCEL-ENV `accept_bounded`; U-T12-RESIDUAL deferred to T12 probe
- **complete_when:** SP-01…SP-09 evidence `passed`; PR open; merge not performed
- **blocking_conditions:** preflight_blocked; envelope breach; baseline drift; T12 BLOCKED on in-scope items

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U3 | Keep `.vscode` tracked | `accept_bounded` — ownership only |
| unknown | U-VERCEL-ENV | Vercel project env not probed | `accept_bounded` — infrastructureOnly add, no rename |
| unknown | U-T12-RESIDUAL | Overall PASS after T7–T11 unknown | `probe` at T12; do not expand to T13–T15 |

### Next

| Field | Value |
|-------|-------|
| next_skill | `l9-ynp` (after planning); execute via `@environment/program-execution` + `/autonomy` on Build |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease |
| broader_work_requires_separate_contract | `true` |

---

## Preconditions (already shipped; do not redo)

Cursor-Governance PR 201 landed the shared Infisical / Packages / in-place memory work (Waves 0–2). SEO-Bot still hydrates product secrets via `@quantum-l9/infisical-config`. That path is not rewritten here.

Local SEO-Bot checkout is on `claude/campaign-7-seo-build-intelligence-producer` and is dirty. **W0 ignores that checkout state** and starts from `origin/main`.
