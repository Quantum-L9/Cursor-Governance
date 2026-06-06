---
name: l9-component-verification
description: Component audit, deterministic verify, and runtime probe (escalation ladder)
disable-model-invocation: true
---

---
name: audit-component
version: "1.0.0"
description: "Audit a component for export consistency, file wiring, and API instantiation"
auto_chain: ynp
dag: component-audit-v1
dag_file: .cursor-commands/workflows/dags/component_audit_dag.py
---

# /audit-component — Component Wiring Audit

**DAG-ENFORCED.** Execute the `component-audit-v1` DAG.

## Usage

```
/audit-component memory          # Audit a specific package
/audit-component core            # Audit core
/audit-component                 # Discover and pick highest-priority
```

## What It Does

1. **Level A** — Package export audit (`__all__` vs imports)
2. **Level B** — File-level wiring (consumers, tests, re-exports)
3. **Level C** — API instantiation (used symbols, missing APIs)

## Execution

```python
from .cursor-commands.workflows.dags import COMPONENT_AUDIT_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/component_audit_dag.py`
- **Script**: `tools/validation/audit_package_exports.py`
- **Guide**: `reports/COMPONENT_WIRING_AUDIT_GUIDE.md`
- **Confirm-Wiring**: `.cursor-commands/workflows/dags/confirm_wiring_dag.py`


name: verify-component
version: "2.1.0"
description: "Read-only verification of component correctness and wiring, including protected/kernel files. Diagnose only — NO edits."
auto_chain: none
---

# /verify-component — Deterministic Component Verification

## ROLE

You are Cursor, acting as an **L9 verification and enforcement agent**.

Your job is to **PROVE** that a component is:
- correctly defined
- correctly imported
- correctly wired
- correctly integrated into runtime and kernel layers

You do **not** assume correctness.  
You do **not** fix issues.  
You only report **evidence**.

---

## MISSION

Verify that a specified component is valid and properly wired by exhaustively checking:

- imports
- file existence
- symbol existence
- runtime import safety
- wiring into **protected/kernel files** (read-only)

This command is **diagnostic only**.

---

## AUTHORITY & LIMITS (CRITICAL)

### ✅ ALLOWED
- READ any file, including protected/kernel files
- TRACE wiring into protected files
- DIAGNOSE missing, partial, or incorrect wiring
- REPORT required actions

### ❌ FORBIDDEN
- Writing or editing code
- Adding imports
- Changing wiring
- Modifying protected files
- Auto-fixing anything

**If a fix is required in a protected file → ESCALATE TO `/gmp`.**

---

## SCOPE

- Files explicitly provided by the user
- Any files they import (directly or indirectly)
- All **protected files**, for wiring diagnosis only:

```

core/agents/executor.py
runtime/websocket_orchestrator.py
memory/substrate_service.py
docker-compose.yml
core/singleton_registry.py

````

---

## VERIFICATION PROTOCOL (MANDATORY, NO SKIPS)

### STEP 1 — Enumerate Imports (STATIC)

For each target file:
- Extract **all** `import X` and `from X import Y` statements

Produce a table:
| Source File | Module | Symbol(s) |
|------------|--------|-----------|

---

### STEP 2 — Verify Module Paths Exist (FILESYSTEM)

For every imported module:
- Confirm the file exists
- Resolve package directories and `__init__.py` where applicable

Report:
- FOUND ✅
- MISSING ❌ (HARD FAILURE → STOP)

---

### STEP 3 — Verify Symbols Exist (SOURCE-LEVEL)

For every imported symbol:
- Locate its definition
- Confirm correct name and type (function / class / async)

Report:
- FOUND (file + line) ✅
- NOT FOUND ❌ (HARD FAILURE → STOP)

---

### STEP 4 — Import-Safety Scan (SEMANTIC)

Scan verified files for import-time hazards:
- Python 3.12 annotation evaluation issues
- Top-level side effects
- Circular import risks
- Runtime operations at import time (DB, network, I/O)

Classify:
- SAFE ✅
- UNSAFE ❌ (with exact reason)

---

### STEP 5 — Runtime Import Proof (AUTHORITATIVE)

Construct and report a **real Python import test** that mirrors runtime behavior.

Example:
```bash
python3 -c "
from api.startup_guard import ensure_bootstrap
from core.agents.executor import AgentExecutor
print('IMPORT OK')
"
````

If this would fail → HARD FAILURE.

---

### STEP 6 — Protected File Wiring Diagnosis (READ-ONLY)

For the specified component `{X}`, inspect protected files and determine:

* Is `{X}` imported?
* Is `{X}` injected (setter / constructor / registry)?
* Is wiring partial, implicit, or bypassing setters?
* Is it behind feature flags or guards?
* Does it affect execution order or governance flow?

Produce a **Protected Wiring Matrix**:

```markdown
## 🔍 Protected Wiring Diagnosis — {Component}

| File | Status | Evidence | Action Needed |
|------|--------|----------|---------------|
| core/agents/executor.py | ❌ Missing | No setter call | GMP REQUIRED |
| api/server.py | ⚠ Partial | Direct attr set | GMP RECOMMENDED |
| core/singleton_registry.py | ✅ OK | Registered | None |
```

---

## ESCALATION RULE (MANDATORY)

If **any** of the following are true:

* Protected file requires change
* Kernel execution behavior is affected
* Tool dispatch or governance flow is involved
* Wiring is incomplete or unsafe

Then the output **MUST END WITH**:

```markdown
⛔ Kernel or protected-file wiring required.
→ Generate a `/gmp` plan before making any changes.
```

No auto-chain.
No fixes.
No exceptions.

---

## OUTPUT FORMAT (STRICT)

* Evidence tables only
* File paths + line numbers
* Clear PASS / FAIL / PARTIAL
* Explicit escalation notice if applicable

---

## PURPOSE STATEMENT

`/verify-component` is an **X-ray**, not a scalpel.

It exists to:

* prevent silent kernel drift
* force explicit governance
* ensure wiring correctness before execution

--- End Command ---

---
name: probe
version: "1.1.0"
description: "Import & wiring verification (SAFE)"
before_chain: rules
auto_chain: ynp
---

# /probe — Import & Wiring Verification (SAFE)

## Purpose

Verify that code loads, wires, and registers correctly in the real runtime.

## Risk Level

- 🟢 Zero mutation
- 🟢 No DB writes
- 🟢 No side effects beyond imports

## Usage

```
/probe memory.substrate_repository
/probe core.tools.tool_embeddings
/probe core.agents.bootstrap.orchestrator
```

## What Cursor Does

1. Enters the running container
2. Imports the module
3. Reports:
   - Import success
   - Registry activity
   - Dependency failures
   - Circular import crashes

## Execution (Cursor-internal)

```bash
docker compose exec -T l9-api python - <<EOF
import importlib
importlib.import_module("{TARGET}")
print("IMPORT OK:", "{TARGET}")
EOF
```

## Output Format

```markdown
## 🔎 PROBE: memory.substrate_repository

**Status:** ✅ PASS

**Verified:**
- Import path resolves
- Dependencies available
- No runtime import crash
- Registry wiring executed

**Side effects:**
- None
```

## When to Use /probe

- After refactors
- After dependency changes
- When Cursor says "should work"
- Before enabling traffic
- Before deeper tests
