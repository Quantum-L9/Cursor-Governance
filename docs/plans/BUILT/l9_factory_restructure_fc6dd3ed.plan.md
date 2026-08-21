---
name: L9 Factory Restructure
overview: Updated plan reflecting the significant new additions to codegen/. The extractor, factory CLI, meta_ir loader/registry, tools, utils, and many templates are now complete. Remaining work is filesystem consolidation, Tier 1 schemas, Tier 2 validators, Tier 3 resolver, missing templates, contract docs, CI, and tests.
todos:
  - id: fs-consolidation
    content: "Filesystem consolidation: merge old jinja2 templates/ into codegen/templates/, resolve dual CLIs, move orphaned engine/ files, create pyproject.toml"
    status: completed
  - id: template-gap
    content: "Template gap fill: copy/rename 14 old templates into codegen/templates/ with names matching template_registry.py _EXPLICIT_MAP; create 4 missing templates"
    status: completed
  - id: tier1-schemas
    content: "Build Tier 1 schemas: codegen/schemas/engine_schema.py (EngineSchema), meta_contract.py (canonical Pydantic), constellation_manifest.py"
    status: completed
  - id: tier2-validators
    content: "Build Tier 2 validators: engine_validator.py, contract_validator.py, output_validator.py, rules.py -- leverage existing contract_scanner.py and validate_*.py scripts"
    status: completed
  - id: tier3-resolver
    content: "Build Tier 3 resolver: glue_resolver.py, dependency_graph.py -- extend existing registry.dependency_ordered()"
    status: completed
  - id: tests-docs-ci
    content: Tests (9 files), contract docs (20 .md files), examples (5 files), CI scripts (2 files)
    status: completed
isProject: false
---

# L9 Engine Factory -- Updated Restructure Plan

## What Changed Since Last Review

You added **20 new files** across 5 new packages:


| Package                  | Files                                                                               | Status                                               |
| ------------------------ | ----------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `codegen/extractor/`     | `__init__.py`, `engine_extractor.py`, `module_extractor.py`, `template_registry.py` | **Complete** -- Full Tier 4                          |
| `codegen/meta_ir/`       | `__init__.py`, `loader.py`, `registry.py`                                           | **Complete** -- ContractSpec + ContractRegistry      |
| `codegen/tools/`         | `__init__.py`, `contract_scanner.py`, `spec_extract.py`, `audit_rules.yaml`         | **Complete** -- 28 rules                             |
| `codegen/utils/`         | `__init__.py`, `safe_eval.py`, `security.py`                                        | **Complete**                                         |
| `codegen/factory_cli.py` | 1 file (256 lines)                                                                  | **Complete** -- generate/validate/check/order/module |
| `codegen/templates/`     | 19 .j2 files                                                                        | **Partial** -- see gap below                         |


## Revised Scorecard vs `l9-engine-factory.md` Target

```
Component                    Target                    Repo Status
---------------------------------------------------------------------------
Tier 1: Schemas              3 files (engine_schema,   MISSING
                              meta_contract,
                              constellation_manifest)

Tier 2: Validators           4 files (engine_validator, MISSING (scripts/validate_*.py
                              contract_validator,        exist but are standalone CI
                              output_validator, rules)   scripts, not packaged)

Tier 3: Resolver             2 files (glue_resolver,   MISSING
                              dependency_graph)

Tier 4: Extractor            3 files                   DONE (codegen/extractor/)

Templates                    ~25 .j2 files             PARTIAL -- 19 of ~25 exist
                                                        in codegen/templates/
                                                        + 15 in old jinja2 templates/

CLI                          1 file                    DONE x2 (codegen/cli.py +
                                                        codegen/factory_cli.py)

Pipeline                     1 file                    DONE (codegen/pipeline.py)

Generators                   14 modules                DONE (codegen/generators/)

Routing                      2 YAML + 2 .py            DONE (codegen/routing/)

Meta-IR loader/registry      2 files                   DONE (codegen/meta_ir/)

Tools                        2 files + rules           DONE (codegen/tools/)

Utils                        2 files                   DONE (codegen/utils/)

Contract YAMLs (meta_ir/)    34 files                  DONE (meta_ir/)

CI workflow                  1 file                    DONE (.github/workflows/)

pyproject.toml               1 file                    MISSING (repo-level)

Tests                        ~9 files                  MISSING

Contract docs (.md)          20 files                  MISSING

Examples                     ~5 files                  MISSING
```

