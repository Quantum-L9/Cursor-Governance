---
name: Dead Code Audit v2.0
overview: 5-phase production-ready dead code detection with false positive elimination, risk categorization, and automated /gmp remediation.
todos:
  - id: phase1-baseline
    content: "Create scripts/audit/find_dead_code.py: vulture (--min-confidence=80) + ruff (F401,F841,ARG) + custom AST for dataclass fields + parallel scanning"
    status: completed
  - id: phase2-resolve
    content: "Create scripts/audit/resolve_dead_code_refs.py: eliminate false positives via getattr detection, registry patterns, Protocol implementations, inheritance chains"
    status: completed
  - id: phase3-categorize
    content: "Create scripts/audit/categorize_dead_code.py: classify by risk (HIGH/MEDIUM/LOW), assign confidence scores, determine action (WIRE_UP/DELETE/NOQA)"
    status: completed
  - id: phase4-generate
    content: "Create scripts/audit/generate_gmp_todos.py: auto-generate GMP Phase 0 TODO plan (reports/dead_code_gmp_todos.yaml) with line numbers and proposed fixes"
    status: completed
  - id: phase5-gmp
    content: "Execute /gmp GMP-63 with generated TODO plan: auto-fix low-risk items, manual review high-risk configs, revalidate with 0 new dead code"
    status: in_progress
  - id: ci-integrate
    content: Update scripts/audit/run_all.py with run_dead_code_pipeline() orchestrator + create .vultureignore whitelist
    status: completed
---

# Dead Code Audit v2.0 - Production-Ready Plan

## Problem Statement

The L9 repo has "defined but never used" code patterns (e.g., `AgentConfig.retry_count` was defined but never wired up). This plan creates a systematic audit to find ALL such instances, eliminate false positives, and fix them via `/gmp`.

## Detection Categories

| Category | Tool | Confidence | Risk |

|----------|------|------------|------|

| Unused imports | `ruff F401` | 98% | Low |

| Unused variables | `ruff F841` | 95% | Low |

| Unused function args | `ruff ARG` | 90% | Low |

| Config/dataclass fields | **Custom AST** | 95% | HIGH |

| Class attributes | `vulture --min-confidence=80` | 80% | Medium |

| Private methods | `vulture` + cross-ref | 70% | Medium |

| Dead branches | `ruff` | 98% | Low |

---

## Phase 1: Baseline Static Analysis (WITH DEDUPLICATION)

**Create:** [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py)

**Tools:**

- Vulture with high confidence threshold (`--min-confidence=80`)
- Ruff (`F401`, `F841`, `ARG001-ARG005`)
- Custom AST for dataclass/config fields
- Coverage integration (parse `.coverage` file)

**Dataclass Field Detection (PROPER):**

```python
def find_dataclass_field_access(field_name, class_name):
    patterns = [
        f"self.{field_name}",           # Direct access
        f"obj.{field_name}",            # Via reference
        f"['{field_name}']",            # Dict-like
        f'["{field_name}"]',
        f"getattr(.*{field_name}",      # Dynamic
        f"asdict(.*{field_name}",       # Via asdict
        f"__dict__['{field_name}']",    # Via __dict__
    ]
    # Search entire codebase, filter comments/strings
```

**Execution:**

```bash
python scripts/audit/find_dead_code.py \
  --min-vulture-confidence 80 \
  --coverage-file .coverage \
  --exclude tests,_archived,__pycache__ \
  --parallel 8 \
  --output reports/dead_code_baseline.json
```

**Output:** `reports/dead_code_baseline.json`

---

## Phase 2: Cross-Reference Resolution (ELIMINATE FALSE POSITIVES)

**Create:** [scripts/audit/resolve_dead_code_refs.py](scripts/audit/resolve_dead_code_refs.py)

Purpose: Reduce 30-50% false positives by checking:

| Pattern | Detection | Action |

|---------|-----------|--------|

| `getattr()` / `__dict__` access | Grep for dynamic patterns | Mark NOT dead |

| `importlib.import_module()` | Track dynamic imports | Mark NOT dead |

| Registry patterns (`@register`) | Decorator analysis | Mark NOT dead |

| Protocol/ABC implementations | Inheritance chain | Mark NOT dead |

| Test fixtures/mocks | File path check | Add `# noqa` |

| Subclass usage | Class hierarchy scan | Mark NOT dead |

**False Positive Detection:**

```python
def is_truly_dead(symbol, codebase):
    # Check 1: Dynamic access via getattr
    if grep(f"getattr(.*{symbol.name}", codebase):
        return False
    
    # Check 2: Registry pattern
    if "@register" in symbol.decorators:
        return False
    
    # Check 3: Protocol implementation
    if symbol in protocol_implementations:
        return False
    
    # Check 4: Inheritance chain
    if used_in_any_subclass(symbol):
        return False
    
    return True  # Truly dead
```

**Output:** `reports/dead_code_resolved.json`

```json
{
  "dead_code_instances": [
    {
      "file": "agents/base_agent.py",
      "symbol": "AgentConfig.retry_count",
      "type": "dataclass_field",
      "accessed_in": [],
      "confidence": 0.95,
      "reason": "Never read outside class definition",
      "false_positive_risk": "medium"
    }
  ],
  "false_positives_eliminated": 47,
  "remaining_findings": 23
}
```

---

## Phase 3: Categorize by Risk + Fix Strategy

**Create:** [scripts/audit/categorize_dead_code.py](scripts/audit/categorize_dead_code.py)

**Risk Classification:**

| Category | Confidence | Action | Auto-fixable |

|----------|------------|--------|--------------|

| Unused import | 98% | Auto-remove via ruff | YES |

| Config field (never accessed) | 95% | Manual: wire-up or deprecate | NO |

