---
name: CursorActionExtractor Full Instantiation
overview: Fix critical import/initialization issues, wire CursorActionExtractor into extraction pipeline, and create integration points for chat history processing per _Notes (Live).md requirements (Methods, Integration Points, Wiring Code, Strategies).
todos:
  - id: T1.1
    content: Add logging import to memory/extractor/base_extractor.py
    status: pending
  - id: T1.2
    content: Fix import path and add logging import to cursor_action_extractor.py
    status: pending
  - id: T1.3
    content: Add __init__ method to CursorActionExtractor class
    status: pending
    dependencies:
      - T1.2
  - id: T1.4
    content: Export CursorActionExtractor from __init__.py
    status: pending
    dependencies:
      - T1.3
  - id: T2.1
    content: Fix logger usage in exception handling (use self.logger)
    status: pending
    dependencies:
      - T1.3
  - id: T2.2
    content: Create CLI script scripts/extract_cursor_chat.py
    status: pending
    dependencies:
      - T1.4
  - id: T2.3
    content: Create API route api/routes/cursor.py for extraction endpoint
    status: pending
    dependencies:
      - T1.4
  - id: T3.1
    content: Wire cursor router into api/server.py
    status: pending
    dependencies:
      - T2.3
  - id: T3.2
    content: Add usage examples to CLI script
    status: pending
    dependencies:
      - T2.2
  - id: T4.1
    content: Create unit tests tests/agents/cursor/test_cursor_action_extractor.py
    status: pending
    dependencies:
      - T1.4
      - T2.1
---

# GMP Plan: Cu

rsorActionExtractor Full Instantiation

## Variable Bindings

```yaml
TASK_NAME: cursor_action_extractor_full_instantiation
EXECUTION_SCOPE: Fix import/initialization issues, wire CursorActionExtractor into extraction pipeline, create integration points for chat history processing
SPEC_PATH: docs/__Notes/_Notes (Live).md
REPORT_ROOT: /Users/ib-mac/Projects/L9/reports
RISK_LEVEL: Medium
IMPACT_METRICS: Extraction functionality, chat history processing, module instantiation completeness
VALIDATION_NOTES: Run py_compile, lint, verify imports resolve, test extraction on sample chat file
```



## State Sync Summary

- **Phase**: 6 – FINALIZE (Governance Upgrade Complete)

- **Priority**: 🟡 MEDIUM

- **Tier**: RUNTIME_TIER (extractors are runtime utilities)

- **Context**: CursorActionExtractor exists but cannot be instantiated due to missing dependencies

## Analysis Summary

**Current State:**

- `CursorActionExtractor` class exists at `agents/cursor/extractors/cursor_action_extractor.py` (661 lines)

- Inherits from `BaseExtractor` but import path is wrong

- Missing `__init__` method (required by `BaseExtractor`)
- Missing `logging` import (used on line 175)

- `BaseExtractor` also missing `logging` import
- Not exported from `__init__.py`

- Not wired into any extraction pipeline

**Integration Pattern Found:**

- Other extractors use `UniversalExtractor` pattern in `api/routes/factory.py`

- Extraction typically happens via API routes or scripts
- Base extractor pattern expects `config: Dict` and `logger` in `__init__`

## Constraint Check

- ✅ KERNEL-TIER files NOT in scope
- ✅ No duplicated responsibilities (extractor is unique)
- ✅ Unified interfaces (uses structlog, follows BaseExtractor pattern)
- ✅ No placeholders in output (all methods implemented)

## TODO Plan (Locked)

### Phase 1: Foundation Fixes

**T1.1** File: `memory/extractor/base_extractor.py`

- Lines: 1-10
- Action: Insert
- Target: Imports section
- Change: Add `import logging` after line 9
- Gate: py_compile
- Imports: logging

**T1.2** File: `agents/cursor/extractors/cursor_action_extractor.py`

- Lines: 1-13
- Action: Replace
- Target: Import statements
- Change: Fix import path from `.base_extractor` to `memory.extractor.base_extractor`, add `import logging`
- Gate: py_compile
- Imports: logging

**T1.3** File: `agents/cursor/extractors/cursor_action_extractor.py`

- Lines: 16-18
- Action: Insert
- Target: After class declaration
- Change: Add `__init__` method that accepts config and logger, calls `super().__init__(config, logger)`
- Gate: py_compile
- Imports: None

**T1.4** File: `agents/cursor/extractors/__init__.py`

- Lines: 1-1 (empty file)
- Action: Insert
- Target: File content
- Change: Export `CursorActionExtractor` class
- Gate: py_compile
- Imports: from .cursor_action_extractor import CursorActionExtractor

### Phase 2: Integration Points

**T2.1** File: `agents/cursor/extractors/cursor_action_extractor.py`

- Lines: 175
- Action: Replace
- Target: Exception handling
- Change: Replace `logging.exception()` with `self.logger.exception()` (use instance logger)
- Gate: lint
- Imports: None

**T2.2** File: `scripts/extract_cursor_chat.py` (NEW FILE)

- Lines: 1-100
- Action: Create
- Target: CLI script for chat extraction
- Change: Create script that instantiates CursorActionExtractor, processes chat files, outputs extracted artifacts
- Gate: py_compile, lint
- Imports: structlog, pathlib, agents.cursor.extractors.CursorActionExtractor

**T2.3** File: `api/routes/cursor.py` (NEW FILE or append to existing)

