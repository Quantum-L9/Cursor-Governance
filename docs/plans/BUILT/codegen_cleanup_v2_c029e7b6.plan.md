---
name: CodeGen Cleanup v2
overview: Comprehensive reorganization of the 7 codegen organizational folders with pre-execution verification, file migrations, reference updates, and post-execution validation. Includes baseline scans, backup strategy, and full validation suite.
todos:
  - id: p0-1-scan-imports
    content: Run grep scans for codegen.sympy imports and document all locations
    status: completed
  - id: p0-2-scan-templates
    content: Run grep scans for codegen/templates references and document all locations
    status: completed
  - id: p0-3-scan-schemas
    content: Run grep scans for meta-yaml and README.gold-standard references
    status: completed
  - id: p0-4-check-configs
    content: Check .gitignore and CI configs for codegen/ references
    status: completed
  - id: p0-5-analyze-deps
    content: Compare sympy requirements with root requirements.txt
    status: completed
  - id: p0-6-create-branch
    content: Create git branch refactor/codegen-cleanup and tag pre-codegen-cleanup
    status: completed
  - id: p1-1-create-dir
    content: Create services/symbolic_computation/ and docs/ directories
    status: completed
    dependencies:
      - p0-6-create-branch
  - id: p1-2-move-py
    content: Move 7 Python files from codegen/sympy/ to services/symbolic_computation/
    status: completed
    dependencies:
      - p1-1-create-dir
  - id: p1-3-move-infra
    content: Move Dockerfile, docker-compose, requirements, env files
    status: completed
    dependencies:
      - p1-1-create-dir
  - id: p1-4-move-docs
    content: Move README and guide files to services/symbolic_computation/docs/
    status: completed
    dependencies:
      - p1-1-create-dir
  - id: p1-5-move-refs
    content: Move CSV and PNG reference files
    status: completed
    dependencies:
      - p1-1-create-dir
  - id: p2-1-create-schemas
    content: Create codegen/schemas/ and codegen/schemas/samples/ directories
    status: completed
    dependencies:
      - p0-6-create-branch
  - id: p2-2-move-core-schemas
    content: Move Module-Spec-v2.4.yaml, Module-Prompt-CURSOR-v2.0.yaml, dora-contract.yaml
    status: completed
    dependencies:
      - p2-1-create-schemas
  - id: p2-3-move-samples
    content: Move 5 sample YAML files to codegen/schemas/samples/
    status: completed
    dependencies:
      - p2-1-create-schemas
  - id: p3-1-create-process
    content: Create codegen/process/ directory
    status: completed
    dependencies:
      - p0-6-create-branch
  - id: p3-2-move-process
    content: Move 4 meta.*.yaml files from master_meta_templates/
    status: completed
    dependencies:
      - p3-1-create-process
  - id: p3-3-create-readme
    content: Create codegen/process/README.md documenting pipeline
    status: completed
    dependencies:
      - p3-2-move-process
  - id: p4-1-create-dirs
    content: Create codegen/templates/python/ and codegen/templates/readme/
    status: completed
    dependencies:
      - p0-6-create-branch
  - id: p4-2-move-py-templates
    content: Move and rename python-dora-template.py and python-l9-module-template.py
    status: completed
    dependencies:
      - p4-1-create-dirs
  - id: p4-3-move-readme-templates
    content: Move and rename 8 files from README.gold-standard/
    status: completed
    dependencies:
      - p4-1-create-dirs
  - id: p5-1-create-docs
    content: Create codegen/docs/, archive/, and sympy-phases/ directories
    status: completed
    dependencies:
      - p0-6-create-branch
  - id: p5-2-move-guides
    content: Move USAGE_GUIDE.md and QUICKSTART.md from master_meta_templates/
    status: completed
    dependencies:
      - p5-1-create-docs
  - id: p5-3-move-meta2-docs
    content: Move INTEGRATION_GUIDE.md and DELIVERY_SUMMARY.md from meta-yaml-2/
    status: completed
    dependencies:
      - p5-1-create-docs
  - id: p5-4-move-meta1-docs
    content: Move 11 documentation files from meta-yaml-1/
    status: completed
    dependencies:
      - p5-1-create-docs
  - id: p5-5-move-phase-docs
    content: Move sympy phase 1-4 documentation to docs/sympy-phases/
    status: completed
    dependencies:
      - p5-1-create-docs
  - id: p6-delete-folders
    content: Delete 6 empty folders after all moves complete
    status: completed
    dependencies:
      - p1-5-move-refs
      - p2-3-move-samples
      - p3-2-move-process
      - p4-3-move-readme-templates
      - p5-5-move-phase-docs
  - id: p7-create-readme
    content: Create codegen/README.md with folder structure documentation
    status: completed
    dependencies:
      - p6-delete-folders
  - id: p8-1-update-imports
    content: Update all Python import paths from codegen.sympy to services.symbolic_computation
    status: completed
    dependencies:
      - p1-2-move-py
  - id: p8-2-update-templates
    content: Update all template path references to new locations
    status: completed
    dependencies:
      - p4-2-move-py-templates
      - p4-3-move-readme-templates
  - id: p8-3-update-schemas
    content: Update all schema path references to codegen/schemas/
    status: completed
    dependencies:
      - p2-2-move-core-schemas
  - id: p8-4-update-ci
    content: Update CI/test references in .github/ and ci/
    status: completed
    dependencies:
      - p0-4-check-configs
  - id: p8-5-verify-gitignore
    content: Verify .gitignore still covers codegen/extractions/
    status: completed
    dependencies:
      - p0-4-check-configs
  - id: p9-1-validate-imports
    content: Run py_compile on all moved Python files
    status: completed
    dependencies:
      - p8-1-update-imports
  - id: p9-2-run-tests
    content: Run pytest on codegenagent and symbolic_computation
    status: completed
    dependencies:
      - p9-1-validate-imports
  - id: p9-3-validate-files
    content: Verify old folders deleted and new structure exists
    status: completed
    dependencies:
      - p6-delete-folders
  - id: p9-4-validate-refs
    content: Grep to confirm no old paths remain in codebaseGit add, review, and commit with detailed message
    status: completed
    dependencies:
      - p8-3-update-schemas
