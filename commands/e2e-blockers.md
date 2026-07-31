---
name: e2e-blockers
version: "1.0.0"
description: "Run e2e/local-proof, fix in-repo blockers, brief + TODO for the rest"
disable-model-invocation: true
---

# /e2e-blockers — E2E Blocker Resolution

## WHAT IT DOES

Invoke skill **`l9-e2e-blocker-resolution`**: discover and run this repo’s e2e / local-proof path, fix in-repo blockers, write a `docs/` brief for remaining external gates, and add a `TODO.md` session-reference link for `/start-session`.

## WHEN TO USE

| Use /e2e-blockers | Prefer other |
|---|---|
| Clear e2e / local-proof failures and document leftover secrets/targets | `/` CI-only triage without e2e intent → `l9-ci-ops` |
| Need a session-start surface for remaining gates | Pure API route smoke → `l9-api-smoke-testing` |

## EXECUTION

1. Load and follow `.cursor-commands/skills/l9-e2e-blocker-resolution/SKILL.md` (or `~/.cursor-governance/skills/l9-e2e-blocker-resolution/SKILL.md`).
2. Obey its Authority Order, Compact Workflow, and validation checklist.
3. Do not invent secrets. Do not claim green e2e while external blockers remain.

## OUTPUT

Report: **Fixed** | **Remaining** | **Files** | **Operator next steps**.
