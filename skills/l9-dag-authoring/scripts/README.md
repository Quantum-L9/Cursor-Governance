# Scripts

**Path:** `skills/l9-dag-authoring/scripts` | **Tier:** discovered

## Purpose

Classify a SessionDAG CONVERT request against session-deprecation.yaml.



## Components

_No public classes in this path._

## Functions

- `def load_catalog(path) -> dict`
- `def classify_row(repo, row, dag_id) -> dict`
- `def classify_request(repo, dag_id, catalog_path) -> dict`
- `def classify_all(repo, catalog_path) -> dict`
- `def main(argv) -> int`
- `def classify(path) -> dict`
- `def main(argv) -> int`
- `def load_session_graph(path) -> dict`
- `def load_ir_graph(path) -> dict`
- `def refuse_prose(repo, graph) -> list[str]`
- `def emit_package(repo, graph, emit_dir, dag_id) -> dict`
- `def convert(repo) -> dict`
- `def main(argv) -> int`
- `def inspect(root)`
- `def main(argv)`
- `def probe(repo_root, dag_id)`
- `def main(argv)`
- `def main()`
- `def main()`
- `def validate(path, expected_dag_id)`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `ast`, `classify_conversion_disposition`, `classify_graph_kind`, `convert_session_to_langgraph`, `json`, `os`, `pathlib`, `re`, `subprocess`, `sys`, `tempfile`, `validate_command_trigger`, `validate_langgraph_source`, `validate_request`, `validate_session_dag_source`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
