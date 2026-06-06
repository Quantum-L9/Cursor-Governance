---
name: l9-code-maintenance
description: Lint-fix, migrate, clean/compress, consolidate, and refactor operations (sweep + DAG workflow)
disable-model-invocation: true
---

---
name: lint-fix
version: "1.0.0"
description: "TRIGGER ONLY — Invokes lint_fix_executor.py for systematic lint fixes"
auto_chain: ynp
dag_executor: .cursor-commands/workflows/lint_fix_executor.py
---

# /lint-fix — Systematic Lint Fixing (v1.0.0)

## THIS IS A TRIGGER ONLY

`/lint-fix` invokes the Lint-Fix Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor-commands/workflows/lint_fix_executor.py
python3 .cursor-commands/workflows/lint_fix_executor.py --only B904 N811
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  SCAN-ERRORS      │ Run ruff to find all errors        │
├─────────────────────────────────────────────────────────┤
│  CATEGORIZE       │ Sort into AUTO/SEMI/MANUAL         │
├─────────────────────────────────────────────────────────┤
│  APPLY-AUTO       │ ruff --fix for auto-fixable        │
├─────────────────────────────────────────────────────────┤
│  APPLY-SEMI       │ sed patterns for known patterns    │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile on modified files       │
├─────────────────────────────────────────────────────────┤
│  RESCAN           │ Count remaining errors             │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **Category-aware** — Handles AUTO, SEMI, MANUAL differently
- **B904 pattern** — Adds `from e` to raises in except blocks
- **Safe validation** — Ensures fixes don't break syntax
- **Auto-report** — Uses canonical report generator

## FIX CATEGORIES

| Category | How | Examples |
|----------|-----|----------|
| AUTO | `ruff --fix` | I001, I002, F401, UP*, W*, E* |
| SEMI | sed patterns | B904 (raise from) |
| MANUAL | Report only | Complex issues |

## USAGE

```bash
# Fix all lint errors
python3 .cursor-commands/workflows/lint_fix_executor.py

# Fix only specific codes
python3 .cursor-commands/workflows/lint_fix_executor.py --only B904 N811

# Check status
python3 .cursor-commands/workflows/lint_fix_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/lint_fix_executor.py --resume
```

## OUTPUT

Produces:
- Terminal progress showing before/after counts
- GMP report with fix statistics
- Local commit (no push)

## EXAMPLE

```
Found 189 lint errors:
| Code | Count |
|------|-------|
| B904 |   186 |
| N811 |     3 |

Results:
  Before: 189 errors
  After:  0 errors
  Fixed:  189 errors
```

---
name: migrate
version: "1.0.0"
description: "TRIGGER ONLY — Invokes migrate_executor.py for autonomous code migration"
auto_chain: ynp
dag_executor: .cursor-commands/workflows/migrate_executor.py
---

In plain English: 
When you need to rename something across the entire codebase (a function name, import path, class name, variable, etc.), /migrate finds every occurrence using rg, replaces them all using sed, validates the changes compile, and commits locally.

When to use it: 
Use /migrate when you have a pattern like old_name that needs to become new_name across many files — function renames, import path changes, class renames, etc.

Example:
python3 .cursor-commands/workflows/migrate_executor.py "from core.old_module" "from core.new_module"

This will find all 47 files with that import, sed-replace them all, validate with py_compile, and commit (no push).

----

# /migrate — Code Migration (v1.0.0)

## THIS IS A TRIGGER ONLY

`/migrate` invokes the Migrate Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor-commands/workflows/migrate_executor.py "old_pattern" "new_pattern"
```

## WHAT THE DAG DOES (FULLY AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  INDEX-ANALYSIS   │ Find ALL occurrences with rg       │
├─────────────────────────────────────────────────────────┤
│  PATTERN-EXTRACT  │ Analyze migration type             │
├─────────────────────────────────────────────────────────┤
│  BATCH-GENERATE   │ Group changes by file              │
├─────────────────────────────────────────────────────────┤
│  APPLY-CHANGES    │ sed/cp ONLY (NO manual rewrite)    │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile + import test           │
├─────────────────────────────────────────────────────────┤
│  WIRE-REFS        │ Update dependent imports           │
├─────────────────────────────────────────────────────────┤
│  CONFIRM-WIRING   │ Verify old pattern removed         │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **sed-based** — Uses sed for replacements, NOT manual rewriting
- **Protected file awareness** — Warns but continues
- **Auto-wiring** — Updates dependent imports
- **Auto-report** — Uses canonical report generator
- **Safe commit** — Commits locally, does NOT push

## USAGE

```bash
# Simple replacement
python3 .cursor-commands/workflows/migrate_executor.py "old_name" "new_name"

