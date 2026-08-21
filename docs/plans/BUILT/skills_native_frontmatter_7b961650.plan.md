---
name: Skills native frontmatter
overview: Execute skills-normalization-pack Stages 1–4 on a fresh `chore/skills-normalization` branch from `origin/main`, then close every producer, consumer, test, generated registry, and path alias so the nested-metadata contract has no dangling teachers or readers.
todos:
  - id: todo-01-baseline-preflight
    content: "PE W0: branch chore/skills-normalization from origin/main, lock SHA, re-run nest dry-run + glob census; stop_and_replan on drift"
    status: completed
  - id: todo-02-archive-and-nest
    content: "PE W1: write docs/skills-frontmatter-archive.yaml then nest_skill_metadata.py --apply --include-archived (values unchanged, no paths)"
    status: completed
  - id: todo-03-wiring-closure
    content: "PE W1: retarget every SKILL.md frontmatter producer and consumer to nested metadata; dual-read status; regenerate derived registries; do not leave a teacher or reader on the old shape"
    status: completed
  - id: todo-04-archived-lock
    content: "PE W1: enumerate _archived flags, add disable-model-invocation true only if missing; record flag-all; do not relocate"
    status: completed
  - id: todo-05-checker-inventory
    content: "PE W2: install yaml-safe ops/scripts/check_skills_standard.py + docs/skills-standard.md; append-only make skills-check; write inventory; add checker tests"
    status: completed
  - id: todo-06-paths-verify
    content: "PE W3: reconfirm 12-apply / 5-skip census on execution SHA; abort Stage 4 if the set differs"
    status: completed
  - id: todo-07-paths-apply
    content: "PE W3: add paths to the 12 apply-set skills, one local commit each; leave skip-set unscoped"
    status: completed
  - id: todo-08-prove
    content: "PE W4: make skills-check + make pr-check + wiring closeout rg; prove zero dangling old-shape teachers/readers"
    status: completed
  - id: todo-09-pickup-hygiene
    content: "PE W4: regenerate artifacts, reconcile Claude skill copies, retarget pack/housekeeping path aliases, remove residue; no loose strings"
    status: completed
  - id: todo-10-converge
    content: "PE W4: L4 authorize-release, make pr, l9-pr-remediation to green+mergeable, merge this stack after older PRs"
    status: completed
isProject: false
---

# Normalize skill frontmatter and scoped paths

> **PLAN_DOCUMENT:** validated PASS (`schema` + semantic gates, depth=`deep`, convergence=`partial`). Machine JSON is staged at `/tmp/plan-skills-normalization-s1-s4.json` for execute-time projection via `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py`.
> **Execute:** [@environment/program-execution](environment/program-execution/) then subordinate [@autonomy](commands/autonomy.md) / `l9-bounded-autonomy` under a Program lease. Do not free-form mutate from this markdown alone.
> **Clicking Build authorizes this stack** (L4 plan-Build merge after green+mergeable). It does **not** authorize the five Stage-4 skip rows.
> **Improve kernel:** this revision adds a wiring-closure + pickup obligation. Nesting SKILL.md without retargeting every teacher, reader, test, generated registry, and path alias is an incomplete delivery.

## Execute via @environment/program-execution + autonomy

1. Attach PE + `/autonomy`. Project this plan to Blueprint artifacts under `$HOME/.l9/programs/pes-skills-normalization/`.
2. Bootstrap Controller (`pec.py bootstrap` → `reconcile` → `next`). Admit exact task scope; worker gets only the Rendered Contract.
3. L4 local autonomy: local commits only until `python3 ops/autonomy/l4_local.py authorize-release`, then scoped push/PR and `l9-pr-remediation`.
4. `autonomous_merge: false` in the packet. Merge this stack only after green+mergeable; older open PRs first.

**Stop / do not execute when:** current branch is `feat/wip-legal-defense-26cr-ingest`; Program Lock drift; apply/skip census differs from this plan; archive missing before nest; empty `paths` about to be written; closeout `rg` still hits an old-shape teacher or `tools/check_skills_standard.py`.

Campaign packet stub: `authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE`, `profile: pr-convergence`, `adapter_id: cursor-foreground`, `declared_branches: [chore/skills-normalization]`, `autonomous_merge: false`.

## Architect framing

