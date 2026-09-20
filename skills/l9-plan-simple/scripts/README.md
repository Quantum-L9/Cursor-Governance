# Scripts

**Path:** `skills/l9-plan-simple/scripts` | **Tier:** discovered

## Purpose

Write a section-completeness receipt for a simple plan pair.



## Components

_No public classes in this path._

## Functions

- `def build_receipt(plan_json_path, plan_md_path) -> dict[str, Any]`
- `def main(argv) -> int`
- `def plans_store_root() -> Path | None` — Machine Cursor plans store (``~/.cursor/plans`` or ``L9_PLANS_STORE``).
- `def is_under(path, root) -> bool`
- `def confined_roots() -> list[Path]`
- `def safe_cli_path(value) -> Path` — Resolve a CLI path; require cwd or the canonical plans store.
- `def plan_schema_path() -> Path`
- `def template_path() -> Path`
- `def json_required_keys(schema) -> list[str]`
- `def md_required_headings(template_text, mode) -> list[str]`
- `def heading_present(text, required) -> bool`
- `def parse_frontmatter(text) -> dict[str, Any]`
- `def handoff_mode(text) -> str` — The plan's declared handoff mode; cursor-build is the default.
- `def frontmatter_presence(text) -> dict[str, bool]`
- `def live_pe_heading(text) -> bool`
- `def live_make_campaign(text) -> bool`
- `def json_section_presence(plan) -> dict[str, bool]`
- `def md_section_presence(text) -> dict[str, bool]`
- `def execute_swap_presence(text) -> dict[str, bool]`
- `def receipt_status(json_sections, md_sections, frontmatter, execute_swap, gar_invoked) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `datetime`, `generate_plan_section_receipt`, `hashlib`, `json`, `os`, `pathlib`, `paths`, `plan_sections`, `re`, `subprocess`, `sys`, `tempfile`, `typing`, `validate_plan_section_receipt`

<!-- l9-module-readme: generated-from-ast -->
