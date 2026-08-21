---
name: Business Logic Bug Fixes
overview: Fix 14 confirmed business logic bugs in the enrichment pipeline, material profile model, and seed data. These bugs cause polymer/form/source misclassification that corrupts matching engine results.
todos: []
isProject: false
---

# Business Logic Bug Fix Plan

## Scope

Fix 14 confirmed bugs across 4 files that cause material misclassification in the enrichment pipeline.

## Files to Modify

1. [plasticos_enrichment/models/enrichment_service.py](plasticos_enrichment/models/enrichment_service.py) - Normalization maps and resolve methods
2. [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py) - Domain fix and attribute sync
3. [plasticos_material_profile/data/material_form_data.xml](plasticos_material_profile/data/material_form_data.xml) - Add form_supersacs
4. [plasticos_material_profile/data/grade_template_data.xml](plasticos_material_profile/data/grade_template_data.xml) - Fix PP Supersacs refs
5. [plasticos_material_profile/form_codes.py](plasticos_material_profile/form_codes.py) - Add SUPERSACS code

---

## Commit 1: Polymer Normalization Fixes (enrichment_service.py)

### P1 - LLDPE Fix
```python
# Change:
"lldpe": "LDPE",
# To:
"lldpe": "LLDPE",
"linear low-density polyethylene": "LLDPE",
"linear low density polyethylene": "LLDPE",
```

### P4 - PA/Nylon Fix (emit NYLON directly)
```python
# Change:
"pa": "PA",
"nylon": "PA",
"polyamide": "PA",
# To:
"pa": "NYLON",
"nylon": "NYLON",
"polyamide": "NYLON",
"pa6": "NYLON",
"pa66": "NYLON",
```

### P5 - PP-PE Fix (emit PP_PE directly)
```python
# Change:
"pp-pe": "PP-PE",
# To:
"pp-pe": "PP_PE",
"pp/pe": "PP_PE",
"pp pe": "PP_PE",
```

### P6 - HMW HDPE Fix (emit HDPE_HMW directly)
```python
# Change:
"hmw hdpe": "HMW HDPE",
"hmw": "HMW HDPE",
# To:
"hmw hdpe": "HDPE_HMW",
"hmw": "HDPE_HMW",
"hdpe hmw": "HDPE_HMW",
"high molecular weight hdpe": "HDPE_HMW",
```

### P7 - Mixed Fix (emit MIXED directly)
```python
# Change:
"mixed": "Mixed",
# To:
"mixed": "MIXED",
"co-mingled": "MIXED",
"comingled": "MIXED",
"commingled": "MIXED",
```

### P8 - Add Missing Polymer Aliases
Add entries for: EVA, TPE, PBT, POM, PPO, MRP, EWASTE, METAL, PLASTIC_PALLETS, GAYLORD_BOXES (see full list in bug doc)

### Clean up polymer_code_map
Remove now-redundant entries from `_resolve_polymer_id()`:
- `"HMW HDPE": "HDPE_HMW"` - no longer needed
- `"PC-PMMA": "PC_PMMA"` - already fixed
- `"PP-PE": "PP_PE"` - no longer needed
- `"PA": "NYLON"` - no longer needed
- `"Mixed": "MIXED"` - no longer needed

---

## Commit 2: Source Type Normalization Fix (enrichment_service.py)

### S1 - Replace SOURCE_TYPE_NORMALIZE
Replace the entire map to emit actual seed codes directly and fix semantic errors:
- `"clean"` should map to `POST_INDUSTRIAL` (not PRIME)
- `"mixed"` should map to `None` (condition, not source type)
- `"reusable"` should map to `None` (condition, not source type)
- Add proper aliases for all 8 source types

### Simplify _resolve_source_type_id
Remove the `st_map` translation layer - direct DB lookup only.

---

## Commit 3: Form Normalization Fixes (enrichment_service.py)

### F1 - FILM Fix
```python
# Change:
"FILM": "ROLLSTOCK",
# To:
"FILM": "FILM",
```

### F2 - REPRO Fix
```python
# Change:
"REPRO": "REGRIND",
# To:
"REPRO": "PELLETS",
```

### F3 - Packaging Routing
Add `FORM_TO_PACKAGING_CODE` map and `PACKAGING_NORMALIZE` map to route gaylord/supersack/pallet tokens to `packaging_type_id` instead of `form_id`.

---

## Commit 4: Material Profile Model Fixes

### D3 - Fix partner_id domain
```python
# Change:
domain="[('parent_id','!=',False)]",
# To:
domain="[('is_facility','=',True)]",
```

### D1 - Add condition attribute sync
Add `_sync_condition_attributes()` method that syncs `has_metal`, `is_metalized`, `has_fr` booleans to `material_attribute_ids`.

---

## Commit 5: Seed Data Fixes

### G2a - Add form_supersacs to material_form_data.xml
```xml
<record id="form_supersacs" model="plasticos.material.form">
  <field name="name">Supersacs</field>
  <field name="code">SUPERSACS</field>
  <field name="sequence">157</field>
</record>
```

### G2b - Add SUPERSACS to form_codes.py
Add `"SUPERSACS"` to `FORM_CODES` tuple.

### G2c - Fix grade_template_data.xml
Change PP Supersacs grade:
- `form_id`: `form_parts` to `form_supersacs`
- `packaging_type_id`: `packaging_bales` to `packaging_supersacks`

---

## Deployment

After push to staging:
```bash
odoo-bin -u plasticos_material_profile,plasticos_enrichment -d plasticos --stop-after-init
```

## Risk Assessment

- **Commit 1-3**: Zero DB risk, pure Python map changes
- **Commit 4**: Requires module update, low risk
- **Commit 5**: Requires module update, adds new seed record