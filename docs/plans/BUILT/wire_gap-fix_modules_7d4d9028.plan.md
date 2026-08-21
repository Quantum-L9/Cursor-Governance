---
name: Wire Gap-Fix Modules
overview: Copy pre-built files from gap_fix_wire_pack into canonical repo locations using cp, surgically update __init__.py exports, delete old non-canonical files, wire boot_gap_wiring into boot.py, and relocate tests.
todos:
  - id: copy-pack-files
    content: cp 7 source files from wire pack to canonical locations (overwrites non-canonical copies). cp 4 test files. Do NOT overwrite existing __init__.py files.
    status: completed
  - id: copy-boot-wiring
    content: cp engine/boot_gap_wiring.py from pack (new file, corrected imports)
    status: completed
  - id: update-init-files
    content: Surgically add new exports to 4 existing __init__.py files (feedback, packet, compliance, graph)
    status: completed
  - id: delete-old-files
    content: "Delete 6 old non-canonical files: engine/contract_enforcement.py, engine/graph_return_channel.py, engine/inference_rule_registry.py, engine/convergence_controller_patch.py, engine/startup_wiring.py, engine/graph/graph_sync_client_fix.py"
    status: completed
  - id: delete-old-tests
    content: Delete tests/gap_fixes/ directory (replaced by tests/unit/ copies)
    status: completed
  - id: wire-boot
    content: "Surgical edit: add 3-line import+call of apply_all_gap_fixes() in engine/boot.py startup() after init_dependencies (PROTECTED)"
    status: completed
  - id: validate
    content: py_compile all new files, run 4 unit tests, lint check
    status: completed
isProject: false
---

# Wire Gap-Fix Modules Into Production Paths

## Source: Wire Pack

All files come from `current work/04-25-2026/gap_fix_wire_pack/` which contains pre-built copies with:
- Correct canonical location docstrings
- All imports pre-corrected to final paths
- Tests rewritten with new import paths
- `boot_gap_wiring.py` with fixed imports and graceful Gap-6 degradation

**Key rule: DO NOT overwrite existing `__init__.py` files** -- they have L9_META headers and existing exports. Surgically append new exports instead.

---

## Phase 1: Copy Pack Files to Canonical Locations

Source: `PACK = "current work/04-25-2026/gap_fix_wire_pack"`

### 1a. Engine source files (cp from pack, overwriting old non-canonical copies)

```bash
# Files that move to NEW canonical locations (overwrite old location later via delete)
cp "$PACK/engine/packet/contract_enforcement.py"      engine/packet/contract_enforcement.py
cp "$PACK/engine/feedback/graph_return_channel.py"     engine/feedback/graph_return_channel.py
cp "$PACK/engine/feedback/inference_rule_registry.py"  engine/feedback/inference_rule_registry.py
cp "$PACK/engine/feedback/enrich_helpers.py"           engine/feedback/enrich_helpers.py

# Files that STAY in current location (overwrite with import-corrected versions)
cp "$PACK/engine/compliance/audit_persistence.py"      engine/compliance/audit_persistence.py
cp "$PACK/engine/graph/community_export.py"            engine/graph/community_export.py
cp "$PACK/engine/inference_bridge.py"                  engine/inference_bridge.py

# New file: boot gap wiring helper
cp "$PACK/engine/boot_gap_wiring.py"                   engine/boot_gap_wiring.py
```

### 1b. Test files (cp from pack to tests/unit/)

```bash
cp "$PACK/tests/unit/test_contract_enforcement.py"     tests/unit/test_contract_enforcement.py
cp "$PACK/tests/unit/test_graph_return_channel.py"     tests/unit/test_graph_return_channel.py
cp "$PACK/tests/unit/test_inference_rule_registry.py"  tests/unit/test_inference_rule_registry.py
cp "$PACK/tests/unit/test_audit_persistence.py"        tests/unit/test_audit_persistence.py
```

---

## Phase 2: Update Existing `__init__.py` Files (Surgical Append)

These files have L9_META headers + existing exports. Add new imports and `__all__` entries only.

### [engine/feedback/__init__.py](engine/feedback/__init__.py) -- add 3 new modules

