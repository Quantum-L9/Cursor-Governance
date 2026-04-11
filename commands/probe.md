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