# Import migration
python3 .cursor-commands/workflows/migrate_executor.py "from old.module" "from new.module"

# Function rename
python3 .cursor-commands/workflows/migrate_executor.py "old_function(" "new_function("

# Check status
python3 .cursor-commands/workflows/migrate_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/migrate_executor.py --resume

# Reset state
python3 .cursor-commands/workflows/migrate_executor.py --reset
```

## STATE FILE

Execution state is persisted to `.migrate_executor_state.json`

If interrupted, resume with `--resume`.

## KEY PRINCIPLE

**sed, NOT manual rewriting.**

The executor uses `sed -i` for all replacements. This ensures:
- Exact pattern matching
- No accidental modifications
- Reproducible results
- Audit trail in commit

## OUTPUT

The executor produces:
1. Terminal progress for each step
2. GMP report at `reports/GMP-Report-*.md`
3. Local commit (no push)

## ENFORCEMENT

The DAG is MANDATORY. The slash command is just a trigger.

All step ordering, validation, and reporting is handled by the executor.

---
name: clean_compress
version: "1.0.0"
description: "Clean and compress code/files"
auto_chain: ynp
---

# /clean_compress — Code Cleanup

## WHAT IT DOES

Clean and compress code:

1. Remove dead code
2. Remove unused imports
3. Compress verbose patterns
4. Standardize formatting

---

## EXECUTION

### 1. FIND DEAD CODE

```bash
vulture . --min-confidence 80
```

### 2. FIND UNUSED IMPORTS

```bash
ruff check --select F401 .
```

### 3. AUTO-FIX

```bash
ruff check --fix .
```

### 4. FORMAT

```bash
ruff format .
```

---

## CLEANUP TARGETS

| Target | Tool |
|--------|------|
| Dead code | vulture |
| Unused imports | ruff F401 |
| Formatting | ruff format |
| Type stubs | ruff |

---

## OUTPUT

```markdown
## 🧹 CLEANUP: {scope}

### Found
| Issue | Count |
|-------|-------|
| Dead code | N |
| Unused imports | N |
| Format issues | N |

### Fixed
| Fix | Files |
|-----|-------|
| Imports removed | N |
| Formatted | N |

### Remaining (manual)
| Issue | Location |
|-------|----------|
```

→ **Auto-chains to /ynp**

--- End Command ---

---
name: consolidate
version: "1.1.0"
description: "Consolidate scattered code/files"
before_chain: rules
auto_chain: ynp
---

# /consolidate — Code Consolidation

## WHAT IT DOES

Consolidate scattered implementations:

1. Find duplicates
2. Identify common patterns
3. Extract to shared module
4. Update references

---

## EXECUTION

### 1. FIND DUPLICATES

```bash
# Find similar code
rg "{pattern}" --type py -l
```

### 2. ANALYZE

| File | Implementation | Lines |
|------|----------------|-------|
| a.py | version 1 | 20-40 |
| b.py | version 2 | 30-50 |

### 3. CONSOLIDATE

```markdown
## Consolidation Plan

**Target:** shared/{module}.py
**Source Files:** {list}
**Action:** Extract common code

| # | From | To | Lines |
|---|------|-----|-------|
| 1 | a.py:20-40 | shared/module.py | new |
| 2 | b.py:30-50 | import from shared | replace |
```

### 4. EXECUTE

Via `/gmp`:
- Create shared module
- Update imports
- Remove duplicates
- Add tests

---

## OUTPUT

```markdown
## 📦 CONSOLIDATE: {pattern}

### Duplicates Found
| File | Lines | Similarity |
|------|-------|------------|

### Plan
**Consolidate to:** {target}
**Files affected:** {count}

