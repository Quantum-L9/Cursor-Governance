---
name: Audit Strategy Consolidation
overview: Consolidate and streamline the L9 audit infrastructure by reducing duplication, integrating all Tier 1 audits into CI/CD, and establishing a clear audit execution strategy with proper triggers and reporting.
todos:
  - id: t1-shared-detection
    content: Extract shared detection functions (uncalled functions, orphan classes) into audit_shared_core.py
    status: pending
  - id: t2-refactor-code-integrity
    content: Refactor audit_code_integrity.py to use shared core (remove CacheManager duplicate)
    status: pending
  - id: t3-refactor-find-dead-code
    content: Refactor find_dead_code.py to use shared core (keep vulture/ruff unique logic)
    status: pending
  - id: t4-ci-gates
    content: Add CI gates 14-17 to run_ci_gates.sh for all Tier 1 audits
    status: pending
  - id: t5-unified-cli
    content: Create audit_cli.py as single entry point with --ci and --gmp flags
    status: pending
  - id: t6-update-audit-yaml
    content: "Clean audit.yaml: remove unimplemented Tier 2/3 and export options"
    status: pending
  - id: t7-precommit-hook
    content: "Optional: Add pre-commit hook configuration for fast audit subset"
    status: pending
---

# L9 Audit Strategy Consolidation Plan

## Current State Analysis

### Inventory (17 scripts in `scripts/audit/`)

**Master Orchestrator:**

- [run_all.py](scripts/audit/run_all.py) - Tier 1 orchestrator (1096 lines)

**Dead Code Pipeline (5 files, ~3500 lines total):**

- [find_dead_code.py](scripts/audit/find_dead_code.py) - Phase 1: vulture + ruff (1932 lines)
- [resolve_dead_code_refs.py](scripts/audit/resolve_dead_code_refs.py) - Phase 2: false positive filtering
- [categorize_dead_code.py](scripts/audit/categorize_dead_code.py) - Phase 3: risk categorization
- [generate_gmp_todos.py](scripts/audit/generate_gmp_todos.py) - Phase 4: auto-fix + GMP report
- [run_dead_code_audit.py](scripts/audit/run_dead_code_audit.py) - Pipeline runner

**Tier 1 Audits:**

- [tier1/audit_code_integrity.py](scripts/audit/tier1/audit_code_integrity.py) - Call graph, orphans (1024 lines)
- [tier1/audit_capability_inventory.py](scripts/audit/tier1/audit_capability_inventory.py) - Tool discovery
- [tier1/audit_infrastructure_health.py](scripts/audit/tier1/audit_infrastructure_health.py) - Service probes

**Specialized Audits:**

- [audit_api_signatures.py](scripts/audit/audit_api_signatures.py) - API mismatch detection
- [verify_wiring_alignment.py](scripts/audit/verify_wiring_alignment.py) - Doc-code path alignment
- [verify_memory_spec_v3.py](scripts/audit/verify_memory_spec_v3.py) - Memory spec verification

**Shared Infrastructure:**

- [audit_shared_core.py](scripts/audit/audit_shared_core.py) - CacheManager, Reporter, GMPIntegration
- [audit.yaml](scripts/audit/audit.yaml) - Configuration

---

## Problems Identified

### 1. Duplication

- `find_dead_code.py` + `audit_code_integrity.py` both detect uncalled functions/orphan classes
- Multiple `CacheManager` implementations
- Overlapping false positive logic

### 2. No Automated Triggers

- Only `verify_wiring_alignment.py` is in CI (Gate 12)
- No pre-commit hooks
- No scheduled execution

### 3. Over-Engineering

- 4-phase dead code pipeline is complex for what it does
- Tier 2/3 audits are stubs (not implemented)
- `audit.yaml` defines unimplemented features (Datadog, Slack, substrate export)

### 4. Scattered Audit Code

- `scripts/memory/audit_graphs.py` - separate location
- `core/compliance/audit_log.py`, `audit_reporter.py` - compliance layer
- No unified entry point

---

## Consolidation Strategy

### Phase 1: Reduce Duplication (Remove ~800 lines)

**Action:** Extract overlapping logic from `find_dead_code.py` and `audit_code_integrity.py` into shared modules

| Component | Current Location | Consolidate To |

|-----------|-----------------|----------------|

| Uncalled function detection | Both files | `audit_shared_core.py` |

| Orphan class detection | Both files | `audit_shared_core.py` |

| CacheManager | Both files | Keep in `audit_shared_core.py` only |

| File hash/incremental logic | Both files | `audit_shared_core.py` |

**Files to modify:**

- `scripts/audit/audit_shared_core.py` - Add shared detection functions
- `scripts/audit/tier1/audit_code_integrity.py` - Import from shared core
- `scripts/audit/find_dead_code.py` - Import from shared core (keep pipeline-specific logic)

### Phase 2: CI Integration (Add All Tier 1 to Pipeline)

**Current CI:** Only Gate 12 (wiring alignment)

**Target CI:** Add new gates to [ci/run_ci_gates.sh](ci/run_ci_gates.sh)

```
GATE 14: DEAD CODE AUDIT (--quick mode, ~30s)
GATE 15: API SIGNATURE CHECK (~10s)
GATE 16: CODE INTEGRITY (--fast mode, ~20s)
GATE 17: MEMORY SPEC VERIFICATION (~5s)
```

