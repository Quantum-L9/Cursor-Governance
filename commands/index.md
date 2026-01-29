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

Location: `reports/repo-index/`

| File | Contents |
|------|----------|
| readme_manifest.txt | All READMEs with descriptions |
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
# Find README for a module
grep "memory/" reports/repo-index/readme_manifest.txt

# Find class
grep "ClassName" reports/repo-index/class_definitions.txt

# Find function
grep "function_name" reports/repo-index/function_signatures.txt

# Find route
grep "POST /api" reports/repo-index/route_handlers.txt
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

**Location:** reports/repo-index/
```

--- End Command ---
