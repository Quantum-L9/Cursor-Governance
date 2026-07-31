<!-- L9_META
l9_schema: 1
parent: l9-e2e-blocker-resolution
layer: reference
role: discovery_protocol
tags: [e2e, discovery, package-json, workflows, verify]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Discovery — Canonical Proof Commands

## Purpose

Find this repo’s authoritative e2e / local-proof commands without hardcoding stack-specific script names.

## Search Order

1. User-supplied command or workflow name.
2. Root docs: `AGENTS.md`, `README*`, `docs/**` mentioning e2e / verify / local-proof / disposable.
3. Package scripts: `package.json` → `scripts` keys matching `(e2e|end-to-end|playwright|cypress|verify:.*e2e|test:e2e|site:test|local-proof)`.
4. Task runners: `Makefile`, `justfile` targets with the same patterns.
5. CI: `.github/workflows/*` job/step names matching e2e, disposable, local-proof, smoke.
6. Sibling verify chains: `verify:all`, `verify:launch-env`, unit suites — use only as **narrower** substitutes when full e2e is blocked and the user accepts local proof.

## Preference Ladder

| Preference | When |
|---|---|
| Local unit / contract tests | Always safe first signal |
| Local e2e / local-proof (no remote mutate) | Default proof path |
| CI workflow re-run (`gh run`) | When failure is CI-only |
| Disposable remote e2e (creates/uses throwaway GitHub/Vercel) | Only with explicit user OK + disposable-named targets |

## Record Before Running

| Field | Example |
|---|---|
| Command | `npm run site:test:e2e` |
| Source | `package.json#scripts` or workflow path |
| Requires secrets? | yes/no + secret **names** only |
| Mutates remote? | no / disposable / production (forbid unless explicit) |

## Fail Closed

If multiple candidates conflict, list them and ask which to run. Do not invent a script that is not defined in the repo.
