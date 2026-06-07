<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-repo-index
layer: reference
role: index_export_protocol
tags: [l9, index, repo, lookup, odoo]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
--- /SKILL_META ---
-->

# /index — Repo Index Export

## WHAT IT DOES

Generate/update repo index files for fast lookup. Works in any repo.

## Execution (Repo-Agnostic)

Run from **current workspace (repo) root**. Indexes are written to this repo's `reports/repo-index/`.

### Resolution Order for Generator Script

1. `.cursor/workflows-synced/scripts/export_repo_indexes.py` (synced)
2. `scripts/repo_generators/export_repo_indexes.py` (repo-local)
3. Manual generation (see below)

### Run Command

```bash
# If synced script exists:
python3 .cursor/workflows-synced/scripts/export_repo_indexes.py

# Or if repo has local script:
python3 scripts/repo_generators/export_repo_indexes.py

# Or manual generation (see Manual Index Generation below)
```

## Index Files

Location: `reports/repo-index/`

| File | Contents |
|------|----------|
| `readme_manifest.txt` | All READMEs with descriptions |
| `class_definitions.txt` | All classes with paths |
| `function_signatures.txt` | All functions |
| `imports.txt` | Import graph |
| `route_handlers.txt` | API routes |
| `test_catalog.txt` | All tests |
| `inheritance_graph.txt` | Class hierarchy |
| `method_catalog.txt` | Class methods |
| `pydantic_models.txt` | BaseModel subclasses |

### Odoo-Specific Indexes

For Odoo repos, additional indexes:

| File | Contents |
|------|----------|
| `odoo_model_registry.txt` | Odoo model definitions |
| `odoo_xml_data_files.txt` | XML data files by module |
| `odoo_security_groups.txt` | Security groups |
| `odoo_email_templates.txt` | Email templates |
| `odoo_cron_jobs.txt` | Cron jobs |
| `odoo_automations.txt` | Automated actions |
| `odoo_module_dependencies.txt` | Module dependency graph |
| `odoo_views.txt` | View files by module |

## Usage

Before searching codebase, check indexes:

```bash
# Find README for a module
grep "memory/" reports/repo-index/readme_manifest.txt

# Find class
grep "ClassName" reports/repo-index/class_definitions.txt

# Find function
grep "function_name" reports/repo-index/function_signatures.txt

# Find route (non-Odoo)
grep "POST /api" reports/repo-index/route_handlers.txt

# Find Odoo model
grep "plasticos.transaction" reports/repo-index/odoo_model_registry.txt
```

## Manual Index Generation

If no generator script exists, generate indexes manually:

```bash
mkdir -p reports/repo-index

# Model/class definitions
grep -rn "class " --include="*.py" . | grep -v __pycache__ > reports/repo-index/class_definitions.txt

# Function signatures
grep -rn "def " --include="*.py" . | grep -v __pycache__ > reports/repo-index/function_signatures.txt

# For Odoo repos:
grep -r "_name = " --include="*.py" . | grep -v __pycache__ > reports/repo-index/odoo_model_registry.txt
```

## Output

```markdown
## 📇 INDEX UPDATED

| Index | Entries |
|-------|---------|
| classes | N |
| functions | N |
| models | N |

**Location:** reports/repo-index/
```
