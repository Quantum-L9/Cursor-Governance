# Scripts

**Path:** `skills/l9-update-agent-docs/scripts` | **Tier:** discovered

## Purpose

Normalize canonical Harvest IR into evidence for DocumentationObligation objects.



## Components

### `ModuleRow`

No description

- File: `skills/l9-update-agent-docs/scripts/doc_filetree.py` (L92–97)
- Methods: _none_

### `FiletreeInventory`

No description

- File: `skills/l9-update-agent-docs/scripts/doc_filetree.py` (L101–104)
- Methods: _none_

### `ClassInfo`

No description

- File: `skills/l9-update-agent-docs/scripts/generate_module_readmes.py` (L152–160)
- Methods: _none_

### `FunctionInfo`

No description

- File: `skills/l9-update-agent-docs/scripts/generate_module_readmes.py` (L164–172)
- Methods: _none_

### `ModuleFacts`

No description

- File: `skills/l9-update-agent-docs/scripts/generate_module_readmes.py` (L176–184)
- Methods: _none_

## Functions

- `def load_json(path) -> dict[str, Any]`
- `def schema_errors(data, schema_path) -> list[str]`
- `def action_for(concept) -> str`
- `def compile_harvest_evidence(harvest, required_surfaces, destinations, harvest_schema) -> dict[str, Any]`
- `def main() -> int`
- `def changed_files_since(root, base) -> tuple[list[str] | None, str | None]`
- `def worktree_changes(root) -> list[str]`
- `def automatic_changed_scope(root) -> tuple[list[str], str | None, str | None]`
- `def impact_analysis(policy, changed) -> dict[str, Any]`
- `def semantic_harvest_required(policy, impact, root) -> list[str]`
- `def managed_block_mutations(before, after, policy) -> list[str]`
- `def validate_managed_regions(root, base, changed, policy) -> tuple[str, list[str]]`
- `def probe_module_readme_capability(root, policy, changed) -> dict[str, Any]`
- `def skip_prefixes(extra) -> tuple[str, ...]`
- `def skipped_rel(rel, prefixes) -> bool`
- `def interest_files(path) -> list[str]`
- `def corpus_files(path) -> list[str]`
- `def is_module_dir(path) -> bool`
- `def under_skill_pack(root, rel) -> bool`
- `def is_corpus_dir(root, rel, path) -> bool`

## Exports

`CONFIG_PATH`, `ClassInfo`, `FunctionInfo`, `GENERATED_MARKER`, `LEGACY_HANDWRITTEN_RE`, `ModuleFacts`, `README_TEMPLATE`, `ROOT_README`, `classify_readme`, `discover_module_paths`, `extract_subsystem_facts`, `generate_readme`, `is_generated`, `is_handwritten`, `is_legacy_generated`, `is_root_readme`, `list_subsystems`, `load_config`, `main`, `report_gaps` (+8 more)

## Dependencies

`__future__`, `argparse`, `ast`, `collections`, `collections.abc`, `compile_semantic_obligations`, `dataclasses`, `datetime`, `doc_change`, `doc_filetree`, `doc_llm`, `doc_obligations`, `doc_owned_write`, `doc_policy`, `doc_surface_analysis`, `fnmatch`, `generate_module_readmes`, `hashlib`, `json`, `jsonschema`, `pathlib`, `re`, `referencing`, `repo_docs`

<!-- l9-module-readme: generated-from-ast -->
