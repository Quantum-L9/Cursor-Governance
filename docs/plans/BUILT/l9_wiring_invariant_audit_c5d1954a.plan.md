---
name: L9 Wiring Invariant Audit
overview: Establish and enforce a repo-wide wiring invariant that ensures all references to Memory APIs and Cursor integration point to actual files, consistent with the current router layout and memory substrate topology. This protects the integrity of the Memory + Cursor integration boundary.
todos:
  - id: fix-stale-paths
    content: Replace api/routes/memory.py with api/memory/router.py in gap-analysis-memory.md (7+ occurrences)
    status: completed
  - id: add-alignment-table
    content: Insert Doc-Code Alignment Table into gap-analysis-memory.md
    status: completed
  - id: add-guardrail
    content: Add validate_no_deprecated_paths() guardrail to scripts/audit/run_all.py
    status: completed
  - id: create-verifier
    content: Create scripts/audit/verify_wiring_alignment.py wiring verifier script
    status: completed
  - id: regen-cache
    content: Regenerate audit cache with python3 scripts/audit/run_all.py --skip-cache
    status: completed
  - id: run-verification
    content: Run verification checklist to confirm green criteria met
    status: completed
---

# L9 Wiring Invariant Audit

## Wiring Invariant Definition

**Every referenced path to Memory APIs and Cursor integration must be:**

1. A real file/module in the repo (verified via `file_metrics.txt`)
2. Consistent with the canonical router layout:
   - `api/memory/router.py` (689 LOC) - L9 Memory API
   - `mcp_memory/src/routes/memory.py` / `memory_unified.py` - MCP Memory routes
   - `api/routes/cursor.py` - Cursor API routes
3. Consistent with the memory substrate topology:
   - `memory/substrate_repository.py` (976 LOC)
   - `memory/substrate_service.py` (908 LOC)
   - `memory/substrate_graph.py` (836 LOC)
4. Consistent with Cursor integration location:
   - `agents/cursor/cursor_memory_kernel.py` (689 LOC)
   - `agents/cursor/extractors/cursor_action_extractor.py` (661 LOC)
   - `agents/cursor/integrations/cursor_*.py`

## Protected Boundaries (DO NOT MODIFY)

These files are OUT OF SCOPE - only references TO them may be fixed:
- `core/governance/approval_manager.py` - Governance engine
- `core/governance/engine.py` - Policy engine
- `memory/governance_patterns.py` - Memory governance
- `core/schemas/packet_envelope*.py` - Packet protocol
- `memory/substrate_models.py` - Data models

---

## Step 1: Pattern-Based Doc-Code Cross-Check

### 1.1 Scan Targets

Scan these locations for path references:
- `docs/**/*.md`
- `*.md` (root level)
- `readme/**/*.md`
- `reports/**/*.md`
- `scripts/audit/**/*.py`
- `scripts/memory/**/*.py`

### 1.2 Stale Path Patterns to Detect

| Pattern | Status | Canonical Replacement |
|---------|--------|----------------------|
| `api/routes/memory.py` | STALE | `api/memory/router.py` |
| `tools/cursor_client.py` | MOVED | `agents/cursor/cursor_client.py` |
| `scripts/cursor_check_mistakes.py` | MOVED | `agents/cursor/scripts/cursor_check_mistakes.py` |
| `memory/extractor/cursor_action_extractor.py` | MOVED | `agents/cursor/extractors/cursor_action_extractor.py` |
| `core/governance/cursor_memory_kernel.py` | MOVED | `agents/cursor/cursor_memory_kernel.py` |

### 1.3 Create Doc-Code Alignment Table

Add to [gap-analysis-memory.md](gap-analysis-memory.md):

```markdown
## Doc-Code Alignment Table

| Logical Component | Old Path | New Path | Router/Module | Notes |
|-------------------|----------|----------|---------------|-------|
| Memory API Router | api/routes/memory.py | api/memory/router.py | 17 async endpoints | 689 LOC, batch/search/health |
| Cursor Memory Kernel | core/governance/cursor_memory_kernel.py | agents/cursor/cursor_memory_kernel.py | Session memory | 689 LOC, 33 functions |
| Cursor Client | tools/cursor_client.py | agents/cursor/cursor_client.py | API client | 77 LOC |
| Cursor Extractor | memory/extractor/cursor_action_extractor.py | agents/cursor/extractors/cursor_action_extractor.py | Action extraction | 661 LOC |
| MCP Memory Routes | - | mcp_memory/src/routes/memory.py | MCP server | Separate service |
| MCP Memory Unified | - | mcp_memory/src/routes/memory_unified.py | MCP unified | With caller tracking |
```

