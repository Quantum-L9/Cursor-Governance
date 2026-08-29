---
name: Dead Code Cleanup v2
overview: "Rigorous 5-phase dead code removal plan with safety rails, incremental validation, and explicit GMP scoping. Target: reduce 502 findings to under 50 legitimate edge cases with zero test regressions."
todos:
  - id: p0-verify-script
    content: Verify scripts/audit/find_dead_code.py exists and works
    status: completed
  - id: p0-install-tools
    content: "Install vulture and ruff: pip3 install vulture ruff"
    status: completed
  - id: p0-baseline
    content: "Run baseline audit: python3 scripts/audit/find_dead_code.py --output reports/dead_code_baseline_phase0.json"
    status: completed
  - id: p1-exclusions
    content: Update EXCLUDE_DIRS to add docs, codegen, igor, Perplexity-Search-Pack
    status: completed
  - id: p1-validate
    content: Re-run audit with --wiring-only, verify count drops from 502 to ~382
    status: completed
  - id: p2-branch
    content: "Create branch: git checkout -b dead-code-phase-2"
    status: completed
  - id: p2-gmp-routers
    content: "GMP-DC-01: Wire 26 routers to api/server.py"
    status: completed
  - id: p2-gmp-deps
    content: "GMP-DC-02: Wire or delete 6 dependencies in api/dependencies.py"
    status: completed
  - id: p2-gmp-tools
    content: "GMP-DC-03: Register AGENT_SELF_MODIFY_TOOL_DEFINITIONS"
    status: completed
  - id: p2-validate
    content: "Validate Phase 2: unwired_router=0, unwired_dependency=0, unwired_tool=0"
    status: completed
  - id: p3-branch
    content: "Create branch: git checkout -b dead-code-phase-3"
    status: completed
  - id: p3-gmp-dataclass
    content: "GMP-DC-04 to DC-07: Remove 292 unused dataclass fields in batches"
    status: in_progress
  - id: p3-gmp-services
    content: "GMP-DC-08: Wire or delete 12 unwired services"
    status: pending
  - id: p3-gmp-orchestrators
    content: "GMP-DC-09: Wire or delete 9 unwired orchestrators"
    status: pending
  - id: p3-gmp-background
    content: "GMP-DC-10 to DC-11: Fix 33 unwired background tasks"
    status: pending
  - id: p3-validate
    content: "Validate Phase 3: dataclass_field count <30"
    status: pending
  - id: p4-branch
    content: "Create branch: git checkout -b dead-code-phase-4"
    status: pending
  - id: p4-gmp-final
    content: "GMP-DC-12: Wire events, pydantic, document edge cases"
    status: pending
  - id: p4-final-audit
    content: Run final audit, verify <50 findings
    status: pending
  - id: signoff
    content: Complete sign-off checklist, merge to main
    status: pending
---

# Dead Code Cleanup Plan v2

## Executive Summary

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Total Findings | 502 | <50 | Phased removal with validation |
| False Positives | ~120 | 0 | Exclusion pattern updates |
| Legitimate Issues | ~382 | ~50 | Delete/wire/document |
| Test Coverage | Baseline | No regression | Per-phase validation |

---

## Phase Breakdown Table

| Phase | Category | Findings | Effort | GMPs | Validation Command | Success Criteria |
|-------|----------|----------|--------|------|-------------------|------------------|
| 0 | Prerequisites + Baseline | N/A | 1 hour | 0 | `python3 scripts/audit/find_dead_code.py` | Baseline JSON created, tools installed |
| 1 | False Positives (exclusions) | 120 | 30 min | 0 | `--wiring-only` quick scan | Archived/codegen excluded, count drops to ~382 |
| 2 | Wiring Issues (routers, deps, tools) | 33 | 3 hours | 3 | `pytest tests/api/ -x` | All routers mounted, deps wired, 0 import errors |
| 3 | Unused Code (dataclass fields, services) | 313 | 6 hours | 8 | `pytest --tb=short` | Fields removed, no AttributeError, tests pass |
| 4 | Edge Cases (events, background, pydantic) | 36 | 1 hour | 1 | Full audit | <50 findings, all documented |

