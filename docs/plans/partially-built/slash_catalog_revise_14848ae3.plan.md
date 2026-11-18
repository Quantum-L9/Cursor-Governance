---
name: Slash catalog revise
overview: Retire, rename, absorb, and slim the annotated slash rows into skill-backed triggers; fold the verify ladder into analyze/evaluate; publish one PR via PR_REMEDIATE=0 make pr. No merge.
todos:
  - id: wt-branch
    content: "PE W0: fetch origin/main; create wired worktree+branch; lock that SHA; copy this plan onto the branch; stop_and_replan on drift"
    status: completed
  - id: retire-archive
    content: Archive RETIRE+FOLD+ABSORB plus retired readme-dag.md into commands/_archived/ (git mv, original basenames)
    status: in_progress
  - id: rename-docs-lint
    content: Add commands/docs.md (l9-update-agent-docs) and git mv lint-fix.md → lint.md; drop COMMIT from lint
    status: pending
  - id: slim-triggers
    content: Rewrite annotated SLIM set + /governance + analyze family to gold-standard skill triggers; add verify-ladder modes
    status: pending
  - id: registries
    content: Regen manifest; one-time alias inject; update index + 02-slash + ynp + AUTONOMY_MANIFEST + commands/README.md + update-command example; project llm-rules
    status: pending
  - id: prove-pr
    content: make pr-check; kernels Recursive Alignment + Validate & Repair; L4 begin/record-kernels/authorize-release; PR_REMEDIATE=0 make pr
    status: pending
isProject: false
---

# PLAN: Slash catalog revision (annotated index)

> **First-class SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Schema:** `canonical.schema.plan_document.v1`
> **plan_id:** `plan.governance.slash-catalog-revise.v1`
> **schema_version:** `1.0.0`
> **status:** `executable`
> **Improve.md:** applied in place 2026-08-22 (pass log at end). Catalog decisions unchanged; contracts hardened.

## Execute via @environment/program-execution + autonomy (required)

```text
this .plan.md
        │
        ▼
@environment/program-execution   Blueprint → Program Lock → Controller
        │ lease (narrow-never-widen)
        ▼
@autonomy (/autonomy → l9-bounded-autonomy)   subordinate
        │
        ▼
cursor-foreground
        │
        ▼
kernels/Recursive Alignment.md → kernels/Validate & Repair.md
        │
        ▼
python3 ops/autonomy/l4_local.py begin → record-kernels → authorize-release
        │
        ▼
PR_REMEDIATE=0 make pr          # auto_pr=true; path rule, not raw git/gh
```

`autonomous_merge: false`. Do not raw `git push` / `gh pr create` / MCP `create_pull_request`. Do not merge.

### Campaign packet stub (fill at execute)

```yaml
packet_id: autonomy-2026-08-22-slash-catalog
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
autonomous_merge: false
plan_id: plan.governance.slash-catalog-revise.v1
declared_branches: [feat-slash-catalog-revise]
allowed_inside_packet:
  - execute_plan_todos_inside_envelope
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch   # only after L4 release_authorized
forbidden_inside_packet:
  - merge_outside_l4_plan_build_stack
  - force_push
  - widen_blueprint_or_task_card_ceiling
  - commit_secrets
  - weaken_tests_for_green
```

### Phase-0 ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | isolation_key |
|----|------------|------|------------|----------|---------------|
| wt-branch | TASK-001 | W0 | [] | false | preflight |
| retire-archive | TASK-002 | W1 | [wt-branch] | true | mutate |
| rename-docs-lint | TASK-003 | W1 | [retire-archive] | true | mutate |
| slim-triggers | TASK-004 | W1 | [rename-docs-lint] | true | mutate |
| registries | TASK-005 | W1 | [slim-triggers] | true | mutate |
| prove-pr | TASK-006 | W2 | [registries] | true | converge |

**Critical path:** `wt-branch` → `retire-archive` → `rename-docs-lint` → `slim-triggers` → `registries` → `prove-pr`

