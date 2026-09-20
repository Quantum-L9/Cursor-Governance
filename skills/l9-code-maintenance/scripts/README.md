# Scripts

**Path:** `skills/l9-code-maintenance/scripts` | **Tier:** discovered

## Purpose

Unified CLI for l9-code-maintenance modes with --dry-run support.



## Components

### `Hit`

No description

- File: `skills/l9-code-maintenance/scripts/refactor_sweep.py` (L60–65)
- Methods: _none_

### `SweepResult`

No description

- File: `skills/l9-code-maintenance/scripts/refactor_sweep.py` (L69–83)
- Methods: _none_

## Functions

- `def cmd_refactor_sweep(args) -> int`
- `def cmd_migrate(args) -> int`
- `def cmd_lint_fix(args) -> int`
- `def cmd_status(_args) -> int`
- `def main(argv) -> int`
- `def analyze(intent, root) -> SweepResult`
- `def render_markdown(result) -> str`
- `def main(argv) -> int`
- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def validation_parity() -> None`
- `def test_refactor_sweep_dry_run() -> None`
- `def test_migrate_dry_run_no_state() -> None`
- `def test_campaign_intent_gmp() -> None`
- `def test_scripts_exist() -> None`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `dataclasses`, `json`, `os`, `pathlib`, `re`, `shutil`, `subprocess`, `sys`

<!-- l9-module-readme: generated-from-ast -->