---

## Phase 0: Prerequisites and Baseline

### 0.1 Verify Audit Script Exists

**Path:** [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py)

```bash
ls -la scripts/audit/find_dead_code.py
# Expected: File exists (created earlier in this session)
```

### 0.2 Install Missing Tools

```bash
pip3 install vulture ruff
python3 -m vulture --version  # Verify: vulture 2.x
python3 -m ruff --version     # Verify: ruff 0.x
```

### 0.3 Run Baseline Audit

```bash
python3 scripts/audit/find_dead_code.py \
  --output reports/dead_code_baseline_phase0.json \
  --format json
```

### 0.4 Categorize 502 Findings

Generate category breakdown:

```bash
cat reports/dead_code_baseline_phase0.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
cats = {}
for f in d['findings']:
    t = f['symbol_type']
    cats[t] = cats.get(t, 0) + 1
for t, c in sorted(cats.items(), key=lambda x: -x[1]):
    print(f'{t}: {c}')
"
```

**Expected Output:**
```
dataclass_field: 292
unwired_agent: 104
unwired_background: 33
unwired_router: 26
unwired_kernel: 16
unwired_service: 12
unwired_orchestrator: 9
unwired_dependency: 6
unwired_event: 2
unwired_tool: 1
unwired_pydantic: 1
```

### 0.5 Define Legitimate Edge Cases

These findings are ACCEPTABLE and should not be "fixed":

| Category | Legitimate Cases | Threshold |
|----------|------------------|-----------|
| dataclass_field | API contract fields (never accessed locally but serialized) | Document with `# API: ` comment |
| unwired_agent | Agent configs loaded dynamically via env vars | Document in README |
| unwired_service | Services instantiated via DI framework | Must have `Depends()` or factory |
| unwired_orchestrator | Orchestrators used via reflection/registry | Must be in registry |

**Final Target:** <50 findings, all documented with justification.

---

## Phase 1: False Positive Elimination

### 1.1 Update Exclusion Patterns

**File:** [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py)

**Current `EXCLUDE_DIRS`:**
```python
EXCLUDE_DIRS = {"tests", "_archived", "__pycache__", ".venv", "venv", ".git", "node_modules"}
```

**Updated `EXCLUDE_DIRS`:**
```python
EXCLUDE_DIRS = {
    "tests", "_archived", "__pycache__", ".venv", "venv", ".git", "node_modules",
    "docs",           # Non-Python files with .py extension
    "codegen",        # Generated specs, not production code
    "igor",           # Audit tools, not production code
    "Perplexity-Search-Pack",  # External package
}
```

### 1.2 Exclude Codegen Agent Specs Pattern

Add to `find_unwired_agents()`:
```python
# Skip generated spec directories
if "codegen+codegenAgent_specs" in str(filepath):
    continue
```

### 1.3 Validation Command

```bash
# Quick wiring-only scan (skips vulture/ruff/dataclass)
python3 scripts/audit/find_dead_code.py --wiring-only --output reports/phase1_check.json

# Compare counts
echo "Before: 502, After: $(cat reports/phase1_check.json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["findings"]))')"
```

**Success Criteria:** Count drops from 502 to ~382 (120 false positives removed).

---

## Phase 2: Wiring Issues (HIGH Priority)

### Safety Rails

```bash
# Create branch BEFORE any changes
git checkout -b dead-code-phase-2

# Run baseline tests for affected modules
pytest tests/api/ -x --tb=short
```

### 2.1 GMP-DC-01: Wire Routers (26 findings)

**Scope:** Mount all legitimate routers in [api/server.py](api/server.py)

**TODO Plan:**
| File | Line | Action | Target |
|------|------|--------|--------|
| `api/server.py` | EOF | Insert | `app.include_router(os_router, prefix="/os")` |
| `api/server.py` | EOF | Insert | `app.include_router(webhook_twilio_router, prefix="/webhook/twilio")` |
| `api/server.py` | EOF | Insert | `app.include_router(webhook_mac_router, prefix="/webhook/mac")` |
| ... | ... | ... | ... (23 more) |

