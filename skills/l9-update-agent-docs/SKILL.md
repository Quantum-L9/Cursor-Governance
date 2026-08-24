---
name: l9-update-agent-docs
description: audit the repo and update agents.md, architecture.md, invariants.md, and claude.md with current ci pipeline rules, known false positives, pre-commit hooks, and agent skill registries. use when the user says update agent docs, refresh repo docs, sync agent files, create root claude.md/invariants.md, or after ci checks or pre-commit hooks change.
paths: "AGENTS.md, docs/**, README.md"
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, docs, agents, ci, maintenance]
  owner: igor_beylin
  status: active
  version: 2.1.0
  updated: 2026-08-24
---

# Update Agent Documentation (L9)

## Purpose

Regenerate root-level agent instruction files so coding agents write CI-passing code and review agents flag real issues (not false positives). Surgical edits only — every metric from repo ground truth.

## Core Contract

| Step | Target files | Source |
|------|--------------|--------|
| 1 Inventory | Modules/packages | Project adapter if present |
| 2 CI audit | `.github/workflows/*` | Blocking vs non-blocking tables |
| 3 Pre-commit | `.pre-commit-config.yaml` | Hook count and exclusions |
| 4 Domain patterns | Adapter scripts | Odoo/domain checks when wired |
| 5 Lint config | `pyproject.toml`, etc. | Rules, ignores, line length |
| 6 False positives | CI + pre-commit + lint | Documented exclusions |
| 7 Write | `AGENTS.md`, `ARCHITECTURE.md`, `INVARIANTS.md`, `CLAUDE.md` | Preserve structure; create root `CLAUDE.md` / `INVARIANTS.md` if missing (Step 7a) |

## Authority Order

1. Actual repo files — workflows, hooks, manifests, module counts.
2. Project adapter (`.claude/adapters/*-update-agent-docs.md`) when present.
3. `.claude/README.md` for skill registry sync.
4. This skill's execution protocol below.
5. `Unknown` — mark metric as `TBD`; never fabricate counts.

## When to Use

- CI workflows (`.github/workflows/*`) changed
- Pre-commit hooks (`.pre-commit-config.yaml`) changed
- Lint/type config (`pyproject.toml`, `ruff.toml`, etc.) changed
- Agent skill registry changed (new skills, unwired/deprecated skills, subagent preload lists)
- Root `CLAUDE.md` or `INVARIANTS.md` is missing (bootstrap creation — Step 7a)
- Periodic refresh (monthly or after large PRs)

Skill **wire / unwire / deprecate / deregister** is owned by `l9-wire-skill-into-repo`
(archive out of live `skills/`, clear autonomy tiers + adapter symlinks). Use this
skill afterward only to refresh docs that still list skills.

Load a **project adapter** when the repo has domain-specific docs (modules, domain pattern scripts, custom invariants).

## Project Adapters

Before Step 1, probe for adapters (first match wins):

1. `.claude/adapters/cursor-governance-update-agent-docs.md` (this repo)
2. `.claude/adapters/{repo}-update-agent-docs.md`
3. `.claude/adapters/plasticos-update-agent-docs.md` (PlasticOS / Odoo 19)

Adapters add domain inventory steps, extra audit scripts, and domain-specific doc sections.

## Execution Protocol

Follow all steps. Do not skip generic steps; run adapter steps when an adapter exists.

### Step 1 — Domain Inventory (adapter or skip)

If an adapter defines module/package inventory, run it. Otherwise skip.

### Step 2 — Audit CI Pipeline

Read every workflow file under `.github/workflows/`.

For each workflow, extract:

- **Job names** and what they check
- **Blocking vs non-blocking**: `continue-on-error: true` or `|| true`
- **Baselines**: threshold env vars or documented limits
- **Exclusions**: `--exclude`, `paths-ignore`, `grep -v`

Produce two tables:

1. **Blocking jobs** — must pass for merge
2. **Non-blocking jobs** — informational only

### Step 3 — Audit Pre-commit Hooks

Read `.pre-commit-config.yaml` (or equivalent). For each hook: type, blocking status, global exclusions. Count total hooks.

### Step 4 — Domain Pattern Scripts (adapter or skip)

If an adapter references domain lint/pattern scripts (e.g. Odoo pattern checks), audit them per adapter instructions.

### Step 5 — Audit Lint/Type Config

Read `pyproject.toml` / `ruff.toml` / `mypy.ini` and extract line length, rules, per-file ignores, complexity limits.

### Step 6 — Audit Known False Positives

Search intentional exclusions across CI, pre-commit, lint config, and audit scripts. Record **where**, **what**, **why**.

### Step 7 — Write Agent Docs

Update surgically (preserve structure). In Cursor-Governance, root `ARCHITECTURE.md` and `INVARIANTS.md` are **live indexes** (not optional, not competing SSOTs). Follow the Cursor-Governance adapter: pointer-not-dump.

| File | Sections |
|------|----------|
| `AGENTS.md` | Operating SSOT — additive only here; do not re-dump CI / hook / skill tables |
| `ARCHITECTURE.md` | Module/package index, CI/CD architecture, version bump (pointer index) |
| `INVARIANTS.md` | Invariant list, CI enforcement map, false positives (pointer index) |
| `CLAUDE.md` | Stay a load pointer; no Always/Never or CI tables in this repo |

Adapter defines extra sections (e.g. Odoo 19 pattern table, `plasticos_*` module index).

When skills change, verify **`l9-wire-skill-into-repo`** gates were followed (`.claude/adapters/plasticos-repo-wiring.md` in PlasticOS).

Sync skill tables from `.claude/README.md` (L9 global + project skills).

### Step 7a — Create Missing Root Docs (`CLAUDE.md`, `INVARIANTS.md`)

Applies only when the file is **absent at repo root**. Never overwrite an existing
file from this step — an existing file falls through to the Step 7 update contract.

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

## Resource Map

No `references/` folder — protocol lives in this file. Load project adapters when present:

- `.claude/adapters/cursor-governance-update-agent-docs.md`
- `.claude/adapters/{repo}-update-agent-docs.md`
- `.claude/adapters/plasticos-update-agent-docs.md` (PlasticOS / Odoo 19)

Wiring verification: `.claude/adapters/plasticos-repo-wiring.md` when skills changed.

## Validation

After updating, verify counts match repo state (modules, hooks, jobs). Cross-reference `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md`, `ARCHITECTURE.md`. Documented false positives MUST cite exclusion location. Files created by Step 7a meet the same bar: no fabricated counts, `CLAUDE.md` stays pointer-shaped, and new root files are registered in the repo's root-file protection config when one exists.

## Failure Handling

- Adapter missing for domain repo → run generic steps; note domain gaps in summary.
- Count mismatch after edit → re-audit source files; do not ship stale numbers.
- User asked to commit → present diff for review; do not commit unless explicitly requested.
- Skill registry drift → run **`l9-wire-skill-into-repo`** checklist before updating skill tables.

## Stop Condition

All targeted files updated. Documented counts match actual repo files. Present summary with lines changed and key metrics.

## Constraints

- Surgical edits only — do not rewrite from scratch
- No fabricated data — every number from repo files
- Do not commit — present for user review
