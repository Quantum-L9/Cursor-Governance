# Scripts

**Path:** `skills/l9-update-agent-docs/scripts` | **Kind:** subsystem

## Modules

### `compile_semantic_obligations.py`

Normalize canonical Harvest IR into evidence for DocumentationObligation objects.

- `def load_json(path) -> dict[str, Any]`
- `def schema_errors(data, schema_path) -> list[str]`
- `def action_for(concept) -> str`
- `def compile_harvest_evidence(harvest, required_surfaces, destinations, harvest_schema) -> dict[str, Any]`
- `def main() -> int`

### `doc_change.py`

Repository change, impact, managed-region, and capability mechanics.

- `def changed_files_since(root, base) -> tuple[list[str] | None, str | None]`
- `def worktree_changes(root) -> list[str]`
- `def automatic_changed_scope(root) -> tuple[list[str], str | None, str | None]`
- `def impact_analysis(policy, changed) -> dict[str, Any]`
- `def semantic_harvest_required(policy, impact, root) -> list[str]`
- `def managed_block_mutations(before, after, policy) -> list[str]`
- `def validate_managed_regions(root, base, changed, policy) -> tuple[str, list[str]]`
- `def probe_module_readme_capability(root, policy, changed) -> dict[str, Any]`

### `doc_filetree.py`

Deterministic root filetree.md inventory owned by l9-update-agent-docs.

- `ModuleRow`
- `FiletreeInventory`
- `def skip_prefixes(extra) -> tuple[str, ...]`
- `def is_excluded_path(rel, prefixes) -> bool` — Whole-subtree exclusion, decided before any classification.
- `def skipped_rel(rel, prefixes) -> bool` — Compatibility alias of :func:`is_excluded_path`.
- `def interest_files(path) -> list[str]`
- `def corpus_files(path) -> list[str]`
- `def is_module_dir(path) -> bool`
- _+13 more public symbol(s)_

### `doc_llm.py`

Small llm.txt projection mechanics for repository documentation.

- `def llm_enabled(root, policy, directives) -> tuple[bool, str]`
- `def llm_base_url(directives, cli) -> tuple[str | None, str]`
- `def render_llm_txt(root, policy, base_url) -> str`
- `def retire_legacy_llms_txt(root) -> list[str]` — Keep handwritten bytes; only drop the obsolete name once llm.txt exists.
- `def write_llm_txt(root, rendered) -> tuple[bool, Admission]` — Owned write of llm.txt.
- `def validate_llm_txt(text) -> list[str]`

### `doc_obligations.py`

Compile repository documentation topology into first-class obligation objects.

- `def source_changes_for_surface(policy, impact, surface) -> tuple[list[str], list[str]]`
- `def semantic_source_digest(root, policy, impact, required_surfaces) -> tuple[str | None, list[str]]`
- `def build_obligations(root, policy, impact, revision) -> list[dict[str, Any]]` — Compile obligations.
- `def apply_semantic_resolutions(obligations, semantic) -> list[dict[str, Any]]`
- `def validate_and_close_obligations(obligations) -> list[dict[str, Any]]`
- `def summarize_obligations(obligations) -> dict[str, Any]`
- `def status_from_obligations(obligations) -> str`

### `doc_owned_write.py`

Admit writes only for missing files or skill-owned generated files.

- `def admit_owned_write(existing, rendered, marker) -> Admission`
- `def apply_owned_write(path, rendered, marker) -> tuple[bool, Admission]`

### `doc_policy.py`

Typed documentation topology and repository-surface mechanics.

- `def git(root) -> subprocess.CompletedProcess[str]`
- `def load_json(path) -> dict[str, Any]`
- `def schema_errors(value, path) -> list[str]`
- `def load_policy() -> dict[str, Any]`
- `def validate_policy(policy) -> list[str]`
- `def resolve_under_root(root, rel) -> Path | None`
- `def repository_identity(root) -> str`
- `def repo_slug(root) -> str`
- _+7 more public symbol(s)_

### `doc_surface_analysis.py`

Closed-world assessment of executable repository contract surfaces.

- `def assess_surface_obligations(root, policy, obligations) -> list[dict[str, Any]]` — Attach deterministic assessment and separated ownership to obligations.

### `generate_module_readmes.py`

Repository README compiler owned by l9-update-agent-docs.