**Overall: ~65% complete (up from ~35% last review)**

## Remaining Work (6 tasks)

### Task 1: Filesystem Consolidation

The repo has two template directories and two CLIs that need merging:

- **Old `jinja2 templates/`** (15 .j2 files) -- contains domain-specific templates (gates/compiler, scoring/assembler, sync/generator, graph/driver, etc.) that are NOT in `codegen/templates/`
- **New `codegen/templates/`** (19 .j2 files) -- contains structural templates (**init**.py.j2s, config/, tests/, root/)
- **Two CLIs**: `codegen/cli.py` (pipeline-based) and `codegen/factory_cli.py` (extractor-based)

Actions:

- Merge the 15 old templates from `jinja2 templates/` into `codegen/templates/`, mapping to the paths expected by [codegen/extractor/template_registry.py](codegen/extractor/template_registry.py) `_EXPLICIT_MAP` (lines 40-77)
- Delete `jinja2 templates/` after merge
- Decide which CLI is canonical (recommend `factory_cli.py` since it wraps the full Tier 4 extractor; `cli.py` wraps the pipeline which is a different code path)
- Move `engine/config/spec_parser_extensions.py` and `engine/config/loader.py` into `codegen/` package (currently orphaned under `engine/`)
- Create repo-level `pyproject.toml` with package definition, entry point (`l9-factory = "codegen.factory_cli:main"`), and dependencies (pydantic, jinja2, structlog, pyyaml)

### Task 2: Tier 1 Schemas

Per [l9-engine-factory.md](l9-engine-factory.md) lines 21-25, three Pydantic models are needed:

- `codegen/schemas/engine_schema.py` -- `EngineSchema` (service-level spec: gates, scoring, sync, datastores, chassis_binding, constellation_wiring, governance, deployment)
- `codegen/schemas/meta_contract.py` -- `MetaContract` Pydantic model (currently exists as a dataclass in `codegen/extractor/module_extractor.py` line 31 and as `ContractSpec` in `codegen/meta_ir/loader.py` line 53; needs a canonical Pydantic version)
- `codegen/schemas/constellation_manifest.py` -- `ConstellationManifest` (multi-engine wiring: services, feeds, packet types)

Note: `codegen/meta_ir/loader.py` already has `ContractSpec` which covers most of `meta_contract.py`. The gap is `EngineSchema` and `ConstellationManifest`.

### Task 3: Tier 2 Validators

Per [l9-engine-factory.md](l9-engine-factory.md) lines 27-33:

- `codegen/validators/engine_validator.py` -- validates EngineSchema (handler actions, datastore types, packet types, gate dimensions, constellation wiring)
- `codegen/validators/contract_validator.py` -- validates MetaContract (non-empty responsibilities/guarantees, required_tests, valid contract refs)
- `codegen/validators/output_validator.py` -- post-generation enforcement (wraps the logic in `codegen/tools/contract_scanner.py` and `scripts/validate_*.py`)
- `codegen/validators/rules.py` -- single source of truth for all 28 rule IDs (currently in `codegen/tools/audit_rules.yaml`; `rules.py` would be the Python-importable version)

Existing assets to leverage:

- [codegen/tools/contract_scanner.py](codegen/tools/contract_scanner.py) -- already has 28 rules, `scan()`, `load_rules()`
- [codegen/tools/audit_rules.yaml](codegen/tools/audit_rules.yaml) -- 28 rules in YAML
- [scripts/validate_spec.py](scripts/validate_spec.py), [scripts/validate_handlers.py](scripts/validate_handlers.py), [scripts/validate_cypher.py](scripts/validate_cypher.py) -- standalone CI scripts

