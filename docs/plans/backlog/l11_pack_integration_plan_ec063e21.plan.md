---
name: L11 Pack Integration Plan
overview: Integrate the L11 Debt Governance Pipeline pack into L9 by placing modules in scripts/github_actions/, tests in tests/github_actions/, config in config/l11/, and workflow as a parallel .github/workflows/l11-debt-governance.yml. All files will be renamed to remove "XX-L11-" prefixes and aligned with L9 ADRs.
todos:
  - id: create-dirs
    content: "Create target directories: scripts/github_actions/, tests/github_actions/, readme/github_actions/"
    status: completed
  - id: copy-modules
    content: Copy and rename 6 Python modules (remove XX-L11- prefix)
    status: completed
  - id: copy-config
    content: Copy pipeline_config.yaml to scripts/github_actions/
    status: completed
  - id: copy-tests
    content: Copy and rename 8 test files to tests/github_actions/
    status: completed
  - id: copy-workflow
    content: Copy workflow to .github/workflows/l11-debt-governance.yml
    status: completed
  - id: copy-validator
    content: Copy validator to .github/scripts/validate-protected-files.py
    status: completed
  - id: copy-docs
    content: Copy 3 documentation files to readme/github_actions/
    status: completed
  - id: update-dora
    content: Update __dora_meta__ module_name and domain fields in all Python files
    status: completed
  - id: update-imports
    content: Verify and fix import paths in test files
    status: completed
  - id: update-workflow-paths
    content: Update script paths in workflow YAML
    status: completed
  - id: merge-protected-files
    content: Merge protected_files.yaml with existing policy
    status: pending
  - id: validate-syntax
    content: Run syntax check on all new Python files
    status: completed
  - id: validate-dora
    content: Run DORA compliance check on new modules
    status: pending
  - id: run-tests
    content: Run pytest on tests/github_actions/
    status: completed
isProject: false
---

# L11 Debt Governance Pipeline Integration Plan

## Pack Summary

The L11 pack provides a two-layer debt governance system:

- **Deterministic Layer** (blocking): Ruff, Mypy, Bandit, Semgrep, ADR compliance
- **AI Enrichment Layer** (non-blocking): Perplexity-powered classification
- **Debt Graph**: Neo4j-backed persistent tracking with JSON fallback
- **Risk Scorer**: 5-factor weighted model
- **Auto-Fix Engine**: Shadow branch validation with HITL approval
- **Protected Files Gate**: Fail-closed CI gate for protected file modifications

---

## Target File Structure

All "XX-L11-" prefixes removed per invariant.

```
scripts/github_actions/
├── __init__.py
├── orchestrator.py              (from 02-L11-ORCHESTRATOR.py)
├── deterministic_engine.py      (from 03-L11-DETERMINISTIC-ENGINE.py)
├── ai_enrichment_engine.py      (from 04-L11-AI-ENRICHMENT-ENGINE.py)
├── debt_graph_service.py        (from 05-L11-DEBT-GRAPH-SERVICE.py)
├── risk_scorer.py               (from 06-L11-RISK-SCORER.py)
├── auto_fix_engine.py           (from 07-L11-AUTO-FIX-ENGINE.py)
└── pipeline_config.yaml         (from 01-L11-PIPELINE-CONFIG.yaml)

config/l11/
├── pipeline_config.yaml         (symlink or copy from scripts/github_actions/)
└── protected_files.yaml         (merge with existing config/policies/protected_files.yaml)

tests/github_actions/
├── __init__.py
├── conftest.py
├── test_orchestrator.py
├── test_deterministic_engine.py
├── test_ai_enrichment_engine.py
├── test_debt_graph_service.py
├── test_risk_scorer.py
└── test_auto_fix_engine.py

.github/workflows/
└── l11-debt-governance.yml      (from 08-L11-CI-WORKFLOW-v3.3.yaml)

.github/scripts/
└── validate-protected-files.py  (from validate-protected-files-v6.py)

readme/github_actions/
├── README.md                    (from 00-L11-MASTER-README.md)
├── RUNBOOK.md                   (from 09-L11-RUNBOOK.md)
└── METRICS-DASHBOARD.md         (from 10-L11-METRICS-DASHBOARD.md)
```

