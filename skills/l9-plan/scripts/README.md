# Scripts

**Path:** `skills/l9-plan/scripts` | **Tier:** discovered

## Purpose

CLI path confinement for SonarCloud pythonsecurity:S8707.



## Components

_No public classes in this path._

## Functions

- `def emit(plan) -> str`
- `def main() -> int`
- `def safe_cli_path(value) -> Path` — Resolve a CLI-supplied path and require it to stay within cwd.
- `def render(plan) -> str`
- `def main() -> int`
- `def projection_for(execute_via) -> _Projection`
- `def render(plan, template_text, execute_via) -> str` — Fill a minimal executable head from JSON; append template body as fill guide.
- `def main() -> int`
- `def classify(risk, evidence) -> str`
- `def omitted_gates(_depth) -> list[str]`
- `def main() -> int`
- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def skill_validation_scripts() -> list[str]`
- `def main() -> int`
- `def main() -> int`
- `def load_mapping(path) -> dict`
- `def main() -> int`
- `def main() -> int`
- `def load_json(path) -> dict`
- `def has_cycle(deps) -> bool`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `dataclasses`, `datetime`, `hashlib`, `json`, `os`, `pathlib`, `paths`, `re`, `subprocess`, `sync_cursor_plan_template`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
