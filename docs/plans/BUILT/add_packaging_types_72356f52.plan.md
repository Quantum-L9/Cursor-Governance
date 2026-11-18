---
name: Add packaging types
overview: Add Stacked and Nested as seeded packaging types in plasticos_material_profile,
  and bump the module so an upgrade creates the two records. Stretch Film is already
  a seeded grade and is not added again.
todos:
- id: seed-records
  content: Add packaging_stacked and packaging_nested records to packaging_type_data.xml
  status: completed
- id: version-bump
  content: Bump plasticos_material_profile to 19.0.5.11.17 in the manifest and README
    front matter
  status: completed
isProject: false
built: true
status: built
---

# Add Stacked and Nested packaging types

Add two records to [`plasticos_material_profile/data/packaging_type_data.xml`](plasticos_material_profile/data/packaging_type_data.xml), using the same shape as the existing rows (`name`, lowercase `code`, `description`, `sequence`). Codes must be unique: `plasticos.packaging.type` enforces `unique(code)`.

Insert them after Bulk Trailer and before Other:

- `packaging_stacked` — name `Stacked`, code `stacked`, sequence `70`. Description: parts stacked for shipment, without the wrap that Palletized names.
- `packaging_nested` — name `Nested`, code `nested`, sequence `80`. Description: parts nested inside one another for shipment (totes, buckets, pallets).

Palletized stays as it is (`code` `palletized`, “Material stacked and wrapped on pallets.”).

## Version

[`plasticos_material_profile/__manifest__.py`](plasticos_material_profile/__manifest__.py) is `19.0.5.11.16`. The data file is `noupdate="0"`, so a patch bump to `19.0.5.11.17` is what makes `-u plasticos_material_profile` create the records. Set the same version in the README front matter `module_version` (the `readme-module-version` hook rewrites it when the manifest is staged).

No model, ACL, view, or migration change. The packaging field is already a Many2one to `plasticos.packaging.type`, so the new rows appear in existing Packaging dropdowns after the upgrade.

## Stretch Film

[`plasticos_material_profile/data/material_grade_data.xml`](plasticos_material_profile/data/material_grade_data.xml) already has `material_grade_stretch_film`: name `Stretch Film`, code `STRETCH_FILM`, sequence `190`. [`grade_codes.py`](plasticos_material_profile/grade_codes.py) lists `STRETCH_FILM` in the same order, and `tests/test_material_grade_codes.py` requires those two lists to match. A second record with that code would fail the unique-code constraint. Do not add it again.

## Left unchanged

[`scripts/build_material_mapping.py`](scripts/build_material_mapping.py) still maps the VanillaSoft form hint `stacked` to packaging `palletized`, and [`material_mapping.csv`](plasticos_material_profile/data/material_mapping.csv) line 2263 records that same decision. This change only adds the master values. It does not retarget that hint or rewrite mapping rows.

## Build evidence (auto)

- detected_at: `2026-11-12T21:08:37Z`
- conversation_id: `72965399-0741-4df5-be1f-98b99d2ac48e`
- generation_id: `045e2545-0c4f-4acb-af76-c5da4f1672c2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/72965399-0741-4df5-be1f-98b99d2ac48e/72965399-0741-4df5-be1f-98b99d2ac48e.jsonl`
- todos at build time:
- `seed-records`: completed
- `version-bump`: completed
