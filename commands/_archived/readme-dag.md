---
name: readme
version: "1.2.0"
description: "Generate subsystem READMEs via AST-heavy, repo-agnostic pipeline"
auto_chain: ynp
dag: readme-pipeline-v1
dag_file: .cursor/workflows-synced/dags/readme_pipeline_dag.py
---

# /readme — README Generation Pipeline

**Repo-agnostic.** Uses AST parsing and core docs discovery.

**Auto-config:** When run in any repo, the generator checks for `readme_config.yaml` (under `config/subsystems/` or `README_PIPELINE_CONFIG`). If it does not exist, it creates a minimal one from discovered structure (Odoo manifests, Python packages).

```
/readme                    # Full pipeline
/readme --tier core        # Only core tier
/readme --subsystem memory # Single subsystem
```

## Execution

**Script resolution (repo-agnostic):**
1. `.cursor/workflows-synced/scripts/generate_subsystem_readmes.py` (preferred)
2. `scripts/generate_subsystem_readmes.py` (fallback — in repo)

**DAG (optional):** If DAG exists at `.cursor/workflows-synced/dags/readme_pipeline_dag.py`, follow its phases. Otherwise run the generator directly.

```bash
# Direct run (no DAG)
python3 scripts/generate_subsystem_readmes.py

# With filters
python3 scripts/generate_subsystem_readmes.py --tier core
python3 scripts/generate_subsystem_readmes.py --subsystem plasticos_transaction

# List / validate
python3 scripts/generate_subsystem_readmes.py --list
python3 scripts/generate_subsystem_readmes.py --validate
```

## AST Parsing

| Repo Type | AST Usage |
|-----------|-----------|
| **Odoo** | `ast.literal_eval` for `__manifest__.py`; regex + AST for model `_name`, `_description`, fields |
| **Python** | `ast.parse()` → `NodeVisitor` for classes, top-level functions, docstrings |
| **Generic** | Directory scan; minimal AST for `.py` files |

## Core Docs Discovery

When present in the repo, these files are read and used to enrich READMEs:

**Core (10):** ARCHITECTURE.md, API_REFERENCE.md, DATA_MODEL.md, WORKFLOW_GUIDE.md, TEST_STRATEGY.md, DEPLOYMENT.md, MIGRATION_GUIDE.md, SECURITY_MODEL.md, CHANGELOG.md, ROADMAP.md

**Config (2):** ENVIRONMENT_SPEC.yaml, NEO4J_ONTOLOGY.yaml

**User (6):** README.md, QUICK_START.md, CONTRIBUTING.md, GLOSSARY.md, FAQ.md, LICENSE

**Search paths:** repo root, `docs/`, `AI Agent Files/`, `docs/AI Files/`, `doc/`, `.cursor/docs/`

## Key Files (Repo-Agnostic)

| File | Location | Purpose |
|------|----------|---------|
| Generator | `scripts/generate_subsystem_readmes.py` | AST-heavy generator (fallback) |
| Config | `config/subsystems/readme_config.yaml` | Per-repo config (created if missing) |
| DAG | `.cursor/workflows-synced/dags/readme_pipeline_dag.py` | Optional pipeline definition |

## Environment Variables (Optional)

- `README_PIPELINE_CONFIG` — Custom config path
- `README_PIPELINE_REPO_ROOT` — Repo root (auto-detected if not set)
