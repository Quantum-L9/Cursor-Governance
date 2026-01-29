/probe — Import & wiring verification (SAFE)

Purpose
Verify that code loads, wires, and registers correctly in the real runtime.

Risk level
🟢 Zero mutation
🟢 No DB writes
🟢 No side effects beyond imports

Usage
/probe memory.substrate_repository
/probe core.tools.tool_embeddings
/probe core.agents.bootstrap.orchestrator

What Cursor does

Enters the running container

Imports the module

Reports:

import success

registry activity

dependency failures

circular import crashes

Execution (Cursor-internal)
docker compose exec -T l9-api python - <<EOF
import importlib
importlib.import_module("{TARGET}")
print("IMPORT OK:", "{TARGET}")
EOF

Output (Cursor)
## 🔎 PROBE: memory.substrate_repository

Status: ✅ PASS

Verified:
- Import path resolves
- Dependencies available
- No runtime import crash
- Registry wiring executed

Side effects:
- None

When to use /probe:
- After refactors
- After dependency changes
- When Cursor says “should work”
- Before enabling traffic
- Before deeper tests