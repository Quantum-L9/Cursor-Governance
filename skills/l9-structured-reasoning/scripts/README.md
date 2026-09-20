# Scripts

**Path:** `skills/l9-structured-reasoning/scripts` | **Kind:** subsystem

## Modules

### `compare_runs.py`

- `def summarize(rows) -> dict`
- `def main() -> int`

### `evaluate_confidence_cases.py`

- `def main() -> int`

### `evaluate_fixtures.py`

- `def main() -> int`

### `route_reasoning.py`

- `def route(request) -> dict[str, Any]`
- `def main() -> int`

### `self_test.py`

- `def run() -> None`
- `def main() -> int`

### `validate_exemplary_skill.py`

- `def main() -> int`

### `validate_ledger.py`

- `def load_allow_set() -> dict[str, dict[str, list[str]]]`
- `def validate(data) -> list[str]`
- `def main() -> int`

### `validate_skill.py`

- `def parse_frontmatter(text) -> dict[str, str]`
- `def main() -> int`

## Dependencies

**Internal:** `route_reasoning`, `validate_ledger`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
