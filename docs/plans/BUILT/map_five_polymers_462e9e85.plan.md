---
name: Map five polymers
overview: Wire the ERP phrases that name only SAN, EPP, MDPE, EPE, or PETG into the
  worksheet resolver that `make import-erp` and `make import-vanillasoft` already
  call. Leave the production targets, blend rows, and the unrelated roster failures
  alone.
todos:
- id: specs
  content: Add the fourteen exact _SPECS entries in material_normalizer.py
  status: completed
- id: matrix
  content: Mark only those fourteen material_mapping.csv rows mapped, with the same
    cells
  status: completed
- id: proof
  content: Assert worksheet resolution for the new phrases and unchanged blend rows;
    bump material_profile to 19.0.5.11.18
  status: completed
isProject: false
built: true
status: built
---

# Map the five new polymers through the existing importers

The seed on `feat/seed-five-polymers` added the masters and the stored `polymer` selection. It left the resolver unchanged, which is why those ERP descriptions still import as unresolved. The fix stays inside that resolver. It does not add an import path and it does not retarget production.

## What the makefile already calls

- `make import-erp` classifies each `InvoiceDesc` with `normalize_material` and no CRM aliases, in [`plasticos_transaction/models/native_document_import.py`](plasticos_transaction/models/native_document_import.py) (`_normalize_line`). Only an exact `_SPECS` hit resolves.
- `make import-vanillasoft` classifies with `crm_aliases=True` in [`plasticos_crm_sync/services/orchestrator.py`](plasticos_crm_sync/services/orchestrator.py). `_SPECS` is checked first, so the same phrases cover the sync.
- [`Makefile`](Makefile) `import-vanillasoft` writes the Odoo.sh production database over SSH and refuses a test-env clone. That recipe stays as it is. Do not run either import as part of this change.

## Cause, and what is not the cause

Phrases such as `EPE - Pink`, `SAN Regrind`, and `PETG Resin` are `unknown` / `names no polymer master` in [`plasticos_material_profile/data/material_mapping.csv`](plasticos_material_profile/data/material_mapping.csv) because the masters did not exist when the matrix was built. The masters exist now. The worksheet resolver still returns `unresolved material` for them.

The eight full-roster failures are not this defect. They sit in web leads, security, commission, CRM bridge, enrichment, and an existing CRM-versus-worksheet assertion for `Bottles (HD/PET)`. This branch does not change those modules. Do not edit them.

## Rows to map

Add one `_SPECS` entry per phrase, and set that same row in the matrix to `mapped` / `names_one_polymer` with the same cells. A secondary master is filled only when the phrase names exactly one seeded form, grade, color, source, or attribute. Do not invent `PINK`, `CLIPS`, or a tint color.

- `epe - pink` → `EPE`
- `epe - white` → `EPE`, color `WHITE`
- `epp - black` → `EPP`, color `BLACK`
- `mdpe clips` → `MDPE`
- `mdpe film on rolls - clear with print` → `MDPE`, color `CLEAR`, attribute `printed`. Film and rolls are two forms, so form stays empty.
- `mdpe post industrial printed rolls` → `MDPE`, form `ROLLSTOCK`, source `POST_INDUSTRIAL`, attribute `printed`
- `petg bad pellets - bad melt` → `PETG`, form `PELLETS`
- `petg clear rolls` → `PETG`, form `ROLLSTOCK`, color `CLEAR`
- `petg clear/cloudy repro pellet` → `PETG`, form `PELLETS`. Clear and cloudy are both named, so color stays empty.
- `petg resin` → `PETG`
- `petg rolls - clear` → `PETG`, form `ROLLSTOCK`, color `CLEAR`
- `petg rolls - tinted` → `PETG`, form `ROLLSTOCK`
- `petg trays` → `PETG`, material grade `TRAYS`
- `san regrind` → `SAN`, form `REGRIND`

## Rows that stay as they are

These already name more than one polymer, or an operator already chose one:

- `ldpe/hdpe/mdpe purge...` stays `ambiguous`
- `ldpe/mdpe film rolls...`, `ldpe / mdpe mixed color film`, and `ldpe/mdpe printed rolls` stay mapped to `LDPE`
- `rejected material - pet clear sheet w/ petg contamination` stays `PET` / `SHEET` / `CLEAR`
- `mixed plastic mdpe` stays unknown. It names both `MIXED` and `MDPE`.

Do not run [`scripts/build_material_mapping.py`](scripts/build_material_mapping.py) across the matrix. A full rebuild would reclassify existing PET and polyethylene rows because `PET` is a prefix of `PETG` and `MDPE` now matches inside blend text. Edit only the fourteen rows above.

[`tests/test_material_ledger_resolution.py`](tests/test_material_ledger_resolution.py) checks the closed 11-04-26 ledger (`applied == 16`). These phrases are not in that ledger, so the ledger files stay untouched. [`plasticos_crm_sync/tests/test_material_mapping_map.py`](plasticos_crm_sync/tests/test_material_mapping_map.py) requires every `_SPECS` key to be a mapped matrix row, which the fourteen row edits satisfy. VanillaSoft’s own CSV has none of these tokens and stays untouched.

## Version and proof

[`plasticos_material_profile`](plasticos_material_profile/__manifest__.py) is `19.0.5.11.17`. The normalizer change is a patch, so bump the manifest and the README `module_version` to `19.0.5.11.18`.

Extend [`plasticos_material_profile/tests/test_material_normalizer.py`](plasticos_material_profile/tests/test_material_normalizer.py) so each new phrase resolves on the worksheet call (`crm_aliases` left false), which is the `make import-erp` path, and so `mixed plastic mdpe` and the PET-with-PETG contamination phrase stay on their current results.

Do not change the facility-profile migration, the harvest documents, `plasticos_product`, or the Makefile.

## Build evidence (auto)

- detected_at: `2026-11-11T21:06:25Z`
- conversation_id: `24515ea1-fd20-49bc-87d9-9898de8ab129`
- generation_id: `c02972af-5f0d-44be-b179-30a8afd01d36`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/24515ea1-fd20-49bc-87d9-9898de8ab129/24515ea1-fd20-49bc-87d9-9898de8ab129.jsonl`
- todos at build time:
- `specs`: completed
- `matrix`: completed
- `proof`: completed
