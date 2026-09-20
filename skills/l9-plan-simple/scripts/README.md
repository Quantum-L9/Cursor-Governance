# Scripts

**Path:** `skills/l9-plan-simple/scripts` | **Kind:** subsystem

## Modules

### `generate_plan_section_receipt.py`

Write a section-completeness receipt for a simple plan pair.

- `def build_receipt(plan_json_path, plan_md_path) -> dict[str, Any]`
- `def main(argv) -> int`

### `paths.py`

CLI path confinement for SonarCloud pythonsecurity:S8707.

- `def plans_store_root() -> Path | None` — Machine Cursor plans store (``~/.cursor/plans`` or ``L9_PLANS_STORE``).
- `def is_under(path, root) -> bool`
- `def confined_roots() -> list[Path]`
- `def safe_cli_path(value) -> Path` — Resolve a CLI path; require cwd or the canonical plans store.

### `plan_sections.py`

Required simple-plan sections — derived from owners, not a third list.

- `def plan_schema_path() -> Path`
- `def template_path() -> Path`
- `def json_required_keys(schema) -> list[str]`
- `def md_required_headings(template_text, mode) -> list[str]`
- `def heading_present(text, required) -> bool`
- `def parse_frontmatter(text) -> dict[str, Any]`
- `def handoff_mode(text) -> str` — The plan's declared handoff mode; cursor-build is the default.
- `def frontmatter_presence(text) -> dict[str, bool]`
- _+7 more public symbol(s)_

### `self_test.py`

Pack self-test for l9-plan-simple GAR wire + section receipt (both handoff modes).

- `def main() -> int`

### `validate_plan_section_receipt.py`

Fail-closed check that a simple plan has every skill-required section.

- `def check_receipt(path) -> list[str]`
- `def main(argv) -> int`

## Dependencies

**Internal:** `generate_plan_section_receipt`, `paths`, `plan_sections`, `validate_plan_section_receipt`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
