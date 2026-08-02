name: ci-policy
version: "1.0.0"
description: "Add regression-prevention rules to CI — encode patterns as enforceable gates"
auto_chain: n

# /ci-policy — CI Governance & Regression Prevention

RULES (ABSOLUTE)

- NO code fixes
- NO refactors
- NO CI execution
- NO guessing intent
- This command DEFINES policy only

---

USAGE

/ci-policy "ban print() usage"
/ci-policy "no sync I/O in async code"
/ci-policy "require timeouts on httpx calls"
/ci-policy --from-incident INC-2026-01

---

PURPOSE

Convert an architectural rule or learned constraint into:
- a CI-enforced gate
- a permanent regression blocker

Once added, CI will fail if the rule is violated.

---

CHAIN

/ci-policy
→ DEFINE RULE
→ SELECT ENFORCEMENT MECHANISM
→ SCOPE TARGETS
→ REGISTER POLICY
→ REPORT
→ STOP

---

PHASE 1 — DEFINE RULE (EXPLICIT)

Extract:
- Rule statement (plain language)
- Forbidden pattern OR required pattern
- Rationale (1–2 lines, factual)

Example:
Rule: "No print() in runtime code"
Pattern: `print(`
Scope: `api/, core/, runtime/`

If rule is vague → STOP.

---

PHASE 2 — SELECT ENFORCEMENT MECHANISM

Choose ONE:

| Mechanism | Use When |
|---------|----------|
| ruff rule | lintable syntax |
| custom ruff plugin | repeated pattern |
| semgrep rule | structural / security |
| pytest regression test | behavioral |
| grep gate | simple forbidden text |

No hybrid mechanisms.

---

PHASE 3 — SCOPE TARGETS

Define:
- directories
- file types
- exclusions (tests, scripts, etc.)

Example:
- include: `api/**.py`
- exclude: `tests/**`

---

PHASE 4 — REGISTER POLICY

Add rule to:
- CI config
- lint config
- security ruleset
- or tests

Rules:
- Minimal surface area
- Deterministic failure
- Clear error message

NO other CI changes allowed.

---

PHASE 5 — REPORT (INLINE ONLY)

## CI POLICY ADDED

Rule:
“No print() in runtime code”

Enforcement:
ruff custom rule

Scope:
api/, core/, runtime/

Failure Message:
“print() is forbidden in runtime code — use logger”

Status:
Registered (not executed)

---

STOP CONDITION

After report:
- STOP
- CI will enforce on next run