### Task 4: Tier 3 Resolver

Per [l9-engine-factory.md](l9-engine-factory.md) lines 35-37:

- `codegen/resolver/glue_resolver.py` -- reads constellation_glue.yaml, resolves build order, parallel groups, circular deps, per-engine imports
- `codegen/resolver/dependency_graph.py` -- pure graph algorithms (topo sort, cycle detection, parallel grouping)

Note: `codegen/meta_ir/registry.py` already has `dependency_ordered()` (line 62) with topological sort. The resolver would extend this to multi-engine constellation-level ordering.

### Task 5: Template Gap Fill

**Templates in old `jinja2 templates/` NOT yet in `codegen/templates/`:**


| Old Path                               | Needed As (per template_registry.py)           |
| -------------------------------------- | ---------------------------------------------- |
| `gates/compiler.py.j2`                 | `gates_compiler.py.j2`                         |
| `scoring/assembler.py.j2`              | `scoring_assembler.py.j2`                      |
| `sync/generator.py.j2`                 | `sync_generator.py.j2`                         |
| `sync/validators.py.j2`                | (not in registry -- may need adding)           |
| `gds/scheduler.py.j2`                  | `gds_scheduler.py.j2`                          |
| `graph/driver.py.j2`                   | (mapped to `schema_manager.py.j2` in registry) |
| `graph/schema_manager.py.j2`           | `schema_manager.py.j2`                         |
| `handlers.py.j2`                       | `handlers.py.j2`                               |
| `hooks/registry.py.j2`                 | (mapped to `handlers.py.j2` in registry)       |
| `compliance/prohibited_factors.py.j2`  | `compliance.py.j2`                             |
| `plugins/arbitration/arbitrator.py.j2` | `arbitration.py.j2`                            |
| `plugins/resolver.py.j2`               | `resolver.py.j2`                               |
| `traversal/assembler.py.j2`            | `traversal_assembler.py.j2`                    |
| `traversal/resolver.py.j2`             | `direction_resolver.py.j2`                     |


**Templates referenced in `template_registry.py` _EXPLICIT_MAP but not on disk anywhere:**

- `config_loader.py.j2`
- `gates_registry.py.j2`
- `gates_null_semantics.py.j2`
- `data_gravity.py.j2`

**Also missing per l9-engine-factory.md:**

- `scoring/__init__.py.j2`
- `config/loader.py.j2` (same as `config_loader.py.j2`)

### Task 6: Tests, Contract Docs, Examples, CI

**Tests** (per [l9-engine-factory.md](l9-engine-factory.md) lines 98-108):

- `tests/test_engine_schema.py`
- `tests/test_meta_contract.py`
- `tests/test_engine_validator.py`
- `tests/test_contract_validator.py`
- `tests/test_output_validator.py`
- `tests/test_glue_resolver.py`
- `tests/test_engine_extractor.py`
- `tests/test_templates.py`
- `tests/conftest.py`

**Contract docs** (per system spec `l9_codegen_system_spec.yaml`):

- 20 `.md` files: `01_FIELDNAMES` through `20_SHAREDMODELS`

**Examples** (per l9-engine-factory.md lines 88-97):

- `examples/graph_engine_spec.yaml`
- `examples/score_engine_spec.yaml`
- `examples/health_engine_spec.yaml`
- `examples/meta_contracts/` (3 example contracts)
- `examples/constellation_glue.yaml`

**CI** (per l9-engine-factory.md lines 84-86):

- `ci/run_ci_gates.sh`
- `ci/validate_all.py`

## Execution Priority

1. **Task 1** (Filesystem) -- unblocks everything; eliminates duplication
2. **Task 5** (Templates) -- can run in parallel with Task 1; merges old templates
3. **Task 2** (Schemas) -- prerequisite for Tasks 3 and 4
4. **Task 3** (Validators) -- depends on schemas
5. **Task 4** (Resolver) -- depends on schemas
6. **Task 6** (Tests/Docs/CI) -- last; validates everything above
