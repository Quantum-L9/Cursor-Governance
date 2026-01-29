name: wire
version: "10.2.0"
description: "Structural wiring repair with semantic guards. Fix refs, exports, and registrations — NOT a correctness proof."
auto_chain: ynp

# /wire — Component Wiring (Canonical)

IMPORTANT
/ wire is a STRUCTURAL REPAIR command.
It fixes references and exports.
It does NOT prove runtime correctness.
Runtime proof REQUIRES /verify-component.

---

USAGE

/wire path/to/component.py
/wire ModuleName

---

CHAIN

/wire
→ DISCOVERY
→ ANALYSIS
→ PLAN
→ EXECUTE
→ VALIDATE
→ RE-DISCOVERY
→ REPORT

---

PHASE 1 — DISCOVERY (EXHAUSTIVE)

Find ALL references to the target component.

Commands:
rg "{component}" --type py -n
rg "from .*{component}|import .*{component}" --type py -n

Collect EVERY occurrence.
No sampling. No assumptions.

Output table:
| File | Line | Ref Type | Status |
|------|------|----------|--------|
| service.py | 12 | import | ❌ |
| loader.py | 41 | usage | ❌ |

If no references are found → STOP → report “unused component”.

---

PHASE 2 — ANALYSIS (STRUCTURAL + CONTEXT)

Classify the component:

- module
- class
- function
- service
- route
- tool
- config

Apply required checks:

| Type | Required Structure |
|-----|--------------------|
| Module | file exists, __init__.py exports |
| Class | imported, instantiated, reachable |
| Service | registered, lifecycle-safe |
| Route | exported, mounted |
| Tool | registered, discoverable |
| Config | loader exists, path valid |

If classification is ambiguous → STOP → request clarification.

---

PHASE 3 — PLAN (MINIMAL + EXPLICIT)

Create a numbered, surgical plan.

Rules:
- One action = one edit
- No speculative changes
- No batching

Plan table:
| # | Action | File | Change |
|---|--------|------|--------|
| W1 | Fix import path | service.py:12 | old → new |
| W2 | Add export | module/__init__.py | from .x import Y |
| W3 | Register component | registry.py | add Y |

If plan requires refactor → STOP → escalate to /gmp.

---

PHASE 4 — EXECUTE (SURGICAL ONLY)

Constraints:
- StrReplace / Insert only
- Preserve formatting
- Preserve logic
- No rewrites

If execution would:
- change behavior
- add side effects
- restructure logic

→ STOP → escalate to /gmp.

---

PHASE 5 — VALIDATE (LOCAL STRUCTURE)

Run ALL:

python3 -m py_compile {modified_files}
python3 -c "from {package} import {component}"
pytest tests/{package}/ -v

Purpose:
- syntax safety
- obvious import correctness
- wiring-level test coverage

This does NOT prove runtime safety.

---

PHASE 6 — RE-DISCOVERY (STRUCTURAL CONFIRMATION)

Repeat PHASE 1.

Confirm:
- all previous ❌ refs are now ✅
- no new broken refs introduced
- no duplicate or shadowed imports

If ANY unresolved reference remains → FAIL.

---

POST-CONDITION (MANDATORY)

After /wire completes, you MUST run:

/verify-component {component}

If /verify-component fails:
/wire is INCOMPLETE.
Do NOT claim success.

---

SEMANTIC REFUSALS (HARD STOPS)

STOP IMMEDIATELY if wiring would:

- introduce import-time side effects
- cause DB / network access at import time
- wire sync code into async-only paths
- violate bootstrap vs runtime boundaries
- mutate global state at import
- rely on implicit side effects

Escalate to /gmp with evidence.

---

PROTECTED FILES (DO NOT TOUCH)

If changes are required in ANY of these → STOP → /gmp:

- core/agents/executor.py
- runtime/websocket_orchestrator.py
- memory/substrate_service.py
- any Dockerfile
- docker-compose.yml

---

OUTPUT FORMAT

## 🔌 WIRE: {component}

| Metric | Value |
|------|-------|
| References found | N |
| References fixed | N |
| Exports added | N |
| Files modified | N |

### Actions
| # | Action | File | Status |
|---|--------|------|--------|
| W1 | Fix import | service.py | ✅ |

### Validation
| Check | Status |
|------|--------|
| py_compile | ✅ |
| import test | ✅ |
| tests | ✅ |

### Post-Condition
/verify-component REQUIRED

---

SUCCESS CRITERIA

/ wire may declare STRUCTURAL SUCCESS only if:

- all references resolve
- no broken imports remain
- no protected files touched
- no semantic refusals triggered

Runtime correctness is explicitly OUT OF SCOPE.

---

ENFORCEMENT

If unsure → STOP.
If ambiguous → STOP.
If unsafe → STOP.

Evidence over confidence.