- Lines: 1-50
- Action: Create/Insert
- Target: API route for cursor extraction
- Change: Create POST endpoint `/api/v1/cursor/extract` that accepts chat file, uses CursorActionExtractor, returns manifest
- Gate: py_compile, lint
- Imports: FastAPI, UploadFile, agents.cursor.extractors.CursorActionExtractor

### Phase 3: Wiring Code

**T3.1** File: `api/server.py` (if cursor.py route created separately)

- Lines: ~200-250 (router registration area)
- Action: Insert
- Target: Router includes

- Change: Add `from api.routes import cursor` and `app.include_router(cursor.router, prefix="/api/v1/cursor", tags=["cursor"])`

- Gate: py_compile

- Imports: None

**T3.2** File: `scripts/extract_cursor_chat.py`

- Lines: 50-100

- Action: Insert

- Target: Main execution block

- Change: Add example usage showing config dict structure, logger setup, extractor instantiation pattern

- Gate: None

- Imports: None

### Phase 4: Validation & Testing

**T4.1** File: `tests/agents/cursor/test_cursor_action_extractor.py` (NEW FILE)

- Lines: 1-100

- Action: Create

- Target: Unit tests

- Change: Create tests for instantiation, extract() method, all helper methods, error handling
- Gate: pytest

- Imports: pytest, unittest.mock, agents.cursor.extractors.CursorActionExtractor

## Methods (Per _Notes Live.md)

**Required Methods Status:**

- ✅ `extract(input_path, output_root)` - Implemented

- ✅ `create_directory_structure()` - Implemented

- ✅ `extract_yaml_configs()` - Implemented

- ✅ `extract_executive_mode()` - Implemented

- ✅ `extract_loader_config()` - Implemented

- ✅ `extract_components()` - Implemented

- ✅ `extract_reasoning_pattern_schema()` - Implemented

- ✅ `generate_python_modules()` - Implemented

- ✅ `write_yaml()` - Implemented

- ✅ `write_manifest()` - Implemented

**Missing:**

- ❌ `__init__()` - Will be added in T1.3

## Integration Points (Per _Notes Live.md)

**Planned Integration Points:**

1. **CLI Script** (`scripts/extract_cursor_chat.py`)

- Purpose: Command-line tool for processing chat transcripts

- Usage: `python scripts/extract_cursor_chat.py <chat_file> <output_dir>`

- Wiring: Direct instantiation with config dict and logger

2. **API Route** (`api/routes/cursor.py`)

- Purpose: REST endpoint for chat extraction

- Usage: `POST /api/v1/cursor/extract` with file upload

- Wiring: FastAPI route handler instantiates extractor

3. **Future: Batch Processing** (deferred)

- Purpose: Process multiple chat files
- Usage: TBD

- Wiring: TBD

## Wiring Code (Per _Notes Live.md)

**Example 1: CLI Script Instantiation**

```python
import structlog
from pathlib import Path
from agents.cursor.extractors import CursorActionExtractor

logger = structlog.get_logger(__name__)
config = {
    "extractors": {
        "cursor_action_extractor": {
            "enabled": True
        }
    }
}

extractor = CursorActionExtractor(config, logger)
result = extractor.extract(
    input_path=Path("chat_transcript.md"),
    output_root=Path("extracted/")
)
```



**Example 2: API Route Integration**

```python
from fastapi import APIRouter, UploadFile, File
from agents.cursor.extractors import CursorActionExtractor
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)

@router.post("/extract")
async def extract_chat(file: UploadFile = File(...)):
    config = {"extractors": {"cursor_action_extractor": {"enabled": True}}}
    extractor = CursorActionExtractor(config, logger)
    # Process file...
```



## Strategies (Per _Notes Live.md)

**Not Applicable:** Strategies refer to memory hygiene/consolidation pipeline approaches. CursorActionExtractor is a file extraction utility, not a memory consolidation component.

## Files Modified Summary

**New Files:**

- `scripts/extract_cursor_chat.py` (~100 lines)

- `api/routes/cursor.py` (~50 lines)

- `tests/agents/cursor/test_cursor_action_extractor.py` (~100 lines)

**Modified Files:**

- `memory/extractor/base_extractor.py` (add logging import)

- `agents/cursor/extractors/cursor_action_extractor.py` (fix imports, add **init**, fix logger usage)

- `agents/cursor/extractors/__init__.py` (export class)

- `api/server.py` (wire router if cursor.py created separately)

## Validation Gates

- [ ] py_compile: All Python files compile

- [ ] lint: ruff check passes
- [ ] type-check: pyright (if applicable)

- [ ] tests: pytest tests/test_cursor_action_extractor.py passes

- [ ] integration: Manual test of CLI script with sample chat file

- [ ] integration: Manual test of API endpoint with file upload

## Risk Assessment

**Low Risk:**

- Import fixes are straightforward

- Adding **init** follows established pattern

- New files are additive (no existing code modified)

**Medium Risk:**

- API route wiring requires understanding FastAPI router registration

- Config dict structure must match BaseExtractor expectations

- Logger setup must use structlog (L9 standard)

**Mitigation:**

- Follow existing extractor patterns in `api/routes/factory.py`

- Use structlog.get_logger() pattern from other L9 modules

- Test with minimal config dict first

## Success Criteria

✅ CursorActionExtractor can be instantiated with config and logger

✅ All imports resolve correctly

✅ extract() method works end-to-end on sample chat file

✅ CLI script successfully processes chat transcript