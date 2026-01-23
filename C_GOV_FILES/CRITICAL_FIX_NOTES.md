---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "INT-CM-002"
component_name: "Context Memory Critical Fix Notes"
layer: "intelligence"
domain: "context_memory"
type: "documentation"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: true
audit_trail: true

# === BUSINESS METADATA ===
purpose: "Document critical fixes applied to context extractor system"
summary: "Notes on fixing context extractor format assumptions and alignment with learning system"
---

# Critical Fix Notes - Context Extractor

**Date:** 2025-11-08  
**Issue:** Context extractor was built with WRONG format assumption

## The Problem

Initial implementation assumed:
- ❌ Chat data in LevelDB format at `chat_data/`
- ❌ Direct message table access
- ❌ Same as broken recursive learning

## The Fix (Applied)

Based on recursive learning fix from other session:

### Correct Format
- ✅ Chat data stored in **SQLite** at `User/workspaceStorage/*/state.vscdb`
- ✅ Access via `composer.composerData` key
- ✅ Multiple workspace databases to process

### Updated Code
```python
# OLD (BROKEN):
db_path = self.export_dir / "chat_data"
conn = sqlite3.connect(str(db_path))

# NEW (FIXED):
workspace_storage = self.export_dir / "User/workspaceStorage"
# Process each workspace/*.vscdb database
# Extract composer.composerData
```

## Files Updated

1. `intelligence/context-memory/context-extractor.py`
   - Changed `extract_context_from_export()` to use workspaceStorage
   - Iterate through workspace directories
   - Extract from state.vscdb files
   - Process composer.composerData

## Alignment with Learning System

Now matches the FIXED learning system pattern:
- ✅ Same export source (workspaceStorage)
- ✅ Same database format (SQLite .vscdb)
- ✅ Same extraction method (composer.composerData)
- ✅ Same error handling

## Testing Required

After sync to GlobalCommands:
```bash
# Test manually
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/process_context.sh

# Should now find conversations from workspaceStorage
# Should create session JSON files
```

## Related Documents

- `Work Files/fix_recursive_learning.md` - Full learning system fix
- Export script already correct (uses workspaceStorage)
- Memory aggregator fixed in other session
- This aligns context-extractor with that fix

