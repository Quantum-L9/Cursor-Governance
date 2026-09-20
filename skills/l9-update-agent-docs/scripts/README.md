# Scripts

**Path:** `skills/l9-update-agent-docs/scripts` | **Tier:** discovered

## Purpose

Normalize canonical Harvest IR into evidence for DocumentationObligation objects.



## Components

_No public classes in this path._

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
- `def llms_enabled(root, policy, directives) -> tuple[bool, str]`
- `def llms_base_url(directives, cli) -> tuple[str | None, str]`
- `def render_llms_txt(root, policy, base_url) -> str`
- `def validate_llms_txt(text) -> list[str]`
- `def source_changes_for_surface(policy, impact, surface) -> tuple[list[str], list[str]]`
- `def semantic_source_digest(root, policy, impact, required_surfaces) -> tuple[str | None, list[str]]`
- `def build_obligations(root, policy, impact, revision) -> list[dict[str, Any]]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections`, `collections.abc`, `compile_semantic_obligations`, `doc_change`, `doc_llms`, `doc_obligations`, `doc_policy`, `doc_surface_analysis`, `fnmatch`, `hashlib`, `json`, `jsonschema`, `pathlib`, `re`, `referencing`, `repo_docs`, `runpy`, `subprocess`, `surface_analyzers.makefile`, `surface_analyzers.pyproject`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
