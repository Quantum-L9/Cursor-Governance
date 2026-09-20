# Nodes

**Path:** `workflows/nodes` | **Kind:** subsystem

## Modules

### `__init__.py`

Workflow Nodes — Reusable LangGraph node implementations.

Exports: `checkpoint_node`, `deploy_files_node`, `extract_files_node`, `inject_files_node`, `report_node`, `validate_node`

### `checkpoint.py`

Checkpoint Node — Human-in-the-loop confirmation.

- `async def checkpoint_node(state) -> dict` — Pause workflow for user confirmation.
- `async def cli_checkpoint_node(state) -> dict` — CLI version with interactive confirmation.

### `deploy.py`

Deploy Node — Copy extracted files to their destinations.

- `async def deploy_files_node(state) -> dict` — Copy extracted files to their target locations.

### `extract.py`

Extract Node — Extract code blocks from source documents.

- `async def extract_files_node(state) -> dict` — Extract code blocks from source document to harvest directory.

### `inject.py`

Inject Node — Inject/replace code in existing files.

- `async def inject_files_node(state) -> dict` — Inject or replace content in existing files.

### `report.py`

Report Node — Generate final workflow report.

- `async def report_node(state) -> dict` — Generate final workflow report.

### `validate.py`

Validate Node — Run validation checks on deployed files.

- `async def validate_node(state) -> dict` — Run validation checks on deployed files.

## Dependencies

**Internal:** `workflows`

**External:** `structlog`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
