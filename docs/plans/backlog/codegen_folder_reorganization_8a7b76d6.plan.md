---
name: CodeGen Folder Reorganization
overview: Reorganize the 7 codegen organizational folders into a clean, discoverable structure. Move sympy code to services/, create schemas/ and process/ folders for critical definitions, consolidate documentation, and update references.
todos:
  - id: p1-1-create-dir
    content: Create services/symbolic_computation/ directory
    status: pending
  - id: p1-2-move-py
    content: Move 7 Python files from codegen/sympy/ to services/symbolic_computation/
    status: pending
    dependencies:
      - p1-1-create-dir
  - id: p1-3-move-infra
    content: Move test, Dockerfile, docker-compose, requirements files
    status: pending
    dependencies:
      - p1-1-create-dir
  - id: p1-4-move-docs
    content: Move README and guide files to services/symbolic_computation/docs/
    status: pending
    dependencies:
      - p1-1-create-dir
  - id: p1-5-move-refs
    content: Move CSV and PNG reference files
    status: pending
    dependencies:
      - p1-1-create-dir
  - id: p1-6-update-imports
    content: Update import paths in c_gmp_engine.py if needed
    status: pending
    dependencies:
      - p1-2-move-py
  - id: p2-1-create-schemas
    content: Create codegen/schemas/ directory
    status: pending
  - id: p2-2-move-core-schemas
    content: Move Module-Spec-v2.4.yaml, Module-Prompt-CURSOR-v2.0.yaml, dora-contract.yaml
    status: pending
    dependencies:
      - p2-1-create-schemas
  - id: p2-3-move-samples
    content: Create codegen/schemas/samples/ and move 5 sample YAML files
    status: pending
    dependencies:
      - p2-1-create-schemas
  - id: p3-1-create-process
    content: Create codegen/process/ directory
    status: pending
  - id: p3-2-move-process
    content: Move 4 meta.*.yaml files from master_meta_templates/
    status: pending
    dependencies:
      - p3-1-create-process
  - id: p3-3-create-readme
    content: Create codegen/process/README.md documenting pipeline
    status: pending
    dependencies:
      - p3-2-move-process
  - id: p4-1-create-python-dir
    content: Create codegen/templates/python/ subdirectory
    status: pending
  - id: p4-2-move-py-templates
    content: Move python-dora-template.py and python-l9-module-template.py
    status: pending
    dependencies:
      - p4-1-create-python-dir
  - id: p4-3-create-readme-dir
    content: Create codegen/templates/readme/ directory
    status: pending
  - id: p4-4-move-readme-templates
    content: Move and rename 8 files from README.gold-standard/
    status: pending
    dependencies:
      - p4-3-create-readme-dir
  - id: p5-1-create-docs
    content: Create codegen/docs/ and codegen/docs/archive/ directories
    status: pending
  - id: p5-2-move-guides
    content: Move USAGE_GUIDE.md and QUICKSTART.md from master_meta_templates/
    status: pending
    dependencies:
      - p5-1-create-docs
  - id: p5-3-move-meta2-docs
    content: Move INTEGRATION_GUIDE.md and DELIVERY_SUMMARY.md from meta-yaml-2/
    status: pending
    dependencies:
      - p5-1-create-docs
  - id: p5-4-move-meta1-docs
    content: Move 11 documentation files from meta-yaml-1/
    status: pending
    dependencies:
      - p5-1-create-docs
  - id: p5-5-move-phase-docs
    content: Move sympy phase 1-4 documentation to docs/sympy-phases/
    status: pending
    dependencies:
      - p5-1-create-docs
  - id: p6-delete-folders
    content: "Delete 6 empty folders: sympy/, meta-yaml-1/, meta-yaml-2/, master_meta_templates/, input_schemas/, README.gold-standard/"
    status: pending
    dependencies:
      - p1-5-move-refs
      - p2-3-move-samples
      - p3-2-move-process
      - p4-4-move-readme-templates
      - p5-5-move-phase-docs
  - id: p7-create-readme
    content: Create codegen/README.md with folder structure documentation
    status: pending
    dependencies:
      - p6-delete-folders
  - id: p8-1-update-agent-path
    content: Update codegen_agent.py default specs_dir path
    status: pending
    dependencies:
      - p2-3-move-samples
  - id: p8-2-update-readme-gen
    content: Update readme_generator.py template path references
    status: pending
    dependencies:
      - p4-4-move-readme-templates
  - id: p8-3-verify-emitter
    content: Verify file_emitter.py template references are correct
    status: pending
    dependencies:
      - p4-2-move-py-templates
---

# CodeGen Organizational Folder Cleanup

## Current Problem

The `codegen/` directory has 7 organizational folders with:

- Confusing names (`meta-yaml-1`, `meta-yaml-2`)
- Misplaced code (actual Python module in `sympy/`)
- Buried critical specs (DORA contract hidden in `sympy/phase 4/`)
- Scattered documentation across multiple folders

## Target Structure

```javascript
codegen/
├── README.md                  # NEW: System overview
├── schemas/                   # NEW: All schema definitions
│   ├── Module-Spec-v2.4.yaml
│   ├── Module-Prompt-CURSOR-v2.0.yaml
│   ├── dora-contract.yaml
│   └── samples/
├── templates/                 # REORGANIZED
│   ├── python/
│   ├── readme/
│   └── glue/
├── process/                   # NEW: Pipeline definitions
│   ├── meta.codegen.schema.yaml
│   ├── meta.extraction.sequence.yaml
│   ├── meta.validation.checklist.yaml
│   └── meta.dependency.integration.yaml
├── docs/                      # NEW: Consolidated documentation
│   ├── USAGE_GUIDE.md
│   ├── QUICKSTART.md
│   ├── INTEGRATION_GUIDE.md
│   └── sympy-phases/
├── specs/                     # UNCHANGED (excluded from scope)
└── extractions/               # UNCHANGED (excluded from scope)
```

Additionally:

```javascript
services/symbolic_computation/  # NEW: Moved from codegen/sympy/
├── __init__.py
├── config.py
├── core.py
├── models.py
├── utils.py
├── exceptions.py
├── logger.py
├── test_symbolic_computation.py
├── health_check.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Phase 1: Extract SymPy Code to Services

The `codegen/sympy/` folder contains a complete Python module that should live in `services/`.

### 1.1 Create services/symbolic_computation/ directory

Create the target directory structure.

### 1.2 Move Python files

| Source | Destination ||--------|-------------|| `codegen/sympy/symbolic_computation_init.py` | `services/symbolic_computation/__init__.py` || `codegen/sympy/symbolic_computation_core.py` | `services/symbolic_computation/core.py` || `codegen/sympy/symbolic_computation_config.py` | `services/symbolic_computation/config.py` || `codegen/sympy/symbolic_computation_models.py` | `services/symbolic_computation/models.py` || `codegen/sympy/symbolic_computation_utils.py` | `services/symbolic_computation/utils.py` || `codegen/sympy/symbolic_computation_exceptions.py` | `services/symbolic_computation/exceptions.py` || `codegen/sympy/symbolic_computation_logger.py` | `services/symbolic_computation/logger.py` |

### 1.3 Move test and infrastructure files

| Source | Destination ||--------|-------------|| `codegen/sympy/test_symbolic_computation.py` | `services/symbolic_computation/test_symbolic_computation.py` || `codegen/sympy/health_check_symbolic.py` | `services/symbolic_computation/health_check.py` || `codegen/sympy/Dockerfile_symbolic` | `services/symbolic_computation/Dockerfile` || `codegen/sympy/docker-compose_symbolic.yml` | `services/symbolic_computation/docker-compose.yml` || `codegen/sympy/requirements_symbolic.txt` | `services/symbolic_computation/requirements.txt` || `codegen/sympy/env_example_symbolic.txt` | `services/symbolic_computation/.env.example` |

### 1.4 Move documentation files

| Source | Destination ||--------|-------------|| `codegen/sympy/README_SYMBOLIC_COMPUTATION.md` | `services/symbolic_computation/README.md` || `codegen/sympy/SYMPY_UTILITIES_COMPLETE_GUIDE.md` | `services/symbolic_computation/docs/UTILITIES_GUIDE.md` || `codegen/sympy/Move Sympy To Services Diagram.md` | DELETE (obsolete after move) |

### 1.5 Move reference files

| Source | Destination ||--------|-------------|| `codegen/sympy/integration_guide.csv` | `services/symbolic_computation/docs/integration_guide.csv` || `codegen/sympy/sympy_utilities_reference.csv` | `services/symbolic_computation/docs/sympy_utilities_reference.csv` || `codegen/sympy/sympy_architecture.png` | `services/symbolic_computation/docs/architecture.png` || `codegen/sympy/sympy_performance.png` | `services/symbolic_computation/docs/performance.png` |

### 1.6 Update import paths

Update any files that import from `codegen.sympy.*` to use `services.symbolic_computation.*`:Files to check:

- [agents/codegenagent/c_gmp_engine.py](agents/codegenagent/c_gmp_engine.py) - imports `services.symbolic_computation`

---

## Phase 2: Create codegen/schemas/

Consolidate all schema definitions into one discoverable location.

### 2.1 Create codegen/schemas/ directory

### 2.2 Move core schemas

| Source | Destination ||--------|-------------|| `codegen/meta-yaml-1/Module-Spec-v2.4.yaml` | `codegen/schemas/Module-Spec-v2.4.yaml` || `codegen/meta-yaml-1/Module-Prompt-CURSOR-v2.0.yaml` | `codegen/schemas/Module-Prompt-CURSOR-v2.0.yaml` || `codegen/sympy/phase 4/l9-codegen-dora-contract.yaml` | `codegen/schemas/dora-contract.yaml` |

### 2.3 Create codegen/schemas/samples/ and move samples

| Source | Destination ||--------|-------------|| `codegen/meta-yaml-1/sample_schemas/simple_agent.yaml` | `codegen/schemas/samples/simple_agent.yaml` || `codegen/meta-yaml-1/sample_schemas/domain_adapter.yaml` | `codegen/schemas/samples/domain_adapter.yaml` || `codegen/meta-yaml-1/sample_schemas/orchestrator.yaml` | `codegen/schemas/samples/orchestrator.yaml` || `codegen/meta-yaml-1/sample_schemas/glue_layer.yaml` | `codegen/schemas/samples/glue_layer.yaml` || `codegen/input_schemas/sympy_schema_v6.yaml` | `codegen/schemas/samples/sympy_schema_v6.yaml` |---

## Phase 3: Create codegen/process/

Promote the critical pipeline YAMLs to a prominent location.

### 3.1 Create codegen/process/ directory

### 3.2 Move process YAMLs

| Source | Destination ||--------|-------------|| `codegen/master_meta_templates/meta.codegen.schema.yaml` | `codegen/process/meta.codegen.schema.yaml` || `codegen/master_meta_templates/meta.extraction.sequence.yaml` | `codegen/process/meta.extraction.sequence.yaml` || `codegen/master_meta_templates/meta.validation.checklist.yaml` | `codegen/process/meta.validation.checklist.yaml` || `codegen/master_meta_templates/meta.dependency.integration.yaml` | `codegen/process/meta.dependency.integration.yaml` |

### 3.3 Create codegen/process/README.md

Document the purpose of each process YAML.---

## Phase 4: Reorganize codegen/templates/

### 4.1 Create codegen/templates/python/ subdirectory

### 4.2 Move Python templates

| Source | Destination ||--------|-------------|| `codegen/templates/python-dora-template.py` | `codegen/templates/python/dora-template.py` || `codegen/templates/python-l9-module-template.py` | `codegen/templates/python/module-template.py` |

### 4.3 Rename and move README templates

Rename folder `codegen/README.gold-standard/` to `codegen/templates/readme/`:| Source | Destination ||--------|-------------|| `codegen/README.gold-standard/README.gold-standard.md` | `codegen/templates/readme/root-readme-template.md` || `codegen/README.gold-standard/subsystem-readmes-complete.md` | `codegen/templates/readme/subsystem-template.md` || `codegen/README.gold-standard/labs-research-super-prompt.md` | `codegen/templates/readme/ai-super-prompt.md` || `codegen/README.gold-standard/README-suite-complete-index.md` | `codegen/templates/readme/suite-index.md` || `codegen/README.gold-standard/README-quick-reference.md` | `codegen/templates/readme/quick-reference.md` || `codegen/README.gold-standard/README-executive-summary.md` | `codegen/templates/readme/executive-summary.md` || `codegen/README.gold-standard/README-integration-guide.md` | `codegen/templates/readme/readme-integration-guide.md` || `codegen/README.gold-standard/MANIFEST.md` | `codegen/templates/readme/MANIFEST.md` |

### 4.4 Keep glue/ as-is

`codegen/templates/glue/` stays in place.---

## Phase 5: Create codegen/docs/

Consolidate all documentation files.

### 5.1 Create codegen/docs/ directory

### 5.2 Move documentation from master_meta_templates/

| Source | Destination ||--------|-------------|| `codegen/master_meta_templates/CODEGEN_USAGE_GUIDE.md` | `codegen/docs/USAGE_GUIDE.md` || `codegen/master_meta_templates/README_QUICKSTART.md` | `codegen/docs/QUICKSTART.md` |

### 5.3 Move documentation from meta-yaml-2/

| Source | Destination ||--------|-------------|| `codegen/meta-yaml-2/CODEGEN_INTEGRATION_AND_DEPLOYMENT_GUIDE_v6.0.md` | `codegen/docs/INTEGRATION_GUIDE.md` || `codegen/meta-yaml-2/DELIVERY_SUMMARY.md` | `codegen/docs/DELIVERY_SUMMARY.md` |

### 5.4 Move reference docs from meta-yaml-1/

| Source | Destination ||--------|-------------|| `codegen/meta-yaml-1/README.meta.yaml.md` | `codegen/docs/meta-yaml-spec.md` || `codegen/meta-yaml-1/README as a contract.md` | `codegen/docs/readme-as-contract.md` || `codegen/meta-yaml-1/codegen gaps.md` | `codegen/docs/archive/codegen-gaps.md` || `codegen/meta-yaml-1/fill gaps using your codegen.md` | `codegen/docs/archive/fill-gaps-guide.md` || `codegen/meta-yaml-1/meta-gaps.yaml.md` | `codegen/docs/archive/meta-gaps.md` || `codegen/meta-yaml-1/ci.yaml.md` | `codegen/docs/ci-integration.md` || `codegen/meta-yaml-1/ci_meta_check_and_tests.py.md` | `codegen/docs/ci-meta-check.md` || `codegen/meta-yaml-1/meta.yaml.md` | `codegen/docs/meta-yaml-reference.md` || `codegen/meta-yaml-1/meta.yaml & CI.md` | `codegen/docs/meta-yaml-ci.md` || `codegen/meta-yaml-1/What else goes in docs folder_.md` | `codegen/docs/archive/docs-folder-guide.md` || `codegen/meta-yaml-1/GitHub-hosted runners.md` | `codegen/docs/archive/github-runners.md` |

### 5.5 Move SymPy phase documentation

| Source | Destination ||--------|-------------|| `codegen/sympy/phase 1/` (all files) | `codegen/docs/sympy-phases/phase-1/` || `codegen/sympy/phase 2/` (all files) | `codegen/docs/sympy-phases/phase-2/` || `codegen/sympy/phase 3/` (all files) | `codegen/docs/sympy-phases/phase-3/` || `codegen/sympy/phase 4/Dora-Block.md` | `codegen/docs/sympy-phases/phase-4/Dora-Block.md` |(Note: `l9-codegen-dora-contract.yaml` already moved to `schemas/` in Phase 2)---

## Phase 6: Delete Empty Folders

After all files moved, delete:

1. `codegen/sympy/` (empty after moves)
2. `codegen/meta-yaml-1/` (empty after moves)
3. `codegen/meta-yaml-2/` (empty after moves)
4. `codegen/master_meta_templates/` (empty after moves)
5. `codegen/input_schemas/` (empty after moves)
6. `codegen/README.gold-standard/` (empty after moves)

---

## Phase 7: Create codegen/README.md

Create a new README that documents the reorganized structure:

```markdown
# L9 CodeGen System

