---
name: Intake Form UI Optimization
overview: Reorganize the Intake form layout, remove duplicate fields, add ENTITY_STATUS field, fix the normalizer bug, and update field groupings per user specifications.
todos:
  - id: fix-normalizer-bug
    content: "Fix AttributeError in intake_normalizer.py: change self.polymer to self.polymer_id, self.form to self.form_id"
    status: completed
  - id: add-entity-status
    content: Add entity_status Selection field to res.partner and related field on intake
    status: completed
  - id: add-flame-retardant-attr
    content: Add Flame Retardant attribute to material_attribute_data.xml with has_fr sync
    status: completed
  - id: convert-packaging-multiselect
    content: Convert packaging_type_id Many2one to packaging_type_ids Many2many
    status: completed
  - id: restructure-form-view
    content: "Reorganize intake_views.xml: move fields, rename groups, remove Origin tab, reorder tabs"
    status: completed
  - id: enhance-match-button
    content: Update action_match_to_buyers() to auto-create material profile if missing
    status: completed
isProject: false
---

# Intake Form UI Optimization

## Summary

Reorganize the Intake form to optimize layout, remove duplications, add new fields, and fix the normalizer bug that references old field names.

---

## 1. Bug Fix: Normalizer AttributeError

**File:** [plasticos_intake_normalizer/models/intake_normalizer.py](plasticos_intake_normalizer/models/intake_normalizer.py)

**Problem:** Lines 232-253 reference `self.polymer` and `self.form` (old Char fields) instead of `self.polymer_id` and `self.form_id` (current Many2one fields).

**Fix:** Update all references in `_validate_for_normalization()`:

- `self.polymer` -> `self.polymer_id`
- `self.form` -> `self.form_id`
- Update string comparisons to use `.name` attribute

---

## 2. ENTITY_STATUS Field

**Analysis:** No existing ENTITY_STATUS field found. Odoo's built-in `active` field only provides True/False. Need a 3-state field.

**Recommendation:** Add to `res.partner` in [plasticos_facility_profile/models/res_partner.py](plasticos_facility_profile/models/res_partner.py):

```python
entity_status = fields.Selection(
    [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("blocked", "Blocked"),
    ],
    string="Entity Status",
    default="active",
    tracking=True,
)
```

**Best placement on Intake form:** In the "Company & Facility" group, displayed as read-only (pulled from `partner_id.entity_status`).

---

## 3. Flame Retardant -> Attribute

**Current state:** `has_fr` Boolean field exists on intake model.

**Changes:**

- Add "Flame Retardant" attribute to [plasticos_material_profile/data/material_attribute_data.xml](plasticos_material_profile/data/material_attribute_data.xml)
- Remove `has_fr` checkbox from form view (keep field for backward compatibility)
- Add onchange sync like `has_metal` / `is_metalized`

---

## 4. Has Metal Checkbox -> Remove from UI

**Current state:** `has_metal` checkbox shown in "Additives & Flags" group.

**Change:** Remove from form view. Already synced via `material_attribute_ids` (With Metal / No Metal attributes).

---

## 5. Rename "Additives & Flags" -> "Filler"

**File:** [plasticos_intake/views/intake_views.xml](plasticos_intake/views/intake_views.xml) line 301

**Change:** `string="Additives &amp; Flags"` -> `string="Filler"`

Keep only:

- `filler_type_id`
- `filler_pct`

---

## 6. Rename "Observed Quality" -> "Specs"

**File:** [plasticos_intake/views/intake_views.xml](plasticos_intake/views/intake_views.xml) line 290

**Change:** `string="Observed Quality"` -> `string="Specs"`

---

## 7. Packaging -> Multi-Select

**Current:** `packaging_type_id` is Many2one (single select).

**Change:** Convert to Many2many:

- Model: `packaging_type_ids = fields.Many2many("plasticos.packaging.type", ...)`
- View: `widget="many2many_tags"`

---

## 8. Delete origin_form_id from View

**File:** [plasticos_intake/views/intake_views.xml](plasticos_intake/views/intake_views.xml) line 262

**Change:** Remove `<field name="origin_form_id"/>` (duplicates `form_id`).

---

## 9. Move source_type_id Above polymer_id

**Current order:** polymer_id, form_id, origin_form_id, color_id, source_type_id

**New order:** source_type_id, polymer_id, form_id, color_id

---

## 10. Move Process Type & Sector to Top Section

**Current:** In "Origin" tab.

**Change:** Move `origin_sector` and `origin_process_type` to main page, above "Volume & Frequency" group.

---

## 11. Hide origin_application Field

**Change:** Add `invisible="1"` to the field (preserves data, hides from UI).

---

## 12. Disable "Origin" Tab, Make "Quality" Default

**Changes:**

- Remove or hide the "Origin" page entirely (all useful fields moved out)
- Reorder notebook pages so "Quality" (renamed "Specs") is first visible tab

---

## 13. Rename "Intake Notes" -> "Notes"

**File:** [plasticos_intake/views/intake_views.xml](plasticos_intake/views/intake_views.xml) line 308

**Change:** `string="Intake Notes"` -> `string="Notes"`

---

## 14. Match To Buyers Button Enhancement

**Current behavior:** Creates match lines but does NOT auto-create material profile.

**Required enhancement:** In `action_match_to_buyers()`:

1. If `material_profile_id` is not set, auto-create one from intake fields
2. Link profile to `partner_id` (or create partner from `pending_company_name` first)
3. Then proceed with buyer matching

---

## Files to Modify


| File                                                          | Changes                                                                                          |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `plasticos_intake/models/intake.py`                           | Convert `packaging_type_id` to `packaging_type_ids` Many2many; add `entity_status` related field |
| `plasticos_intake/views/intake_views.xml`                     | Major form restructure (field order, tab removal, renames)                                       |
| `plasticos_facility_profile/models/res_partner.py`            | Add `entity_status` Selection field                                                              |
| `plasticos_material_profile/data/material_attribute_data.xml` | Add "Flame Retardant" attribute                                                                  |
| `plasticos_intake_normalizer/models/intake_normalizer.py`     | Fix `polymer` -> `polymer_id`, `form` -> `form_id` bug                                           |


---

## Proposed Form Layout (After Changes)

```
HEADER: [Match To Buyers] [Edit] [Send Offers] | Status: draft/matched

SMART BUTTONS: [Profile] [Company] [Facility]

GROUP 1: Company & Facility          | GROUP 2: Contact & Assignment
- pending_company_name (if no partner)| - contact_id
- partner_id                          | - contact_phone
- facility_id                         | - contact_email
- entity_status (readonly, from partner)| - assigned_user_id
- material_profile_id                 |

GROUP 3: Material                    | GROUP 4: Classification
- source_type_id                     | - origin_sector
- polymer_id                         | - origin_process_type
- form_id                            |
- color_id                           |
- packaging_type_ids (multi-select)  |
- material_attribute_ids             |

GROUP 5: Volume & Frequency
- quantity_per_load_lbs
- loads_per_month
- grade_hint

NOTEBOOK:
- Tab 1: Specs (was Quality, now default)
  - Specs: mfi_value, density_value, moisture_pct
  - Contamination: contamination_pct, contamination_notes
  - Filler: filler_type_id, filler_pct
  - Notes: intake_notes (renamed)
- Tab 2: Facility Info (unchanged)
- Tab 3: Buyer Matches (unchanged, visible when matched)
```

