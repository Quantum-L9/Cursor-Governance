<!-- L9_META
l9_schema: 1
parent: l9-e2e-blocker-resolution
layer: reference
role: classification_protocol
tags: [e2e, blockers, classification, secrets, ci]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Blocker Classification

## Purpose

Route each failure to fix-in-repo, document-as-external, or out-of-scope.

## Classes

| Class | Meaning | Agent action |
|---|---|---|
| **fixable** | Code, lockfile, workflow flag, install script, permissions scope (`packages: read`), path bug | Patch + re-run |
| **external** | Missing/invalid secrets, org visibility, disposable targets, vendor API 401, Infisical not populated | Document in brief; do not invent values |
| **out-of-scope** | Other repos, infra not in workspace, human legal/compliance text | Name owner repo/team in brief |

## Signal → Class Heuristics

| Symptom | Likely class |
|---|---|
| `Cannot find module`, native binding missing after `--ignore-scripts` | fixable |
| `401` / `User not found` / `Invalid API key` from LLM/vendor | external (refresh secret) |
| `secrets.X` empty / workflow skips for missing env | external |
| Disposable e2e needs `GITHUB_SITE_TOKEN` / `VERCEL_TOKEN` unset | external |
| Wrong Node version / deprecated Actions runner warning only | fixable or defer (non-blocking) |
| Failure in dependency package unpublished | out-of-scope or external publish gate |
| Launch-env / disclaimer placeholders | external (operator-owned values) |

## Resolve Rules (fixable only)

- Smallest diff that addresses the failing step.
- Re-run the **same** command after the fix.
- Prefer CI/workflow corrections that preserve command semantics.
- Do not commit unless the user asks.

## External Rules

- Record: secret/var **name**, purpose, where to source, org vs repo vs `.env.local`, which workflow/script needs it.
- Never write secret values into docs, TODO, commits, or chat artifacts.
- If a secrets inventory doc already exists, extend or cross-link it rather than duplicating.

## Classification Table (required in brief)

```markdown
| Blocker | Class | Evidence | Action taken / needed |
|---|---|---|---|
| … | fixable \| external \| out-of-scope | command + excerpt | … |
```
