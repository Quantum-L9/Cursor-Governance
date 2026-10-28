<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [ci, policy, regression, governance]
status: active
/L9_META -->

# CI Policy Authoring

## Absolute rules

- NO code fixes
- NO refactors
- NO CI execution
- NO guessing intent
- DEFINES policy only

## Usage examples

```
/ci-policy "ban print() usage"
/ci-policy "no sync I/O in async code"
/ci-policy --from-incident INC-2026-01
```

## Chain

DEFINE RULE → SELECT MECHANISM → SCOPE TARGETS → REGISTER POLICY → REPORT → STOP

## Phase 1 — Define rule

Extract: rule statement, forbidden OR required pattern, rationale (1–2 lines). If vague → STOP.

## Phase 2 — Select mechanism (ONE only)

| Mechanism | Use when |
|-----------|----------|
| ruff rule | lintable syntax |
| semgrep rule | structural / security |
| pytest regression test | behavioral |
| grep gate | simple forbidden text |

No hybrid mechanisms.

## Phase 3 — Scope

Define include paths, file types, exclusions (tests, scripts).

## Phase 4 — Register

Add to CI config, lint config, or tests. Minimal surface; deterministic failure; clear error message. NO other CI changes.

## Phase 5 — Report (inline only)

```markdown
## CI POLICY ADDED

Rule: ...
Enforcement: ...
Scope: ...
Failure Message: ...
Status: Registered (not executed)
```

STOP after report.