**Validation:**
```bash
# Check no import errors
python3 -c "from api.server import app; print('OK')"

# Run API tests
pytest tests/api/ -x --tb=short
```

### 2.2 GMP-DC-02: Wire Dependencies (6 findings)

**Scope:** Use or delete deps in [api/dependencies.py](api/dependencies.py)

**TODO Plan:**
| Dependency | Used In | Action |
|------------|---------|--------|
| `get_agent_executor` | None found | DELETE or wire to agent routes |
| `get_governance_engine` | None found | DELETE or wire to governance routes |
| `get_neo4j_client` | None found | DELETE or wire to graph routes |
| `get_redis_client` | None found | DELETE or wire to cache routes |
| `get_observability_service` | None found | DELETE or wire to metrics routes |
| `get_world_model_service` | None found | DELETE or wire to world model routes |

**Validation:**
```bash
pytest tests/api/test_dependencies.py -v
```

### 2.3 GMP-DC-03: Register Tool Definitions (1 finding)

**Scope:** Register `AGENT_SELF_MODIFY_TOOL_DEFINITIONS` in [core/tools/agent_self_modify.py](core/tools/agent_self_modify.py)

**TODO Plan:**
| File | Line | Action | Change |
|------|------|--------|--------|
| `core/tools/agent_self_modify.py` | 400 | Insert | Call `register_self_modify_tools()` in module init |

**Validation:**
```bash
python3 -c "from core.tools.agent_self_modify import AGENT_SELF_MODIFY_TOOL_DEFINITIONS; print(f'Tools: {len(AGENT_SELF_MODIFY_TOOL_DEFINITIONS)}')"
```

### Phase 2 Completion

```bash
# Run phase-specific validation
python3 scripts/audit/find_dead_code.py --wiring-only --output reports/phase2_check.json

# Expected: unwired_router=0, unwired_dependency=0, unwired_tool=0
cat reports/phase2_check.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in ['unwired_router', 'unwired_dependency', 'unwired_tool']:
    count = len([f for f in d['findings'] if f['symbol_type'] == t])
    status = '✅' if count == 0 else '❌'
    print(f'{status} {t}: {count}')
"

# Merge if passing
git checkout main && git merge dead-code-phase-2
```

---

## Phase 3: Unused Code Removal (MEDIUM Priority)

### Safety Rails

```bash
git checkout -b dead-code-phase-3
pytest --tb=short -q  # Full baseline
```

### 3.1-3.4 Dataclass Field GMPs (292 findings, 4 GMPs)

**Strategy:** Batch by file, 10-15 deletions per GMP.

| GMP | Files | Fields | Validation |
|-----|-------|--------|------------|
| GMP-DC-04 | `memory/hybrid_rag.py`, `memory/schema_introspection.py` | 20 | `pytest tests/memory/` |
| GMP-DC-05 | `core/evaluation/evaluator.py`, `core/testing/` | 15 | `pytest tests/core/` |
| GMP-DC-06 | `core/agents/`, `core/governance/` | 15 | `pytest tests/core/agents/` |
| GMP-DC-07 | All remaining dataclass files | ~242 | `pytest --tb=short` |

**Per-GMP TODO Template:**
```markdown
## TODO PLAN (LOCKED)

- [T1] File: `memory/hybrid_rag.py`
       Lines: 45-47
       Action: Delete
       Target: `HybridRAGConfig.unused_field_1`
       Change: Remove field definition
       Gate: py_compile

- [T2] File: `memory/hybrid_rag.py`
       Lines: 52-54
       Action: Delete
       Target: `HybridRAGConfig.unused_field_2`
       Change: Remove field definition
       Gate: pytest tests/memory/test_hybrid_rag.py
```

### 3.5-3.6 Service and Orchestrator GMPs (21 findings, 2 GMPs)

