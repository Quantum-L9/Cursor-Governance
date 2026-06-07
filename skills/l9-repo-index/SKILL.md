---
name: l9-repo-index
description: export repo indexes for fast lookup — repo-agnostic index generation. use when refreshing reports/repo-index, searching classes/functions/models before grep, or bootstrapping codebase navigation indexes.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, index, repo, lookup, odoo]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
disable-model-invocation: true
---

# Repo Index

## Purpose

Generate or update repo index files under `reports/repo-index/` for fast codebase lookup — works in any repo; includes Odoo-specific indexes when applicable.

## Core Contract

`RESOLVE SCRIPT → GENERATE INDEXES → VERIFY ENTRIES → REPORT`

1. **Resolve** generator script (synced → repo-local → manual fallback).
2. **Generate** index files from repo root.
3. **Verify** files exist with non-zero entry counts.
4. **Report** index counts and location.

## Authority Order

1. `.cursor/workflows-synced/scripts/export_repo_indexes.py` — synced generator (preferred)
2. `scripts/repo_generators/export_repo_indexes.py` — repo-local generator
3. [`references/index-export-protocol.md`](references/index-export-protocol.md) — manual generation and usage
4. `reports/repo-index/` — output location (repo root)

## Compact Workflow

Run from **current workspace (repo) root**:

```bash
# Preferred: synced script
python3 .cursor/workflows-synced/scripts/export_repo_indexes.py

# Or repo-local
python3 scripts/repo_generators/export_repo_indexes.py

# Or manual (see reference)
```

Before searching codebase, check indexes:

```bash
grep "ClassName" reports/repo-index/class_definitions.txt
grep "plasticos.transaction" reports/repo-index/odoo_model_registry.txt
```

See [`references/index-export-protocol.md`](references/index-export-protocol.md).

## Resource Map

- [`references/index-export-protocol.md`](references/index-export-protocol.md) — index files, manual generation, usage examples
- `.cursor/workflows-synced/scripts/export_repo_indexes.py` — synced generator
- `scripts/repo_generators/export_repo_indexes.py` — repo-local generator
- `reports/repo-index/` — output directory

## Validation

- `reports/repo-index/` directory exists after run.
- Core index files present: `class_definitions.txt`, `function_signatures.txt`.
- Odoo repos: `odoo_model_registry.txt` and module dependency index populated.
- Entry counts reported in output summary.

## Failure Handling

| Symptom | Action |
|---------|--------|
| No generator script found | Use manual generation from reference |
| Empty index file | Re-run from repo root; check path exclusions |
| Stale indexes | Regenerate before large search tasks |
| Odoo indexes missing | Run Odoo-specific grep commands from reference |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: manual index generation from reference).
