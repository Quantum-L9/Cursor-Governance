---
name: Add Missing Buyer Gates (Revised v2)
overview: |
  Add 6 missing gates to matcher.py Stage 1, add Source Type gate + soft multiplier
  to graph_service.py Stage 2 (both strict AND relaxed), fix existing gate-count bug,
  update extraction for both branches, and add polymer-specific MFI-Process helper.
  Verified against staging branch SHA: 8ea900e (matcher.py), a7a02ec (graph_service.py),
  d21b11e (intake.py), 6e75e02 (facility_profile.py).
todos:
  - id: T1-fix-gate-count-constant
    content: Replace hardcoded gate count with class constant
    status: pending
  - id: T2-add-extraction-fields-intake
    content: Add 6 missing fields to _extract_material_requirements() intake branch
    status: pending
  - id: T3-add-extraction-fields-fallback
    content: Add 6 explicit defaults to _extract_material_requirements() fallback branch
    status: pending
  - id: T4-add-helpers
    content: Add _check_mfi_process_compatibility() and _haversine_miles() methods
    status: pending
  - id: T5-add-strict-gates
    content: Add Gates 13-18 to _check_gates_strict()
    status: pending
  - id: T6-add-relaxed-gates
    content: Add Gates 13-18 as soft signals in _check_gates_relaxed()
    status: pending
  - id: T7-add-source-cypher-strict
    content: Add Source Type gate to _build_strict_query() in graph_service.py
    status: pending
  - id: T8-add-source-cypher-relaxed
    content: Add Source Type soft multiplier to _build_relaxed_query() in graph_service.py
    status: pending
  - id: T9-add-source-param
    content: Add source_type to _intake_to_match_params() in graph_service.py
    status: pending
  - id: T10-tests
    content: Add unit tests for all 6 new gates + helpers + null-safety
    status: pending
  - id: T11-sync-feedstock-type
    content: Add feedstock_type to _build_facility_payloads() and sync Cypher
    status: pending
isProject: false
---

# Add Missing Buyer Matching Gates — Revised Build Plan v2

## Field Verification (from staging)

Before any code, here is the verified field mapping against actual models:

### intake.py (plasticos.intake) — CONFIRMED FIELDS


| Field Used by Gate  | Actual Field Name     | Type      | Notes                                  |
| ------------------- | --------------------- | --------- | -------------------------------------- |
| source_type_id      | `source_type_id`      | Many2one  | -> plasticos.source.type, has .code    |
| mfi_value           | `mfi_value`           | Float     | Direct field                           |
| polymer_id.code     | `polymer_id`          | Many2one  | -> plasticos.polymer, has .code        |
| moisture_pct        | `moisture_pct`        | Float     | "Moisture content as a percentage"     |
| origin_sector       | `origin_sector`       | Selection | Values: 'food', 'medical', etc.        |
| origin_process_type | `origin_process_type` | Selection | Values: 'injection', 'blow_mold', etc. |
| lat / lon           | `lat`, `lon`          | Float     | NOT latitude/longitude                 |


> **CRITICAL FIX from original plan**: Intake uses `lat`/`lon`, NOT `latitude`/`longitude`.
> The existing `_extract_material_requirements()` references `intake.latitude` which does
> not exist on the model. The actual fields are `intake.lat` and `intake.lon`.
> **This plan fixes the pre-existing extraction bug as part of T2.**

### facility_profile.py (plasticos.facility.profile) — CONFIRMED FIELDS


