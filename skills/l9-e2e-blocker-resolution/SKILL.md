---
name: l9-e2e-blocker-resolution
description: run repo e2e or local-proof tests, classify and fix in-repo blockers, then write a brief for remaining external gates and a todo.md session-reference entry. use when the user asks to run e2e, clear e2e blockers, document remaining secrets/env gaps, or produce a session-start surface for blocked proof paths.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, e2e, blockers, verification, secrets, todo, brief, session-start]
owner: igor_beylin
status: active
disable-model-invocation: true
version: 1.0.0
updated: 2026-07-31
---

# E2E Blocker Resolution

## Purpose

Run this repo’s end-to-end (or nearest local-proof) path, fix what can be fixed in-repo, and leave durable operator artifacts for everything that cannot: a brief under `docs/` plus a `TODO.md` session-reference entry that `/start-session` will surface.

## Core Contract

| Phase | Mutates | Output |
|-------|---------|--------|
| Discover | no | Canonical e2e / local-proof command(s) + evidence sources |
| Run | no (exec only) | Pass/fail log excerpts |
| Classify | no | Fixable / external / out-of-scope table |
| Resolve | yes (code/CI/docs only) | Fixes + re-run evidence |
| Brief + TODO | yes | `docs/…` brief + top `TODO.md` link |
| Report | no | Fixed \| Remaining \| Files \| Operator next steps |

## Authority Order

1. Explicit user command names, targets, or “local-only / disposable / CI” scope.
2. Repo verify docs and scripts — `package.json`, `Makefile`, `justfile`, `AGENTS.md`, `README*`, `.github/workflows/*`.
3. Existing secrets/env docs in the repo (e.g. `docs/secrets-and-environment.md`, `.env.example`).
4. This skill’s references.
5. `Unknown` — do not invent secrets, tokens, disposable IDs, or “ready” claims without command evidence.

## Compact Workflow

1. **Discover** — load [references/discovery.md](references/discovery.md). Prefer the narrowest documented proof path (local unit/e2e before disposable remote e2e).
2. **Run** — execute the chosen command(s). Capture failing step + error class.
3. **Classify** — load [references/blocker-classification.md](references/blocker-classification.md). Split fixable-in-repo vs external/operator vs out-of-scope.
4. **Resolve** — fix only fixable items (scripts, lockfiles, permissions flags, code). After each meaningful fix, re-run the same command. Never invent credential values or mark credential-bound checks green without runtime evidence.
5. **Brief + TODO** — load [references/brief-and-todo-templates.md](references/brief-and-todo-templates.md). Write the brief; prepend a session-reference section to root `TODO.md` (create file if missing).
6. **Report** — deliver Fixed / Remaining / Files / Operator next steps. Load [references/validation-checklist.md](references/validation-checklist.md) before claiming complete.

## Behavior Rules

- Repo-agnostic: discover commands; do not hardcode Website-Bot script names.
- Fail closed on secrets: names and sourcing guidance only — never values.
- Prefer smallest change that unblocks the next proof step.
- Do not push, force-push, or amend unless the user explicitly requests git publish/amend.
- Do not claim production readiness or e2e green when remaining blockers exist.
- Idempotent brief/TODO updates: refresh the same canonical paths when re-run; do not spawn duplicate unrelated TODO sections for the same brief.

## Resource Map

- [references/discovery.md](references/discovery.md) — find canonical e2e / proof commands.
- [references/blocker-classification.md](references/blocker-classification.md) — classify and route fixes.
- [references/brief-and-todo-templates.md](references/brief-and-todo-templates.md) — brief path + TODO session-reference format.
- [references/validation-checklist.md](references/validation-checklist.md) — completion gates.

## Validation

Before reporting complete: checklist in [references/validation-checklist.md](references/validation-checklist.md) MUST pass. Brief MUST list remaining blockers with purpose + where to source + storage recommendation. `TODO.md` MUST link the brief under a **session reference** heading.

## Failure Handling

- No e2e / proof script found → STOP; report searched locations; ask user for the command.
- All failures are external (secrets/targets) → skip code mutation; still write brief + TODO.
- Disposable e2e needs destructive remote targets → require explicit user confirmation before creating/mutating disposable repos or projects.
- AGENTS.md / launch-env forbids inventing values → convert missing values to env names + blocked-check records, never fabricate.
- Brief path already exists with different topic → use `docs/ops/e2e-blockers-<topic>.md` or ask which path to refresh.
