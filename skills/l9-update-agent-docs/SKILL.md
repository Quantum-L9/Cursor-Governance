---
name: l9-update-agent-docs
description: "maintain the root agent-doc pointer stack (agents.md, claude.md, readme.md) and generate module READMEs via readme-pipeline-v1. use when the user says update agent docs, refresh repo docs, generate module readmes, sync agent files, create root claude.md/invariants.md, or after ci checks or pre-commit hooks change. creates those two only when absent; never invents other root files."
paths: "AGENTS.md, CLAUDE.md, README.md, INVARIANTS.md"
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, docs, agents, ci, maintenance]
  owner: igor_beylin
  status: active
  version: 2.5.1
  updated: 2026-08-28
  when_to_use: "refreshing AGENTS.md, CLAUDE.md, or README.md as a pointer stack after CI, hook, or registry changes; generating module READMEs via readme-pipeline-v1; or creating root CLAUDE.md / INVARIANTS.md when missing"
---

# Update Agent Documentation (L9)

## Purpose

Keep the **root-doc pointer stack** aligned with live authority. This skill is a
pointer maintainer, not a second doctrine author. Surgical edits only — every
metric from repo ground truth.

Live files on this host (do not invent others):

| File | Role |
|------|------|
| `CLAUDE.md` | Load pointer. Authority chain only. Must stay short. |
| `AGENTS.md` | Operating-instruction SSOT. Additive-only on this repo. |
| `README.md` | Index that points at `CANONICAL_LAW.md` and `AGENTS.md`. |
| `INVARIANTS.md` / `ARCHITECTURE.md` | Live indexes **where present** (maps, not rungs; adapter-managed on this repo). |

Bind targets from `ops/config/root-file-protection.json` before any write.
When root `CLAUDE.md` or `INVARIANTS.md` is **absent**, create it via
Step 3a — those two only. Never invent any other root file to satisfy a
template.

## Authority Order

1. `CANONICAL_LAW.md`
2. `ops/autonomy/surface_profile.yaml`
3. `AGENTS.md`
4. This skill's write contract
5. `Unknown` — mark unverified counts `Unknown`; never fabricate

When the audit needs the full alignment auditor, **read**
`kernels/Recursive Alignment.md` by that path. When a confirmed pointer defect
needs repair, **read** `kernels/Validate & Repair.md` by that path. Do not copy,
compress, wrap, or distill either kernel into this skill (no compressed-kernel
table, no kernel YAML in `references/`). Each kernel file remains the only full
auditor or repairer.

## Named write rules (harvested; not a kernel dump)

1. **Target bind** — inventory files that exist. Skip and record `Unknown` for
   missing paths. Never invent a root file to satisfy a template. Harvest
   nugget `c-bind-before-write` (MERGE_WITH_EXISTING): this step already owns
   that contract; do not add a second gap-analysis generator.
2. **Authority map** — skills do not author doctrine. Point at the live owner.
3. **Required headings** — a live index is invalid when headings or pointers
   required by `references/pointer-heading-map.yaml` are absent. Fail closed
   and report the missing names. Rebound to this pointer stack only — never
   require donor sections `overview`, `airules`, `apisurface`, `datamodels`,
   or `components` on the **root** pointer map. Never overwrite root
   `README.md` from a template to make the check pass. Module READMEs may
   use Purpose / Components via `readme_config.yaml`. Harvest nugget
   `c-required-section-validation`.
4. **One owner** — `CLAUDE.md` stays a pointer; `AGENTS.md` stays the operating
   SSOT; generated formatter blocks stay companions owned by
   `environment/ide/policy.json` via `ops/scripts/adapters/agentdocs.sh`.
5. **No competing SSOT** — do not dump CI, pre-commit, toolchain, or skill-registry
   tables that already live in `AGENTS.md` §§4–6 or generated registries.
6. **Evidence + Unknown** — every number from repo files.
7. **Audit-only default** — inspect before write; modify only files that exist
   and that the user (or a locked plan) authorized.

## Named repair rules (Validate & Repair; not a kernel dump)

1. **Inspect before edit** — finish target bind + evidence before any write.
2. **Root cause before patch** — fix the stale pointer or invented write-target;
   do not hide it by dumping CI tables into `CLAUDE.md`.
3. **Smallest source-aligned change** — one additive `AGENTS.md` line or one
   `CLAUDE.md` pointer correction. No fold, no rewrite, no extra files.
4. **Honest validation** — report only checks that ran as Passed / Failed /
   Skipped / Unknown / NotApplicable. Local `make pr` is not remote CI.
   Do not claim a gate from inspection or grep alone.
