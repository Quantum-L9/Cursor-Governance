<!-- L9_META
l9_schema: 1
parent: l9-e2e-blocker-resolution
layer: reference
role: artifact_templates
tags: [e2e, brief, todo, session-reference, docs]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Brief and TODO Templates

## Purpose

Leave durable, session-start-visible artifacts for remaining external gates after in-repo fixes.

## Brief path

Prefer (first match that fits):

1. User-specified path
2. Existing `docs/e2e-blockers.md` or `docs/secrets-and-environment.md` when the topic is the same — **update in place**
3. New `docs/e2e-blockers.md`
4. Topic-specific `docs/ops/e2e-blockers-<slug>.md` when multiple unrelated briefs would collide

Create `docs/` or `docs/ops/` only if needed.

## Brief skeleton

```markdown
# E2E blockers — {repo or topic}

Evidence-backed remaining gates after in-repo fixes.
Do not commit secret values.

## Commands run

| Command | Result | Evidence |
|---|---|---|
| … | pass/fail | log excerpt or run URL |

## Fixed in-repo

- …

## Remaining blockers

| Name | Purpose | Source | Store (org/repo/local) | Consumers |
|---|---|---|---|---|
| … | … | … | … | workflow / script |

## Gap checklist

| Item | Status |
|---|---|
| … | present / missing / invalid |

## Operator next steps

1. …
```

## TODO.md session-reference entry

Prepend near the top of root `TODO.md` (after the title/intro if present). Create `TODO.md` if absent.

```markdown
## E2E blockers (session reference)

**Doc:** [`docs/e2e-blockers.md`](docs/e2e-blockers.md) — remaining external gates after
local/code fixes. Use at session start when wiring CI or disposable targets.
```

Adjust the link if the brief path differs. Keep the heading phrase **session reference** so `/start-session` GMP extraction and humans both spot it.

## Idempotency

On re-run: refresh the same brief path and the same TODO section (replace body under that heading). Do not add a second parallel “E2E blockers (session reference)” section.
