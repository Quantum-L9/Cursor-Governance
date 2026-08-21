---
name: Dual-Mode Cypher Queries
overview: Implement strict and relaxed Cypher query modes in graph_service.py with corrected property locations, multiplicative penalties, and proper Stage 1 → Stage 2 wiring.
todos:
  - id: fix-duplicate-match-result
    content: Remove duplicate MatchResult class from matcher.py lines 273-294
    status: pending
  - id: fix-mfi-sync
    content: Add mfi_min/mfi_max to _build_material_payloads() and sync_material_nodes()
    status: pending
  - id: update-partner-types
    content: Update gate_mode values and add 4 new partner types in partner_type_data.xml
    status: pending
  - id: build-strict-query
    content: Add _build_strict_query() with all gates as WHERE predicates using correct m.*/f.* properties
    status: pending
  - id: build-relaxed-query
    content: Add _build_relaxed_query() with multiplicative penalties and MFI-process at 0.1
    status: pending
  - id: match-buyers-method
    content: Add match_buyers(intake, facility_ids, mode) that receives Stage 1 survivors
    status: pending
  - id: wire-mode-to-matcher
    content: Update find_matches_for_supplier() to collect facility_ids and pass mode
    status: pending
isProject: false
---

# Dual-Mode Cypher Query Implementation (REVISED v2)

## Summary of Agent Feedback Integration

All 6 critical issues from the feedback have been addressed:


| Issue                   | Resolution                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| Wrong file path         | Use canonical `[plasticos_matching/models/match_result.py](plasticos_matching/models/match_result.py)` |
| Duplicate model         | Remove duplicate from `[matcher.py](plasticos_buyer_match_engine/models/matcher.py)` lines 273-294     |
| `run_id` vs `l9_run_id` | Use existing `l9_run_id` field with values `strict_v1`, `relaxed_v1`                                   |
| Property location       | Use `m.*` (MaterialProfile) for density/MFI/contamination/moisture                                     |
| Relaxed too lenient     | Multiplicative penalties: `100 × 0.3 × 0.3 × 0.3 = 2.7` not 25+                                        |
| MFI-process removed     | Keep as heavy soft penalty (×0.1) - physics constraint                                                 |
| Missing facility_ids    | Pass `facility_ids` from Stage 1 to Stage 2                                                            |


## Pre-Existing Gap: MFI Not Synced

MFI range fields (`melt_index_min`, `melt_index_max`) are now on `plasticos.material.profile` (per user fix) but not yet synced to Neo4j `MaterialProfile` nodes. Phase 0.2 adds them to `_build_material_payloads()` and `sync_material_nodes()`.

---

## Phase 0: Fix Pre-Existing Issues

### 0.1 Remove duplicate MatchResult class

- File: `[plasticos_buyer_match_engine/models/matcher.py](plasticos_buyer_match_engine/models/matcher.py)`
- Action: Delete lines 273-294 (duplicate `plasticos.match.result` model)

### 0.2 Add MFI to MaterialProfile sync

- File: `[plasticos_buyer_match_engine/models/graph_service.py](plasticos_buyer_match_engine/models/graph_service.py)`
- Add `mfi_min`, `mfi_max` to `_build_material_payloads()` (line ~475)
- Add to Cypher MERGE in `sync_material_nodes()` (line ~608)

---

## Phase 1: Update Partner Types

File: `[plasticos_facility_profile/data/partner_type_data.xml](plasticos_facility_profile/data/partner_type_data.xml)`

### Updates

- `broker`: flexible → optimistic
- `mrf`: optimistic → flexible
- `recycler`: optimistic → flexible
- `processor`: keep flexible (per feedback)

### New Records

- `end_user` (strict)
- `grinder` (flexible)
- `toll_processor` (flexible)
- `converter` (strict)

---

## Phase 2: Dual Cypher Queries

File: `[plasticos_buyer_match_engine/models/graph_service.py](plasticos_buyer_match_engine/models/graph_service.py)`

### 2.1 `_build_strict_query()`

- All gates as WHERE predicates
- Uses `m.*` for density/MFI/contamination/moisture (MaterialProfile)
- Uses `f.*` for lot_size/geo/certifications (Facility)

### 2.2 `_build_relaxed_query()`

- Only polymer is hard (WHERE)
- All other gates as multiplicative CASE penalties
- MFI-process compatibility: ×0.1 penalty (heavy, physics constraint)
- Other failures: ×0.3 penalty
- Final: `100 × mult1 × mult2 × ...`

### 2.3 `match_buyers(intake, facility_ids, mode)`

- Receives `facility_ids` from Stage 1
- Runs strict/relaxed/both based on mode
- Persists with `l9_run_id = "strict_v1"` or `"relaxed_v1"`

---

## Phase 3: Wire Mode Through Pipeline

File: `[plasticos_buyer_match_engine/models/matcher.py](plasticos_buyer_match_engine/models/matcher.py)`

### Update `find_matches_for_supplier()`

- Add `mode` parameter
- Collect `facility_ids` from Stage 1 survivors
- Pass to `graph_svc.match_buyers(intake, facility_ids, mode)`

---

## Gate Matrix (All 14 Gates with Corrected Property Locations)

| # | Gate | Strict | Relaxed | Location |
|---|------|--------|---------|----------|
| 1 | Polymer | WHERE | WHERE | `m.polymer` |
| 2 | Density | WHERE | ×0.3 | `m.min_density`, `m.max_density` |
| 3 | MFI Range | WHERE | ×0.3 | `m.mfi_min`, `m.mfi_max` |
| 4 | MFI-Process | WHERE | **×0.1** | `f.process_type` (physics constraint) |
| 5 | Contamination | WHERE | ×0.3 | `m.contamination_tolerance` |
| 6 | Moisture | WHERE | ×0.3 | `m.moisture_tolerance` |
| 7 | Metal Removal | WHERE | ×0.3 | intake: `has_metal` → facility: `f.can_remove_metal` |
| 8 | FR Filtering | WHERE | ×0.3 | intake: `has_fr` → facility: `f.can_filter_fr` |
| 9 | Wash Line/Dryer | WHERE | ×0.3 | intake: `requires_wash_line` → `f.has_wash_line`, `requires_dryer` → `f.can_reduce_moisture` |
| 10 | Form-Equipment | WHERE | ×0.3 | intake form → facility equipment (bales→`f.has_granulator`, regrind→`f.handles_regrind`, etc.) |
| 11 | PVC/Filler/Odor | WHERE | ×0.3 | intake: `has_pvc`, `has_filler`, `has_odor` → `f.accepts_pvc`, `f.accepts_filled_materials`, `f.accepts_odor` |
| 12 | Lot Size | WHERE | ×0.3 | `f.min_lot_size_lbs`, `f.max_lot_size_lbs` |
| 13 | Geo Distance | WHERE | ×0.3 | `f.lat`, `f.lon` |
| 14 | Certifications | WHERE | ×0.3 | `f.food_grade_certified`, `f.medical_grade_capable` |


