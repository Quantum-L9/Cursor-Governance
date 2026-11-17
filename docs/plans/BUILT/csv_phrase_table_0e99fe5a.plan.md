---
name: CSV phrase table
overview: Make material_mapping.csv the only phrase table. The normalizer loads a
  mapped row and resolves its masters. The three Python phrase dictionaries go away,
  and the generator can no longer rewrite the sheet from them.
todos:
- id: mark-blends
  content: Mark the four two-polymer rows ambiguous in material_mapping.csv
  status: completed
- id: loader
  content: Load mapped material rows in the normalizer and delete the three phrase
    dictionaries
  status: completed
- id: retire-builder
  content: Stop build_material_mapping.py from reading the normalizer or writing the
    matrix
  status: completed
- id: proof
  content: Point the phrase tests at the sheet and bump material_profile to 19.0.5.12.1
  status: completed
isProject: false
built: true
status: built
---

# The CSV is the phrase table

Work stays on `feat/ld-lld-phrase-map` in [`/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19-ld-lld`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld). The open checkout `docs/candidate-add-ons` is not edited. No push.

[`plasticos_material_profile/data/material_mapping.csv`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld/plasticos_material_profile/data/material_mapping.csv) is the only phrase table. [`plasticos_material_profile/models/material_normalizer.py`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld/plasticos_material_profile/models/material_normalizer.py) loads it once and looks up the collapsed `match_key`. A row is live only when `field_role` is `material`, `status` is `mapped`, and `polymer` is set. `unknown`, `ambiguous`, `not_material`, and `note_not_material` stay unresolved. Duplicate material keys fail the load.

ERP and CRM both use that lookup. `crm_aliases` remains on the function so current callers still run, and it no longer selects a second table. Bare `ldpe` and `hdpe` therefore resolve on an invoice description, because those rows are already mapped. `PET Bottles` and `Bottles (HD/PET)` resolve on both paths too.

The loader copies the sheet cells onto the existing spec: polymer, material grade, grade letter, form, source, attributes, color, filler, process, packaging. Colors and attributes stay space-separated. Conflict checking stays in code: a description and a grade hint that disagree on polymer, material grade, grade letter, form, or source stay unresolved. `is_crm_call_note` and its phrase set stay in code. `classify_material_word` stays for web-lead eligibility and is no longer a fallback inside `normalize_material`.

## Rows that must not start resolving

These name two polymers and are mapped to one of them today. Set `status` to `ambiguous` and say so in `note`, so the sheet and the lookup agree:

- `ldpe/mdpe film rolls and post industrial bales`
- `ldpe / mdpe mixed color film`
- `ldpe/mdpe printed rolls`
- `rejected material - pet clear sheet w/ petg contamination`

`ldpe/hdpe/mdpe purge clean, no paper, no metal` is already `ambiguous`. `shrink wrap` and `mixed plastic mdpe` stay `unknown`.

## Remove the other authority

Delete `_SPECS`, `_CRM_EXACT`, and `_CRM_ALIASES` from the normalizer. [`scripts/build_material_mapping.py`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld/scripts/build_material_mapping.py) stops reading those dictionaries and exits before it can write the committed matrix. The sheet is edited by hand.

Bump [`plasticos_material_profile`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld/plasticos_material_profile/__manifest__.py) and its README `module_version` from `19.0.5.12.0` to `19.0.5.12.1`. The CSV stays out of the manifest `data` list. No new migration.

## Proof

Update the phrase tests so they read the sheet instead of `_SPECS`: a mapped row resolves to its cells, the four blends and `shrink wrap` stay unresolved, and `hdpe crates` still carries injection. The worksheet assertion that `PET Bottles` is unresolved, and the CRM assertion that `Bottles (HD/PET)` is unresolved, change to the mapped cells. [`tests/test_material_mapping_map.py`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/IB-Odoo_19-ld-lld/plasticos_crm_sync/tests/test_material_mapping_map.py) stops walking the three dictionaries.

## Build evidence (auto)

- detected_at: `2026-11-12T15:59:49Z`
- conversation_id: `24515ea1-fd20-49bc-87d9-9898de8ab129`
- generation_id: `e63b1739-c625-41e2-bac0-59e57c3d2791`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/24515ea1-fd20-49bc-87d9-9898de8ab129/24515ea1-fd20-49bc-87d9-9898de8ab129.jsonl`
- todos at build time:
- `mark-blends`: completed
- `loader`: completed
- `retire-builder`: completed
- `proof`: completed