| Dead branch (after return) | 98% | Auto-remove | YES |

| Private method (never called) | 70% | Delete if not in subclasses | MAYBE |

| Test fixture / Mock | 5% | Add `# noqa` comment | YES |

| Dynamic dispatch (registry) | 5% | Add explanatory comment | YES |

**Confidence Scoring:**

```python
HIGH_RISK = {
    "config_field": 0.95,        # Almost certainly a bug
    "public_method": 0.85,       # Breaking API change
    "imported_but_unused": 0.98, # Safe to remove
}
MEDIUM_RISK = {
    "private_method": 0.70,      # Could be used in subclasses
    "internal_constant": 0.75,   # Could be legacy
}
LOW_RISK = {
    "test_fixture": 0.05,        # Always add # noqa
    "mock_object": 0.05,
}
```

**Output:** `reports/dead_code_risk_matrix.json`

```json
{
  "high_risk": [
    {"symbol": "AgentConfig.retry_count", "reason": "Config field—likely bug", "action": "WIRE_UP"}
  ],
  "medium_risk": [...],
  "low_risk": [...],
  "false_positives": [...],
  "auto_fixable": 15,
  "manual_review": 8
}
```

---

## Phase 4: Generate GMP Phase 0 TODO Plan

**Create:** [scripts/audit/generate_gmp_todos.py](scripts/audit/generate_gmp_todos.py)

Auto-generate `/gmp` executable TODO plan from findings:

**Output:** `reports/dead_code_gmp_todos.yaml`

```yaml
gmp_id: GMP-63
task_name: dead_code_remediation
risk_level: Medium

todos:
 - id: DC-001
    file: agents/base_agent.py
    target_symbol: "AgentConfig.retry_count"
    lines: "50"
    action: WIRE_UP
    reason: "Config field defined but never used"
    proposed_fix: |
      Wire into BaseAgent.__init__ retry logic (already done in GMP-62),
      or delete if redundant.
    confidence: 0.95
    test_needed: true
    
 - id: DC-002
    file: memory/substrate_graph.py
    target_symbol: "_unused_helper"
    lines: "145-150"
    action: DELETE
    reason: "Private method, no internal calls"
    confidence: 0.98
    test_needed: false
    
 - id: DC-003
    file: api/server.py
    target_symbol: "import asyncio"
    lines: "15"
    action: DELETE
    reason: "Unused import"
    confidence: 0.99
    test_needed: false
    auto_fix: true  # ruff --fix can handle this
```

**Markdown Report:** `reports/dead_code_gmp_plan.md`

---

## Phase 5: /gmp Execution + Revalidation

**Execute:** `/gmp` with the generated TODO plan

**Workflow:**

1. Load `reports/dead_code_gmp_todos.yaml`
2. Execute Phase 0-6 GMP flow
3. Apply fixes:

      - Auto-fix low-risk items (unused imports, dead branches)
      - Manual review for high-risk items (config fields, public methods)
      - Add `# noqa: vulture` for intentional "dead" code

4. Re-scan codebase
5. Assert: **0 new dead code introduced**

**Final Report:** `reports/GMP_Report_GMP-63-Dead-Code-Remediation.md`

---

## Files to Create

| File | Purpose |

|------|---------|

| [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py) | Phase 1: Baseline static analysis |

| [scripts/audit/resolve_dead_code_refs.py](scripts/audit/resolve_dead_code_refs.py) | Phase 2: False positive elimination |

| [scripts/audit/categorize_dead_code.py](scripts/audit/categorize_dead_code.py) | Phase 3: Risk categorization |

| [scripts/audit/generate_gmp_todos.py](scripts/audit/generate_gmp_todos.py) | Phase 4: GMP TODO generation |

| [.vultureignore](.vultureignore) | Vulture whitelist for intentional patterns |

| `reports/dead_code_*.json` | Intermediate outputs |

| `reports/dead_code_gmp_todos.yaml` | GMP-ready TODO plan |

---

## CI Integration

**Update:** [scripts/audit/run_all.py](scripts/audit/run_all.py)

```python
async def run_dead_code_pipeline():
    # Phase 1: Static analysis
    baseline = await run_dead_code_audit(min_confidence=80, parallel=8)
    
    # Phase 2: Resolve false positives
    resolved = await resolve_dead_code_refs(baseline)
    
    # Phase 3: Categorize by risk
    categorized = await categorize_dead_code(resolved)
    
    # Phase 4: Generate TODO plan
    todos = await generate_gmp_todos(categorized)
    
    # Phase 5: [Optional] Auto-execute low-risk fixes
    if all(t['risk'] == 'low' for t in todos['auto_fixable']):
        await auto_fix_dead_code(todos['auto_fixable'])
    
    return {
        "baseline_count": len(baseline),
        "false_positives_eliminated": baseline - resolved,
        "high_risk": len(categorized['high_risk']),
        "auto_fixable": len(todos['auto_fixable']),
        "manual_review": len(todos['manual_review']),
    }
```

---

## Performance Optimization

**Parallel Scanning (500+ files in ~5s):**

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(scan_file, file_list))
```

**Incremental Mode (CI):**

- Only scan changed files (via git diff)
- Cache AST parse results
- Skip unchanged modules

---

## Validation Checklist

- [ ] Vulture findings verified (80+ confidence)
- [ ] Cross-reference graph built (no false positives)
- [ ] Risk matrix generated (color-coded)
- [ ] Phase 0 TODO plan ready for `/gmp`
- [ ] GMP execution completed
- [ ] Re-scan: 0 new dead code
- [ ] CI pipeline passes
- [ ] Report: `reports/GMP_Report_GMP-63-Dead-Code-Remediation.md`