---

# CodeGen Organizational Folder Cleanup v2

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

## Phase 0: Pre-Execution Verification

### 0.1 Baseline Scan

Run these commands and document ALL results before making any changes:

```bash
# Find all imports from codegen.sympy
grep -r "from codegen.sympy" . --include="*.py"
grep -r "import codegen.sympy" . --include="*.py"

# Find all template path references
grep -r "codegen/templates" agents/ --include="*.py"
grep -r "codegen/templates" . --include="*.py"

# Find all schema path references  
grep -r "meta-yaml" agents/ --include="*.py"
grep -r "meta-yaml" . --include="*.py"

# Find all README.gold-standard references
grep -r "README.gold-standard" . --include="*.py"
grep -r "Readme-CodeGen" . --include="*.py"

# Check test files for codegen.sympy imports
grep -r "codegen.sympy" tests/ --include="*.py"
```

Expected files to update (document actual findings):

- [agents/codegenagent/c_gmp_engine.py](agents/codegenagent/c_gmp_engine.py) - imports `services.symbolic_computation`
- [agents/codegenagent/codegen_agent.py](agents/codegenagent/codegen_agent.py) - `meta-yaml-pack` path
- [agents/codegenagent/readme_generator.py](agents/codegenagent/readme_generator.py) - `Readme-CodeGen` path

### 0.2 Check Configuration Files

```bash
# Check .gitignore for codegen/ paths
grep -n "codegen" .gitignore

# Check CI configs for codegen/ references
grep -r "codegen" .github/ --include="*.yml" --include="*.yaml"
grep -r "codegen" ci/ --include="*.py" --include="*.sh"
```