Autonomous code generation from YAML specifications.

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `schemas/` | Schema definitions (Module-Spec-v2.4, DORA contract, samples) |
| `templates/` | Code templates (Python, README, glue) |
| `process/` | Pipeline definitions (phases, validation, dependencies) |
| `docs/` | Usage guides, references, phase documentation |
| `specs/` | YAML specs to be converted to code |
| `extractions/` | Generated output (gitignored) |

## Quick Start

1. Define spec using `schemas/Module-Spec-v2.4.yaml`
2. Run: `python -m agents.codegenagent generate specs/my_spec.yaml`
3. Review output in `extractions/`

## Key Files

- `schemas/Module-Spec-v2.4.yaml` - Canonical 22-section module spec
- `schemas/dora-contract.yaml` - DORA block enforcement rules
- `process/meta.codegen.schema.yaml` - Pipeline orchestration
- `templates/python/dora-template.py` - Python file template

## Related

- `agents/codegenagent/` - Python implementation
- `ir_engine/` - Intermediate representation compiler
- `services/symbolic_computation/` - SymPy integration
```

---

## Phase 8: Update References

### 8.1 Update codegen_agent.py default path

In [agents/codegenagent/codegen_agent.py](agents/codegenagent/codegen_agent.py) line 159, change:

```python
# FROM:
self.specs_dir = Path(specs_dir) if specs_dir else self.repo_root / "codegen" / "meta-yaml-pack"

# TO:
self.specs_dir = Path(specs_dir) if specs_dir else self.repo_root / "codegen" / "specs"
```



### 8.2 Update readme_generator.py template path

In [agents/codegenagent/readme_generator.py](agents/codegenagent/readme_generator.py), if it references `Readme-CodeGen`, update to `templates/readme`.

### 8.3 Verify file_emitter.py template references

Check [agents/codegenagent/file_emitter.py](agents/codegenagent/file_emitter.py) for any template path references.---

## Summary

| Phase | Files Moved | Folders Created | Folders Deleted ||-------|-------------|-----------------|-----------------|| 1 | 17 | 1 (`services/symbolic_computation/`) | 0 || 2 | 7 | 2 (`schemas/`, `schemas/samples/`) | 0 || 3 | 4 | 1 (`process/`) | 0 || 4 | 10 | 2 (`templates/python/`, `templates/readme/`) | 0 || 5 | 17 | 3 (`docs/`, `docs/archive/`, `docs/sympy-phases/`) | 0 || 6 | 0 | 0 | 6 || 7 | 0 | 0 (new file) | 0 || 8 | 0 (edits only) | 0 | 0 |