| Field Used by Gate           | Actual Field Name       | Type      | Notes                                 |
| ---------------------------- | ----------------------- | --------- | ------------------------------------- |
| source_type_id               | **DOES NOT EXIST**      | --        | No source_type_id on profile          |
| feedstock_type               | `feedstock_type`        | Selection | post_industrial, post_consumer, etc.  |
| process_type                 | `process_type`          | Selection | injection, blow_mold, extrusion, etc. |
| has_wash_line                | `has_wash_line`         | Boolean   | Computed from equipment_type_ids      |
| can_reduce_moisture          | `can_reduce_moisture`   | Boolean   | Direct field                          |
| food_grade_certified         | `food_grade_certified`  | Boolean   | Direct field                          |
| medical_grade_capable        | `medical_grade_capable` | Boolean   | Direct field                          |
| partner_id.partner_latitude  | via res.partner         | Float     | Standard Odoo geo fields              |
| partner_id.partner_longitude | via res.partner         | Float     | Standard Odoo geo fields              |


> **CRITICAL FIX from original plan**: Gate 13 (Source Type) referenced
> `buyer_profile.source_type_id` which DOES NOT EXIST on facility.profile.
> The facility profile has `feedstock_type` (Selection: post_industrial,
> post_consumer, mixed, virgin, unknown). Gate 13 must compare
> `intake.source_type_id.code` against `buyer_profile.feedstock_type` using
> the correct hierarchy mapping.

---

## T1: Replace Hardcoded Gate Count with Constant

**File**: `matcher.py`
**Location**: Top of `BuyerMatcher` class (after `_description`)

```python
# Total gates in _check_gates_strict() -- update when adding/removing gates
TOTAL_STRICT_GATES = 18
```

**Also update the return statement** (~line 369) in `_check_gates_strict()`:

```python
# BEFORE (buggy -- says 10 but has 12 gates today):
return {"passed": len(gates_failed) == 0, "gates_passed": 10 - len(gates_failed), "gates_failed": gates_failed}

# AFTER:
return {
    "passed": len(gates_failed) == 0,
    "gates_passed": self.TOTAL_STRICT_GATES - len(gates_failed),
    "gates_failed": gates_failed,
}
```

**Why**: Current code hardcodes 10 but actually has 12 gates (Color=11, Filler=12 were
added without updating the counter). Using a constant prevents future drift.

---

## T2: Add Missing Fields to Extraction (Intake Branch)

**File**: `matcher.py`
**Method**: `_extract_material_requirements()`
**Location**: Inside the `if intake:` block (~line 197), add after the `filler_type_id` line:

```python
# -- New fields for Gates 13-18 --
'source_type_code': intake.source_type_id.code if intake.source_type_id else None,
'mfi': intake.mfi_value or None,
'polymer_code': intake.polymer_id.code if intake.polymer_id else None,
'moisture_pct': intake.moisture_pct or 0.0,
'food_grade_required': intake.origin_sector == 'food',
'medical_grade_required': intake.origin_sector == 'medical',
```

**Also fix the pre-existing geo bug** in the same block:

```python
# BEFORE (BUG -- intake has lat/lon, not latitude/longitude):
'latitude': intake.latitude if intake.latitude else None,
'longitude': intake.longitude if intake.longitude else None,

# AFTER:
'latitude': intake.lat if intake.lat else None,
'longitude': intake.lon if intake.lon else None,
```

---

## T3: Add Explicit Defaults to Extraction (Fallback Branch)

**File**: `matcher.py`
**Method**: `_extract_material_requirements()`
**Location**: Inside the `return` block under `# Fallback: supplier facility profile` (~line 237):

Add after the existing filler fields:

```python
# -- Gate 13-18 defaults (null-safe: all gates pass on None) --
'source_type_code': None,
'mfi': None,
'polymer_code': profile.accepted_polymer_ids[0].code if profile.accepted_polymer_ids else None,
'moisture_pct': 0.0,
'food_grade_required': False,
'medical_grade_required': False,
```

**Also fix the same geo bug** in the fallback:

```python
# BEFORE (profile doesn't have latitude/longitude either):
'latitude': profile.latitude if profile.latitude else None,
'longitude': profile.longitude if profile.longitude else None,

# AFTER -- use partner-level Odoo geo fields:
'latitude': profile.partner_id.partner_latitude or None,
'longitude': profile.partner_id.partner_longitude or None,
```

---