---

## ADR Compliance Fixes Required

Each Python module needs these changes:

### 1. DORA Metadata (ADR-0014)

Already present via injection script. Verify `__dora_meta__` has all required fields:

- `component_name`, `module_version`, `created_by`, `created_at`, `updated_at`
- `layer`: change from `operations` to `ci` or `governance`
- `domain`: change from `governance` to `l11` or `ci`
- `module_name`: update to match new path (e.g., `scripts.l11.orchestrator`)

### 2. Import Path Updates

All test files have imports like:

```python
from scripts.l11.orchestrator import L11Orchestrator
```

These will work after placement. Verify no circular imports.

### 3. Logging (ADR-0019)

All modules already use `structlog.get_logger(__name__)`. Verified compliant.

### 4. Error Handling (ADR-0055)

Modules use fail-loudly pattern with explicit exceptions. Verified compliant.

### 5. UTC Datetime (ADR-0083)

All modules use `datetime.now(tz=timezone.utc)`. Verified compliant.

---

## Integration Steps

### Phase 1: Directory Setup and File Placement

1. Create target directories:
  - `scripts/github_actions/`
  - `tests/github_actions/`
  - `readme/github_actions/`
2. Copy and rename Python modules (6 files):


| Source                           | Target                                           |
| -------------------------------- | ------------------------------------------------ |
| `02-L11-ORCHESTRATOR.py`         | `scripts/github_actions/orchestrator.py`         |
| `03-L11-DETERMINISTIC-ENGINE.py` | `scripts/github_actions/deterministic_engine.py` |
| `04-L11-AI-ENRICHMENT-ENGINE.py` | `scripts/github_actions/ai_enrichment_engine.py` |
| `05-L11-DEBT-GRAPH-SERVICE.py`   | `scripts/github_actions/debt_graph_service.py`   |
| `06-L11-RISK-SCORER.py`          | `scripts/github_actions/risk_scorer.py`          |
| `07-L11-AUTO-FIX-ENGINE.py`      | `scripts/github_actions/auto_fix_engine.py`      |


1. Copy and rename config (1 file):


| Source                        | Target                                        |
| ----------------------------- | --------------------------------------------- |
| `01-L11-PIPELINE-CONFIG.yaml` | `scripts/github_actions/pipeline_config.yaml` |


1. Copy and rename tests (8 files):


| Source                         | Target                                              |
| ------------------------------ | --------------------------------------------------- |
| `conftest.py`                  | `tests/github_actions/conftest.py`                  |
| `test_orchestrator.py`         | `tests/github_actions/test_orchestrator.py`         |
| `test_deterministic_engine.py` | `tests/github_actions/test_deterministic_engine.py` |
| `test_ai_enrichment_engine.py` | `tests/github_actions/test_ai_enrichment_engine.py` |
| `test_debt_graph_service.py`   | `tests/github_actions/test_debt_graph_service.py`   |
| `test_risk_scorer.py`          | `tests/github_actions/test_risk_scorer.py`          |
| `test_auto_fix_engine.py`      | `tests/github_actions/test_auto_fix_engine.py`      |
| `__init__.py`                  | `tests/github_actions/__init__.py`                  |


1. Copy and rename workflow (1 file):


| Source                         | Target                                      |
| ------------------------------ | ------------------------------------------- |
| `08-L11-CI-WORKFLOW-v3.3.yaml` | `.github/workflows/l11-debt-governance.yml` |


1. Copy and rename validator (1 file):


| Source                           | Target                                        |
| -------------------------------- | --------------------------------------------- |
| `validate-protected-files-v6.py` | `.github/scripts/validate-protected-files.py` |


