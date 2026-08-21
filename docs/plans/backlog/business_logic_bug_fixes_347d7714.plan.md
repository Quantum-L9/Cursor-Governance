---
name: Business Logic Bug Fixes
overview: Fix 11 confirmed business logic bugs in the enrichment pipeline, material profile model, and seed data. P2 (PC) and P3 (PS) already fixed in prior GMP. These bugs cause polymer/form/source misclassification that corrupts matching engine results.
todos:
  - id: commit-1
    content: Polymer normalization fixes (P1, P4-P8) + PC-PMMA underscore fix + clean up polymer_code_map
    status: pending
  - id: commit-2
    content: Source type normalization fix (S1) - replace map + simplify resolver
    status: pending
  - id: commit-3
    content: Form normalization fixes (F1, F2, F3) + packaging routing with exact insertion point
    status: pending
  - id: commit-4
    content: Material profile model fixes (D1, D3) - domain + attribute sync (direct field assignment)
    status: pending
  - id: commit-5
    content: Seed data fixes (G2a, G2b, G2c) - form_supersacs + grade template
    status: pending
isProject: false
---

# Business Logic Bug Fix Plan (Amended)

## Evaluator Verification Summary

- P2 (PC/Polycarbonate): NOT A BUG - already `"pc": "PC"` in live code
- P3 (PS/EPS): NOT A BUG - already `"ps": "PS"` in live code
- TPO, BOPP, OCC: Already mapped - skip in P8
- PC-PMMA: Still emits `"PC-PMMA"` (hyphen) - must fix to `"PC_PMMA"` (underscore)

## Scope

Fix 11 confirmed bugs across 4 files that cause material misclassification in the enrichment pipeline.

## Files to Modify

1. [plasticos_enrichment/models/enrichment_service.py](plasticos_enrichment/models/enrichment_service.py) - Normalization maps and resolve methods
2. [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py) - Domain fix and attribute sync
3. [plasticos_material_profile/data/material_form_data.xml](plasticos_material_profile/data/material_form_data.xml) - Add form_supersacs
4. [plasticos_material_profile/data/grade_template_data.xml](plasticos_material_profile/data/grade_template_data.xml) - Fix PP Supersacs refs
5. [plasticos_material_profile/form_codes.py](plasticos_material_profile/form_codes.py) - Add SUPERSACS code (verified: FORM_CODES tuple exists)

---

## Commit 1: Polymer Normalization Fixes (enrichment_service.py)

### P1 - LLDPE Fix (CONFIRMED: line 43 has `"lldpe": "LDPE"`)

```python
# Change:
"lldpe": "LDPE",
# To:
"lldpe": "LLDPE",
"linear low-density polyethylene": "LLDPE",
"linear low density polyethylene": "LLDPE",
```

### PC-PMMA Underscore Fix (CONFIRMED: lines 61-62 emit hyphen)

```python
# Change:
"pc-pmma": "PC-PMMA",
"pc/pmma": "PC-PMMA",
# To:
"pc-pmma": "PC_PMMA",
"pc/pmma": "PC_PMMA",
```

