---
name: L9 Engine Factory Restructure
overview: Restructure the repo from its current flat layout into the canonical `l9_engine_factory/` Python package described in l9-engine-factory.md and l9_codegen_system_spec.yaml, mapping existing assets to their target locations and identifying every missing component.
todos:
  - id: restructure-fs
    content: "Restructure filesystem: move existing files to target l9_engine_factory/ package layout, create __init__.py files, pyproject.toml, rename dirs"
    status: pending
  - id: tier1-schemas
    content: "Build Tier 1 schemas: engine_schema.py (EngineSchema), meta_contract.py (MetaContract), constellation_manifest.py"
    status: pending
  - id: tier2-validators
    content: "Build Tier 2 validators: package existing scripts, create rules.py (28 rule IDs), engine_validator.py, contract_validator.py, output_validator.py"
    status: pending
  - id: tier4-extractor
    content: "DONE -- Tier 4 extractor exists as codegen/pipeline.py + codegen/generators/_base.py + codegen/generators/__init__.py"
    status: completed
  - id: tier3-resolver
    content: "Build Tier 3 resolver: glue_resolver.py, dependency_graph.py"
    status: pending
  - id: cli
    content: "DONE -- CLI exists as codegen/cli.py with generate/validate/scan/list commands"
    status: completed
  - id: generators
    content: "DONE -- All 14 generator modules exist in codegen/generators/"
    status: completed
  - id: routing
    content: "DONE -- Routing tables exist in codegen/routing/ (engines.yaml + packs.yaml + loaders)"
    status: completed
  - id: missing-templates
    content: "Build missing Jinja2 templates: __init__.py.j2s, test templates, root file templates, config/schema.py.j2"
    status: pending
  - id: tools-utils
    content: Build tools (contract_scanner.py, spec_extract.py) and utils (safe_eval.py, security.py)
    status: pending
  - id: contract-docs
    content: Create 20 contract .md files (01_FIELDNAMES through 20_SHAREDMODELS)
    status: pending
  - id: tests
    content: "Build test suite: test_engine_schema, test_meta_contract, test_validators, test_resolver, test_extractor, test_templates"
    status: pending
isProject: false
---

# L9 Engine Factory Repo Restructure

## Current State (what exists)

```
L9 Engine Codegen/                        (repo root)
  codegen/                                Python package (loader + registry)
    __init__.py                           empty
    meta_ir/
      __init__.py                         empty
      loader.py                           162 lines -- discovers + parses YAML contracts
      registry.py                         246 lines -- maps contracts to generator IDs
  meta_ir/                                41 YAML contract files across 10 subdirs
  jinja2 templates/                       14 .py.j2 Jinja2 templates
  engine/
    config/loader.py                      42 lines -- DomainSpec loader (lru_cache)
    config/spec_parser_extensions.py      196 lines -- Pydantic v2 extension models
    matcher.yaml                          155 lines -- orphaned meta-IR contract (old format)
  scripts/
    validate_spec.py                      199 lines
    validate_handlers.py                  203 lines
    validate_cypher.py                    212 lines
    setup-new-workspace.yaml              838 lines (governance, not codegen)
  .github/workflows/codegen-validate.yml  230 lines
  docs/
    l9_codegen_system_spec.yaml           869 lines -- master system spec
    delivery/                             3 delivery manifests
  INTEGRATION_GUIDE.md                    247 lines
  l9-engine-factory.md                    252 lines
  L9 Codegen System Integration...md      247 lines
```

## Target State (from l9-engine-factory.md)

The canonical package name is `l9_engine_factory`. The target layout has 4 tiers: Schemas, Validators, Resolver, Extractor -- plus templates, CLI, CI, examples, and tests.

