# Scripts

**Path:** `skills/l9-dag-authoring/scripts` | **Kind:** subsystem

## Modules

### `classify_conversion_disposition.py`

Classify a SessionDAG CONVERT request against session-deprecation.yaml.

- `def load_catalog(path) -> dict`
- `def classify_row(repo, row, dag_id) -> dict`
- `def classify_request(repo, dag_id, catalog_path) -> dict`
- `def classify_all(repo, catalog_path) -> dict`
- `def main(argv) -> int`

### `classify_graph_kind.py`

Classify a graph source as SESSION_GUIDANCE, LANGGRAPH_RUNTIME, or UNKNOWN.

- `def classify(path) -> dict`
- `def main(argv) -> int`

### `convert_session_to_langgraph.py`

Emit a LangGraph package only for CONVERT_TO_LANGGRAPH.

- `def load_session_graph(path) -> dict`
- `def load_ir_graph(path) -> dict`
- `def refuse_prose(repo, graph) -> list[str]`
- `def emit_package(repo, graph, emit_dir, dag_id) -> dict`
- `def convert(repo) -> dict`
- `def main(argv) -> int`

### `inspect_repo_surfaces.py`

- `def inspect(root)`
- `def main(argv)`

### `probe_registration.py`

- `def probe(repo_root, dag_id)`
- `def main(argv)`

### `render_receipt.py`

- `def main()`

### `self_test.py`

- `def main()`

### `validate_command_trigger.py`

- `def validate(path, expected_dag_id)`
- `def main(argv)`

### `validate_langgraph_source.py`

Validate a LANGGRAPH_RUNTIME source.

- `def validate(path) -> dict`
- `def validate_package(directory) -> dict`
- `def main(argv) -> int`

### `validate_request.py`

- `def validate(data)`
- `def main(argv)`

### `validate_session_dag_source.py`

- `def validate(path)`
- `def main(argv)`

## Dependencies

**Internal:** `classify_conversion_disposition`, `classify_graph_kind`, `convert_session_to_langgraph`, `validate_command_trigger`, `validate_langgraph_source`, `validate_request`, `validate_session_dag_source`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
