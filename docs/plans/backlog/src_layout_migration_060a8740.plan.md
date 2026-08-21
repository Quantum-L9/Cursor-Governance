---
name: src layout migration
overview: Migrate L9 from flat layout (20+ top-level directories) to industry-standard src/l9/ layout using an incremental strategy that maintains backwards compatibility during transition.
todos:
  - id: adr-decision
    content: Create ADR-0056 documenting src/l9/ layout decision and incremental migration strategy
    status: pending
  - id: phase1-skeleton
    content: Create src/l9/ directory structure with re-export __init__.py files
    status: pending
  - id: phase1-pyproject
    content: Update pyproject.toml for src layout with backwards compatibility
    status: pending
  - id: phase2-rules
    content: Update .cursor/rules to enforce l9.* imports in new code
    status: pending
  - id: phase3-tooling
    content: Set up rope/bowler for automated import rewriting
    status: pending
  - id: phase3-core
    content: Migrate core/ module (174 files, 532 imports)
    status: pending
  - id: phase3-memory
    content: Migrate memory/ module (69 files, 205 imports)
    status: pending
  - id: phase3-remaining
    content: Migrate remaining modules (runtime, api, agents, etc.)
    status: pending
  - id: phase4-cleanup
    content: Remove old directories and re-export shims
    status: pending
---

# L9 Source Layout Migration Plan

## Decision Summary

Adopt **Strategy B: Incremental Namespace Migration** to realign L9 with OpenAI/Anthropic `src/` layout pattern.

**Rationale:** Full big-bang migration (Strategy A) is high-risk with 1,200+ import rewrites. Incremental approach provides backwards compatibility via re-exports while gradually migrating.

## Current State

- 57 top-level directories
- 1,388 Python files
- 7,157 import statements
- Key imports: `from core.X`, `from memory.Y`, `from api.Z` (no unified namespace)
- pyproject.toml uses flat layout: `packages = { find = { where = ["."] } }`

## Target State

```
l9/
├── src/
│   └── l9/                  # Single importable package
│       ├── __init__.py      # Package root
│       ├── core/            # from l9.core import X
│       ├── api/             # from l9.api import Y
│       ├── memory/          # from l9.memory import Z
│       ├── runtime/
│       ├── agents/
│       ├── orchestration/
│       └── ...
├── tests/                   # Stays at root
├── scripts/                 # Stays at root
├── config/                  # Stays at root
├── migrations/              # Stays at root
└── pyproject.toml
```

## Migration Phases

### Phase 1: Foundation (Low Risk)

**Deliverables:**

- Create `src/l9/` directory structure
- Add `__init__.py` files with re-exports from current locations
- Update [pyproject.toml](pyproject.toml) to use src layout:
```toml
[tool.setuptools]
package-dir = {"" = "src"}
packages = { find = { where = ["src"] } }
```

- Verify `pip install -e .` works with both old and new imports

**Files to create:**

- `src/l9/__init__.py` — Re-exports all subpackages
- `src/l9/core/__init__.py` — `from core import *` (temporary re-export)
- Similar for: `api`, `memory`, `runtime`, `agents`, `orchestration`, `orchestrators`, `workers`, `clients`, `services`, `tools`, `world_model`

### Phase 2: New Code Convention (No Risk)

**Deliverables:**

- Update [.cursor/rules/00-global.mdc](.cursor/rules/00-global.mdc) to require `from l9.X import Y` in new files
- Add CI lint check for import style in new files
- Document import convention in README

**Enforcement rule:**

```python
# NEW CODE (required):
from l9.core.agents import AgentExecutorService

# OLD CODE (allowed during migration):
from core.agents import AgentExecutorService
```

### Phase 3: Gradual Migration (Controlled Risk)

**Approach:** One module at a time, automated import rewriting

**Migration order (by dependency depth):**

1. `core/` (174 files, 532 imports) — Foundation, migrate first
2. `memory/` (69 files, 205 imports) — Depends on core
3. `runtime/` (30 files, 59 imports) — Depends on core
4. `api/` (44 files, 79 imports) — Depends on core, memory, runtime
5. `agents/`, `orchestrators/` (91 files) — Depends on above
6. Remaining modules (services, tools, world_model, etc.)

**Per-module process:**

1. Move files: `core/` to `src/l9/core/`
2. Run `rope` or `bowler` to rewrite imports in all files
3. Update re-export `__init__.py` to point to new location
4. Run full test suite
5. Create PR for review
6. Merge when green

**Tooling:**

- Primary: `rope` (Python refactoring library)
- Alternative: `bowler` (Facebook's refactoring tool)
- Fallback: `rg --replace` for simple patterns

### Phase 4: Cleanup (Low Risk)

**Deliverables:**

- Remove old top-level directories (`core/`, `memory/`, etc.)
- Remove re-export shims from `__init__.py` files
- Update pyproject.toml to final form
- Update all documentation (README, RUNBOOK)
- Update CI/CD scripts if needed

## Risk Mitigation

| Risk | Mitigation |

|------|------------|

| Broken imports | Re-export pattern maintains backwards compatibility |

| Test failures | Full test suite run per-module migration |

| Merge conflicts | Small PRs, coordinate with active branches |

| Deployment issues | Test `pip install` at each phase |

| Git history loss | Use `git mv` to preserve history |

## Estimated Effort

| Phase | Duration | Effort |

|-------|----------|--------|

| Phase 1 | 2-3 hours | Low |

| Phase 2 | 1-2 hours | Low |

| Phase 3 | 2-3 weeks | Medium (automated) |

| Phase 4 | 2-3 hours | Low |

## Success Criteria

- All tests pass
- CI pipeline green
- `pip install -e .` works
- All imports use `l9.*` namespace
- No duplicate module warnings from mypy

## References

- OpenAI Python SDK: [github.com/openai/openai-python](https://github.com/openai/openai-python) (src/openai/)
- Anthropic Python SDK: [github.com/anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) (src/anthropic/)
- Python Packaging Authority: src layout recommendation