### 0.3 Dependency Analysis

```bash
# Compare sympy deps with root deps
cat codegen/sympy/requirements_symbolic.txt
cat requirements.txt | grep -E "sympy|numpy"
```

Decision to document: Standalone deps (copy to services/) or shared deps (reference root)?

### 0.4 Backup Strategy

```bash
# Create feature branch
git checkout -b refactor/codegen-cleanup-2026-01-02

# Tag current state for easy rollback
git tag pre-codegen-cleanup

# Verify clean state
git status
```

---

## Phase 1: Extract SymPy Code to Services

### 1.1 Create services/symbolic_computation/ directory

```bash
mkdir -p services/symbolic_computation/docs
```



### 1.2 Move Python files

| Source | Destination |

|--------|-------------|

| `codegen/sympy/symbolic_computation_init.py` | `services/symbolic_computation/__init__.py` |

| `codegen/sympy/symbolic_computation_core.py` | `services/symbolic_computation/core.py` |

| `codegen/sympy/symbolic_computation_config.py` | `services/symbolic_computation/config.py` |

| `codegen/sympy/symbolic_computation_models.py` | `services/symbolic_computation/models.py` |

| `codegen/sympy/symbolic_computation_utils.py` | `services/symbolic_computation/utils.py` |

| `codegen/sympy/symbolic_computation_exceptions.py` | `services/symbolic_computation/exceptions.py` |

| `codegen/sympy/symbolic_computation_logger.py` | `services/symbolic_computation/logger.py` |

### 1.3 Move test and infrastructure files

| Source | Destination |

|--------|-------------|

| `codegen/sympy/test_symbolic_computation.py` | `services/symbolic_computation/test_symbolic_computation.py` |

| `codegen/sympy/health_check_symbolic.py` | `services/symbolic_computation/health_check.py` |

| `codegen/sympy/Dockerfile_symbolic` | `services/symbolic_computation/Dockerfile` |

| `codegen/sympy/docker-compose_symbolic.yml` | `services/symbolic_computation/docker-compose.yml` |

| `codegen/sympy/requirements_symbolic.txt` | `services/symbolic_computation/requirements.txt` |

| `codegen/sympy/env_example_symbolic.txt` | `services/symbolic_computation/.env.example` |

### 1.4 Move documentation files

| Source | Destination |

|--------|-------------|

| `codegen/sympy/README_SYMBOLIC_COMPUTATION.md` | `services/symbolic_computation/README.md` |

| `codegen/sympy/SYMPY_UTILITIES_COMPLETE_GUIDE.md` | `services/symbolic_computation/docs/UTILITIES_GUIDE.md` |

| `codegen/sympy/Move Sympy To Services Diagram.md` | DELETE (obsolete) |

### 1.5 Move reference files

| Source | Destination |

|--------|-------------|

| `codegen/sympy/integration_guide.csv` | `services/symbolic_computation/docs/integration_guide.csv` |

| `codegen/sympy/sympy_utilities_reference.csv` | `services/symbolic_computation/docs/sympy_utilities_reference.csv` |

| `codegen/sympy/sympy_architecture.png` | `services/symbolic_computation/docs/architecture.png` |

| `codegen/sympy/sympy_performance.png` | `services/symbolic_computation/docs/performance.png` |---

## Phase 2: Create codegen/schemas/

### 2.1 Create directories

```bash
mkdir -p codegen/schemas/samples
```



### 2.2 Move core schemas

| Source | Destination |

|--------|-------------|

| `codegen/meta-yaml-1/Module-Spec-v2.4.yaml` | `codegen/schemas/Module-Spec-v2.4.yaml` |

| `codegen/meta-yaml-1/Module-Prompt-CURSOR-v2.0.yaml` | `codegen/schemas/Module-Prompt-CURSOR-v2.0.yaml` |

