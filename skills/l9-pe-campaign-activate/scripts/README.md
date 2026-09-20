# Scripts

**Path:** `skills/l9-pe-campaign-activate/scripts` | **Tier:** discovered

## Purpose

Fail-closed compatibility shim: Program Execution owns no merge authority.



## Components

### `CompileError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_activation_files.py` (L58–59)
- Methods: _none_

### `BriefError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_brief.py` (L83–86)
- Methods: _none_

## Functions

- `def main() -> int`
- `def utc_now() -> str`
- `def load_yaml(path) -> Any`
- `def yaml_text(value) -> str` — The exact text `dump_yaml` writes, so a receipt can be taken over it.
- `def dump_yaml(path, value) -> None`
- `def require_intent(raw) -> dict[str, Any]`
- `def project_conditionally_ready(intent) -> dict[str, Any]` — Fill kernel fields from declared plan/memo facts. Ready seeds stay untouched.
- `def refuse_stub_intent(intent) -> None`
- `def build_source(intent) -> dict[str, Any]`
- `def write_receipt(source_path, campaign_id) -> dict[str, Any]` — Record what was placed at `source_path`, measured from the file itself.
- `def patch_allowlist(path, campaign_id) -> bool` — Append an id to the legacy compile allowlist.
- `def patch_execution_policy(path, campaign_id) -> bool`
- `def patch_surface_profile(path, campaign_id) -> bool`
- `def patch_status_ledger(path, campaign_id) -> bool`
- `def assert_no_forbidden(campaign_dir) -> None`
- `def compile_activation(intent_path, repo_root) -> dict[str, Any]`
- `def slugify_token(value) -> str`
- `def slugify_filename(filename) -> str`
- `def title_from_filename(filename) -> str`
- `def assign_campaign_id(base, existing_ids) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `datetime`, `hashlib`, `json`, `pathlib`, `program_policy`, `re`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
