---
name: Wiring Mis-Alignment Audit
overview: Systematically identify and fix all path/wiring mis-alignments where documentation or configuration references files at incorrect paths. One confirmed finding in gap-analysis-memory.md (7 refs to wrong path), plus stale audit cache entries.
todos:
  - id: fix-gap-analysis
    content: "Fix gap-analysis-memory.md: replace api/routes/memory.py with api/memory/router.py (7+ occurrences)"
    status: pending
  - id: regen-audit-cache
    content: Regenerate .audit_cache to clear stale file path entries
    status: pending
  - id: verify-no-stale-refs
    content: Grep verify no other stale path references exist outside allowed files
    status: pending
---

# Wiring Mis-Alignment Audit Plan

## Confirmed Findings

### Finding 1: gap-analysis-memory.md - Wrong Memory Router Path (7 refs)

- **Wrong**: `api/routes/memory.py` (doesn't exist)
- **Correct**: `api/memory/router.py` (exists)
- **Lines**: 482, 705, 806, 990, 1083, 1216, 1363, 1375, 1386, 1403
- **Action**: Replace all instances

### Finding 2: .audit_cache/manifest.json - Stale Entries (5 files)

- `tools/cursor_client.py` (moved to `agents/cursor/`)
- `scripts/cursor_check_mistakes.py` (moved to `agents/cursor/scripts/`)
- `memory/extractor/cursor_action_extractor.py` (moved to `agents/cursor/extractors/`)
- `core/governance/cursor_memory_kernel.py` (moved to `agents/cursor/`)
- **Action**: Regenerate audit cache (auto-fixes on next audit run)

### Finding 3: Already Fixed

- `setup-new-workspace.yaml` cursor_memory_kernel.py path - FIXED this session

## Implementation Steps

### Step 1: Fix gap-analysis-memory.md

Surgical replace: `api/routes/memory.py` → `api/memory/router.py`

Files to modify:

- [gap-analysis-memory.md](gap-analysis-memory.md) - 7+ occurrences

### Step 2: Regenerate Audit Cache

Run audit script to clear stale entries:

```bash
rm -rf .audit_cache && python3 scripts/audit/run_all.py
```

Or let it auto-regenerate on next CI run.

### Step 3: Verify No Other Mis-Alignments

Run validation grep to confirm all paths from `architecture_decisions.md` "Files Moved" section have no stale references (excluding architecture_decisions.md itself and .audit_cache).

## Verification Checklist

- All `api/routes/memory.py` refs updated to `api/memory/router.py`
- No imports reference old Cursor file paths
- Audit cache regenerated with current paths

## Scope Boundaries

- DO fix documentation path references
- DO regenerate audit cache
- DO NOT modify architecture_decisions.md (it documents the moves, correctly uses old paths)
- DO NOT modify .audit_cache manually (let regeneration handle it)