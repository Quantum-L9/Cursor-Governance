---
name: l9-inspect
description: deprecated — do not activate. the inspect capability runs directly from its canonical DAG (workflows/dags/inspect_dag.py) via /inspect. archived out of live skills discovery.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, inspect, dag, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 9.0.0
  updated: 2026-08-28
---

# l9-inspect (Deprecated)

**Deprecated. Do not activate this pack.**

The inspect capability is **not** retired — its Skill wrapper is. `/inspect` triggers
the canonical LangGraph DAG at `workflows/dags/inspect_dag.py` directly.

The existence of a DAG does not justify a Skill. This pack was a wrapper around an
execution graph that already carried the whole protocol.

Archived under `skills/_archived/l9-inspect/` for history only. The body below is the
retired pack, retained verbatim for comparison.

---


# Inspect

## Purpose

Gate external code before L9 import and audit existing files — validate imports, ADR compliance, config drift, AST structure, and route to fix/refactor/wire/GMP paths.

## Core Contract

`CLASSIFY → ORIENT → STRUCTURE → COMPLIANCE → IMPACT → ROUTE → REPORT`

1. **Classify** input as external (markdown/non-repo) or existing repo file.
2. **Orient** — extract code blocks or load file AST.
3. **Structure** — parse classes, functions, hotspots, syntax.
4. **Compliance** — run wired validators (imports, ADR, config drift, DORA, async safety).
5. **Impact** — assess blast radius for existing files.
6. **Route** — `FIX-BEFORE-IMPORT`, `/harvest-analyze`, `/refactor-sweep`, `/wire`, `/gmp`, or `STOP`.
7. **Report** — emit structured gate report.

## Authority Order

1. `.cursor-commands/workflows/dags/inspect_dag.py` — `inspect-v1` DAG
2. `tools/validation/validate_external_code.py` — import/ADR/config validators
3. [`references/inspect-protocol.md`](references/inspect-protocol.md) — usage, validators, flow
4. `make validate-external-code FILE=path` — Makefile shortcut

## Compact Workflow

```
/inspect current_work/02-13-2026/guide.md    # External code
/inspect path/to/proposed_file.py             # File not yet in repo
/inspect core/tools/registry_adapter.py       # Existing file audit
```

Execute `inspect-v1` DAG:

```python
from .cursor_commands.workflows.dags.inspect_dag import run_inspect

result = await run_inspect("current_work/02-13-2026/guide.md")
print(result.report)
```

See [`references/inspect-protocol.md`](references/inspect-protocol.md).

Auto-chains to `/ynp` after report.

## Resource Map

- [`references/inspect-protocol.md`](references/inspect-protocol.md) — validators, flow, routing details
- `.cursor-commands/workflows/dags/inspect_dag.py` — inspect DAG
- `tools/validation/validate_external_code.py` — external code validators
- `Makefile` — `make validate-external-code FILE=path`

## Validation

- External code: imports resolve against actual L9 modules.
- ADR compliance: no print(), no f-string SQL, structlog patterns.
- Config drift: no hardcoded values vs `config_constants`.
- AST: no syntax errors; DORA meta present where required.
- Routing decision explicit in report.

## Failure Handling

| Symptom | Action |
|---------|--------|
| Import validation fails | Route `FIX-BEFORE-IMPORT`; list missing modules |
| ADR violation | Route fix with specific rule citation |
| Syntax error in extracted code | Block import; report line-level error |
| Existing file audit fails compliance | Route `/refactor-sweep` or `/wire` per severity |
| Validator script missing | Fall back to AST + manual ADR grep; note gap |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: run `make validate-external-code FILE=path`).
