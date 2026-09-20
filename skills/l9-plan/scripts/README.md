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
- `def projection_for(execute_via) -> _Projection`
- `def render(plan, template_text, execute_via) -> str` — Fill a minimal executable head from JSON; append template body as fill guide.
- `def classify(risk, evidence) -> str`
- `def omitted_gates(_depth) -> list[str]`
- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def skill_validation_scripts() -> list[str]`
- `def load_mapping(path) -> dict`
- `def load_json(path) -> dict`
- `def has_cycle(deps) -> bool`
- `def semantic_errors(plan) -> list[str]`
- `def validate_path(path) -> list[str]`
- `def main(argv) -> int`
- `def canonicalize(text) -> str` — Zero the self-referential body_sha256 so the plan can hash itself.
- `def canonical_sha256(text) -> str`
- `def parse_kernel_pass_fallback(raw) -> dict[str, Any] | None`
- `def parse_frontmatter(text) -> tuple[dict[str, Any], str]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `copy`, `dataclasses`, `datetime`, `hashlib`, `importlib.util`, `json`, `os`, `pathlib`, `paths`, `re`, `subprocess`, `sync_cursor_plan_template`, `sys`, `tempfile`, `typing`, `validate_plan_document`

<!-- l9-module-readme: generated-from-ast -->
