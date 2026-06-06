---
name: l9-ci-ops
description: CI/CD operations (status, fix, gates) and CI policy authoring
disable-model-invocation: true
---

> For multi-job failures, load [references/parallel-ci-triage.md](references/parallel-ci-triage.md) — split independent failing jobs across parallel subagents.

---
name: ci
version: "1.1.0"
description: "CI/CD pipeline operations"
before_chain: rules
auto_chain: ynp
---

# /ci — CI/CD Operations

## USAGE

```
/ci status              # Check pipeline status
/ci run                 # Trigger CI run
/ci fix                 # Fix CI failures
/ci gates               # List required gates
```

---

## GATES

| Gate | Command | Required |
|------|---------|----------|
| Lint | `ruff check .` | ✅ |
| Types | `mypy .` | ✅ |
| Tests | `pytest` | ✅ |
| Security | `semgrep` | ✅ |
| Build | `docker build` | For deploy |

---

## FIX WORKFLOW

### 1. IDENTIFY FAILURES

```bash
gh run list --limit 5
gh run view {id} --log-failed
```

### 2. CATEGORIZE

| Type | Fix |
|------|-----|
| Lint | `ruff check --fix` |
| Type | Fix annotations |
| Test | Fix code or test |
| Security | Address finding |

### 3. FIX & VERIFY

```bash
ruff check --fix .
pytest tests/ -v
git add . && git commit -m "fix: CI failures"
```

---

## OUTPUT

```markdown
## 🔄 CI STATUS

| Gate | Status | Details |
|------|--------|---------|
| Lint | ✅ | 0 errors |
| Tests | ❌ | 2 failed |

### Failures
| Test | Error |
|------|-------|
| test_x | AssertionError |

### Fix Plan
1. {action}
```

--- End Command ---

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