5. **No stubs or fake validation** — no TODO-as-done, no invented root files,
   no claimed PASS without the command output.
6. **Edit authority, regenerate companions** — do not hand-edit the generated
   formatter block; do not treat generated skill-registry JSON as doctrine.

## Forbidden

- Wrapping or compressing `kernels/Recursive Alignment.md` or
  `kernels/Validate & Repair.md` into this pack
- Always/Never lists, CI tables, or skill-registry dumps in `CLAUDE.md`
- Folding `AGENTS.md` into a thin pointer (requires `ALLOW-ROOT-DELETION`)
- Creating any root file outside Step 3a's contract (`CLAUDE.md` /
  `INVARIANTS.md`, only when absent); root `ARCHITECTURE.md` is never
  created by this skill
- Editing `CANONICAL_LAW.md` or either kernel file
- Rewriting generated formatter-ownership blocks by hand
- Generating or overwriting the **root** `README.md` from a template or CodeGenAgent
- Moving `readme-pipeline-v1` out of `workflows/` — the DAG stays the sequencer
- Treating the root `README.md` as a binding AI-scope contract

## When to Use

- User says update agent docs / refresh repo docs / sync agent files
- After CI, pre-commit, or skill-registry changes that make a **pointer** stale
- After `l9-wire-skill-into-repo` when docs still name a skill incorrectly
- Root `CLAUDE.md` or `INVARIANTS.md` is missing (bootstrap creation — Step 3a)
- User asks to generate or refresh **module / subsystem** READMEs from code facts

Skill **wire / unwire** is owned by `l9-wire-skill-into-repo`. Use this skill
afterward only to keep pointers honest.

## Project Adapters

Before writing, probe (first match wins) — adapters may add domain inventory,
never invented root files:

1. `.claude/adapters/cursor-governance-update-agent-docs.md` (this repo)
2. `.claude/adapters/{repo}-update-agent-docs.md`
3. `.claude/adapters/plasticos-update-agent-docs.md` (PlasticOS / Odoo 19)

## Execution Protocol

### Step 1 — Bind live targets

Read `ops/config/root-file-protection.json`. Confirm which of `AGENTS.md`,
`CLAUDE.md`, `README.md` exist. If an adapter names additional **existing**
files, include those. Record excluded or missing paths as `Unknown`. Do not
create a missing `README.md` to satisfy the heading map.

### Step 2 — Audit (read-only)

If ownership or source-of-truth is in doubt, load
`kernels/Recursive Alignment.md` (audit_only). Otherwise inspect:

- `CLAUDE.md` still opens as an authority pointer
- `AGENTS.md` still owns operating instructions; append-only on this repo
- `README.md` still points at law + `AGENTS.md`
- Counts you intend to cite (hooks, jobs) match the files that own them

Run `scripts/validate_pointer_headings.py --root <repo>`. Missing required
headings or pointers on a **live** file mean the index is not honest
(Failed). A mapped path that does not exist is Unknown — do not create it.
Do not produce CI/pre-commit tables for pasting into `CLAUDE.md`.

If a pointer is stale or a write target was invented, load
`kernels/Validate & Repair.md` before editing.

### Step 3 — Write

| File | Allowed write |
|------|----------------|
| `CLAUDE.md` | Fix a stale pointer or a factual error in the existing short bullets. Do not add Always/Never, CI, or registry sections. |
| `AGENTS.md` | Surgical additive update of an existing operating section, or a new marked append. Do not fold. Do not delete lines without `ALLOW-ROOT-DELETION`. |
| `README.md` (repo root) | Fix an index pointer that names a missing or invented file. Never generate this file. |
| `<module>/README.md` | Generate or refresh only through Step 3b (AST + config). Never the root index. |

Preserve generated `<!-- BEGIN L9 FORMATTER OWNERSHIP -->` blocks. If
`install_ide_profile` dirtied only that block, restore from HEAD unless
`environment/ide/policy.json` changed.

### Step 3a — Create Missing Root Docs (`CLAUDE.md`, `INVARIANTS.md`)

Applies only when the file is **absent at repo root**. Never overwrite an existing
file from this step — an existing file falls through to the Step 3 write contract.

**Root `CLAUDE.md` (create as load pointer):**

- Shape it on the Cursor-Governance root `CLAUDE.md`: an **authority pointer**,
  not a doctrine copy. State where doctrine lives and what outranks what.