**Stop when:** worktree HEAD ≠ locked `origin/main` SHA at start; envelope breach; blocking SP fail; `make pr-check` FAIL.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.governance.slash-catalog-revise.v1` |
| owner | igor_beylin |
| created_at | 2026-08-22 |
| updated_at | 2026-08-22 |
| planning_ssot | annotated `commands-index.md` rows 25–64 (user selection) + this plan |
| plan_class | `retirement_plan` (rename/absorb/slim overlay) |
| redesign_allowed | `false` |

## Architect framing

Slash files are thin triggers. Skills own procedures. `COMMANDS_MANIFEST.yaml` is generated from live `commands/*.md`. Human tables in `commands-index.md` and `rules/02-slash-commands.mdc` must match the generator output in the same commit. Generated `environment/generated/llm-rules/02-slash-commands.md` is projected from the `.mdc` — edit the `.mdc`, then regenerate.

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | 2026-08-22T21:19:00-04:00 |
| repository | Quantum-L9/Cursor-Governance |
| workspace_at_plan | `/Users/ib-mac/Cursor-Governance` on dirty `main` |
| plan_workspace_sha | `6440800201ede7991f3e63eeebfd9b4eed085bf7` (local main, **not** the execute lock) |
| execute_base | fetched `origin/main` at worktree create (plan-time tip `fda7f5fe`; re-fetch and lock the full SHA then) |
| dirty | `true` on the plan-time checkout (unrelated local commit + untracked plans) |
| overlap_policy | `require_clean_tree` on the **new worktree** |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |
| allowed_local_dirt | this plan file copied onto the feature branch |

Do **not** mutate the dirty `main` checkout. Do **not** mix into `feat-ff-slash-dirt-park`.

## Objective

### Mission

Apply the annotated index rows. After this PR, the **annotated mutate set** is skill-backed and registry-aligned. The **LEAVE set is unchanged** (those slashes may stay fat). `make pr-check` PASSes. One PR opens. Merge stays denied.

### Locked decisions

- `/plan`, `/plan-simple`, `/pr-remediation` already live as `/l9-plan`, `/l9-plan-simple`, `/l9-pr-remediation`. Sweep leftover old filenames only; do not rename again.
- Verify ladder **folds now**: delete `/probe`, `/audit-component`, `/verify-component`; add modes on `/analyze`, `/evaluate`, `/analyze_evaluate` → skill `l9-component-verification`.
- `/docs` replaces `/readme` and calls `l9-update-agent-docs`. README DAG stays under `workflows/`; it is not a slash.
- Harden/improve = gold-standard trigger (`commands/l9-plan.md`): frontmatter + named skill + short EXECUTION list. No pasted DAG, no auto-commit.

### Taxonomy (do not collapse)

| Class | Slashes | Resolve after PR? |
|-------|---------|-------------------|
| RETIRE (no alias) | `/rules`, `/git-work-preserve`, `/harvest2` | **No** |
| FOLD (no alias) | `/probe`, `/audit-component`, `/verify-component` | **No** — use analyze family |
| RENAME+ALIAS | `/readme`→`/docs`, `/lint-fix`→`/lint` | Old name is alias only |
| ABSORB+ALIAS | `/violation`→`/governance` report-violation mode | `/violation` aliases `/governance` |
| SLIM | `/wire`, `/confirm-wiring`, `/gap-analysis`, `/inspect`, `/consolidate`, `/clean_compress`, `/governance`, `/analyze`, `/evaluate`, `/analyze_evaluate` | Same slash, thinner body |
| LEAVE | `/start-session`, `/autonomy`, `/ynp`, `/harvest`, `/use-harvest`, `/pr`, `/l9-plan`, `/l9-plan-simple`, `/l9-pr-remediation`, `/index`, `/end-session`, `/e2e-blockers`, `/mem`, `/governance-backup`, `/ci`, `/ci-policy`, `/migrate`, `/refactor`, `/refactor-sweep`, `/extract-chat`, `/extract-from-chat`, `/extract_align`, `/spec`, `/dag-authoring`, `/update-command`, `/lcto` | Unchanged bodies |
| ABSENT on origin/main | `/ff` | Do not create |

Skills kept for every RETIRE/FOLD slash (`l9-git-work-preserve`, `l9-governance-wiring` rules-inventory, `l9-harvest-pipeline`, `l9-component-verification`).

## Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Feature worktree HEAD equals fetched `origin/main` SHA locked at wt-branch | `repository_state` | `git rev-parse HEAD` == lock file | true |
| SP-02 | RETIRE+FOLD slashes have no live `commands/*.md` and no `enabled: true` manifest row | `filesystem` | `test ! -f commands/{rules,git-work-preserve,harvest2,probe,audit-component,verify-component,violation,readme-dag}.md` and `rg -n "slash: /(rules\|probe\|…)" commands/COMMANDS_MANIFEST.yaml` empty | true |
| SP-03 | `/docs` and `/lint` exist; `/readme` and `/lint-fix` are aliases on those file keys; `/docs` names `l9-update-agent-docs` | `structural` | `rg -n "l9-update-agent-docs" commands/docs.md`; manifest aliases | true |
| SP-04 | Each SLIM file names its skill in the first 30 lines; `commands/lint.md` has no COMMIT / `git commit` step | `structural` | `rg -n "Delegates to skill\\|COMMIT\\|git commit" commands/{wire,confirm-wiring,gap-analysis,inspect,consolidate,clean_compress,governance,analyze,evaluate,analyze_evaluate,lint}.md` | true |
| SP-05 | `commands-index.md` and `rules/02-slash-commands.mdc` tables list the same enabled slashes as the regenerated manifest | `structural` | three-way set compare | true |
| SP-06 | `make pr-check` PASS on the feature branch | `quality_gate` | `make pr-check` | true |
| SP-07 | `PR_REMEDIATE=0 make pr` prints a GitHub PR URL | `proof_receipt` | PR URL + `.l9/pr` receipt | true |

## Capability preflight

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `origin/main` resolvable | `git fetch origin main && git rev-parse origin/main` | 40-char SHA | true |
| CP-02 | worktree helper | `test -x ops/scripts/worktree_add_wired.sh` | executable | true |
| CP-03 | gov python | `"$HOME/.cursor-governance/.venv/bin/python" -c "import yaml"` | import OK | true |
| CP-04 | generators | `test -f ops/scripts/generate_commands_manifest.py && test -f ops/scripts/project_llm_rules.py` | present | true |

Failed blocking probe → status `preflight_blocked`.

## Execution envelope

### Filesystem

**write_allow:**

- `commands/*.md` (live triggers; not `commands/dora-commands/`, not `commands/emma-repo-commands/`)
- `commands/_archived/*.md` (retired command files only)
- `commands/COMMANDS_MANIFEST.yaml` (via generator, plus one-time alias inject on `/docs`, `/lint`, `/governance`)
- `commands/commands-index.md`
- `rules/02-slash-commands.mdc`
- `environment/generated/llm-rules/02-slash-commands.md` (via `project_llm_rules.py` only)
- `skills/AUTONOMY_MANIFEST.yaml` (path string for archived `violation.md` only)
- `skills/l9-component-verification/SKILL.md` (description / “use for” lines only)
- `ops/feedback_loop_config.yaml` (path string only)
- `docs/plans/slash_catalog_revise_14848ae3.plan.md` (this file, onto the feature branch)

**write_deny:**

- `CANONICAL_LAW.md`
- `AGENTS.md`, `ARCHITECTURE.md`, `INVARIANTS.md`, `CLAUDE.md` (root additive-only / docs skill is invoked later by `/docs`, not this PR)
- `skills/**` except the two skill files above
- `workflows/**` (README DAG stays)
- `ops/autonomy/surface_profile.yaml`
- `environment/program-execution/core/**`
- consumer-repo `.cursor/commands/**`

**delete_allow:** none. Retire via `git mv` into `_archived/`.

### Commands

**allow:** `git mv`, `git add` pathspecs, scoped `git commit` after L4 begin, worktree helpers, `generate_commands_manifest.py`, `project_llm_rules.py`, `sync_generated_artifacts.py` (stage **only** catalog-related generated paths), `make pr-check`, `ops/autonomy/l4_local.py`, `PR_REMEDIATE=0 make pr`.

**deny:** `git push` / `gh pr create` / `make push` / MCP PR tools; `git add -A`; force-push; hard-reset; merge; `pre-commit install`.

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | GitHub via `make pr` after L4 release only |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only` (`openclaw-igorbot/github#token` through existing `gh` / make-pr path) |
| redaction_required | `true` |

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| wt-branch | `filesystem_mutation` | `safe_to_repeat` (new branch name if collide) | `manual_only` | remove unused worktree | false |
| retire-archive | `filesystem_mutation` | `safe_with_dedupe` (`git mv` no-op if already archived) | `manual_only` | `git mv` back to `commands/` | false |
| rename-docs-lint | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | delete new files; restore lint-fix.md | false |
| slim-triggers | `filesystem_mutation` | `unsafe_blind_repeat` (rewrite) | `manual_only` | `git restore -- path` | false |
| registries | `filesystem_mutation` | `safe_with_dedupe` (generators) | `retry_once` | restore + regen | false |
| prove-pr | `network_write` | `safe_with_dedupe` (same HEAD → update PR) | `manual_only` | leave PR open; do not merge | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| retire-archive | slash catalog | `policy` | `commands/COMMANDS_MANIFEST.yaml` generator | delete skills; edit CANONICAL_LAW |
| slim-triggers | slash → skill | `control_plane` | named `l9-*` SKILL.md | rewrite skill procedures / DAGs |
| registries | discovery | `policy` | `rules/02-slash-commands.mdc` + generator | hand-edit generated llm-rules body |
| prove-pr | publish | `ops` | AGENTS.md `make pr` | merge; raw push |

## Inventory (retire / replace / keep)

| path | category |
|------|----------|
| `commands/rules.md` | `migrate_then_delete` → `_archived/rules.md` |
| `commands/git-work-preserve.md` | `migrate_then_delete` → `_archived/git-work-preserve.md` |
| `commands/harvest2.md` | `migrate_then_delete` |
| `commands/violation.md` | `migrate_then_delete` (behavior moves into `/governance`) |
| `commands/probe.md` | `migrate_then_delete` (mode on `/analyze`) |
| `commands/audit-component.md` | `migrate_then_delete` (mode on `/evaluate`) |
| `commands/verify-component.md` | `migrate_then_delete` (mode on `/analyze_evaluate`) |
| `commands/readme-dag.md` | `migrate_then_delete` |
| `commands/lint-fix.md` | `replace` → `commands/lint.md` |
| `commands/docs.md` | new `replace` for `/readme` |
| SLIM set | `keep` (rewrite body) |
| LEAVE set | `keep` (no body rewrite) |
| `commands/README.md` | `replace` — stop being a second `/readme` protocol; become a pointer to `commands-index.md` + note `/docs` |
| `workflows/dags/readme_pipeline_dag.py` | `keep` |

No `_archived/` basename collision exists today (`do-templates/` and `workflow-executors/` only).

## Regeneration extinguishment

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| RG-01 | `ops/scripts/generate_commands_manifest.py` | none — `_archived/` already in `excluded` | after archive, regen must omit retired slashes |
| RG-02 | `ops/scripts/project_llm_rules.py` | none — projects from `rules/02-slash-commands.mdc` | `--check` clean after `.mdc` + project |
| RG-03 | `sync_generated_artifacts.py` | stage only catalog-touched generated paths | `git diff --name-only` has no unrelated generated churn |

## Gold-standard command file

```markdown
---
name: <slash-without-slash>
version: "x.y.z"
description: "<one line>"
auto_chain: ynp
---

# /<name> — <title>

Delegates to skill **`l9-…`** (mode `…` when applicable).

## EXECUTION
1. Read and follow that skill.
2. …
3. Auto-chain `/ynp`.

## FORBIDDEN
- …
```

- `/docs`: skill `l9-update-agent-docs`. One line: this is not the README DAG.
- `/lint`: `l9-code-maintenance --mode lint-fix`. Dry-run first. **No commit step** (current `lint-fix.md` COMMIT block is the defect).
- `/analyze` / `/evaluate` / `/analyze_evaluate`: primary `l9-code-analysis` modes `analyze` / `evaluate` / `analyze+evaluate`. Verification subsection → `l9-component-verification` when the user names a component, import, or wiring check.
- `/governance`: `l9-governance-wiring` mode `governance check` plus absorbed `report-violation` (format from archived `violation.md`, not a second slash).
- `/wire` + `/confirm-wiring`: same skill, modes `wire governance` / `wire component` / `confirm-wiring`.
- Explicit-only skills (`disable-model-invocation: true`) are still valid: the slash **is** the explicit invoke.

## Registry procedure (root-cause, not “edit YAML twice”)

`generate_commands_manifest.py` rebuilds `commands:` from live `commands/*.md` and **preserves `aliases` keyed by file path**. It does not read aliases from frontmatter.

1. Finish all `git mv` / new files / slims.
2. Run `"$HOME/.cursor-governance/.venv/bin/python" ops/scripts/generate_commands_manifest.py`.
3. **One authorized surgical edit** of `COMMANDS_MANIFEST.yaml`: add `aliases` only on `commands/docs.md` (`/readme`), `commands/lint.md` (`/lint-fix`), `commands/governance.md` (`/violation`). Do not edit other rows.
4. Re-run the generator. Confirm those three alias blocks survive (file-key preserve).
5. Rewrite human tables in `commands/commands-index.md` and `rules/02-slash-commands.mdc` to the **same slash set** as the manifest (including `/docs`, `/lint`; excluding RETIRE+FOLD live names; aliases as a footnote, not a second primary row).
6. Point updates: `commands/ynp.md` GOVERNANCE row; `commands/update-command.md` `/update-command readme` example → `/update-command docs`; `commands/README.md` → folder index pointing at `commands-index.md`; `skills/AUTONOMY_MANIFEST.yaml` `do_not_migrate` path; `ops/feedback_loop_config.yaml`; `l9-component-verification` “use for” line → analyze-family slashes.
7. `"$HOME/.cursor-governance/.venv/bin/python" ops/scripts/project_llm_rules.py --root "$(pwd)"`.
8. If `sync_generated_artifacts.py` dirties extra generated files, restore anything outside write_allow.

Do **not** edit `CANONICAL_LAW.md`. Skill `l9-git-work-preserve` remains the law binding; the retired slash is accepted staleness. Do **not** overwrite `AGENTS.md`. Do **not** invent `/ff`.

## Doc / Root Surface Impact

| surface | action | reason |
|---------|--------|--------|
| `commands/commands-index.md` | rewrite table | human SSOT for enabled slashes |
| `rules/02-slash-commands.mdc` | rewrite enabled table | always-apply recognition |
| `environment/generated/llm-rules/02-slash-commands.md` | regenerate | projection of the `.mdc` |
| `commands/README.md` | replace `/readme` body | excluded from manifest but currently a second protocol |
| `AGENTS.md` / other roots | N/A | no live slash table; additive-only |
| `CANONICAL_LAW.md` | N/A | high-risk; skill still named |

## Out of scope

- Creating `/ff` or `l9-repo-sync`
- Deleting `/gap-analysis-new`, `/issues`, `/plan-audit`, `/clean`
- Slimming the LEAVE set
- Rewriting skill procedures, DAGs, or `workflows/dags/readme_pipeline_dag.py`
- Purging consumer-repo `.cursor/commands/{old}.md` overlays (resolution order 1st — index footnote only)
- Merge, force-push, root-file overwrites, changing `tests/ops/scripts/test_sync_generated_artifacts.py` harvest2 **fixture** unless that test’s API actually breaks

## Property evidence matrix

| evidence_id | SP | evidence_kind | command | expected_positive | status |
|-------------|----|---------------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | `git rev-parse HEAD` | locked origin/main SHA | `not_run` |
| EV-SP-02 | SP-02 | `filesystem_evidence` | `test ! -f` + manifest `rg` | retired files absent from live tree + manifest | `not_run` |
| EV-SP-03 | SP-03 | `structural_evidence` | `rg l9-update-agent-docs commands/docs.md` | hit + aliases present | `not_run` |
| EV-SP-04 | SP-04 | `structural_evidence` | skill-name `rg` + no COMMIT in lint.md | all SLIM files hit; lint has no commit | `not_run` |
| EV-SP-05 | SP-05 | `structural_evidence` | three-way slash-set compare | sets equal | `not_run` |
| EV-SP-06 | SP-06 | `quality_gate_evidence` | `make pr-check` | PASS | `not_run` |
| EV-SP-07 | SP-07 | `proof_receipt` | `PR_REMEDIATE=0 make pr` | PR URL | `not_run` |

## Stress and disconfirm

### Disconfirming questions

1. If `generate_commands_manifest.py` drops the surgically added aliases on the second run, the RENAME+ALIAS contract is false — stop and extend the generator to read frontmatter `aliases` rather than re-hand-editing forever.
2. If Cursor still lists `/probe` after the live file is gone, a consumer overlay or plugin cache is winning — do not recreate the slash; document overlay precedence.
3. If `project_llm_rules.py` rewrites more than `02-slash-commands.md`, staging those extras is scope drift — restore and stage only write_allow.

### Assumed false-ifs

- `_archived/` remains excluded (already in generator `DEFAULT_EXCLUDED` / live `excluded:`).
- `l9-update-agent-docs` is the “root docs skill” named by the user.
- LEAVE slashes are intentionally not slimmed this PR.

### Blast radius

Always-apply `02-slash-commands.mdc` plus plugin discovery. A drifted table trains every session on the wrong catalog. Wrong `/docs` body would silently drop the README DAG slash (authorized) and surprise anyone who still wants subsystem README generation (follow-on: invoke the DAG without a slash, or a later `/docs readme` submode — not this PR).

### Rollback

| Field | Value |
|-------|-------|
| supported | `true` |
| automatic_allowed | `false` |
| code | `git_restore_scoped_paths` / abandon branch; `git mv` out of `_archived/` |
| data | `none` |
| external_state | `manual_recovery` (close PR if opened; never merge) |
| irreversible | none locally; GitHub PR creation is append-only |

Rollback proof: worktree gone or `git diff origin/main` empty of write_allow paths; no merged PR.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `low` |
| blast_radius | `medium` (always-apply rule table) |
| architectural_boundaries_crossed | `1` (slash catalog ↔ skill discovery) |
| external_systems_touched | `1` (GitHub PR at prove-pr) |
| migration_required | `false` (aliases cover rename) |

## Convergence

| Field | Value |
|-------|-------|
| current_state | `execution_ready` |
| implementation_ready | `true` |
| execute_via | PE + autonomy + `PR_REMEDIATE=0 make pr` |

**executable_when:** this Improve pass — envelope, DAG, SP matrix, taxonomy, and registry procedure are filled; no blocking unknowns.

**complete_when:** EV-SP-01..07 `passed`; diff ⊆ write_allow; PR URL exists; merge not performed.

**blocking_conditions:** preflight fail; baseline drift; generator resurrects a retired slash; `make pr-check` FAIL.

## Follow-on (separate plan)

| priority | change | why |
|----------|--------|-----|
| P2 | Slim LEAVE set (`/ynp`, `/harvest`, …) | annotated table did not ask |
| P2 | `/docs readme` submode or documented DAG-only path | users who still want subsystem READMEs |
| P3 | Frontmatter `aliases` in the generator | removes the one-time YAML inject |
| P3 | Fold `/gap-analysis-new` | not in the annotated table |

## Known unknowns (non-blocking)

- Whether a consumer overlay `.cursor/commands/probe.md` exists on other machines — cannot purge from this repo.
- Exact `origin/main` SHA at execute time — re-lock at wt-branch (plan-time tip was `fda7f5fe`).

## Improve.md pass log (this artifact)

| pass | name | findings → changes | measurable |
|------|------|--------------------|------------|
| 1 | bind + inventory | Target = this plan (same path via `~/.cursor/plans` → `docs/plans`). Missing PE sections; two plan copies are one file. | inventory complete |
| 2 | issue discovery | Overclaim “every slash thin”; “retired no longer resolve” vs aliases; wrong execute SHA (dirty main vs origin/main); missing envelope/DAG/SP matrix; second `/readme` in `commands/README.md`; alias vs generator contradiction. | 8 verified issues |
| 3 | contract harden | Taxonomy, execute_base lock, write_allow/deny, alias procedure, RG-01..03, evidence matrix, stress. | contradictions removed |
| 4 | entropy | Dropped leftover-name sweep as a floating paragraph; it is SP-02 + retire-archive. Tightened LEAVE vs SLIM. | one taxonomy table |
| 5 | verify (structural) | Required PE sections present; todos have deps/files/SPs; no fabricated `make pr-check` result. | structural only — runtime Unknown |

**Convergence (plan artifact):** Converged for planning. Another Improve pass on this markdown has no high-value objective. Execution validation remains `not_run`.
