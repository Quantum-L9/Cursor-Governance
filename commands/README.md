---
name: readme
version: "1.0.0"
description: "Generate subsystem READMEs via enforced DAG pipeline"
auto_chain: ynp
dag: readme-pipeline-v1
dag_file: workflows/session/dags/readme_pipeline_dag.py
---

# /readme — README Generation Pipeline (DAG-Enforced)

## TRIGGER DAG

This command triggers the `readme-pipeline-v1` DAG.

```python
from workflows.session.dags import README_PIPELINE_DAG
# DAG handles: gap analysis → config enrichment → generate → validate → report
```

---

## DAG PHASES (ENFORCED)

| Phase | Node | Action |
|-------|------|--------|
| 1 | `gap_analysis` | Compare config vs actual directories |
| 2 | `gate_gaps` | User confirms gaps found |
| 3 | `enrich_config` | Add missing subsystems to `readme_config.yaml` |
| 4 | `gate_template` | User decides if template needs update |
| 5 | `update_template` | (Optional) Enhance README_TEMPLATE |
| 6 | `generate` | Run `scripts/generate_subsystem_readmes.py` |
| 7 | `validate` | Verify READMEs generated correctly |
| 8 | `gate_validation` | User confirms validation passed |
| 9 | `report` | Summarize pipeline results |

---

## KEY FILES

| File | Purpose |
|------|---------|
| `config/subsystems/readme_config.yaml` | Subsystem definitions |
| `scripts/generate_subsystem_readmes.py` | Generator script |
| `workflows/session/dags/readme_pipeline_dag.py` | DAG definition |
| `*/README.md` | Output (~65-70 files) |

---

## EXECUTION

### Start the DAG
```bash
# View DAG structure
python3 -c "from workflows.session.dags import README_PIPELINE_DAG; print(README_PIPELINE_DAG.to_mermaid())"
```

### Phase 1: Gap Analysis
```bash
# List current config
python scripts/generate_subsystem_readmes.py --list

# Find directories without README config
find . -type d -name "*.py" -prune -o -type d -print | \
  grep -E "^\\./[a-z]" | \
  grep -v -E "(node_modules|venv|__pycache__|.git)"
```

### Phase 6: Generate
```bash
# Full generation (all subsystems)
python scripts/generate_subsystem_readmes.py --skip-time-verify

# Specific subsystem
python scripts/generate_subsystem_readmes.py --subsystem memory --skip-time-verify

# Specific tier
python scripts/generate_subsystem_readmes.py --tier core --skip-time-verify
```

### Phase 7: Validate
```bash
# Count generated files
find . -name "README.md" -newer config/subsystems/readme_config.yaml | wc -l

# Validate config
python scripts/generate_subsystem_readmes.py --validate
```

---

## EXPECTED OUTPUT

~65-70 README.md files across:
- `core/*/README.md`
- `memory/*/README.md`
- `api/*/README.md`
- `agents/*/README.md`
- `services/*/README.md`
- `orchestration/*/README.md`
- `runtime/*/README.md`
- `tools/*/README.md`
- `workflows/*/README.md`

---

## DAG FLOW

```
START
  ↓
gap_analysis → gate_gaps
  ↓              ↓
  [gaps]     [no gaps]
  ↓              ↓
enrich_config   gate_template
  ↓              ↓
gate_template ←──┘
  ↓
  [update needed?]
  ↓         ↓
update    generate
  ↓         ↓
generate ←──┘
  ↓
validate → gate_validation
  ↓              ↓
  [pass]      [fail]
  ↓              ↓
report      enrich_config (loop)
  ↓
END
```

---

## SUCCESS CRITERIA

- [ ] All subsystems in config have README.md
- [ ] DORA headers present in all READMEs
- [ ] ASCII diagrams render correctly
- [ ] No template variables remaining (e.g., `{subsystem_name}`)
- [ ] Validation passes

---

## DO NOT

- ❌ Manually write README content
- ❌ Skip gap analysis
- ❌ Generate without validation
- ❌ Bypass the DAG phases

The DAG enforces the workflow. Follow it.