| `codegen/sympy/phase 4/l9-codegen-dora-contract.yaml` | `codegen/schemas/dora-contract.yaml` |

### 2.3 Move samples

| Source | Destination |

|--------|-------------|

| `codegen/meta-yaml-1/sample_schemas/simple_agent.yaml` | `codegen/schemas/samples/simple_agent.yaml` |

| `codegen/meta-yaml-1/sample_schemas/domain_adapter.yaml` | `codegen/schemas/samples/domain_adapter.yaml` |

| `codegen/meta-yaml-1/sample_schemas/orchestrator.yaml` | `codegen/schemas/samples/orchestrator.yaml` |

| `codegen/meta-yaml-1/sample_schemas/glue_layer.yaml` | `codegen/schemas/samples/glue_layer.yaml` |

| `codegen/input_schemas/sympy_schema_v6.yaml` | `codegen/schemas/samples/sympy_schema_v6.yaml` |---

## Phase 3: Create codegen/process/

### 3.1 Create directory

```bash
mkdir -p codegen/process
```



### 3.2 Move process YAMLs

| Source | Destination |

|--------|-------------|

| `codegen/master_meta_templates/meta.codegen.schema.yaml` | `codegen/process/meta.codegen.schema.yaml` |

| `codegen/master_meta_templates/meta.extraction.sequence.yaml` | `codegen/process/meta.extraction.sequence.yaml` |

| `codegen/master_meta_templates/meta.validation.checklist.yaml` | `codegen/process/meta.validation.checklist.yaml` |

| `codegen/master_meta_templates/meta.dependency.integration.yaml` | `codegen/process/meta.dependency.integration.yaml` |

### 3.3 Create process README

Create `codegen/process/README.md` documenting each process YAML's purpose.---

## Phase 4: Reorganize codegen/templates/

### 4.1 Create subdirectories

```bash
mkdir -p codegen/templates/python
mkdir -p codegen/templates/readme
```



### 4.2 Move Python templates

| Source | Destination |

|--------|-------------|

| `codegen/templates/python-dora-template.py` | `codegen/templates/python/dora-template.py` |

| `codegen/templates/python-l9-module-template.py` | `codegen/templates/python/module-template.py` |

### 4.3 Move README templates

| Source | Destination |

|--------|-------------|

| `codegen/README.gold-standard/README.gold-standard.md` | `codegen/templates/readme/root-readme-template.md` |

| `codegen/README.gold-standard/subsystem-readmes-complete.md` | `codegen/templates/readme/subsystem-template.md` |

| `codegen/README.gold-standard/labs-research-super-prompt.md` | `codegen/templates/readme/ai-super-prompt.md` |

| `codegen/README.gold-standard/README-suite-complete-index.md` | `codegen/templates/readme/suite-index.md` |

| `codegen/README.gold-standard/README-quick-reference.md` | `codegen/templates/readme/quick-reference.md` |

| `codegen/README.gold-standard/README-executive-summary.md` | `codegen/templates/readme/executive-summary.md` |

| `codegen/README.gold-standard/README-integration-guide.md` | `codegen/templates/readme/readme-integration-guide.md` |

| `codegen/README.gold-standard/MANIFEST.md` | `codegen/templates/readme/MANIFEST.md` |---

## Phase 5: Create codegen/docs/

### 5.1 Create directories

```bash
mkdir -p codegen/docs/archive
mkdir -p codegen/docs/sympy-phases/phase-1
mkdir -p codegen/docs/sympy-phases/phase-2
mkdir -p codegen/docs/sympy-phases/phase-3
mkdir -p codegen/docs/sympy-phases/phase-4
```



### 5.2 Move documentation from master_meta_templates/

| Source | Destination |

|--------|-------------|

| `codegen/master_meta_templates/CODEGEN_USAGE_GUIDE.md` | `codegen/docs/USAGE_GUIDE.md` |

| `codegen/master_meta_templates/README_QUICKSTART.md` | `codegen/docs/QUICKSTART.md` |

