---
name: l9-update-agent-docs
description: audit the repo and update agents.md, architecture.md, invariants.md, and claude.md with current ci pipeline rules, known false positives, pre-commit hooks, and agent skill registries. use when the user says update agent docs, refresh repo docs, sync agent files, or after ci checks or pre-commit hooks change.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, docs, agents, ci, maintenance]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# Update Agent Documentation (L9)

Regenerate root-level agent instruction files so coding agents write CI-passing code and review agents flag real issues (not false positives).

## When to Use

- CI workflows (`.github/workflows/*`) changed
- Pre-commit hooks (`.pre-commit-config.yaml`) changed
- Lint/type config (`pyproject.toml`, `ruff.toml`, etc.) changed
- Agent skill registry changed (new skills, subagent preload lists)
- Periodic refresh (monthly or after large PRs)

Load a **project adapter** when the repo has domain-specific docs (modules, domain pattern scripts, custom invariants).

## Project Adapters

Before Step 1, probe for adapters (first match wins):

1. `.claude/adapters/{repo}-update-agent-docs.md`
2. `.claude/adapters/plasticos-update-agent-docs.md` (PlasticOS / Odoo 19)

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

Update surgically (preserve structure). Typical targets when they exist:

| File | Sections |
|------|----------|
| `AGENTS.md` | Project overview metrics, CI checklist, false positives, pre-commit table, lint config, skill/subagent tables |
| `ARCHITECTURE.md` | Module/package index, CI/CD architecture, version bump |
| `INVARIANTS.md` | Invariant list, CI enforcement map, false positives |
| `CLAUDE.md` | Always/Never lists, references, imports |

Adapter defines extra sections (e.g. Odoo 19 pattern table, `plasticos_*` module index).

When skills change, verify **`l9-wire-skill-into-repo`** gates were followed (`.claude/adapters/plasticos-repo-wiring.md` in PlasticOS).

Sync skill tables from `.claude/README.md` (L9 global + project skills).

## Validation

After updating, verify counts match repo state (modules, hooks, jobs). Cross-reference `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md`, `ARCHITECTURE.md`.

## Stop Condition

All targeted files updated. Documented counts match actual repo files. Present summary with lines changed and key metrics.

## Constraints

- Surgical edits only — do not rewrite from scratch
- No fabricated data — every number from repo files
- Do not commit — present for user review