**Fast mode requirements:**

- Use cached results when possible
- Skip full call graph build
- Focus on critical findings only

**Estimated total CI time:** < 90 seconds for all Tier 1 audits

### Phase 3: Unified Entry Point

**Create:** `scripts/audit/audit_cli.py` - Single CLI for all audits

```python
# Usage examples:
python scripts/audit/audit_cli.py --all              # Run all Tier 1
python scripts/audit/audit_cli.py --ci               # CI-optimized (fast)
python scripts/audit/audit_cli.py --dead-code        # Dead code pipeline only
python scripts/audit/audit_cli.py --tier 2           # Future: governance audits
```

**Benefits:**

- Single entry point for all audit operations
- Consistent flags across all audits
- Unified reporting and GMP integration

### Phase 4: Clean Up Stubs and Config

**Remove/deprecate:**

- Tier 2/3 stubs in `audit.yaml` (mark as `# TODO: Future`)
- Unimplemented export options (Datadog, Slack, substrate)

**Update:**

- `audit.yaml` - Clean config with only implemented features
- Add `audit.rules.yaml` if rules file is referenced but missing

---

## Implementation TODOs

### T1: Create shared detection module in audit_shared_core.py

- Extract `find_uncalled_functions()` from both files
- Extract `find_orphan_classes()` from both files
- Unify CacheManager to single implementation
- Add `@must_stay_async` decorators where needed

### T2: Refactor audit_code_integrity.py to use shared core

- Remove duplicate CacheManager
- Import shared detection functions
- Reduce file from ~1024 to ~400 lines

### T3: Refactor find_dead_code.py to use shared core

- Import shared detection (uncalled/orphan)
- Keep vulture/ruff integration (unique to this file)
- Keep Phase 1-4 pipeline intact
- Reduce file from ~1932 to ~1200 lines

### T4: Add CI gates to run_ci_gates.sh

- GATE 14: Dead code (--quick)
- GATE 15: API signatures
- GATE 16: Code integrity (--fast)
- GATE 17: Memory spec

### T5: Create unified audit_cli.py

- Single entry point
- Subcommands for each audit type
- --ci flag for fast mode
- --gmp flag for GMP report generation

### T6: Update audit.yaml

- Remove unimplemented Tier 2/3 content
- Remove unimplemented export options
- Add clear comments for future features

### T7: Add pre-commit hook option

- Create `.pre-commit-config.yaml` entry
- Run fast audit subset on commit

---

## File Structure After Consolidation

```
scripts/audit/
├── audit_cli.py              # NEW: Unified CLI entry point
├── audit_shared_core.py      # EXPANDED: All shared detection logic
├── audit.yaml                # CLEANED: Only implemented features
│
├── tier1/
│   ├── audit_code_integrity.py    # REDUCED: Uses shared core
│   ├── audit_capability_inventory.py
│   └── audit_infrastructure_health.py
│
├── dead_code/                # REORGANIZED: Pipeline in subdirectory
│   ├── find_dead_code.py     # REDUCED: Uses shared core
│   ├── resolve_refs.py       # RENAMED for clarity
│   ├── categorize.py         # RENAMED for clarity
│   ├── generate_gmp.py       # RENAMED for clarity
│   └── runner.py             # RENAMED from run_dead_code_audit.py
│
├── specialized/              # REORGANIZED: Clear category
│   ├── audit_api_signatures.py
│   ├── verify_wiring_alignment.py
│   └── verify_memory_spec_v3.py
│
├── run_all.py               # DEPRECATED: Use audit_cli.py instead
└── cleanup_audit_reports.py
```

---

## CI Pipeline Changes

**File:** `.github/workflows/ci.yml`

Add new job after `validate`:

```yaml
audit:
  name: Tier 1 Audits
  runs-on: ubuntu-latest
  needs: [validate]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Run Tier 1 Audits
      run: |
        pip install vulture ruff structlog pyyaml
        python scripts/audit/audit_cli.py --ci --fail-on-critical
```

---

## Success Criteria

- [ ] Single CLI entry point for all audits
- [ ] All Tier 1 audits run in CI (< 90s total)
- [ ] Code duplication reduced by ~800 lines
- [ ] Clear separation: shared core vs. specialized audits
- [ ] Dead code pipeline preserved (4 phases intact)
- [ ] GMP report generation works from CLI

---

## Risk Mitigation

| Risk | Mitigation |

|------|------------|

| Refactoring breaks existing functionality | Run full audit suite before/after each change |

| CI becomes too slow | Implement --fast mode with caching |

| False positives block PRs | Start with warnings-only, then enforce |

| Pipeline changes confuse users | Add clear deprecation notices, migration docs |

---

## Estimated Effort

| Phase | Effort | Priority |

|-------|--------|----------|

| Phase 1: Reduce duplication | 2-3 hours | HIGH |

| Phase 2: CI integration | 1-2 hours | HIGH |

| Phase 3: Unified CLI | 1-2 hours | MEDIUM |

| Phase 4: Clean up config | 30 min | LOW |

**Total:** 5-8 hours for full consolidation