### P4 - PA/Nylon Fix (CONFIRMED: lines 65-67 emit "PA")

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
"nylon 6": "NYLON",
"nylon 66": "NYLON",
```

### P5 - PP-PE Fix (CONFIRMED: line 72 emits "PP-PE")

```python
# Change:
"pp-pe": "PP-PE",
# To:
"pp-pe": "PP_PE",
"pp/pe": "PP_PE",
"pp pe": "PP_PE",
```

### P6 - HMW HDPE Fix (CONFIRMED: lines 37-38 emit "HMW HDPE")

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

### P7 - Mixed Fix (CONFIRMED: line 75 emits "Mixed")

```python
# Change:
"mixed": "Mixed",
# To:
"mixed": "MIXED",
"co-mingled": "MIXED",
"comingled": "MIXED",
"commingled": "MIXED",
"mixed plastics": "MIXED",
```

### P8 - Add Missing Polymer Aliases (SKIP: TPO, BOPP, OCC already mapped)

Add ONLY these (not already in map):

- EVA: `"eva"`, `"ethylene vinyl acetate"`
- TPE: `"tpe"`, `"thermoplastic elastomer"`, `"sebs"`
- PBT: `"pbt"`, `"polybutylene terephthalate"`
- POM: `"pom"`, `"acetal"`, `"delrin"`, `"polyoxymethylene"`
- PPO: `"ppo"`, `"polyphenylene oxide"`, `"noryl"`
- MRP: `"mrp"`, `"mixed rigid plastic"`, `"mixed rigids"`
- EWASTE: `"ewaste"`, `"e-waste"`, `"electronic waste"`
- METAL: `"metal"`, `"aluminum"`, `"steel"`, `"ferrous"`
- PLASTIC_PALLETS: `"plastic pallets"`, `"plastic pallet"`
- GAYLORD_BOXES: `"gaylord boxes"`, `"gaylord box"`

### Clean up polymer_code_map (CONFIRMED: lines 417-423)

Remove these entries from `_resolve_polymer_id()` after fixes above:

- `"HMW HDPE": "HDPE_HMW"` - no longer needed (P6 fix)
- `"PC-PMMA": "PC_PMMA"` - no longer needed (PC-PMMA underscore fix)
- `"PP-PE": "PP_PE"` - no longer needed (P5 fix)
- `"PA": "NYLON"` - no longer needed (P4 fix)
- `"Mixed": "MIXED"` - no longer needed (P7 fix)

Result: `polymer_code_map` becomes empty dict `{}` - can simplify `_resolve_polymer_id()` to direct lookup.

---

## Commit 2: Source Type Normalization Fix (enrichment_service.py)

### S1 - Replace SOURCE_TYPE_NORMALIZE (CONFIRMED: lines 119-131)

Current broken map:

```python
SOURCE_TYPE_NORMALIZE = {
    "clean": "CLEAN",      # -> st_map["CLEAN"] = "PRIME" (WRONG)
    "mixed": "MIXED",      # -> st_map["MIXED"] = "WIDE_SPEC" (WRONG)
    "reusable": "REUSE",   # -> st_map["REUSE"] = "PRIME" (WRONG)
    ...
}
```

Replace with direct seed codes:

```python
SOURCE_TYPE_NORMALIZE = {
    # Post-Consumer
    "post-consumer": "POST_CONSUMER",
    "post consumer": "POST_CONSUMER",
    "pcr": "POST_CONSUMER",
    # Post-Industrial
    "post-industrial": "POST_INDUSTRIAL",
    "post industrial": "POST_INDUSTRIAL",
    "pir": "POST_INDUSTRIAL",
    "clean": "POST_INDUSTRIAL",      # "clean scrap" = clean PI
    "clean scrap": "POST_INDUSTRIAL",
    # Post-Commercial
    "post-commercial": "POST_COMMERCIAL",
    "post commercial": "POST_COMMERCIAL",
    # Agricultural
    "agricultural": "AGRICULTURAL",
    "ag film": "AGRICULTURAL",
    # Prime / Virgin
    "prime": "PRIME",
    "virgin": "PRIME",
    # Wide Spec
    "wide spec": "WIDE_SPEC",
    "wide-spec": "WIDE_SPEC",
    "off-prime": "WIDE_SPEC",
    # Off Spec
    "off-spec": "OFF_SPEC",
    "off spec": "OFF_SPEC",
    "off-grade": "OFF_SPEC",
    "contaminated": "OFF_SPEC",
    # Ocean Recovered
    "ocean recovered": "OCEAN_RECOVERED",
    "ocean plastic": "OCEAN_RECOVERED",
    # Conditions (not source types) - map to None
    "mixed": None,
    "reusable": None,
    "no-value": None,
}
```

### Simplify _resolve_source_type_id (CONFIRMED: lines 442-464)

Remove `st_map` entirely - direct DB lookup:

```python
@api.model
def _resolve_source_type_id(self, code):
    if not code:
        return self.env["plasticos.source.type"]
    return self.env["plasticos.source.type"].search(
        [("code", "=", code)], limit=1
    )
```

---

## Commit 3: Form Normalization Fixes (enrichment_service.py)

### F1 - FILM Fix (CONFIRMED: line 163 in FORM_CODE_TO_MASTER)

```python
# Change:
"FILM": "ROLLSTOCK",
# To:
"FILM": "FILM",
```

### F2 - REPRO Fix (CONFIRMED: line 173 in FORM_CODE_TO_MASTER)

```python
# Change:
"REPRO": "REGRIND",
# To:
"REPRO": "PELLETS",
```

### F3 - Packaging Routing (EXACT INSERTION POINT: lines 689-696)

Add new maps after FORM_CODE_TO_MASTER:

```python
# Route packaging-as-form tokens to packaging_type instead of form
FORM_TO_PACKAGING_CODE = {
    "GAY": "gaylords",
    "SUPERSACK": "supersacks",
    "PAL": "palletized",
}