```python
# ADD after existing imports:
from engine.feedback.enrich_helpers import apply_return_channel_targets, emit_schema_proposal, extract_per_field_confidence
from engine.feedback.graph_return_channel import GraphToEnrichReturnChannel
from engine.feedback.inference_rule_registry import execute_rule, load_domain_rules

# ADD to __all__:
"GraphToEnrichReturnChannel",
"apply_return_channel_targets",
"emit_schema_proposal",
"execute_rule",
"extract_per_field_confidence",
"load_domain_rules",
```

### [engine/packet/__init__.py](engine/packet/__init__.py) -- add contract enforcement

```python
# ADD after existing imports:
from engine.packet.contract_enforcement import ContractViolationError, build_graph_sync_packet, enforce_packet_envelope

# ADD to __all__:
"ContractViolationError",
"build_graph_sync_packet",
"enforce_packet_envelope",
```

### [engine/compliance/__init__.py](engine/compliance/__init__.py) -- add audit persistence

```python
# ADD after existing imports:
from engine.compliance.audit_persistence import configure_audit_pool, flush_audit_entries

# ADD to __all__:
"configure_audit_pool",
"flush_audit_entries",
```

### [engine/graph/__init__.py](engine/graph/__init__.py) -- add community export

```python
# ADD after existing imports:
from engine.graph.community_export import export_community_labels_to_enrich

# ADD to __all__:
"export_community_labels_to_enrich",
```

---

## Phase 3: Delete Old Non-Canonical Files

After pack files are in place, remove the originals that lived in wrong locations:

```bash
# 5 files that moved to new canonical homes
rm engine/contract_enforcement.py
rm engine/graph_return_channel.py
rm engine/inference_rule_registry.py
rm engine/convergence_controller_patch.py
rm engine/startup_wiring.py

# 1 stale file (dropped per user decision)
rm engine/graph/graph_sync_client_fix.py

# Old test directory (replaced by tests/unit/ copies)
rm -rf tests/gap_fixes/
```

---

## Phase 4: Wire boot.py (PROTECTED FILE)

[engine/boot.py](engine/boot.py) -- add 3-line call in `GraphLifecycle.startup()` **after** `init_dependencies()` and **before** GDS scheduler setup:

```python
from engine.boot_gap_wiring import apply_all_gap_fixes
await apply_all_gap_fixes(
    pg_dsn=settings.pg_dsn,
    neo4j_driver=self._graph_driver,
    domain_pack_loader=self._domain_loader,
)
```

The `boot_gap_wiring.py` module handles:
- Gap-5: PostgreSQL audit pool configuration
- Gap-3: Domain KB inference rule loading
- Gap-2: Return channel singleton initialization
- Gap-6: GDS post-job hook (graceful skip if `register_post_job_hook` not yet on `GDSScheduler`)

---

## Phase 5: Validate

```bash
# Compile check all new/moved files
python -m py_compile engine/packet/contract_enforcement.py
python -m py_compile engine/feedback/graph_return_channel.py
python -m py_compile engine/feedback/inference_rule_registry.py
python -m py_compile engine/feedback/enrich_helpers.py
python -m py_compile engine/compliance/audit_persistence.py
python -m py_compile engine/graph/community_export.py
python -m py_compile engine/boot_gap_wiring.py
python -m py_compile engine/inference_bridge.py

# Run relocated tests
pytest tests/unit/test_contract_enforcement.py tests/unit/test_graph_return_channel.py tests/unit/test_inference_rule_registry.py tests/unit/test_audit_persistence.py -v

# Lint
make lint
```

---

## Deferred Items (NOT in this wire)

| Item | Reason |
|------|--------|
| Gap-6: GDS post-job hook | `GDSScheduler` needs `register_post_job_hook()` API -- separate GMP. `boot_gap_wiring.py` gracefully skips. |
| Gap-9: inference_bridge_v2 / DerivationGraph | Large feature build, not a wire |
| Gap-8: enforce_domain_spec | Moot -- `ConvergenceLoop.__init__` already enforces via type signature |
| handlers.py contract enforcement | Wiring `enforce_packet_envelope` into `handle_sync` requires reading the full handler to find the right insertion point -- separate GMP for protected file |
| Multi-pass enrichment controller | `handle_enrich` is one-shot today; return channel + helpers are placed and ready for when this controller is built |