### 5.3 Move documentation from meta-yaml-2/

| Source | Destination |

|--------|-------------|

| `codegen/meta-yaml-2/CODEGEN_INTEGRATION_AND_DEPLOYMENT_GUIDE_v6.0.md` | `codegen/docs/INTEGRATION_GUIDE.md` |

| `codegen/meta-yaml-2/DELIVERY_SUMMARY.md` | `codegen/docs/DELIVERY_SUMMARY.md` |

### 5.4 Move documentation from meta-yaml-1/

| Source | Destination |

|--------|-------------|

| `codegen/meta-yaml-1/README.meta.yaml.md` | `codegen/docs/meta-yaml-spec.md` |

| `codegen/meta-yaml-1/README as a contract.md` | `codegen/docs/readme-as-contract.md` |

| `codegen/meta-yaml-1/codegen gaps.md` | `codegen/docs/archive/codegen-gaps.md` |

| `codegen/meta-yaml-1/fill gaps using your codegen.md` | `codegen/docs/archive/fill-gaps-guide.md` |

| `codegen/meta-yaml-1/meta-gaps.yaml.md` | `codegen/docs/archive/meta-gaps.md` |

| `codegen/meta-yaml-1/ci.yaml.md` | `codegen/docs/ci-integration.md` |

| `codegen/meta-yaml-1/ci_meta_check_and_tests.py.md` | `codegen/docs/ci-meta-check.md` |

| `codegen/meta-yaml-1/meta.yaml.md` | `codegen/docs/meta-yaml-reference.md` |

| `codegen/meta-yaml-1/meta.yaml & CI.md` | `codegen/docs/meta-yaml-ci.md` |

| `codegen/meta-yaml-1/What else goes in docs folder_.md` | `codegen/docs/archive/docs-folder-guide.md` |

| `codegen/meta-yaml-1/GitHub-hosted runners.md` | `codegen/docs/archive/github-runners.md` |

### 5.5 Move SymPy phase documentation

| Source | Destination |

|--------|-------------|

| `codegen/sympy/phase 1/*` | `codegen/docs/sympy-phases/phase-1/` |

| `codegen/sympy/phase 2/*` | `codegen/docs/sympy-phases/phase-2/` |

| `codegen/sympy/phase 3/*` | `codegen/docs/sympy-phases/phase-3/` |

| `codegen/sympy/phase 4/Dora-Block.md` | `codegen/docs/sympy-phases/phase-4/Dora-Block.md` |---

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

Create new README documenting the reorganized structure with folder purposes, quick start, and key files.---

## Phase 8: Update ALL References (EXPANDED)

### 8.1 Update Python Import Paths

For ALL files discovered in Phase 0.1, update imports:

```python
# FROM:
from codegen.sympy.symbolic_computation_core import ...
from codegen.sympy.symbolic_computation_models import ...

# TO:
from services.symbolic_computation.core import ...
from services.symbolic_computation.models import ...
```

Known files (verify with Phase 0 scan):

- [agents/codegenagent/c_gmp_engine.py](agents/codegenagent/c_gmp_engine.py)

### 8.2 Update Template Paths

For ALL files discovered in Phase 0.1, update template references:

```python
# FROM:
template_path = ... / "codegen" / "templates" / "python-dora-template.py"
template_path = ... / "codegen" / "Readme-CodeGen" / ...

# TO:
template_path = ... / "codegen" / "templates" / "python" / "dora-template.py"
template_path = ... / "codegen" / "templates" / "readme" / ...
```

Known files (verify with Phase 0 scan):

- [agents/codegenagent/readme_generator.py](agents/codegenagent/readme_generator.py)
- [agents/codegenagent/file_emitter.py](agents/codegenagent/file_emitter.py)

### 8.3 Update Schema Paths

For ALL files discovered in Phase 0.1, update schema references:

