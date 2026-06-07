<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-inspect
layer: reference
role: inspect_protocol
tags: [l9, inspect, validation, external-code, audit]
owner: igor_beylin
status: active
version: 3.0.1
updated: 2026-06-06
dag: inspect-v1
dag_file: .cursor-commands/workflows/dags/inspect_dag.py
auto_chain: ynp
--- /SKILL_META ---
-->

# /inspect — Code Gate & File Audit

**DAG-ENFORCED.** Execute the `inspect-v1` DAG.

## Usage

```
/inspect current_work/02-13-2026/guide.md    # External code — validate before import
/inspect path/to/proposed_file.py             # File not yet in repo
/inspect core/tools/registry_adapter.py       # Existing file audit
```

## What It Does

### External Code (markdown, non-repo files)

1. Extracts Python code blocks from markdown
2. Validates imports against actual L9 modules
3. Checks ADR compliance (structlog, no print, no f-string SQL, etc.)
4. Detects hardcoded config values
5. Parses AST structure (classes, functions, hotspots)
6. Gates: `FIX-BEFORE-IMPORT` or `/harvest-analyze`

### Existing Files

1. Classifies type (MODULE, SERVICE, AGENT, etc.) and tier
2. Parses AST for structure map
3. Runs same compliance checks
4. Routes to `/refactor-sweep`, `/wire`, `/gmp`, or `STOP`

## Execution

```python
from .cursor_commands.workflows.dags.inspect_dag import run_inspect
result = await run_inspect("current_work/02-13-2026/guide.md")
print(result.report)
```

## Validators Wired In

| Validator | Source | Checks |
|-----------|--------|--------|
| Import validation | `tools/validation/validate_external_code.py` | Non-existent L9 imports |
| ADR compliance | `tools/validation/validate_external_code.py` | print(), logging, f-string SQL, random |
| Config drift | `tools/validation/validate_external_code.py` | Hardcoded values vs config_constants |
| AST structure | Built-in | Classes, functions, long functions, syntax errors |
| DORA check | Built-in | Missing `__dora_meta__` |
| Async safety | Built-in | `time.sleep()` in async functions |

## Flow

```
START → classify → orient → structure → compliance → impact → routing → report → END
```

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/inspect_dag.py`
- **Validator**: `tools/validation/validate_external_code.py`
- **Makefile**: `make validate-external-code FILE=path`
