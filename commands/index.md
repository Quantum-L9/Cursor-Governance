---
name: index
version: "1.0.0"
description: "Export repo indexes for fast lookup"
auto_chain: null
---

# /index — Repo Index Export

## WHAT IT DOES

Generate/update repo index files for fast lookup:

- Class definitions
- Function signatures
- Imports graph
- Route handlers
- Test catalog

---

## EXECUTION

```bash
python tools/export_repo_indexes.py
```

---

## INDEX FILES

Location: `readme/repo-index/`

| File | Contents |
|------|----------|
| class_definitions.txt | All classes with paths |
| function_signatures.txt | All functions |
| imports.txt | Import graph |
| route_handlers.txt | API routes |
| test_catalog.txt | All tests |
| inheritance_graph.txt | Class hierarchy |
| method_catalog.txt | Class methods |
| pydantic_models.txt | BaseModel subclasses |

---

## USAGE

Before searching codebase, check indexes:

```bash
# Find class
grep "ClassName" readme/repo-index/class_definitions.txt

# Find function
grep "function_name" readme/repo-index/function_signatures.txt

# Find route
grep "POST /api" readme/repo-index/route_handlers.txt
```

---

## OUTPUT

```markdown
## 📇 INDEX UPDATED

| Index | Entries |
|-------|---------|
| classes | N |
| functions | N |
| routes | N |
| tests | N |

**Location:** readme/repo-index/
```

--- End Command ---
