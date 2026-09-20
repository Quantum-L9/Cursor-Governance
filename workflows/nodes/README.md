# Nodes

**Path:** `workflows/nodes` | **Tier:** discovered

## Purpose

Workflow Nodes — Reusable LangGraph node implementations.



## Components

_No public classes in this path._

## Functions

- `async def checkpoint_node(state) -> dict` — Pause workflow for user confirmation.
- `async def cli_checkpoint_node(state) -> dict` — CLI version with interactive confirmation.
- `async def deploy_files_node(state) -> dict` — Copy extracted files to their target locations.
- `async def extract_files_node(state) -> dict` — Extract code blocks from source document to harvest directory.
- `async def inject_files_node(state) -> dict` — Inject or replace content in existing files.
- `async def report_node(state) -> dict` — Generate final workflow report.
- `async def validate_node(state) -> dict` — Run validation checks on deployed files.

## Exports

`checkpoint_node`, `deploy_files_node`, `extract_files_node`, `inject_files_node`, `report_node`, `validate_node`

## Dependencies

`__future__`, `asyncio`, `datetime`, `pathlib`, `structlog`, `time`, `workflows.nodes.checkpoint`, `workflows.nodes.deploy`, `workflows.nodes.extract`, `workflows.nodes.inject`, `workflows.nodes.report`, `workflows.nodes.validate`, `workflows.state`

<!-- l9-module-readme: generated-from-ast -->