```
l9-engine-factory/                        (repo root, renamed)
  pyproject.toml
  README.md
  .gitignore
  l9_engine_factory/                      Python package
    __init__.py
    schemas/                              Tier 1: Pydantic models
      __init__.py
      engine_schema.py                    EngineSchema (service-level spec)
      meta_contract.py                    MetaContract (module-level spec)
      constellation_manifest.py           Multi-engine wiring manifest
    validators/                           Tier 2: Enforcement
      __init__.py
      engine_validator.py
      contract_validator.py
      output_validator.py
      rules.py                            Single source of truth for all banned patterns
    resolver/                             Tier 3: Wiring
      __init__.py
      glue_resolver.py                    Inter-engine dependency resolution
      dependency_graph.py                 Topological sort, cycle detection
    extractor/                            Tier 4: Code generation
      __init__.py
      engine_extractor.py                 Full engine generation orchestrator
      module_extractor.py                 Single module generation
      template_registry.py               Discovers + loads .j2 templates
    meta_ir/                              Loader + registry (existing code)
      __init__.py
      loader.py
      registry.py
    templates/                            Jinja2 templates
      engine/handlers.py.j2
      config/schema.py.j2, loader.py.j2, settings.py.j2
      gates/compiler.py.j2, registry.py.j2, gate_type.py.j2
      scoring/assembler.py.j2
      sync/generator.py.j2
      compliance/prohibited_factors.py.j2
      tests/test_handler.py.j2, conftest.py.j2, ...
      root/Dockerfile.j2, pyproject.toml.j2
    cli.py                                CLI entry point
  ci/
    run_ci_gates.sh
    validate_all.py
  contracts/                              41 Meta-IR YAML contracts
    config/, gates/, scoring/, ...
  examples/
    graph_engine_spec.yaml
    meta_contracts/
    constellation_glue.yaml
  tools/
    contract_scanner.py
    spec_extract.py
    audit_rules.yaml
  tests/
    conftest.py
    test_engine_schema.py
    test_meta_contract.py
    test_engine_validator.py
    test_contract_validator.py
    test_output_validator.py
    test_glue_resolver.py
    test_engine_extractor.py
    test_templates.py
  docs/
    l9_codegen_system_spec.yaml
    contracts/                            20 .md contract files
    delivery/
```

## Restructure: Mapping Existing Assets to Target

### Direct moves (existing code, new location)

- `codegen/meta_ir/loader.py` --> `l9_engine_factory/meta_ir/loader.py`
  - Update `META_IR_ROOT` to point to `contracts/` instead of sibling dir
- `codegen/meta_ir/registry.py` --> `l9_engine_factory/meta_ir/registry.py`
- `engine/config/spec_parser_extensions.py` --> `l9_engine_factory/schemas/spec_parser_extensions.py`
  - These Pydantic v2 models become part of the schemas tier
- `engine/config/loader.py` --> `l9_engine_factory/schemas/domain_spec_loader.py`
  - The `load_spec()` / `reload_spec()` functions
- `meta_ir/` (41 YAML files) --> `contracts/` (same structure)
  - The factory doc calls these "examples/meta_contracts/" but they are the actual contracts, not examples. `contracts/` is more accurate.
- `jinja2 templates/*.py.j2` (14 files) --> `l9_engine_factory/templates/` (restructured into subdirs)
- `scripts/validate_spec.py` --> `ci/validate_spec.py` (or `l9_engine_factory/validators/spec_validator.py`)
- `scripts/validate_handlers.py` --> `ci/validate_handlers.py` (or `l9_engine_factory/validators/handler_validator.py`)
- `scripts/validate_cypher.py` --> `ci/validate_cypher.py` (or `l9_engine_factory/validators/cypher_validator.py`)
- `.github/workflows/codegen-validate.yml` --> stays at `.github/workflows/codegen-validate.yml`
- `docs/l9_codegen_system_spec.yaml` --> `docs/l9_codegen_system_spec.yaml`
- `engine/matcher.yaml` --> `contracts/handlers.yaml` (merge with existing `meta_ir/handlers.yaml` or keep as `contracts/matcher.yaml`)

### Docs to consolidate