- `ClassInfo`
- `FunctionInfo`
- `ModuleFacts`
- `def resolve_repo_root(explicit) -> Path`
- `def load_config(repo_root) -> dict[str, Any]`
- `def extract_subsystem_facts(repo_root, subsystem_path) -> ModuleFacts` — Aggregate AST facts for a directory. Evidence only; not a README.
- `def resolve_under_root(repo_root, rel) -> Path | None`
- `def is_root_readme(repo_root, dest) -> bool`
- _+24 more public symbol(s)_

Exports: `CONFIG_PATH`, `ClassInfo`, `FunctionInfo`, `GENERATED_MARKER`, `LEGACY_HANDWRITTEN_RE`, `ModuleFacts`, `README_TEMPLATE`, `ROOT_README`, `classify_readme`, `discover_module_paths`, `extract_subsystem_facts`, `generate_readme` (+16 more)

### `readme_evidence.py`

Deterministic evidence compilation for README targets.

- `SkillContract` — Structural reading of a `SKILL.md`. Never a full Markdown parse.
- `def read_skill_contract(skill_md) -> SkillContract` — Extract only what is structurally unambiguous from a skill contract.
- `def summarize_docstring(doc, limit, hard_limit) -> str | None` — First sentence of a docstring, not its first physical line.
- `def compile_module_docs(repo_root, rel) -> tuple[tuple[ModuleDoc, ...], list[str]]` — One :class:`ModuleDoc` per direct source file, plus raw imports.
- `def repository_module_names(repo_root, paths) -> frozenset[str]` — Top-level names an import could resolve to inside this repository.
- `def classify_dependencies(imports, internal_names) -> DependencyDoc` — Split imports into internal, external and standard library.
- `def compile_readme_model(repo_root, target) -> ReadmeModel` — Compile deterministic evidence for one authorized target.

Exports: `CORPUS_TYPE_LABELS`, `MAX_INTERFACES_PER_MODULE`, `MAX_MODULES_RENDERED`, `SkillContract`, `classify_dependencies`, `compile_module_docs`, `compile_readme_model`, `read_skill_contract`, `repository_module_names`, `summarize_docstring`

### `readme_model.py`

Typed README compilation model owned by l9-update-agent-docs.

- `EvidenceRef` — One deterministic repository fact a rendered statement rests on.
- `ReadmeTarget` — A directory the inventory authorized for a generated README.
- `InterfaceDoc` — One public symbol: a class or a module-level function.
- `ModuleDoc` — One source file's public surface.
- `DependencyDoc` — Imports split by origin. Standard library is tracked but not rendered.
- `ReadmeModel` — The semantic model a renderer projects into Markdown.
- `QualityFinding` — One validation verdict against a compiled model or its rendering.
- `ReadmePlanItem` — One reconciled README destination and the action it requires.
- _+1 more public symbol(s)_

Exports: `DependencyDoc`, `EvidenceRef`, `InterfaceDoc`, `MUTATING_ACTIONS`, `ModuleDoc`, `PlanAction`, `QualityFinding`, `README_KINDS`, `ReadmeKind`, `ReadmeModel`, `ReadmePlan`, `ReadmePlanItem` (+1 more)

### `readme_quality.py`

Quality validation for compiled README models and their rendering.

- `def validate_readme_model(repo_root, model, rendered) -> list[QualityFinding]` — Validate one compiled model against its rendering.
- `def validate_readme_models(repo_root, pairs) -> list[QualityFinding]` — Validate every compiled model in one pass, deterministically ordered.
- `def retirement_findings(path, text) -> list[QualityFinding]` — Refuse to retire a README this generator does not strongly own.

Exports: `FORBIDDEN_PURPOSE_PHRASES`, `PURPOSE_EVIDENCE_KINDS`, `retirement_findings`, `validate_readme_model`, `validate_readme_models`

_+4 further module(s) in this directory._

## Dependencies

**Internal:** `compile_semantic_obligations`, `doc_change`, `doc_filetree`, `doc_llm`, `doc_obligations`, `doc_owned_write`, `doc_policy`, `doc_surface_analysis`, `generate_module_readmes`, `readme_evidence`, `readme_model`, `readme_quality`, `readme_renderers`, `repo_docs`, `surface_analyzers`

**External:** `jsonschema`, `referencing`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