## T4: Add Helper Methods

**File**: `matcher.py`
**Location**: After `_check_all_gates()` method (end of class).

### T4a: Math import at module top

Add to the imports at the top of `matcher.py` (after `from odoo.exceptions import ValidationError`):

```python
from math import atan2, cos, radians, sin, sqrt
```

### T4b: MFI-Process Compatibility Helper

```python
def _check_mfi_process_compatibility(self, polymer_code, mfi, process_type):
    """Check MFI compatibility with buyer process type.

    Uses polymer-specific thresholds from PlasticOS Knowledge Base.
    Falls back to generic thresholds when polymer is unknown.

    Returns True if compatible or data insufficient, False if incompatible.
    """
    if not polymer_code or not mfi or not process_type:
        return True  # Null-safe: missing data = pass

    polymer_upper = (polymer_code or '').upper()

    # PP-specific thresholds (from plasticos_kb_pp_v8.0)
    if polymer_upper == 'PP':
        if process_type == 'injection' and mfi < 15:
            return False  # PP injection typically needs MFI 15-30
        if process_type in ('film_blown', 'film_cast') and mfi > 5:
            return False  # PP film needs MFI < 5
        if process_type == 'extrusion' and mfi > 12:
            return False  # PP extrusion needs MFI <= 12
        if process_type == 'blow_mold' and (mfi < 1.5 or mfi > 4):
            return False  # PP blow mold needs MFI 1.5-4
        return True

    # HDPE-specific thresholds (from plasticos_kb_hdpe_v8.0)
    if polymer_upper == 'HDPE':
        if process_type == 'injection' and mfi < 5:
            return False  # HDPE injection needs MFI 5-60
        if process_type == 'blow_mold' and (mfi < 0.2 or mfi > 1.0):
            return False  # HDPE blow mold needs MFI 0.2-1.0
        if process_type == 'extrusion' and mfi > 5:
            return False  # HDPE extrusion/pipe needs MFI < 5
        if process_type in ('film_blown', 'film_cast') and mfi > 2:
            return False  # HDPE film needs MFI < 2
        return True

    # ABS-specific thresholds (from plasticos_kb_abs_v8.0)
    if polymer_upper == 'ABS':
        if process_type == 'injection' and mfi < 5:
            return False  # ABS injection typically needs MFI 5-30
        if process_type == 'extrusion' and mfi > 8:
            return False  # ABS extrusion needs MFI <= 8
        return True

    # HIPS-specific thresholds (from plasticos_kb_hips_v8.0)
    if polymer_upper == 'HIPS':
        if process_type == 'injection' and mfi < 3:
            return False  # HIPS injection needs MFI 3-15
        if process_type == 'extrusion' and mfi > 6:
            return False  # HIPS extrusion/sheet needs MFI <= 6
        if process_type == 'thermoform' and (mfi < 2 or mfi > 6):
            return False  # HIPS thermoform needs MFI 2-6
        return True

    # Generic fallback (matches existing Cypher Gate 4 logic)
    if process_type == 'injection' and mfi < 10:
        return False
    if process_type == 'extrusion' and mfi > 20:
        return False
    if process_type == 'blow_mold' and (mfi < 0.5 or mfi > 10):
        return False
    if process_type in ('film_blown', 'film_cast') and mfi > 5:
        return False

    return True
```

### T4c: Haversine Distance Helper

```python
def _haversine_miles(self, lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in miles between two coordinates.

    Used by Gate 18 (Geo) as Python fallback when Neo4j is unavailable.
    """
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))
```

---

## T5: Add Gates 13-18 to `_check_gates_strict()`

**File**: `matcher.py`
**Location**: After Gate 12 (Filler Matching), before the `return` statement.

