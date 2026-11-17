---
name: Translucent opaque attributes
overview: Seed XML only. Add Translucent and Opaque attributes, a Corrugated grade,
  Preforms, Resin, and Monofilament forms, and Stacked and Nested packaging. Remove
  Corrugated as a form. Grade templates, Python, tests, mapping, and migrations stay
  untouched.
todos:
- id: seed-attributes
  content: Add attr_translucent and attr_opaque to material_attribute_data.xml
  status: completed
- id: seed-grade
  content: Add material_grade_corrugated to material_grade_data.xml
  status: completed
- id: seed-form
  content: Remove form_corrugated and add form_preforms, form_resin, and form_monofilament
    in material_form_data.xml
  status: completed
- id: seed-packaging
  content: Add packaging_stacked and packaging_nested immediately after Palletized
    in packaging_type_data.xml
  status: completed
- id: bump-version
  content: Bump plasticos_material_profile to 19.0.5.13.2 in the manifest and README
    front matter
  status: completed
isProject: false
built: true
status: built
---

# Seed XML for attributes, grades, forms, and packaging

XML seed files only. Do not edit `grade_template_data.xml`, `form_codes.py`, `grade_codes.py`, tests, `material_mapping.csv`, the normalizer, or a migration. Grade templates get their own revision later. `grade_pp_corrugated` keeps `form_id` ref `form_corrugated` until then.

## Attributes

Append to the `noupdate="1"` block in [plasticos_material_profile/data/material_attribute_data.xml](plasticos_material_profile/data/material_attribute_data.xml), after `attr_pre_work_needed` (sequence 390).

- `attr_translucent` — name `Translucent`, code `translucent`, sequence `400`. Lets light through without being clear.
- `attr_opaque` — name `Opaque`, code `opaque`, sequence `410`. Does not let light through.

## Grades

Append to [plasticos_material_profile/data/material_grade_data.xml](plasticos_material_profile/data/material_grade_data.xml), after `material_grade_trash` (sequence 210).

- `material_grade_corrugated` — name `Corrugated`, code `CORRUGATED`, sequence `220`. Corrugated sheet, usually PP. Sheet stays the form.

## Forms

In [plasticos_material_profile/data/material_form_data.xml](plasticos_material_profile/data/material_form_data.xml):

- Delete the `form_corrugated` record.
- Add `form_preforms` — name `Preforms`, code `PREFORMS`, sequence `190`. Injection-molded preforms, typically PET bottle preforms.
- Add `form_resin` — name `Resin`, code `RESIN`, sequence `200`. Plastic resin as supplied.
- Add `form_monofilament` — name `Monofilament`, code `MONOFILAMENT`, sequence `210`. Single-strand filament.

## Packaging

Insert two records in [plasticos_material_profile/data/packaging_type_data.xml](plasticos_material_profile/data/packaging_type_data.xml) immediately after `packaging_palletized` (sequence 40) and before `packaging_loose` (sequence 50). Same fields as the existing rows: `name`, lowercase `code`, `description`, `sequence`. `plasticos.packaging.type` enforces `unique(code)`. Sequences sit between Palletized and Loose so the list order matches the file order.

- `packaging_stacked` — name `Stacked`, code `stacked`, sequence `42`. Parts stacked for shipment, without the wrap that Palletized names.
- `packaging_nested` — name `Nested`, code `nested`, sequence `44`. Parts nested inside one another for shipment (totes, buckets, pallets).

`packaging_palletized` stays as it is: code `palletized`, sequence `40`, description “Material stacked and wrapped on pallets.” Loose, Bulk Trailer, and Other keep sequences 50, 60, and 999.

## Version

Live manifest is `19.0.5.13.1`. These are the only non-XML edits:

- [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py) → `19.0.5.13.2`
- [plasticos_material_profile/README.md](plasticos_material_profile/README.md) front matter `module_version` to the same value

Do not run `make update`. Existing database rows that still point at the corrugated form are left as they are.

## Build evidence (auto)

- detected_at: `2026-11-12T18:57:54Z`
- conversation_id: `c671c514-b61f-4ac2-acf4-390b08ee8f77`
- generation_id: `f2e0d570-001b-402c-84f4-e80ca0f00d1c`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/c671c514-b61f-4ac2-acf4-390b08ee8f77/c671c514-b61f-4ac2-acf4-390b08ee8f77.jsonl`
- todos at build time:
- `seed-attributes`: completed
- `seed-grade`: completed
- `seed-form`: completed
- `seed-packaging`: completed
- `bump-version`: completed