1. Copy and rename documentation (3 files):


| Source                        | Target                                       |
| ----------------------------- | -------------------------------------------- |
| `00-L11-MASTER-README.md`     | `readme/github_actions/README.md`            |
| `09-L11-RUNBOOK.md`           | `readme/github_actions/RUNBOOK.md`           |
| `10-L11-METRICS-DASHBOARD.md` | `readme/github_actions/METRICS-DASHBOARD.md` |


### Phase 2: DORA Metadata Updates

Update `__dora_meta__` in each Python module:

1. `module_name` field: Update to match new path
  - Example: `"module_name": "scripts.l11.orchestrator"`
2. `domain` field: Change from `"governance"` to `"l11"`
3. `layer` field: Keep as `"operations"` (appropriate for CI/governance scripts)

### Phase 3: Import Path Fixes

1. In test files, verify imports resolve correctly:

```python
from scripts.l11.orchestrator import L11Orchestrator, Finding, ScanResult
from scripts.l11.deterministic_engine import DeterministicEngine
# etc.
```

1. In `conftest.py`, update fixture imports if needed.

### Phase 4: Workflow Configuration

1. Update `.github/workflows/l11-debt-governance.yml`:
  - Change script paths to match new locations
  - Example: `python scripts/github_actions/orchestrator.py` instead of `python scripts/l11_orchestrator.py`
2. Update protected files validator path in workflow:
  - `python .github/scripts/validate-protected-files.py`
3. Update pipeline config path references in Python modules:
  - `Path(__file__).parent / "pipeline_config.yaml"`

### Phase 5: Protected Files Policy Merge

The pack includes `protected_files.yaml`. Merge with existing `config/policies/protected_files.yaml`:

1. Review existing policy at [config/policies/protected_files.yaml](config/policies/protected_files.yaml)
2. Add any new protected paths from L11 pack
3. Ensure no conflicts with existing categories

### Phase 6: Validation

1. Run syntax check on all new Python files:

```bash
python -m py_compile scripts/github_actions/*.py tests/github_actions/*.py
```

1. Run DORA compliance check:

```bash
python scripts/audit/inject_dora_complete.py --repo . --dry-run --file scripts/github_actions/orchestrator.py
```

1. Run tests:

```bash
pytest tests/github_actions/ -v
```

1. Validate workflow YAML:

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/l11-debt-governance.yml'))"
```

---

## Files NOT to Copy

These files are deployment scripts or duplicates not needed in L9:

- `DEPLOY-v3.3.sh` - One-time deployment script (not needed after integration)
- `DEPLOY_ADDITIONS.sh` - Supplemental deployment script
- `NEW_WORKFLOW_JOBS.yaml` - Reference only (jobs already in workflow)
- `CODEOWNERS` - Review and merge with existing `.github/CODEOWNERS` if present
- `BRANCH-PROTECTION-SETTINGS.md` - Reference only
- `INTEGRATION_GUIDE.md` - Reference only
- `inject_dora_complete.py` - Already exists at `scripts/audit/inject_dora_complete.py`

---

## Post-Integration Tasks

1. **GitHub Secrets**: Ensure these are configured:
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (optional, falls back to JSON)
  - `PERPLEXITY_API_KEY` (optional, falls back to deterministic-only)
2. **Branch Protection**: Add L11 workflow jobs to required status checks when ready
3. **Documentation**: Update main README.md to reference L11 pipeline
4. **Monitoring**: Set up Prometheus metrics endpoint if using Grafana dashboard

---

## Risk Mitigation

- **Parallel Workflow**: L11 runs alongside existing `ci.yml` initially
- **Gradual Rollout**: Enable blocking gates one at a time
- **Circuit Breaker**: AI layer degrades gracefully if Perplexity unavailable
- **JSON Fallback**: Debt graph works without Neo4j