---

## Step 2: Audit Pipeline Hardening

### 2.1 Scripts That Feed .audit_cache

These scripts populate `.audit_cache/manifest.json`:
- [scripts/audit/run_all.py](scripts/audit/run_all.py) - Master orchestrator
- [scripts/audit/tier1/audit_code_integrity.py](scripts/audit/tier1/audit_code_integrity.py) - File discovery via `find_python_files()`
- [scripts/audit/tier1/audit_capability_inventory.py](scripts/audit/tier1/audit_capability_inventory.py) - Tool discovery

### 2.2 Verify Input Patterns Alignment

The audit scripts use `SKIP_DIRS` and `SKIP_PATH_PATTERNS` in [audit_code_integrity.py](scripts/audit/tier1/audit_code_integrity.py):

```python
SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules",
    ".venv", "venv", "env", ".cursor", "docs", "reports",
    "archive", "deprecated", "templates", ".dora",
    "codegen/templates", "codegen/code-gen-files",
}
```

**Verification needed:** Confirm `agents/cursor/` is NOT in SKIP_DIRS (it is not - correct).

### 2.3 Add Guardrail: Deprecated Directory Check

Add to [scripts/audit/run_all.py](scripts/audit/run_all.py) after cache regeneration:

```python
DEPRECATED_CURSOR_PATHS = [
    "tools/cursor_client.py",
    "scripts/cursor_check_mistakes.py", 
    "memory/extractor/cursor_action_extractor.py",
    "core/governance/cursor_memory_kernel.py",
]

def validate_no_deprecated_paths(cache_dir: Path) -> List[str]:
    """Fail loudly if deprecated paths appear in cache."""
    manifest = json.loads((cache_dir / "manifest.json").read_text())
    violations = []
    for path in manifest.keys():
        for deprecated in DEPRECATED_CURSOR_PATHS:
            if deprecated in path:
                violations.append(f"DEPRECATED: {path} (moved to agents/cursor/)")
    return violations
```

### 2.4 Post-Regeneration Health Check

After `python3 scripts/audit/run_all.py`:

```bash
# Every path in .audit_cache must either:
# 1. Exist on disk, OR
# 2. Be explicitly listed in architecture_decisions.md as archived

python3 -c "
import json
from pathlib import Path

manifest = json.loads(Path('.audit_cache/manifest.json').read_text())
missing = [p for p in manifest.keys() if not Path(p).exists()]
if missing:
    print(f'ERROR: {len(missing)} paths in cache do not exist:')
    for p in missing[:10]:
        print(f'  - {p}')
    exit(1)
print('OK: All cached paths exist on disk')
"
```

---

## Step 3: Targeted Wiring Probes

### 3.1 Create Wiring Verifier Script

Create [scripts/audit/verify_wiring_alignment.py](scripts/audit/verify_wiring_alignment.py):