- Contents: repo authority chain (highest first), pointers to the operating SSOT
  (`AGENTS.md` or equivalent) and to `INVARIANTS.md` / `ARCHITECTURE.md` as maps,
  and at most a short list of the mistakes agents most often make in that repo.
- Forbidden: Always/Never lists, CI / hook / skill-registry tables, or any body
  text copied from the docs it points at. Keep it short enough to always load.

**Root `INVARIANTS.md` (create as invariant index):**

- Sections: invariant list, CI enforcement map (which workflow job or pre-commit
  hook enforces each invariant), known false positives.
- Every invariant and metric comes from the Step 2–6 audits — workflows, hooks,
  lint config, adapter scripts. Unverifiable entries are `Unknown`, never invented.
- Each false positive cites **where** the exclusion lives (file + key/flag).
- Pointer-not-dump: cite the enforcing file; do not copy rule bodies, org
  invariant bodies, or tables that already live in the operating SSOT.

**Both files:**

- Where the repo tracks root files (e.g. `ops/config/root-file-protection.json`),
  register the new file as `managed` in the same change.
- A project adapter's write rules outrank these defaults when present.

### Step 3b — Module README pipeline (wired)

Owns **module** READMEs, not the root index. Sequencer remains
`readme-pipeline-v1` in `workflows/dags/readme_pipeline_dag.py`. This skill
invokes the same CLI the DAG names:

```bash
python scripts/generate_subsystem_readmes.py --list
python scripts/generate_subsystem_readmes.py --gaps
python scripts/generate_subsystem_readmes.py --validate
python scripts/generate_subsystem_readmes.py --dry-run --subsystem <key>
python scripts/generate_subsystem_readmes.py --skip-time-verify
python scripts/generate_subsystem_readmes.py --validate-sections
```

Pack wrapper (same argv): `scripts/generate_module_readmes.py` in this skill.
After `import workflows.dags`, resolve with
`get_session_dag("readme-pipeline-v1")`. Do not invent a runner class.

Config SSOT: `config/subsystems/readme_config.yaml`. Facts come from stdlib
AST. `--skip-time-verify` is a no-op kept so the DAG argv stays valid.

Must not:

- Write repo-root `README.md`
- Follow `--path` outside the repo or to `.`
- Overwrite `auto_generated: false` or `skip: true` without `--force`
- Emit DORA blocks, worldtime calls, or AI allow/restrict/forbid scopes
- Invent a module path that does not exist (record Unknown / skip)

Do not copy the DAG into this pack.

### Step 4 — Report

List files changed, evidence for each metric, and any `Unknown`. For every
check that ran, record Passed / Failed / Skipped / Unknown / NotApplicable.
Do not claim either kernel was wrapped into this skill.

## Resource Map

- Auditor (load, do not copy): `kernels/Recursive Alignment.md`
- Repairer (load, do not copy): `kernels/Validate & Repair.md`
- Root inventory: `ops/config/root-file-protection.json`
- Formatter companion: `ops/scripts/adapters/agentdocs.sh`
- Skill registry wire: `l9-wire-skill-into-repo`
- No-wrap check: `scripts/self_test.py`
- Pointer heading map: `references/pointer-heading-map.yaml`
- Heading/pointer check: `scripts/validate_pointer_headings.py`
- Module README sequencer: `workflows/dags/readme_pipeline_dag.py` (`readme-pipeline-v1`)
- Module README CLI: `scripts/generate_subsystem_readmes.py`
- Module README map: `config/subsystems/readme_config.yaml`

## Validation

- `CLAUDE.md` first heading remains an authority pointer
- This pack contains no compressed-kernel table and no kernel YAML dump
- Write targets exist — or were created only through Step 3a's
  create-when-missing contract, never by overwrite
- Documented counts match repo files
- Step 3a creations carry no fabricated counts, stay pointer/index-shaped,
  and are registered in the repo's root-file protection config when one exists
- `validate_pointer_headings.py` is Passed for every live mapped file, or
  Unknown for a mapped path that does not exist; Failed headings are reported
  by name and are not repaired by generating a README
- Module generate used `--validate` / `--gaps`; root `README.md` was not written

## Failure Handling

- Adapter missing → run generic steps; note domain gaps
- Count unverified → `Unknown`; do not ship a guessed number
- Doc edits you authored → scoped-commit them by pathspec without asking
  (rule `99-no-auto-commit`); push and PR stay ask-first
- Urge to embed either kernel → refuse; keep the path citation

## Stop Condition

Pointer stack is honest. Invented files were not created. Neither kernel was
wrapped. Module READMEs, if generated, used Step 3b and left the root index
alone.