```python
# -----------------------------------------------------------------
# Gates 13-18: Extended buyer qualification (v2.1)
# All null-safe: if buyer or material data is missing -> PASS
# -----------------------------------------------------------------

# Gate 13: Source Type (PCR/PIR/Virgin) -- HARD if both sides specify
# Compares intake.source_type_id.code against buyer facility.feedstock_type
# Hierarchy: virgin -> accepts anything; mixed -> accepts all recycled;
#   post_industrial -> accepts PIR + PCR; post_consumer -> accepts PCR only
source_code = material_req.get('source_type_code')
buyer_feedstock = buyer_profile.feedstock_type
if source_code and buyer_feedstock and buyer_feedstock != 'unknown':
    _SOURCE_RANK = {
        'virgin': 0,
        'pir': 1, 'post_industrial': 1,
        'pcr': 2, 'post_consumer': 2,
    }
    _FEEDSTOCK_ACCEPTS = {
        'virgin': {0, 1, 2},
        'mixed': {1, 2},
        'post_industrial': {1, 2},
        'post_consumer': {2},
    }
    material_rank = _SOURCE_RANK.get(source_code.lower())
    accepted_ranks = _FEEDSTOCK_ACCEPTS.get(buyer_feedstock, set())
    if material_rank is not None and material_rank not in accepted_ranks:
        gates_failed.append('source_type')

# Gate 14: Process Type / MFI compatibility -- HARD if buyer has process_type
if material_req.get('mfi') is not None and buyer_profile.process_type:
    if not self._check_mfi_process_compatibility(
        material_req.get('polymer_code'),
        material_req['mfi'],
        buyer_profile.process_type,
    ):
        gates_failed.append('process_type_mfi')

# Gate 15: Moisture capability -- HARD if material moisture > 0.5%
material_moisture = material_req.get('moisture_pct') or 0.0
if material_moisture > 0.5:
    if not buyer_profile.has_wash_line and not buyer_profile.can_reduce_moisture:
        gates_failed.append('moisture_capability')

# Gate 16: Food Grade -- HARD if intake requires food-grade compliance
if material_req.get('food_grade_required') and not buyer_profile.food_grade_certified:
    gates_failed.append('food_grade')

# Gate 17: Medical Grade -- HARD if intake requires medical-grade compliance
if material_req.get('medical_grade_required') and not buyer_profile.medical_grade_capable:
    gates_failed.append('medical_grade')

# Gate 18: Geographic distance (Python fallback) -- HARD if max radius configured
max_distance = float(
    self.env['ir.config_parameter'].sudo().get_param(
        'plasticos_graph.match_geo_radius_miles', '0'
    )
)
if max_distance > 0:
    mat_lat = material_req.get('latitude')
    mat_lon = material_req.get('longitude')
    buyer_lat = buyer_profile.partner_id.partner_latitude
    buyer_lon = buyer_profile.partner_id.partner_longitude
    if mat_lat and mat_lon and buyer_lat and buyer_lon:
        distance = self._haversine_miles(mat_lat, mat_lon, buyer_lat, buyer_lon)
        if distance > max_distance:
            gates_failed.append('geo_distance')
```

---

## T6: Add Gates 13-18 as Soft Signals in `_check_gates_relaxed()`

**File**: `matcher.py`
**Method**: `_check_gates_relaxed()`

Replace the entire method with:

```python
def _check_gates_relaxed(self, buyer_profile, material_req):
    """Check gates in RELAXED mode. Only polymer is hard.

    All other gates are evaluated but captured as soft_signals for
    Stage 2 scoring context, not as hard exclusions.
    """
    gates_failed = []
    soft_signals = []

    # ONLY HARD GATE: Polymer Family
    if material_req.get("polymer_family_id") and buyer_profile.polymer_family_id:
        if material_req["polymer_family_id"] != buyer_profile.polymer_family_id.id:
            gates_failed.append("polymer")

    # -- Soft signals (captured, not excluding) --

    # Soft: Source Type mismatch
    source_code = material_req.get('source_type_code')
    buyer_feedstock = buyer_profile.feedstock_type
    if source_code and buyer_feedstock and buyer_feedstock != 'unknown':
        _SOURCE_RANK = {
            'virgin': 0, 'pir': 1, 'post_industrial': 1,
            'pcr': 2, 'post_consumer': 2,
        }
        _FEEDSTOCK_ACCEPTS = {
            'virgin': {0, 1, 2}, 'mixed': {1, 2},
            'post_industrial': {1, 2}, 'post_consumer': {2},
        }
        material_rank = _SOURCE_RANK.get(source_code.lower())
        accepted_ranks = _FEEDSTOCK_ACCEPTS.get(buyer_feedstock, set())
        if material_rank is not None and material_rank not in accepted_ranks:
            soft_signals.append('source_type')

    # Soft: MFI-Process incompatibility
    if material_req.get('mfi') is not None and buyer_profile.process_type:
        if not self._check_mfi_process_compatibility(
            material_req.get('polymer_code'),
            material_req['mfi'],
            buyer_profile.process_type,
        ):
            soft_signals.append('process_type_mfi')

    # Soft: Moisture capability
    if (material_req.get('moisture_pct') or 0.0) > 0.5:
        if not buyer_profile.has_wash_line and not buyer_profile.can_reduce_moisture:
            soft_signals.append('moisture_capability')

    # Soft: Food / Medical grade
    if material_req.get('food_grade_required') and not buyer_profile.food_grade_certified:
        soft_signals.append('food_grade')
    if material_req.get('medical_grade_required') and not buyer_profile.medical_grade_capable:
        soft_signals.append('medical_grade')

    return {
        "passed": len(gates_failed) == 0,
        "gates_passed": 1 if len(gates_failed) == 0 else 0,
        "gates_failed": gates_failed,
        "soft_signals": soft_signals,
    }
```

---

## T7: Add Source Type Gate to `_build_strict_query()`

**File**: `graph_service.py`
**Method**: `_build_strict_query()`
**Location**: After Gate 14 (Certifications), before RETURN.

```cypher
// Gate 15: Source Type (PCR/PIR/Virgin hierarchy)
AND (
    $source_type IS NULL
    OR f.feedstock_type IS NULL
    OR f.feedstock_type = 'unknown'
    OR f.feedstock_type = 'virgin'
    OR f.feedstock_type = 'mixed'
    OR (f.feedstock_type = 'post_industrial'
        AND $source_type IN ['pir', 'pcr', 'post_industrial', 'post_consumer'])
    OR (f.feedstock_type = 'post_consumer'
        AND $source_type IN ['pcr', 'post_consumer'])
)
```

---

## T8: Add Source Type Soft Multiplier to `_build_relaxed_query()`

**File**: `graph_service.py`
**Method**: `_build_relaxed_query()`
**Location**: After the `cert_mult` CASE block, add:

```cypher
// Source Type (x0.3 penalty if mismatch)
CASE
    WHEN $source_type IS NULL OR f.feedstock_type IS NULL
         OR f.feedstock_type IN ['unknown', 'virgin', 'mixed'] THEN 1.0
    WHEN f.feedstock_type = 'post_industrial'
         AND $source_type IN ['pir', 'pcr', 'post_industrial', 'post_consumer'] THEN 1.0
    WHEN f.feedstock_type = 'post_consumer'
         AND $source_type IN ['pcr', 'post_consumer'] THEN 1.0
    ELSE 0.3
END AS source_type_mult
```

**Also update**:

1. Second `WITH` clause: add `source_type_mult` to variable list
2. `total_score` formula: multiply by `* source_type_mult`
3. `RETURN` clause: add `source_type_mult`

---

## T9: Add `source_type` to `_intake_to_match_params()`

**File**: `graph_service.py`
**Location**: After the `filler_pct` line in the return dict:

```python
'source_type': intake.source_type_id.code if intake.source_type_id else None,
```

---

## T11: Add `feedstock_type` to Facility Sync

**File**: `graph_service.py`
**Method**: `_build_facility_payloads()`
**Location**: In the payload dict, add after `accepts_filled_materials`:

```python
'feedstock_type': next(
    (fp.feedstock_type for fp in profiles if fp.feedstock_type),
    None,
),
```

**Also add to `sync_facility_nodes()` Cypher** in both ON CREATE SET and ON MATCH SET:

```cypher
fac.feedstock_type = f.feedstock_type,
```

---

## T10: Unit Tests

**File**: `plasticos_buyer_match_engine/tests/test_buyer_gates_extended.py` (new)

### Test Matrix


| Test Case                          | Gate   | Input                                        | Expected                                 |
| ---------------------------------- | ------ | -------------------------------------------- | ---------------------------------------- |
| PCR material -> PCR buyer          | G13    | source='pcr', feedstock='post_consumer'      | PASS                                     |
| PIR material -> PCR-only buyer     | G13    | source='pir', feedstock='post_consumer'      | FAIL                                     |
| Virgin material -> any buyer       | G13    | source='virgin', feedstock='post_consumer'   | PASS                                     |
| Null source -> any buyer           | G13    | source=None                                  | PASS                                     |
| PP MFI 25 -> injection buyer       | G14    | polymer='PP', mfi=25, process='injection'    | PASS                                     |
| PP MFI 3 -> injection buyer        | G14    | polymer='PP', mfi=3, process='injection'     | FAIL                                     |
| HDPE MFI 0.5 -> blow_mold buyer    | G14    | polymer='HDPE', mfi=0.5, process='blow_mold' | PASS                                     |
| Null MFI -> any process            | G14    | mfi=None                                     | PASS                                     |
| Wet material (2%) -> no wash/dryer | G15    | moisture=2.0, wash=False, reduce=False       | FAIL                                     |
| Wet material (2%) -> has wash      | G15    | moisture=2.0, wash=True                      | PASS                                     |
| Dry material (0.3%) -> no wash     | G15    | moisture=0.3                                 | PASS                                     |
| Food required -> not certified     | G16    | food_required=True, certified=False          | FAIL                                     |
| Food required -> certified         | G16    | food_required=True, certified=True           | PASS                                     |
| Food not required -> not certified | G16    | food_required=False                          | PASS                                     |
| Medical required -> not capable    | G17    | medical_required=True, capable=False         | FAIL                                     |
| Distance 200mi -> max 150mi        | G18    | dist=200, max=150                            | FAIL                                     |
| Distance 100mi -> max 150mi        | G18    | dist=100, max=150                            | PASS                                     |
| Missing coords -> any max          | G18    | lat=None                                     | PASS                                     |
| Max distance 0 (disabled) -> any   | G18    | max=0                                        | PASS                                     |
| Haversine Charlotte->NYC           | Helper | (35.22,-80.84) -> (40.71,-74.01)             | ~ 533 miles                              |
| All 6 new gates null -> all pass   | All    | All fields None/0                            | 18 gates pass                            |
| Relaxed mode captures soft_signals | T6     | food_grade mismatch in relaxed               | passed=True, soft_signals=['food_grade'] |


---

## Verification Checklist

Run these checks after implementation, in order:

### Phase 1: Static Verification

