# Scripts

**Path:** `skills/l9-plan/scripts` | **Kind:** subsystem

## Modules

### `emit_gmp_phase0.py`

- `def emit(plan) -> str`
- `def main() -> int`

### `paths.py`

CLI path confinement for SonarCloud pythonsecurity:S8707.

- `def safe_cli_path(value) -> Path` — Resolve a CLI-supplied path and require it to stay within cwd.

### `render_plan_markdown.py`

- `def render(plan) -> str`
- `def main() -> int`

### `render_plan_pe_autonomy.py`

Project PLAN_DOCUMENT JSON into a Cursor .plan.md (shared template).

- `def projection_for(execute_via) -> _Projection`
- `def render(plan, template_text, execute_via) -> str` — Fill a minimal executable head from JSON; append template body as fill guide.
- `def main() -> int`

### `route_plan.py`

- `def classify(risk, evidence) -> str`
- `def omitted_gates(_depth) -> list[str]`
- `def main() -> int`

### `self_test.py`

- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def skill_validation_scripts() -> list[str]`
- `def main() -> int`

### `sync_cursor_plan_template.py`

Sync local Cursor plan template mirror from first-class git SSOT.

- `def main() -> int`

### `validate_exemplary_skill.py`

- `def load_mapping(path) -> dict`
- `def main() -> int`

### `validate_pack_structure.py`

- `def main() -> int`

### `validate_plan_document.py`

- `def load_json(path) -> dict`
- `def has_cycle(deps) -> bool`
- `def semantic_errors(plan) -> list[str]`
- `def validate_path(path) -> list[str]`
- `def main(argv) -> int`

### `validate_plan_kernel_receipt.py`

Fail-closed kernel_pass receipt checker for a single Cursor .plan.md.

- `def canonicalize(text) -> str` — Zero the self-referential body_sha256 so the plan can hash itself.
- `def canonical_sha256(text) -> str`
- `def parse_kernel_pass_fallback(raw) -> dict[str, Any] | None`
- `def parse_frontmatter(text) -> tuple[dict[str, Any], str]`
- `def slug_key(path) -> str | None`
- `def newer_same_slug_exists(path) -> bool`
- `def check_content_gates(body) -> list[str]`
- `def check_plan(path) -> list[str]`
- _+1 more public symbol(s)_

## Dependencies

**Internal:** `paths`, `sync_cursor_plan_template`, `validate_plan_document`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