- `INTEGRATION_GUIDE.md` --> `docs/integration_guide.md`
- `l9-engine-factory.md` --> `docs/architecture.md`
- `L9 Codegen System Integration...md` --> `docs/gap_analysis.md`
- `scripts/setup-new-workspace.yaml` --> `docs/setup-new-workspace.yaml` (governance, not codegen tooling)

## What Is Missing (by tier)

### Tier 1 -- Schemas (30% built)


| File                                | Status  | Description                                                                                                                                                                    |
| ----------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `schemas/__init__.py`               | MISSING | Package init + public API                                                                                                                                                      |
| `schemas/engine_schema.py`          | MISSING | `EngineSchema` Pydantic v2 model -- the service-level spec covering gates, scoring, traversal, sync, datastores, chassis_binding, constellation_wiring, governance, deployment |
| `schemas/meta_contract.py`          | MISSING | `MetaContract` Pydantic v2 model -- module-level spec with name, kind, inputs, outputs, responsibilities, guarantees, required_tests, L9 contract bindings                     |
| `schemas/constellation_manifest.py` | MISSING | Multi-engine wiring manifest model -- which services exist, who feeds whom, via which packet types. Encodes the 26 feedback loops                                              |
| `schemas/spec_parser_extensions.py` | EXISTS  | SemanticRegistrySpec, DecisionArbitrationSpec, DataGravitySpec                                                                                                                 |
| `schemas/domain_spec_loader.py`     | EXISTS  | load_spec() with lru_cache                                                                                                                                                     |


### Tier 2 -- Validators (60% built, but not packaged)


| File                               | Status                                   | Description                                                                                                                                                                                                                                                  |
| ---------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `validators/__init__.py`           | MISSING                                  | Package init                                                                                                                                                                                                                                                 |
| `validators/engine_validator.py`   | MISSING                                  | Validates EngineSchema: handler actions are valid L9 actions, datastores match service type, packet types exist in registry, gate dimensions reference valid targets, constellation wiring matches glue manifest                                             |
| `validators/contract_validator.py` | MISSING                                  | Validates MetaContract: no empty responsibilities/guarantees, required_tests has unit + error path, contracts section references real L9 contracts, no placeholder text                                                                                      |
| `validators/output_validator.py`   | MISSING                                  | Post-generation enforcement: zero eval/exec, zero FastAPI imports in engine/, zero PacketEnvelope redefinition, zero NotImplementedError outside tests, zero logging.basicConfig, every file imported, every handler registered, test file exists per module |
| `validators/rules.py`              | MISSING                                  | Single source of truth for all 28 banned pattern rule IDs (SEC-001 through PKT-001) and required patterns. Currently scattered across validate_handlers.py and the system spec                                                                               |
| `validators/spec_validator.py`     | EXISTS (as scripts/validate_spec.py)     | Needs packaging                                                                                                                                                                                                                                              |
| `validators/handler_validator.py`  | EXISTS (as scripts/validate_handlers.py) | Needs packaging                                                                                                                                                                                                                                              |
| `validators/cypher_validator.py`   | EXISTS (as scripts/validate_cypher.py)   | Needs packaging                                                                                                                                                                                                                                              |


### Tier 3 -- Resolver (0% built)


| File                           | Status  | Description                                                                                                                                          |
| ------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `resolver/__init__.py`         | MISSING | Package init                                                                                                                                         |
| `resolver/glue_resolver.py`    | MISSING | Reads constellation_glue.yaml, resolves build order (topological sort), parallel groups, circular dependency detection, per-engine import resolution |
| `resolver/dependency_graph.py` | MISSING | Pure graph data structure: nodes, edges, cycle detection, topological sort, parallel grouping                                                        |


### Contract documentation (0% built)

20 `.md` contract files specified by name in the system spec. None exist:

- 01_FIELDNAMES.md through 10_BANNEDPATTERNS.md (engine-internal)
- 11_PACKETENVELOPEFIELDS.md through 20_SHAREDMODELS.md (constellation-wide)

### Tests (0% built)

No test files exist in the repo:

- `test_engine_schema.py`, `test_meta_contract.py`, `test_engine_validator.py`, `test_contract_validator.py`, `test_output_validator.py`, `test_glue_resolver.py`, `test_engine_extractor.py`, `test_templates.py`

### Root files (0% built)

- `pyproject.toml` -- package definition, dependencies, entry points
- `README.md` -- setup, run, test instructions
- `.gitignore` -- Python + codegen specific

## REVISED: New Files Added Since Initial Plan

The following were added to `codegen/` since the initial analysis:

**CLI + Pipeline (now complete)**

- `codegen/cli.py` (246 lines) -- full CLI: generate/validate/scan/list
- `codegen/pipeline.py` (249 lines) -- generation orchestrator with dry-run, incremental, pack filtering
- `codegen/__main__.py` (4 lines) -- enables `python -m codegen.cli`

**14 Generator Modules (all new)**

- `codegen/generators/__init__.py` -- registry + auto-import
- `codegen/generators/_base.py` (125 lines) -- shared Jinja2 render/write helpers
- `codegen/generators/domain_spec_models.py`, `config_loader.py`, `settings_model.py`
- `codegen/generators/gates_core.py` (126 lines) -- compiler + registry + null_semantics
- `codegen/generators/gates_types.py`, `scoring_assembler.py`, `traversal_core.py`
- `codegen/generators/sync_core.py`, `gds_core.py`, `graph_core.py`
- `codegen/generators/compliance_core.py`, `hooks_core.py`, `extensions_core.py`, `kge_core.py`

**Routing (new)**

- `codegen/routing/__init__.py`, `_loaders.py` (Pydantic models + YAML loaders)
- `codegen/routing/engines.yaml` (22 routes), `packs.yaml` (4 pack definitions)

## Revised Execution Priority

1. **Restructure filesystem** -- rename `jinja2 templates/` to `codegen/templates/`, consolidate docs, create `pyproject.toml`
2. **Tier 1 schemas** -- `engine_schema.py` + `meta_contract.py` + `constellation_manifest.py`
3. **Tier 2 validators** -- package 3 existing scripts + build `rules.py`, `output_validator.py`, `engine_validator.py`, `contract_validator.py`
4. **Tier 3 resolver** -- `glue_resolver.py` + `dependency_graph.py`
5. **Missing templates** -- test templates, `__init__.py.j2`, root file templates, `config/schema.py.j2`
6. **Tools** -- `contract_scanner.py`, `spec_extract.py`
7. **Contract docs** -- 20 `.md` files
8. **Tests** -- full test suite

(CLI, pipeline, generators, routing, extractor are now DONE -- removed from priority list)

## Revised Summary Scorecard


| Component               | Exists | Missing | Completion |
| ----------------------- | ------ | ------- | ---------- |
| Schemas (Tier 1)        | 2      | 3       | 30%        |
| Validators (Tier 2)     | 3      | 4       | 43%        |
| Resolver (Tier 3)       | 0      | 2       | 0%         |
| Extractor (Tier 4)      | 3      | 0       | **100%**   |
| Generators              | 14     | 0       | **100%**   |
| Routing                 | 4      | 0       | **100%**   |
| CLI + Pipeline          | 3      | 0       | **100%**   |
| Meta-IR loader/registry | 2      | 0       | **100%**   |
| Templates (.j2)         | 14     | ~19     | 42%        |
| Tools                   | 0      | 3       | 0%         |
| Utils                   | 0      | 2       | 0%         |
| Contract docs           | 0      | 20      | 0%         |
| Tests                   | 0      | 8+      | 0%         |
| Meta-IR contracts       | 41     | 0       | **100%**   |
| CI workflow             | 1      | 0       | **100%**   |
| Root files              | 0      | 3       | 0%         |


**Key change: The core codegen pipeline (CLI + pipeline + 14 generators + routing + meta-IR) is now complete. Remaining gaps: Tier 1 schemas, Tier 3 resolver, 4 new validators, ~19 templates, tools, utils, contract docs, tests, root files.**