```python
# FROM:
schema_path = ... / "codegen" / "meta-yaml-1" / "Module-Spec-v2.4.yaml"
self.specs_dir = ... / "codegen" / "meta-yaml-pack"

# TO:
schema_path = ... / "codegen" / "schemas" / "Module-Spec-v2.4.yaml"
self.specs_dir = ... / "codegen" / "specs"
```

Known files (verify with Phase 0 scan):

- [agents/codegenagent/codegen_agent.py](agents/codegenagent/codegen_agent.py) line 159
- [agents/codegenagent/meta_loader.py](agents/codegenagent/meta_loader.py)

### 8.4 Update CI/Test References

In `.github/workflows/*.yml` and `ci/` scripts:

- Update any `codegen/sympy` paths to `services/symbolic_computation`
- Update any `meta-yaml` paths to `schemas/`
- Update any `master_meta_templates` paths to `process/`

### 8.5 Update .gitignore

Verify `codegen/extractions/` is still gitignored (no change needed if path unchanged).---

## Phase 9: Post-Execution Validation

### 9.1 Import Validation

```bash
# Verify Python syntax
python -m py_compile agents/codegenagent/*.py
python -m py_compile services/symbolic_computation/*.py

# Verify imports work
python -c "from services.symbolic_computation.core import SymbolicComputation; print('OK: services.symbolic_computation')"
python -c "from agents.codegenagent import CodeGenAgent; print('OK: agents.codegenagent')"
```



### 9.2 Test Validation

```bash
# Run codegenagent tests
pytest agents/codegenagent/ -v

# Run symbolic_computation tests (if they exist in new location)
pytest services/symbolic_computation/test_symbolic_computation.py -v

# Run any codegen integration tests
pytest tests/codegen/ -v
```



### 9.3 File Existence Validation

```bash
# Verify old folders are empty/deleted
find codegen/sympy codegen/meta-yaml-1 codegen/meta-yaml-2 \
     codegen/master_meta_templates codegen/input_schemas \
     codegen/README.gold-standard -type f 2>/dev/null
# Expected: "No such file or directory" for each

# Verify new structure exists
ls codegen/schemas/Module-Spec-v2.4.yaml
ls codegen/schemas/dora-contract.yaml
ls codegen/templates/python/dora-template.py
ls codegen/templates/readme/root-readme-template.md
ls codegen/process/meta.codegen.schema.yaml
ls codegen/docs/USAGE_GUIDE.md
ls services/symbolic_computation/core.py
ls services/symbolic_computation/__init__.py
```



### 9.4 Reference Validation

```bash
# Verify no old paths remain in Python files
grep -r "codegen.sympy" . --include="*.py" | grep -v "__pycache__"
grep -r "meta-yaml-1" . --include="*.py" | grep -v "__pycache__"
grep -r "meta-yaml-2" . --include="*.py" | grep -v "__pycache__"
grep -r "README.gold-standard" . --include="*.py" | grep -v "__pycache__"
grep -r "master_meta_templates" . --include="*.py" | grep -v "__pycache__"
# Expected: no matches
```

## Summary

| Phase | Description | Files | Folders Created | Folders Deleted |

|-------|-------------|-------|-----------------|-----------------|

| 0 | Pre-Execution Verification | 0 (scans only) | 0 | 0 |

| 1 | Extract SymPy to Services | 17 | 2 | 0 |

| 2 | Create codegen/schemas/ | 8 | 2 | 0 |

| 3 | Create codegen/process/ | 5 | 1 | 0 |

| 4 | Reorganize templates/ | 10 | 2 | 0 |

| 5 | Create codegen/docs/ | 17+ | 5 | 0 |

| 6 | Delete Empty Folders | 0 | 0 | 6 |

| 7 | Create README | 1 | 0 | 0 |

| 8 | Update ALL References | 5+ edits | 0 | 0 |

| 9 | Post-Execution Validation | 0 (tests only) | 0 | 0 |

| **Total** | | **~60 files** | **12** | **6** |