PACKAGING_NORMALIZE = {
    "gaylord": "gaylords",
    "gaylords": "gaylords",
    "super sack": "supersacks",
    "supersack": "supersacks",
    "fibc": "supersacks",
    "pallet": "palletized",
    "palletized": "palletized",
    "loose": "loose",
    "bulk": "bulk_trailer",
    "baled": "bales",
    "bales": "bales",
}
```

Replace lines 689-696 in `normalize_material()`:

```python
# ── form ──
raw_form = (raw_mat.get("form") or "").strip().lower()
norm_form = FORM_NORMALIZE.get(raw_form)
if norm_form:
    # Route packaging-as-form tokens to packaging_type instead of form
    pkg_code = FORM_TO_PACKAGING_CODE.get(norm_form)
    if pkg_code:
        profile_vals["packaging_type"] = pkg_code
        _prov("packaging_type", pkg_code, raw_mat)
        # Do NOT set profile_vals["form"] for packaging tokens
    else:
        profile_vals["form"] = norm_form
        _prov("form", norm_form, raw_mat)
elif raw_form:
    unmapped.append(("form", raw_mat.get("form")))

# ── packaging (explicit field) ──
raw_pkg = (raw_mat.get("packaging") or "").strip().lower()
if raw_pkg:
    norm_pkg = PACKAGING_NORMALIZE.get(raw_pkg)
    if norm_pkg:
        profile_vals["packaging_type"] = norm_pkg
        _prov("packaging_type", norm_pkg, raw_mat)
```

NOTE: `profile_vals["packaging_type"]` (string code) is resolved to `packaging_type_id` (integer) in the caller that creates `plasticos.material.profile` records, not in `normalize_material()`.

---

## Commit 4: Material Profile Model Fixes

### D3 - Fix partner_id domain (CONFIRMED: line 18)

```python
# Change:
domain="[('parent_id','!=',False)]",
# To:
domain="[('is_facility','=',True)]",
```

NOTE: The existing `_check_partner_is_facility` constraint posts a warning (not ValidationError) - this is intentional to allow enrichment flows. The domain change makes UI consistent with intent.

### D1 - Add condition attribute sync

Add method using DIRECT FIELD ASSIGNMENT (not `self.write()`) to avoid triggering `write()` override recursively:

```python
@api.depends("has_metal", "is_metalized", "has_fr")
def _sync_condition_attributes(self):
    """One-way sync: condition booleans -> material_attribute_ids.
    Booleans are source of truth for matching engine.
    """
    Attr = self.env["plasticos.material.attribute"]
    flag_to_code = {
        "has_metal": "with_metal",
        "is_metalized": "metalized",
        "has_fr": "flame_retardant",
    }
    for rec in self:
        for flag, code in flag_to_code.items():
            attr = Attr.search([("code", "=", code)], limit=1)
            if not attr:
                continue
            flag_value = getattr(rec, flag, False)
            already_present = attr in rec.material_attribute_ids
            if flag_value and not already_present:
                rec.material_attribute_ids = [(4, attr.id)]  # Direct assignment
            elif not flag_value and already_present:
                rec.material_attribute_ids = [(3, attr.id)]  # Direct assignment
```

---

## Commit 5: Seed Data Fixes

### G2a - Add form_supersacs to material_form_data.xml

Insert after form_loose (sequence 155), before form_drums (sequence 160):

```xml
<record id="form_supersacs" model="plasticos.material.form">
  <field name="name">Supersacs</field>
  <field name="code">SUPERSACS</field>
  <field name="description">PP or PE material in FIBC super sacks (bulk bags).</field>
  <field name="sequence">157</field>
</record>
```

### G2b - Add SUPERSACS to form_codes.py (VERIFIED: FORM_CODES tuple at line 16)

Add `"SUPERSACS"` to `FORM_CODES` tuple in alphabetical position.

### G2c - Fix grade_template_data.xml (CONFIRMED: lines 195-205)

Change PP Supersacs grade:

- `form_id`: `form_parts` to `form_supersacs`
- `packaging_type_id`: `packaging_bales` to `packaging_supersacks`

---

## Deployment

Commits 1-3 are pure Python dict changes - take effect on worker restart, no `-u` needed.

Commits 4-5 require module update:

```bash
odoo-bin -u plasticos_material_profile -d plasticos --stop-after-init
```

## Risk Assessment

- **Commit 1-3**: Zero DB risk, pure Python map changes, worker restart only
- **Commit 4**: Requires module update, low risk (domain change + new computed method)
- **Commit 5**: Requires module update, adds new seed record (form_supersacs)