```python
#!/usr/bin/env python3
"""
L9 Wiring Alignment Verifier
Validates that all doc/script path references point to real files.
"""
import re
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

# Patterns to extract from docs
PATH_PATTERNS = [
    r'api/[\w/]+\.py',
    r'mcp_memory/src/[\w/]+\.py', 
    r'agents/cursor/[\w/]+\.py',
    r'memory/substrate_[\w]+\.py',
]

# Known canonical files from file_metrics.txt
CANONICAL_FILES = {
    "api/memory/router.py",
    "mcp_memory/src/routes/memory.py",
    "mcp_memory/src/routes/memory_unified.py",
    "agents/cursor/cursor_memory_kernel.py",
    "agents/cursor/cursor_client.py",
    "agents/cursor/extractors/cursor_action_extractor.py",
    "memory/substrate_service.py",
    "memory/substrate_repository.py",
    "memory/substrate_graph.py",
}

def scan_file(filepath: Path) -> dict:
    """Extract path references from a file."""
    content = filepath.read_text(errors='ignore')
    found = {}
    for pattern in PATH_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            exists = (REPO_ROOT / match).exists()
            found[match] = {"exists": exists, "source": str(filepath)}
    return found

def main():
    results = {"broken_docs": [], "dangling_paths": [], "verified": []}
    
    # Scan docs and scripts
    for glob_pattern in ["**/*.md", "scripts/**/*.py"]:
        for filepath in REPO_ROOT.glob(glob_pattern):
            if ".git" in str(filepath) or ".audit_cache" in str(filepath):
                continue
            refs = scan_file(filepath)
            for path, info in refs.items():
                if not info["exists"]:
                    results["broken_docs"].append({
                        "path": path,
                        "source": info["source"]
                    })
                else:
                    results["verified"].append(path)
    
    # Output
    print(json.dumps(results, indent=2))
    return 1 if results["broken_docs"] else 0

if __name__ == "__main__":
    exit(main())
```

### 3.2 Cross-Check with async_function_map.txt

Verify that referenced endpoints exist in [readme/repo-index/async_function_map.txt](readme/repo-index/async_function_map.txt):

Key memory router functions (must exist):
- `async batch_write(...) @ api/memory/router.py`
- `async compact_storage(...) @ api/memory/router.py`
- `async create_packet(...) @ api/memory/router.py`
- `async semantic_search(...) @ api/memory/router.py`
- `async health_check(...) @ api/memory/router.py`

Key MCP memory functions (must exist):
- `async save_memory(...) @ mcp_memory/src/routes/memory.py`
- `async get_context_injection(...) @ mcp_memory/src/routes/memory_unified.py`

---

## Step 4: Implementation TODOs

### TODO 1: Fix Stale Path References in Docs

**File:** [gap-analysis-memory.md](gap-analysis-memory.md)
**Operation:** Replace
**Pattern:** `api/routes/memory.py`
**Replacement:** `api/memory/router.py`
**Count:** 7+ occurrences (lines 482, 705, 806, 990, 1083, 1216, 1363+)

### TODO 2: Add Doc-Code Alignment Table

**File:** [gap-analysis-memory.md](gap-analysis-memory.md)
**Operation:** Insert (after line ~50, after "## Overview" section)
**Content:** Doc-Code Alignment Table from Step 1.3

### TODO 3: Add Deprecated Path Guardrail

**File:** [scripts/audit/run_all.py](scripts/audit/run_all.py)
**Operation:** Insert (after line 275, after cache regeneration)
**Content:** `validate_no_deprecated_paths()` function and call

### TODO 4: Create Wiring Verifier Script

**File:** [scripts/audit/verify_wiring_alignment.py](scripts/audit/verify_wiring_alignment.py) (NEW)
**Operation:** Create
**Content:** Wiring alignment verifier from Step 3.1

### TODO 5: Regenerate Audit Cache

**Operation:** Shell command
**Command:** `python3 scripts/audit/run_all.py --skip-cache`
**Post-check:** Run health check from Step 2.4

---

## Step 5: Verification Checklist

### Green Criteria

1. `python3 scripts/audit/verify_wiring_alignment.py` returns 0 (no broken paths)
2. `grep -r "api/routes/memory.py" . --include="*.md"` returns only architecture_decisions.md
3. `.audit_cache/manifest.json` contains no paths under deprecated directories
4. All paths in `.audit_cache/manifest.json` exist on disk
5. `async_function_map.txt` contains entries for all canonical memory routers

### Observability Sanity Check

After fixes, verify these metrics paths still resolve:
- `l9_memory_writes_total` maps to `memory/substrate_service.py`
- `l9_memory_searches_total` maps to `memory/substrate_service.py`
- Tool audit logs in `memory/tool_audit.py` reference correct router

---

## Scope Summary

**DO:**
- Fix doc path references
- Add audit guardrails
- Create wiring verifier
- Regenerate audit cache

**DO NOT:**
- Modify `core/governance/*.py` (except references)
- Modify `memory/substrate_*.py` (except references)
- Modify packet protocol or data models
- Touch memory-governance patterns