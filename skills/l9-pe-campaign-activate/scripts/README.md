# Scripts

**Path:** `skills/l9-pe-campaign-activate/scripts` | **Kind:** subsystem

## Modules

### `authorize_campaign_merge.py`

Fail-closed compatibility shim: Program Execution owns no merge authority.

- `def main() -> int`

### `compile_activation_files.py`

Compile only the files required to activate a PE campaign.

- `CompileError`
- `def utc_now() -> str`
- `def load_yaml(path) -> Any`
- `def yaml_text(value) -> str` — The exact text `dump_yaml` writes, so a receipt can be taken over it.
- `def dump_yaml(path, value) -> None`
- `def require_intent(raw) -> dict[str, Any]`
- `def project_conditionally_ready(intent) -> dict[str, Any]` — Fill kernel fields from declared plan/memo facts. Ready seeds stay untouched.
- `def refuse_stub_intent(intent) -> None`
- _+9 more public symbol(s)_

### `compile_brief.py`

Compile a free-form campaign memo or plan into an activate seed.

- `BriefError`
- `def slugify_token(value) -> str`
- `def slugify_filename(filename) -> str`
- `def title_from_filename(filename) -> str`
- `def assign_campaign_id(base, existing_ids) -> str`
- `def extract_release_paths(body) -> list[str]` — Bind file paths from a Release `Files:` list. Skip read-only or orphan entries.
- `def extract_release_tasks(text) -> list[dict[str, Any]]`
- `def extract_program_ordering_tasks(text) -> list[dict[str, str]]`
- _+21 more public symbol(s)_

## Dependencies

**Internal:** `program_policy`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