- **V1**: `matcher.py` imports include `from math import atan2, cos, radians, sin, sqrt`
- **V2**: `TOTAL_STRICT_GATES = 18` exists as class constant on `BuyerMatcher`
- **V3**: `_check_gates_strict()` return uses `self.TOTAL_STRICT_GATES` not a literal
- **V4**: `_extract_material_requirements()` intake branch has all 6 new keys:
`source_type_code`, `mfi`, `polymer_code`, `moisture_pct`,
`food_grade_required`, `medical_grade_required`
- **V5**: Intake branch uses `intake.lat` / `intake.lon` (NOT `intake.latitude`)
- **V6**: Fallback branch has matching 6 keys with safe defaults (None, 0.0, False)
- **V7**: Fallback branch uses `profile.partner_id.partner_latitude` for geo
- **V8**: Gate 13 references `buyer_profile.feedstock_type` (NOT `source_type_id`)
- **V9**: Gate 14 calls `self._check_mfi_process_compatibility()` with 3 args
- **V10**: Gate 15 threshold is `> 0.5` (percent, not decimal)
- **V11**: Gate 16 reads `material_req.get('food_grade_required')` (boolean)
- **V12**: Gate 17 reads `material_req.get('medical_grade_required')` (boolean)
- **V13**: Gate 18 reads `ir.config_parameter` key `plasticos_graph.match_geo_radius_miles`
- **V14**: Gate 18 uses `buyer_profile.partner_id.partner_latitude` for buyer coords
- **V15**: `_check_mfi_process_compatibility()` has polymer-specific blocks for PP, HDPE, ABS, HIPS
- **V16**: `_check_mfi_process_compatibility()` returns `True` when any arg is None/falsy
- **V17**: `_haversine_miles()` uses R=3959 (miles, not km)
- **V18**: `_check_gates_relaxed()` returns `soft_signals` key in its dict
- **V19**: `graph_service.py` `_intake_to_match_params()` includes `'source_type'` key
- **V20**: `_build_strict_query()` has 15 gates total (original 14 + Source Type)
- **V21**: `_build_relaxed_query()` has `source_type_mult` in its multiplier chain
- **V22**: `_build_relaxed_query()` includes `source_type_mult` in the total_score formula
- **V23**: No reference to `buyer_profile.source_type_id` anywhere (field does not exist)
- **V24**: No reference to `intake.latitude` or `intake.longitude` (fields are `lat`/`lon`)

### Phase 2: Null-Safety Verification

- **V25**: Every new gate in strict mode starts with `if material_req.get(...) and ...:`
- **V26**: Gate 18 checks `if max_distance > 0:` before any coordinate logic
- **V27**: Gate 13 checks `buyer_feedstock != 'unknown'` before hierarchy comparison
- **V28**: MFI helper returns `True` (pass) when polymer_code, mfi, or process_type is None
- **V29**: All Cypher gates start with `$source_type IS NULL OR f.feedstock_type IS NULL`

### Phase 3: Mode Parity Verification

- **V30**: Every gate in `_check_gates_strict()` has a corresponding soft multiplier
or soft_signal in relaxed mode (Python or Cypher)
- **V31**: `_build_strict_query()` has Source Type as hard WHERE predicate
- **V32**: `_build_relaxed_query()` has Source Type as soft CASE multiplier
- **V33**: Relaxed Python still only excludes on polymer (gates_failed only has 'polymer')
- **V34**: `soft_signals` list in relaxed return covers the 5 new gates
(source_type, process_type_mfi, moisture_capability, food_grade, medical_grade)
-- geo is NOT a soft signal (infrastructure concern, not scoring)

### Phase 4: Integration Verification

- **V35**: Run `odoo-bin --test-tags plasticos_buyer_match_engine` -- all pass
- **V36**: With Neo4j DOWN: strict mode still filters all 18 gates in Python
- **V37**: With Neo4j DOWN: relaxed mode still passes all non-polymer buyers
- **V38**: With Neo4j UP: strict Cypher returns 0 rows for source type mismatch
- **V39**: With Neo4j UP: relaxed Cypher applies source_type_mult penalty (score < 100)
- **V40**: Run full match on a test intake with all fields populated and verify
`gates_passed` count equals 18 minus actual failures (not hardcoded)

### Phase 5: Cross-Module Verification

- **V41**: `plasticos_offer` module still loads cleanly after gate changes
- **V42**: `plasticos_offer` wizard still reads `match_result.score` correctly
- **V43**: No import cycles between `plasticos_buyer_match_engine` and other modules
- **V44**: `_build_facility_payloads()` includes `feedstock_type` in the sync payload
- **V45**: Facility sync Cypher includes `fac.feedstock_type` in ON CREATE/ON MATCH SET
