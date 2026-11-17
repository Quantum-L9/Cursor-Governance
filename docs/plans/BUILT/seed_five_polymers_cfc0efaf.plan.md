---
name: Seed five polymers
overview: Add SAN, EPP, MDPE, EPE, and PETG as polymer masters in plasticos_material_profile,
  next to their existing families, and register each code on the stored polymer selection
  so profiles keep the code. No default form, attributes, or other-module behavior.
todos:
- id: seed-polymers
  content: Add EPP, MDPE, EPE, PETG, and SAN records to the noupdate=1 block of polymer_data.xml
    with family sequence, resin code, and full name.
  status: completed
- id: selection
  content: Add the five codes to the stored polymer Selection on material_profile.py
    next to their families.
  status: completed
- id: version
  content: Bump plasticos_material_profile to 19.0.5.11.16 in the manifest and README
    front matter.
  status: completed
isProject: false
built: true
status: built
---

# Seed SAN, EPP, MDPE, EPE, and PETG

No Foam form, no default-form field, and no onchange. Each new polymer is a normal `plasticos.polymer` row with the same fields its neighbors already have: `name`, `code`, `full_name`, `resin_id_code`, `category`, `sequence`.

## Where they sit

Insert them in the `noupdate="1"` block of [plasticos_material_profile/data/polymer_data.xml](plasticos_material_profile/data/polymer_data.xml), using free sequence numbers so the list order stays with the family (`_order = "sequence, name"`).

- **EPP** — commodity, sequence `12` (PP is `10`), resin `5`, full name Expanded Polypropylene. XML id `polymer_epp`.
- **MDPE** — commodity, sequence `45` (LDPE `40`, LLDPE `50`), resin `4`, full name Medium-Density Polyethylene. XML id `polymer_mdpe`.
- **EPE** — commodity, sequence `52` (after LLDPE), resin `4`, full name Expanded Polyethylene. XML id `polymer_epe`.
- **PETG** — commodity, sequence `75` (PET is `70`), resin `1`, full name Polyethylene Terephthalate Glycol. XML id `polymer_petg`.
- **SAN** — commodity, sequence `85` (ABS `80`, HIPS `90`), resin `7`, full name Styrene Acrylonitrile. XML id `polymer_san`.

Codes stay uppercase, matching `HDPE` and `EPS`.

## Wiring inside the module

The stored `polymer` Selection on [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py) is what `_compute_polymer_code` will persist. A profile whose polymer is missing from that list stores a blank code. Add the five keys beside their families:

- `EPP` next to `PP`
- `MDPE` and `EPE` next to `LDPE` / `LLDPE`
- `PETG` next to `PET`
- `SAN` next to `ABS`

No new model, field, view, ACL, or form master. [plasticos_product](plasticos_product/models/product_template.py) already creates one product when a polymer is created, so these five products appear on `-u plasticos_material_profile` when that addon is installed. Do not edit `plasticos_product`.

Leave [plasticos_material_profile/data/material_mapping.csv](plasticos_material_profile/data/material_mapping.csv) and the normalizer alone. Those ERP lines stay `unknown` / `names no polymer master` until a later mapping decision. The ledger test in [tests/test_material_ledger_resolution.py](tests/test_material_ledger_resolution.py) stays valid because those rows have an empty polymer cell.

## Version

Bump [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py) and the `module_version` front matter in [plasticos_material_profile/README.md](plasticos_material_profile/README.md) from `19.0.5.11.15` to `19.0.5.11.16`. Data plus a selection list is a patch. No migration folder: new `noupdate="1"` records load on `-u`.

## Check

Existing [tests/test_material_grade_codes.py](tests/test_material_grade_codes.py) and [tests/test_material_mapping_masters.py](tests/test_material_mapping_masters.py) only require mapped codes to exist. Confirm they still pass, and confirm the five new codes appear both in `polymer_data.xml` and in the Selection. Do not run `make update` or `make test-module` from this change.

## Build evidence (auto)

- detected_at: `2026-11-11T18:05:28Z`
- conversation_id: `c8c67d5a-a232-412e-bc61-417d49f9b763`
- generation_id: `8fa06c2f-ae4b-4e4b-997f-15ebda5c24ae`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/c8c67d5a-a232-412e-bc61-417d49f9b763/c8c67d5a-a232-412e-bc61-417d49f9b763.jsonl`
- todos at build time:
- `seed-polymers`: completed
- `selection`: completed
- `version`: completed