### TODO (for /gmp)
| # | Action | File |
|---|--------|------|
```

→ **Auto-chains to /ynp**

--- End Command ---

---

<!-- migrated-from: commands/refactor-sweep.md -->

name: refactor-sweep
version: "2.0.0"
description: "Deterministic refactor impact analysis and execution gating (NO code changes)"
auto_chain: gmp

# /refactor-sweep — Deterministic Refactor Impact Sweep

NON-NEGOTIABLE
- READ-ONLY
- NO code modification
- NO rewriting
- NO automatic fixes
- This command ANALYZES, it does NOT act

---

PURPOSE

Determine whether a proposed refactor is:
1. Safe mechanical change
2. Harvest/use eligible
3. GMP-required (high risk)
4. Architecturally forbidden

This command exists to PREVENT sloppy refactors.

---

USAGE

/refactor-sweep "rename foo to bar"
/refactor-sweep "replace print with logger"
/refactor-sweep "add timeout to httpx calls"

Input MUST describe:
- intent
- scope
- transformation rule

If intent is vague → STOP → ask clarification.

---

CHAIN

/refactor-sweep
→ DISCOVERY
→ CLASSIFICATION
→ IMPACT ANALYSIS
→ GOVERNANCE DECISION
→ REPORT
→ STOP

---

PHASE 1 — DISCOVERY (EXHAUSTIVE)

Locate ALL instances related to the refactor intent.

Commands:
rg "{primary_pattern}" --type py -n

Output table:
| File | Line | Match | Context |
|------|------|-------|---------|
| a.py | 20 | foo() | function call |
| b.py | 35 | foo | attribute |

If zero matches → STOP → report “no-op”.

---

PHASE 2 — CLASSIFICATION (L9 LAYERING)

For EACH file, classify:

| File | Layer | Domain |
|------|------|--------|
| api/x.py | runtime | API |
| bootstrap/y.py | bootstrap | init |
| memory/z.py | substrate | memory |

Flags:
- bootstrap code
- lifecycle code
- async boundary code
- protected files

---

PHASE 3 — IMPACT ANALYSIS (DETERMINISTIC)

For EACH instance, assess:

| Dimension | Result |
|---------|--------|
| Mechanical (sed-safe) | YES / NO |
| Requires logic change | YES / NO |
| Async boundary affected | YES / NO |
| Import graph affected | YES / NO |
| Public contract change | YES / NO |

Rules:
- If ANY instance is NOT mechanical → mark ENTIRE sweep as NON-MECHANICAL
- If ANY protected file involved → GMP REQUIRED

---

PHASE 4 — GOVERNANCE DECISION

Determine execution path:

| Outcome | Action |
|------|--------|
| All mechanical, no protected files | Eligible for /harvest-use |
| Mixed mechanical + semantic | GMP REQUIRED |
| Lifecycle / bootstrap impact | GMP REQUIRED |
| Cross-layer violation | FORBIDDEN |

No gray areas.
No partial approvals.

---

PHASE 5 — REPORT (INLINE ONLY)

Report in workspace chat:

## 🔍 REFACTOR SWEEP REPORT

**Intent:** rename foo → bar

### Summary
| Metric | Value |
|------|------|
| Files affected | N |
| Instances found | N |
| Layers touched | api, runtime |
| Protected files | none |

### Impact Classification
- Mechanical only: ✅
- Async boundary affected: ❌
- Import graph change: ❌

### Governance Decision
✅ Eligible for /harvest-use  
❌ Direct refactor NOT permitted  
❌ Manual edits NOT permitted

### Next Step
Run:
`/harvest-plan` → `/harvest-use`
or
`/gmp` (if required)

---

STOP CONDITION

After REPORT:
- STOP
- Do NOT refactor
- Do NOT write code
- Do NOT auto-chain

---

ANTI-PATTERNS

❌ rewriting code
❌ “small fixes while here”
❌ skipping classification
❌ partial execution
❌ mixing with /wire directly

---

CORE PRINCIPLE

Refactors are not edits.
They are SYSTEM EVENTS.
Treat them accordingly.

---

<!-- migrated-from: commands/refactor.md -->

---
name: refactor
version: "1.0.0"
description: "Trigger systematic refactoring/migration workflow with safety gates"
auto_chain: ynp
dag: refactoring-v1
dag_file: .cursor-commands/workflows/dags/refactoring_dag.py
---

# /refactor — Refactoring Workflow

**DAG-ENFORCED.** Execute the `refactoring-v1` DAG.

## Usage

```
/refactor                          # Begin refactoring workflow
/refactor path/to/migration.md     # With migration/requirements document
```

## Execution

Load and execute the DAG. Follow each node's `action` field in sequence.

- **DAG**: `.cursor-commands/workflows/dags/refactoring_dag.py`
- **Id**: `refactoring-v1`

The DAG contains all instructions (analyze document → cross-reference codebase → plan → batch execute → validate → commit). No separate execution file is required.
