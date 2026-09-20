# Scripts

**Path:** `scripts` | **Kind:** subsystem

## Modules

### `__init__.py`

Repo-root helper scripts. Importable so SessionDAGs can `from scripts…`.

### `generate_subsystem_readmes.py`

Compatibility wrapper for the skill-owned AST module README generator.

Exports: `CONFIG_PATH`, `ClassInfo`, `FunctionInfo`, `GENERATED_MARKER`, `LEGACY_HANDWRITTEN_RE`, `ModuleFacts`, `README_TEMPLATE`, `ROOT_README`, `classify_readme`, `discover_module_paths`, `extract_subsystem_facts`, `generate_readme` (+16 more)

## Entrypoints

- `claude-deepseek.sh`
- `preflight.sh`
- `verify-routing.sh`

## Dependencies

**Internal:** `generate_module_readmes`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
