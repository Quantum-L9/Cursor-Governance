name: gmp
version: "5.0.0"
description: "Governance Managed Process — constitutional execution for semantic, lifecycle, or protected changes"
auto_chain: ynp

# /gmp — Governance Managed Process (Canonical)

NON-NEGOTIABLE PRINCIPLES

1. /gmp is for SEMANTIC change only
2. If code can be harvested → /gmp is NOT allowed
3. No scope drift, no side quests, no cleanup
4. Evidence > intuition
5. STOP is a valid outcome

---

USAGE

/gmp "explicit task description"
/gmp --scope-file path/to/scope.yaml

If task description is vague → STOP → request clarification.

---

POSITION IN TOOLCHAIN

IDEA
 ↓
/refactor-sweep      (risk + eligibility)
 ↓
Decision
 ├─ Mechanical → /harvest-use
 ├─ Structural → /wire
 └─ Semantic / lifecycle → /gmp

/gmp is the FINAL gate.

---

CHAIN

/gmp
→ PHASE 0: SCOPE LOCK
→ PHASE 1: EVIDENCE INTAKE (🧠 MEMORY READ FIRST)
→ PHASE 2: BASELINE VERIFICATION
→ PHASE 3: SEMANTIC IMPLEMENTATION
→ PHASE 4: ENFORCEMENT
→ PHASE 5: VALIDATION
→ PHASE 5.5: 🧠 MEMORY WRITE
→ PHASE 6: FINALIZE + GMP REPORT
→ STOP → /ynp

---

PHASE 0 — SCOPE LOCK (ABSOLUTE)

Lock WHAT will change and NOTHING else.

Required output:

## GMP SCOPE LOCK

GMP ID: GMP-XXX
Tier: KERNEL | RUNTIME | INFRA | UX

TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|

FILE BUDGET
- MAY: files in TODO only
- MAY NOT: everything else

⏸️ Awaiting explicit CONFIRM

NO CONFIRM → NO EXECUTION

---

PHASE 1 — EVIDENCE INTAKE (READ-ONLY)

🧠 MEMORY READ (MANDATORY FIRST STEP)

Before ANY file reading, search L9 memory for context:

```bash
# Search for related work, patterns, lessons
python3 agents/cursor/cursor_memory_client.py search "[task keywords]"
python3 agents/cursor/cursor_memory_client.py search "lessons errors [component]"
python3 agents/cursor/cursor_memory_client.py search "[domain] patterns"
```

Output format:

## 🧠 MEMORY CONTEXT

### Related Work Found
- [prior GMP or task if any]

### Relevant Patterns
- [patterns from memory]

### Lessons to Apply
- [lessons/errors to avoid]

📍 Proceeding with evidence collection...

---

Then collect:
- relevant files
- prior patterns
- harvested artifacts (if provided)

RULES
- NO transformation
- NO rewriting
- NO synthesis

If equivalent code already exists → STOP → recommend /harvest-use

---

PHASE 2 — BASELINE VERIFICATION

Verify:
- files exist
- line ranges are correct
- imports resolve
- assumptions hold

Any failure → STOP → return to Phase 0

---

PHASE 3 — SEMANTIC IMPLEMENTATION

Allowed actions ONLY:
- behavior change explicitly described in TODO
- lifecycle change explicitly described
- contract change explicitly described

FORBIDDEN:
- reformatting
- renaming
- cleanup
- “while I’m here”
- mechanical changes suitable for harvest

All edits must map 1:1 to TODO items.

---

PHASE 4 — ENFORCEMENT

Add:
- guards
- assertions
- fail-fast checks
ONLY if explicitly required by TODO.

No proactive hardening.

---

PHASE 5 — VALIDATION (FAIL-FAST)

Run:
- python3 -m py_compile
- ruff (if applicable)
- tests (if applicable)

RULE
- ANY failure → STOP
- DO NOT patch forward
- Return failure with evidence

---

PHASE 5.5 — MEMORY WRITE (MANDATORY BEFORE FINALIZE)

🧠 MEMORY WRITE (REQUIRED)

Before finalizing, write learnings to L9 memory:

```bash
# Write what was accomplished (include tags in content)
python3 agents/cursor/cursor_memory_client.py write "GMP-XXX: [summary of changes]. Tags: gmp, [component]" --kind lesson

# Write any patterns discovered
python3 agents/cursor/cursor_memory_client.py write "[pattern discovered]. Tags: [domain], pattern" --kind pattern

# Write any errors/fixes for future reference  
python3 agents/cursor/cursor_memory_client.py write "[error encountered and fix]. Tags: error, [component]" --kind lesson
```

Output format:

## 🧠 MEMORY WRITTEN

- ✅ GMP summary saved
- ✅ Patterns saved (if any)
- ✅ Lessons saved (if any)

📍 Proceeding to finalize...

---

PHASE 6 — FINALIZE (INLINE ALWAYS)

Inline report:

## GMP-XXX COMPLETE

Tier: {tier}
Status: PASS | FAIL

TODO EXECUTION
| T# | File | Status |
|----|------|--------|

VALIDATION
| Check | Result |
|------|--------|

NEXT STEP
/ynp

Scripted report generation is OPTIONAL and ON-DEMAND only.

---

PROTECTED FILES (HARD GATE)

runtime/websocket_orchestrator.py
core/agents/executor.py
memory/substrate_service.py
docker-compose.yml
core/singleton_registry.py

→ Require KERNEL-tier GMP with explicit approval

---

STOP CONDITIONS (ENFORCED)

| Condition | Action |
|----------|--------|
| Mechanical change detected | STOP → /harvest-use |
| TODO ambiguous | STOP |
| Scope drift | STOP |
| Validation failure | STOP |
| Protected file without approval | STOP |

---

CORE TRUTH

/gmp is expensive by design.
If it feels heavy, that means it’s working.