- **planning_ssot:** [WIP/Cursor ToDo's/skills-normalization-pack/STANDARD.md](WIP/Cursor%20ToDo's/skills-normalization-pack/STANDARD.md) + [NORMALIZE_TASK.md](WIP/Cursor%20ToDo's/skills-normalization-pack/NORMALIZE_TASK.md) + [PATHS-PROPOSAL.md](WIP/Cursor%20ToDo's/skills-normalization-pack/PATHS-PROPOSAL.md)
- **plan_class:** `bounded_execution_contract`
- **redesign_allowed:** false
- **Depth:** `deep` (`route_plan.py --risk high` → deep; Stage 4 can hide skills)

## Immutable baseline (planning capture — re-lock at execute)

- **workspace:** `/Users/ib-mac/Cursor-Governance`
- **captured_on:** `feat/wip-legal-defense-26cr-ingest` @ `d59d5d175693263d977006e4ee70c41bb66a4e33` (dirty; legal WIP untracked)
- **execution branch:** `chore/skills-normalization` from `origin/main` only
- **overlap_policy:** `stop_if_dirty_overlaps_may_modify`
- **on_drift:** `stop_and_replan`
- **U-MAIN-DRIFT:** re-run nest dry-run + glob census on the execution SHA before any write

Preflight already passed on this workspace: nest dry-run 45 live / 43 change / 0 unparseable / 0 name mismatches; `AUTONOMY_MANIFEST.yaml` not coupled; glob census below.

## Objective

Make every `skills/**/SKILL.md` Cursor-native (`name`, `description`, `paths`, `disable-model-invocation`, `metadata`) with zero metadata loss, lock archived skills, ratchet the standard, scope only proven-safe `paths`, and leave **zero dangling producers, consumers, tests, generated copies, or path aliases** on the pre-nest shape.

### Success properties

- **SP-01** repository_state: execution `HEAD` is `chore/skills-normalization` forked from `origin/main`, not the legal-defense branch
- **SP-02** structural: 0 non-native top-level keys on `SKILL.md`; folded `l9-bounded-autonomy` description preserved; `status` readable from top-level or `metadata.status`
- **SP-03** filesystem: archive entry count equals scanned `SKILL.md` count; inventory exists; skip-set has no `paths`
- **SP-04** quality_gate: `make skills-check` PASS and `make pr-check` PASS
- **SP-05** wiring_closed: every listed producer/consumer/test either understands nested `metadata` or is explicitly classified NotApplicable; closeout `rg` is empty on the old-shape patterns below
- **SP-06** hygiene: generated registries regenerated from source; Claude skill copies reconciled; no `tools/check_skills_standard.py` alias left live; no `/tmp` PLAN_DOCUMENT as the only copy

## Capability preflight

- **CP-01** `git rev-parse --abbrev-ref HEAD` ≠ `feat/wip-legal-defense-26cr-ingest` (blocking)
- **CP-02** `python3` + PyYAML available for nest/check
- **CP-03** write_allow paths writable; Makefile / `.pre-commit-config.yaml` append-only respected

## Execution envelope

**write_allow**

- `skills/**/SKILL.md`
- `docs/skills-frontmatter-archive.yaml`
- `docs/skills-inventory.md`
- `docs/skills-standard.md`
- `ops/scripts/check_skills_standard.py`
- `ops/scripts/sync_generated_artifacts.py`
- `tests/ops/scripts/test_sync_generated_artifacts.py`
- `tests/ops/scripts/test_check_skills_standard.py`
- `Makefile` (append new lines only; do not edit the existing `.PHONY` or `help` lines)
- `.pre-commit-config.yaml` (append a new local hook only)
- `skills/l9-skill-compiler/references/file-contract.md`
- `skills/l9-skill-compiler/references/meta-standard.md`
- `skills/l9-skill-compiler/references/validation-checklist.md`
- `skills/l9-skill-compiler/references/skill-pack-contract.md`
- `skills/l9-issue-remediation/references/validation-checklist.md`
- `skills/l9-structured-reasoning/scripts/validate_skill.py`
- `skills/l9-repository-renovation/scripts/validate_exemplary_skill.py`
- `prompts/Recursive Improvement — Skills Batch.md`
- generated outputs only via `python3 ops/scripts/sync_generated_artifacts.py` (not hand-edit)
- pack/housekeeping path aliases only if those WIP files exist on the execution tree

