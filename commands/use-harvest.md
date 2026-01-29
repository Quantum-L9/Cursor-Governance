name: harvest-use
version: "2.0.0"
description: "Harvest, deploy, and wire code into L9 deterministically using plan + file ops only (NO manual writing)"
auto_chain: ynp

# /harvest-use — Deterministic Harvest Deployment + Wiring

ULTRA-CRITICAL GOVERNANCE RULES

1. NO MANUAL CODE WRITING — EVER
2. NO TYPING CODE — USE cp / sed / cat ONLY
3. NO REWRITES — ONLY COPY OR INJECT EXISTING CODE
4. NO INFERENCE — ALL ACTIONS MUST BE IN PLAN
5. WIRING IS MECHANICAL, NOT CREATIVE
6. VIOLATION = GOVERNANCE FAILURE

---

PURPOSE

Execute harvested code into the L9 repo and wire it correctly using a plan document,
without spending tokens recreating code or relying on agent inference.

This command:
- deploys harvested files
- injects diffs
- performs explicit wiring
- validates structure
- reports
- STOPS

---

USAGE

/harvest-use @plan.md @harvested-files/
/harvest-use @Plan.md @current_work/01-25-2026/harvested-files

---

INPUTS

| Input | Description |
|------|-------------|
| @plan.md | Authoritative deployment + wiring plan |
| @harvested-files/ | Directory of harvested source files |

---

CHAIN

/harvest-use
→ PHASE -1: HARVESTABILITY ANALYSIS
→ PHASE 0: PARSE PLAN
→ PHASE 1: BASELINE
→ PHASE 2: EXECUTE CREATES
→ PHASE 3: EXECUTE INJECTS
→ PHASE 4: EXECUTE WIRING
→ PHASE 5: VALIDATE
→ PHASE 6: REPORT
→ STOP

---

PHASE -1: HARVESTABILITY ANALYSIS (READ-ONLY)

Objective:
Confirm harvested files are suitable for mechanical deployment.

For EACH harvested file:
- verify file is complete (not partial snippets unless marked DIFF)
- verify no placeholders (TODO, FILL_ME, ???)
- classify file type:
  - FULL_FILE
  - DIFF_IMPORT
  - DIFF_BLOCK
  - DIFF_FUNCTION
  - DIFF_CLASS

If any file:
- requires synthesis
- requires interpretation
- contains prose instead of code

→ STOP → report “NOT HARVESTABLE”

---

PHASE 0: PARSE PLAN (AUTHORITATIVE)

Read plan.md and extract ALL actions.

Required sections in plan:
- CREATE
- INJECT
- WIRE

Produce a unified execution table:

| # | Phase | Type | Source (Harvested) | Target | Action | Line/Anchor |
|---|------|------|-------------------|--------|--------|-------------|
| 1 | CREATE | File | service.py | services/service.py | cp | — |
| 2 | INJECT | Diff | diff_imports.py | api/server.py | sed | after imports |
| 3 | WIRE | Import | diff_wire_import.py | api/server.py | sed | after imports |
| 4 | WIRE | Register | diff_router.py | api/server.py | sed | router mount |

If ANY step is ambiguous → STOP and ask.

---

PHASE 1: BASELINE (FAIL FAST)

For MODIFY / INJECT / WIRE targets:
- verify target file exists

For CREATE targets:
- verify parent directory exists

Commands:
ls -la target/file.py
ls -la target/dir/

Failure → STOP → report.

---

PHASE 2: EXECUTE CREATES (FILES ONLY)

For each CREATE:

HARVEST="/path/to/harvested-files"

cp "$HARVEST/source.py" "target/path/file.py"

Verify:
ls -la target/path/file.py
wc -l target/path/file.py

---

PHASE 3: EXECUTE INJECTS (CODE BLOCKS)

All injects MUST come from harvested diff files.

Supported methods ONLY:

A) Insert after line N
sed -i '' 'Nr /tmp/inject.txt' target/file.py

B) Replace lines N-M
sed -i '' 'N,Md' target/file.py
sed -i '' 'N-1r /tmp/replacement.txt' target/file.py

C) Insert before pattern
sed -i '' '/PATTERN/r /tmp/inject.txt' target/file.py

Procedure:
cat "$HARVEST/diff_x.py" > /tmp/inject.txt
run sed
verify via grep

---

PHASE 4: EXECUTE WIRING (MECHANICAL)

WIRING IS JUST INJECTION WITH STRICT INTENT.

Allowed wiring actions:
- add import
- add registration call
- add router mount
- add registry entry

All wiring MUST:
- come from harvested diff files
- be listed explicitly in plan under WIRE

Examples:
- import injection
- app.include_router(...)
- registry.register(...)

NO creative wiring.
NO guessing locations.

Verification:
grep -n "expected_symbol" target/file.py

---

PHASE 5: VALIDATE (STRUCTURAL)

Run ALL:

python3 -m py_compile file1.py file2.py
ls -la target/files
grep -n "expected_pattern" target/file.py

If ANY failure → STOP → report (DO NOT FIX).

---

PHASE 6: REPORT (INLINE ONLY)

Output in workspace chat:

## /harvest-use Complete

Plan: plan.md
Harvest source: harvested-files/

### Execution Summary
| Phase | Actions | Status |
|------|--------|--------|
| CREATE | N | ✅ |
| INJECT | N | ✅ |
| WIRE | N | ✅ |

### Files Touched
- path/file.py
- path/file2.py

### Validation
- py_compile: ✅ / ❌
- patterns: ✅ / ❌

### Next Steps
- run tests
- commit
- deploy

---

STOP CONDITION (ABSOLUTE)

After REPORT:
- STOP
- Do NOT refactor
- Do NOT improve
- Do NOT re-run wiring
- Do NOT infer fixes

---

PROTECTED FILES

If ANY action targets:

core/agents/executor.py
runtime/websocket_orchestrator.py
memory/substrate_service.py
docker-compose.yml
Dockerfile*

→ STOP → recommend /gmp

---

ANTI-PATTERNS (STRICT)

❌ typing code
❌ recreating logic
❌ improving harvested code
❌ “fixing while here”
❌ guessing injection points

✅ copy
✅ inject
✅ validate
✅ report
✅ stop

---

CORE PRINCIPLE

Harvest once.
Reuse many times.
Tokens are for reasoning — not retyping code.
