---
name: l9-harvest-pipeline
description: harvest code extraction via sed/dag and use-harvest deployment pipeline. use when extracting code from documents, deploying harvested files, or running harvest-deploy-v1 dag — never manually rewrite code from documents.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, harvest, sed, deployment, dag, governance]
owner: igor_beylin
status: active
version: 3.2.1
updated: 2026-06-06
disable-model-invocation: true
---

# Harvest Pipeline

## Purpose

Extract code from source documents via `sed` (never manual rewrite) and deploy harvested files through the autonomous use-harvest executor — DAG-enforced end-to-end pipeline.

## Core Contract

`HARVEST (sed ONLY) → TABLE → USE-HARVEST (cp deploy) → VALIDATE → WIRE`

1. **Harvest** — `grep -n` for boundaries, `sed -n` for extraction. Never `Write`/`StrReplace` code from documents.
2. **Catalog** — build `HARVEST_TABLE.md` with source lines and targets.
3. **Deploy** — run `use_harvest_executor.py` (cp-based, autonomous).
4. **Validate** — syntax check deployed files.
5. **Wire** — run wire executor for `__init__.py` imports.

## Authority Order

1. [`references/harvest-extraction.md`](references/harvest-extraction.md) — sed-only extraction (v3.2)
2. `.cursor-commands/workflows/dags/harvest_deploy_dag.py` — `harvest-deploy-v1` DAG
3. [`references/use-harvest-deployment.md`](references/use-harvest-deployment.md) — deployment executor
4. `.cursor-commands/workflows/harvest_executor.py` — standalone harvest CLI
5. `.cursor-commands/workflows/use_harvest_executor.py` — deployment CLI
6. `.cursor/rules/92-learned-lessons.mdc` — copy complete code governance rule
7. [`references/harvest-legacy-v1.md`](references/harvest-legacy-v1.md) — deprecated v1.3 reference only

## Compact Workflow

### Phase 1: Harvest

```
/harvest path/to/document.md
/harvest doc1.md doc2.md
```

Execute `harvest-deploy-v1` DAG or standalone executor. **sed ONLY.**

See [`references/harvest-extraction.md`](references/harvest-extraction.md).

### Phase 2: Deploy

```
/use-harvest  →  use_harvest_executor.py path/to/harvested/
```

Autonomous cp-based deployment, syntax validation, wire hints, report, commit (no push).

See [`references/use-harvest-deployment.md`](references/use-harvest-deployment.md).

### Phase 3: Wire

```bash
python3 .cursor-commands/workflows/wire_executor.py {deployed_module}
```

Or `/wire` for imports and exports.

## Resource Map

- [`references/harvest-extraction.md`](references/harvest-extraction.md) — sed extraction protocol (current)
- [`references/use-harvest-deployment.md`](references/use-harvest-deployment.md) — deployment executor and HARVEST_TABLE format
- [`references/harvest-legacy-v1.md`](references/harvest-legacy-v1.md) — deprecated v1.3 (reference only)
- `.cursor-commands/workflows/dags/harvest_deploy_dag.py` — harvest DAG
- `.cursor-commands/workflows/harvest_executor.py` — standalone harvest CLI
- `.cursor-commands/workflows/use_harvest_executor.py` — deployment executor

## Validation

- All extractions use `sed -n` — no manual code typing.
- `HARVEST_TABLE.md` exists with source lines and targets.
- Post-extraction: `ls -la harvested-files/ && wc -l harvested-files/*`
- Post-deploy: `py_compile` passes on deployed files.
- Wire hints addressed or `/wire` scheduled.

## Failure Handling

| Symptom | Action |
|---------|--------|
| Manual rewrite temptation | Stop — governance breach; use sed extraction |
| sed boundary wrong | Re-run `grep -n` to locate correct line range |
| Target exists (REPLACE vs CREATE) | Let executor detect action; do not overwrite blindly |
| Syntax error post-deploy | Roll back cp; fix source lines; re-harvest |
| Executor interrupted | Resume with `--resume` flag |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: verify line boundaries with `grep -n`).

## Anti-Patterns

- Do not manually type code from source documents.
- Do not regenerate code from memory.
- Do not give copy-paste instructions — execute with tools.
- Do not use deprecated v1.3 Write-tool pattern — see legacy reference only.