**write_deny:** `CANONICAL_LAW.md`, `ORG_INVARIANTS.yaml`, `CODEOWNERS`, `.claude/settings.json`, `.claude/hooks/**`, `skills/AUTONOMY_MANIFEST.yaml`, `pyproject.toml`, `WIP/Legal Defense/**`, existing Makefile `.PHONY`/`help` lines, HTML `L9_META` in `references/*.md`, any skip-set `paths` insert, hand-edits of generated skill-registry JSON

**commands allow:** nest script, checker, `make skills-check`, `make pr-check`, `git commit` on declared branch, `l4_local.py`, `make pr` after release_authorized

**commands deny:** force-push, hard-reset, admin-merge, description rewrites, `_archived/` relocate

**network:** `bounded_external_write` only after L4 release (push/PR)

**secrets:** none

## Stage 1 — lossless nest

Use pack script [nest_skill_metadata.py](WIP/Cursor%20ToDo's/skills-normalization-pack/scripts/nest_skill_metadata.py):

```bash
python3 .../nest_skill_metadata.py --skills-dir skills --archive docs/skills-frontmatter-archive.yaml --include-archived --apply
```

Moves every key except `name` / `description` / `paths` / `disable-model-invocation` / `metadata` under `metadata:`. Expected movers on this tree: `skill_schema`, `layer`, `role`, `status`, `tags`, `owner`, `version`, `updated`, plus `sources` (2) and `future_home` (1). Already native (no nest): `l9-governance-symlinks`, `l9-repository-renovation`, `l9-structured-reasoning`.

Do not alter description text. Do not add `paths` here. Field order: `name`, `description`, `paths`, `disable-model-invocation`, `metadata`.

**Wiring closure — same wave as nest, before Stage 3. Pick up every string.**

Do not treat HTML `L9_META` / `skill_schema:` blocks in `references/*.md` as SKILL.md frontmatter. Those stay. Only YAML frontmatter on `SKILL.md` plus artifacts that **teach or parse** that frontmatter.

**Producers (upstream teachers — will re-emit the old shape if left stale)**

- [skills/l9-skill-compiler/references/meta-standard.md](skills/l9-skill-compiler/references/meta-standard.md) — Required Fields example is top-level `skill_schema` / `layer` / `role` / `tags`
- [skills/l9-skill-compiler/references/file-contract.md](skills/l9-skill-compiler/references/file-contract.md) — “audit fields in the same YAML frontmatter block”
- [skills/l9-skill-compiler/references/validation-checklist.md](skills/l9-skill-compiler/references/validation-checklist.md) — checklist lists audit fields as top-level
- [skills/l9-skill-compiler/references/skill-pack-contract.md](skills/l9-skill-compiler/references/skill-pack-contract.md) — SKILL.md Metadata example (lines 88–100) is the old shape
- [prompts/Recursive Improvement — Skills Batch.md](prompts/Recursive%20Improvement%20—%20Skills%20Batch.md) — `MUST_have_fields: [name, description, skill_schema, layer, role, tags, owner, status, version, updated]`
- [skills/l9-issue-remediation/references/validation-checklist.md](skills/l9-issue-remediation/references/validation-checklist.md) — “frontmatter: name, description, audit fields”

Retarget all of the above to: native keys at top level; audit keys under `metadata:`.

**Consumers (downstream readers)**

- [ops/scripts/sync_generated_artifacts.py](ops/scripts/sync_generated_artifacts.py) `_frontmatter_status` — dual-read `fm.get("status")` or `(fm.get("metadata") or {}).get("status")`. Today [tests/ops/scripts/test_sync_generated_artifacts.py](tests/ops/scripts/test_sync_generated_artifacts.py) `test_live_deprecated_skills_are_rejected` only writes top-level `status`. Add a twin case with `metadata.status` or the dual-read rots.
- [skills/l9-structured-reasoning/scripts/validate_skill.py](skills/l9-structured-reasoning/scripts/validate_skill.py) — `set(frontmatter) != {name, description}`. Allow `metadata` (and native optionals) so the new standard cannot fail this pack.
- [skills/l9-repository-renovation/scripts/validate_exemplary_skill.py](skills/l9-repository-renovation/scripts/validate_exemplary_skill.py) — `allowed_keys = {name, description, disable-model-invocation}`. Add `metadata`.
- [ops/scripts/build_claude_skill_registry.py](ops/scripts/build_claude_skill_registry.py) — reads `name`, `description`, `when_to_use`, `disable-model-invocation`, `user-invocable`. Native-only. **NotApplicable** (no edit).
- [environment/agents/adapters/claude-code/validate_skill_activation.py](environment/agents/adapters/claude-code/validate_skill_activation.py) — same native keys. **NotApplicable**.
- `skills/AUTONOMY_MANIFEST.yaml` — grep clean. **Do not edit.**

**Generated (edit the generator, then regenerate — never hand-edit)**

- `python3 ops/scripts/sync_generated_artifacts.py` after nest + status dual-read
- `make claude-skill-registry` / `make claude-skills` so `ops/generated/skill-registry.json`, Claude adapter `skillOverrides`, and reconciled `~/.claude` / project skill copies match the nested source
- Do not hand-edit `ops/generated/skill-registry.json` or `environment/agents/adapters/claude-code/generated/skill-registry.json`

**In-repo SSOT (so the contract does not live only in WIP)**

- Write [docs/skills-standard.md](docs/skills-standard.md) from the pack STANDARD (native five fields + nest rule + description contract + budgets). Point the checker docstring at this file.

**Path aliases (do not leave `tools/` lying)**

- Checker home is `ops/scripts/check_skills_standard.py`. Do not create `tools/check_skills_standard.py`.
- If the skills-normalization-pack or housekeeping-pack is present on the execution tree, retarget `CHECKLIST.md` / `NORMALIZE_TASK.md` / `housekeeping-pack/workflows/governance-self-check.yml` from `tools/check_skills_standard.py` to `ops/scripts/check_skills_standard.py`. If those WIP files are absent on `origin/main`, record NotApplicable and do not recreate them.

**Makefile additive_only**

- Append a **new** `.PHONY: skills-check` line and target at the file end.
- Do **not** edit the existing long `.PHONY` line or the `help:` echo list (that would overwrite a protected line).

**Closeout rg (todo-08 / todo-09 — must be empty except classified NotApplicable)**

```text
rg -n '^skill_schema:|^layer:|^role:|^owner:|^status:|^version:|^updated:|^tags:' skills --glob 'SKILL.md'
# 0 hits at column 0 (indented metadata: children are fine)

rg -n 'MUST_have_fields:.*skill_schema' prompts skills
# 0 hits

rg -n 'tools/check_skills_standard.py'
# 0 hits on the execution tree, or only inside docs/skills-frontmatter-archive.yaml / this plan
```

## Stage 2 — archived lockdown

Flag-all (already true on `_archived/l9-pr-analysis`). Enumerate the three archived packs; add `disable-model-invocation: true` only if missing. Record relocate-to-`docs/archived-skills/` as a follow-on. **Do not move `_archived/`.**

## Stage 3 — measure + ratchet

Write [docs/skills-inventory.md](docs/skills-inventory.md): live count, discovery footprint (planning capture 14672 bytes / ~3668 tokens vs 16384), description-band flags, overlap clusters quoted side-by-side. **No description rewrites.**

Install checker at [ops/scripts/check_skills_standard.py](ops/scripts/check_skills_standard.py) (this repo’s gate home; do not add `tools/check_skills_standard.py`). Parse frontmatter with `yaml.safe_load` so `description: >-` on `l9-bounded-autonomy` is not measured as two characters. Docstring cites `docs/skills-standard.md`.

Add [tests/ops/scripts/test_check_skills_standard.py](tests/ops/scripts/test_check_skills_standard.py): folded-description PASS, non-native top-level FAIL, archived missing flag FAIL, empty `paths` FAIL.

Append-only (both files are `additive_only`):

- `Makefile`: **new lines at EOF** — `.PHONY: skills-check` + target. Do not touch the existing `.PHONY` or `help` lines.
- `.pre-commit-config.yaml`: new local hook after the existing local hooks

Do not rewrite existing Makefile keys or pre-commit hooks.

## Stage 4 — paths (verify then apply)

`paths` hides a skill when no matching file is in context. A wrong glob is worse than no glob.

Tracked-file census on this workspace (re-verify on execution SHA):

**Apply (12) — Build authorizes these globs as written**

- `l9-api-smoke-testing` — 18
- `l9-architecture-decision-records` — 17
- `l9-ci-ops` — 9
- `l9-code-graph-rag-mcp` — 15
- `l9-dag-authoring` — 61
- `l9-prompt-engineering` — 17
- `l9-python-tdd-with-uv` — 619
- `l9-setting-up-ci` — 8
- `l9-skill-compiler` — 371
- `l9-update-agent-docs` — 104
- `l9-update-command` — 77
- `l9-wire-skill-into-repo` — 372

**Skip (5) — leave unscoped; do not invent replacement globs**

- `l9-e2e-blocker-resolution` — 0 matches (empty = dead)
- `l9-repo-index` — 0 matches
- `l9-setting-up-terraform` — 0 matches
- `l9-kubernetes-deploying` — 1 match, hostile PE fixture only (`environment/program-execution/conformance/fixtures/hostile/deployment-target-omitted.yaml`)
- `l9-aws-secrets` — 14 matches, but **no `.cursorignore`**; do not correlate activation to `**/*.env*` / `**/secrets/**`

Rule-glob notes (not blockers): `97-graph-*` are alwaysApply; `20-lang-python` is `src/**/*.py` and this repo has no `src/` — python-tdd `**/*.py` is the correct wider skill glob; `71-ci-cd-pipeline` is close to `l9-ci-ops` / `l9-setting-up-ci` (ci-ops also includes `.pre-commit-config.yaml`).

Procedure: one local commit per apply-set skill; `make skills-check` after each; if a glob goes empty, revert that commit and leave the skill unscoped.

28 deliberately unscoped skills in PATHS-PROPOSAL stay unscoped.

## Side effects and idempotency

- todo-01: filesystem_read — safe_to_repeat
- todo-02: filesystem_mutation — safe_with_dedupe (re-apply nest is idempotent after first apply)
- todo-03: filesystem_mutation — safe_with_dedupe
- todo-04: filesystem_mutation — safe_with_dedupe
- todo-05: filesystem_mutation — append-only; unsafe if someone rewrites Makefile
- todo-06: filesystem_read — safe_to_repeat
- todo-07: filesystem_mutation — one commit per skill; revert last commit to compensate
- todo-08: filesystem_read — safe_to_repeat
- todo-09: filesystem_mutation — regenerate + alias retarget; safe_with_dedupe
- todo-10: network_write — safe_with_dedupe (reuse PR)

## Architecture impact

Control-plane / policy only. No data-plane, no memory store, no adapter brain move. Prohibited: redesign skill discovery; relocate `_archived/`; rewrite descriptions; leave any teacher or reader on the pre-nest SKILL.md shape; hand-edit generated registries.

## Rollback

- **code:** restore frontmatter from `docs/skills-frontmatter-archive.yaml`; `git revert` the last Stage-4 commit; `git restore` scoped paths
- **automatic_allowed:** false
- **irreversible:** none
- No force-push / history rewrite

## Complexity and uncertainty

- complexity: medium
- uncertainty: medium (origin/main drift; Cursor `paths` hide semantics)
- blast_radius: high for Stage 4 hide-the-skill; medium for nest
- architectural_boundaries_crossed: 0
- migration_required: false

## Execution DAG

```text
W0  todo-01-baseline-preflight
W1  todo-02-archive-and-nest
      ├─ todo-03-wiring-closure
      └─ todo-04-archived-lock
W2  todo-05-checker-inventory
W3  todo-06-paths-verify → todo-07-paths-apply
W4  todo-08-prove → todo-09-pickup-hygiene → todo-10-converge
```

**Critical path:** todo-01 → todo-02 → todo-03 → todo-05 → todo-06 → todo-07 → todo-08 → todo-09 → todo-10

**Forbidden edges:** paths-apply before checker PASS; nest on the legal-defense branch; `paths` on the skip set; converge while closeout `rg` still hits an old-shape teacher or `tools/check_skills_standard.py`.

## Property evidence matrix

- EV-SP-01: `git rev-parse --abbrev-ref HEAD` + `git merge-base --is-ancestor origin/main HEAD`
- EV-SP-02: `python3 ops/scripts/check_skills_standard.py` PASS + yaml assert on `l9-bounded-autonomy`
- EV-SP-03: archive entry count; skip-set has no `paths` key
- EV-SP-04: `make pr-check` PASS
- EV-SP-05: closeout `rg` empty on column-0 SKILL.md audit keys, `MUST_have_fields:.*skill_schema`, and `tools/check_skills_standard.py`
- EV-SP-06: `pytest tests/ops/scripts/test_sync_generated_artifacts.py tests/ops/scripts/test_check_skills_standard.py` PASS; `make claude-skills-check` PASS after reconcile

## Stress and disconfirm

- Empty `paths` match → skill disappears. Three proposal rows are already empty here.
- Nesting `status` without dual-read → deprecated packs can sit in live discovery.
- Compiler, improvement prompt, or issue-remediation checklist still teaching top-level keys → nest drift returns on the next compile or `/improve` pass.
- Scoping k8s to the hostile fixture → skill invisible during real k8s work.
- Pack checker regex vs `description: >-` → false-fail `l9-bounded-autonomy` and block `make pr`.
- `tools/check_skills_standard.py` left in housekeeping/pack docs → next pack install wires the wrong path.
- Generated skill-registry / Claude copies not reconciled → adapters keep serving pre-nest frontmatter.

## Out of scope

- Description rewrites (Stage 3 reports only)
- Relocate `_archived/`
- Paths on the five skip skills
- Nesting or rewriting HTML `L9_META` blocks in `references/*.md` (different contract)
- Rules-normalization pack execution
- Housekeeping pack install (path-alias retarget only if those files exist)
- Legal Defense WIP
- Force-push, hard-reset, admin-merge, scanner weakening
- Editing `CANONICAL_LAW.md` / `AGENTS.md` / existing Makefile `.PHONY` or `help` lines

## Follow-on milestone (separate plan)

- Relocate `skills/_archived/` to `docs/archived-skills/`
- Revisit skip-set if this repo later gains e2e / terraform / real k8s / `.cursorignore`
- Description-band edits after human review of inventory overlap quotes
- Housekeeping pack full install (this plan only retargets the `tools/` path if the pack is present)

## Doc / root surface

- **Makefile** / **.pre-commit-config.yaml:** update, append new lines only (todo-05)
- **docs/skills-standard.md:** create (todo-05) — in-repo SSOT so the contract is not WIP-only
- **AGENTS.md / CANONICAL_LAW.md / README.md / TODO.md:** N/A — no new always-on law; do not rewrite additive_only root docs for a Makefile target

## Convergence

- **status:** partial
- **remaining_unknown_ids:** `U-MAIN-DRIFT` (probe at todo-01)
- **U-PATHS-RUNTIME:** accept_bounded (empty glob = skip)
- **next_skill:** `l9-ynp` after Build; execute path is PE + `/autonomy`
- **stop_reason:** planning artifact is ready; final_validation pending until execute

## GMP / modification lock

**may_modify:** listed write_allow paths

**must_not_modify:** CANONICAL_LAW.md, ORG_INVARIANTS.yaml, CODEOWNERS, `.claude/settings.json`, `.claude/hooks/**`, `skills/AUTONOMY_MANIFEST.yaml`, `pyproject.toml`, `WIP/Legal Defense/**`, existing Makefile `.PHONY`/`help` lines

**preserved:** native-only top-level fields; description text unchanged; additive_only Makefile/pre-commit; deprecated-status detection; no empty/hostile `paths`; HTML `L9_META` on references unchanged

## Pickup hygiene (todo-09) — no loose strings

After prove, before PR:

1. Run `python3 ops/scripts/sync_generated_artifacts.py` and stage any regenerated registries / skillOverrides.
2. Run `make claude-skills` then `make claude-skills-check`.
3. Run `pytest tests/ops/scripts/test_sync_generated_artifacts.py tests/ops/scripts/test_check_skills_standard.py`.
4. Run the closeout `rg` block. Any hit is a failed pickup unless it is indented `metadata:` content, the frontmatter archive, or this plan.
5. Retarget pack/housekeeping `tools/check_skills_standard.py` strings if those files exist on the execution tree.
6. Copy the validated PLAN_DOCUMENT out of `/tmp` into the feature branch (`.cursor/plans/` or `docs/handoffs/`) so execute evidence is not a temp file.
7. Confirm `git status` has no `__pycache__`, nest dry-run leftovers, or untracked debug files from this work.

Delivery is incomplete while any producer still teaches the old SKILL.md shape or any consumer still reads only top-level `status`.
