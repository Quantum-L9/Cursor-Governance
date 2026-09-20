# Scripts

**Path:** `skills/l9-code-maintenance/scripts` | **Kind:** subsystem

## Modules

### `code_maintenance.py`

Unified CLI for l9-code-maintenance modes with --dry-run support.

- `def cmd_refactor_sweep(args) -> int`
- `def cmd_migrate(args) -> int`
- `def cmd_lint_fix(args) -> int`
- `def cmd_status(_args) -> int`
- `def main(argv) -> int`

### `refactor_sweep.py`

Deterministic read-only refactor-sweep analyzer for l9-code-maintenance.

- `Hit`
- `SweepResult`
- `def analyze(intent, root) -> SweepResult`
- `def render_markdown(result) -> str`
- `def main(argv) -> int`

### `self_test.py`

Pack gate for l9-code-maintenance: Validation parity + dry-run non-mutation.

- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def validation_parity() -> None`
- `def test_refactor_sweep_dry_run() -> None`
- `def test_migrate_dry_run_no_state() -> None`
- `def test_campaign_intent_gmp() -> None`
- `def test_scripts_exist() -> None`
- `def main() -> int`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