| GMP | Category | Count | Action |
|-----|----------|-------|--------|
| GMP-DC-08 | unwired_service | 12 | Delete `igor/audit-memory/` services, wire adapters |
| GMP-DC-09 | unwired_orchestrator | 9 | Wire to orchestration registry or delete |

### 3.7-3.8 Background Tasks (33 findings, 2 GMPs)

| GMP | Files | Count | Action |
|-----|-------|-------|--------|
| GMP-DC-10 | `runtime/gmp_worker.py`, `runtime/gmp_approval.py` | 12 | Wire via `add_task()` or rename |
| GMP-DC-11 | All others | 21 | Rename methods (remove `_async` suffix if not scheduled) |

### Phase 3 Completion

```bash
# Run targeted audit (dataclass fields only)
python3 scripts/audit/find_dead_code.py --output reports/phase3_check.json

# Count remaining dataclass findings
cat reports/phase3_check.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
count = len([f for f in d['findings'] if f['symbol_type'] == 'dataclass_field'])
print(f'Remaining dataclass_field findings: {count}')
print('✅ PASS' if count < 30 else '❌ FAIL - investigate')
"

git checkout main && git merge dead-code-phase-3
```

---

## Phase 4: Edge Cases and Final Verification

### Safety Rails

```bash
git checkout -b dead-code-phase-4
```

### 4.1 GMP-DC-12: Final Cleanup

| Category | Count | Action |
|----------|-------|--------|
| unwired_event | 2 | Wire `@app.on_event()` decorators |
| unwired_pydantic | 1 | Use in route or delete |
| Remaining | ~33 | Document as legitimate edge cases |

### 4.2 Final Full Audit

```bash
python3 scripts/audit/find_dead_code.py \
  --output reports/dead_code_final.json \
  --format json

# Generate summary
cat reports/dead_code_final.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Total findings: {len(d[\"findings\"])}')
cats = {}
for f in d['findings']:
    cats[f['symbol_type']] = cats.get(f['symbol_type'], 0) + 1
for t, c in sorted(cats.items(), key=lambda x: -x[1]):
    print(f'  {t}: {c}')
"
```

---

## Rollback Procedures

### Per-Phase Rollback

```bash
# If tests fail after phase changes:
git checkout main
git branch -D dead-code-phase-N  # Delete failed branch

# Investigate:
git diff main..dead-code-phase-N -- <failing_file>
```

### Rollback Triggers

| Trigger | Action |
|---------|--------|
| Any test failure in phase validation | Revert entire phase branch |
| Import errors after router wiring | Revert GMP, check circular imports |
| AttributeError after field deletion | Field was used dynamically, restore and document |
| Audit count INCREASES after phase | Revert, investigate new findings |

### Emergency Full Rollback

```bash
# If production issues after merge:
git revert --no-commit HEAD~N..HEAD  # N = commits since phase start
git commit -m "Revert: Dead code cleanup caused regression"
```

---

## Final Acceptance Criteria

### Quantitative

| Metric | Threshold | Verification |
|--------|-----------|--------------|
| Total findings | <50 | `jq '.findings | length' reports/dead_code_final.json` |
| Test pass rate | 100% | `pytest --tb=short` exits 0 |
| Import errors | 0 | `python3 -c "import api.server"` |
| Type errors | 0 | `pyright api/ core/ memory/` (if configured) |

### Qualitative

| Requirement | Verification |
|-------------|--------------|
| All remaining findings documented | Each has `# LEGITIMATE: <reason>` comment |
| No broken API contracts | Manual review of deleted dataclass fields |
| No orphaned routes | `curl` test of all wired endpoints |
| GMP reports generated | `ls reports/GMP_Report_GMP-DC-*.md` |

### Sign-off Checklist

- [ ] Phase 0 baseline created
- [ ] Phase 1 exclusions applied (120 false positives removed)
- [ ] Phase 2 wiring complete (33 → 0)
- [ ] Phase 3 unused code removed (313 → <30)
- [ ] Phase 4 edge cases documented
- [ ] Final audit: <50 findings
- [ ] All tests passing
- [ ] GMP reports archived
- [ ] Main branch updated
