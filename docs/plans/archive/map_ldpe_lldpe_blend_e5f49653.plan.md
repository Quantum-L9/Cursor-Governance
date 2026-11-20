---
name: Map LDPE LLDPE blend
overview: Point the LDPE/LLDPE blend at the LDPE_LLDPE master, and stop web-lead merge from storing a grade in the form slot so the physical form still reaches the partner material profile.
todos:
  - id: retarget-specs
    content: Set LDPE_LLDPE on the clear-repro spec, the thick/stretch alias, the matrix rows, and the ledger note
    status: pending
  - id: assert-and-bump
    content: Assert both phrases in the normalizer test and bump plasticos_material_profile to 19.0.5.11.3
    status: pending
  - id: split-grade-from-form
    content: Move web-lead form and grade words into the normalizer and make _merge_ai_and_vision fill empty slots from it
    status: pending
isProject: false
---

# Map the LDPE/LLDPE blend to LDPE_LLDPE

The master already exists: `polymer_ldpe_lldpe` in [plasticos_material_profile/data/polymer_data.xml](plasticos_material_profile/data/polymer_data.xml) (`code` `LDPE_LLDPE`, approved 2026-11-04) and the matching Selection key in [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py). Importers read the polymer slot from the normalizer and from [plasticos_material_profile/data/material_mapping.csv](plasticos_material_profile/data/material_mapping.csv). Both still say `LLDPE`.

Change only the two rows that are already mapped. Leave the unmapped `ambiguous` phrases (`ldpe/lldpe repro`, `ldpe/lldpe blue repro`, `ldpe/lldpe blue/white purge`, `contaminated ldpe/lldpe`, `ld/lldpe repro`, `lldpe/ldpe mixed color purge`) unmapped.

## Code

- In [plasticos_material_profile/models/material_normalizer.py](plasticos_material_profile/models/material_normalizer.py), set `polymer="LDPE_LLDPE"` on the `ldpe/lldpe clear repro` spec. Keep form `PELLETS`, source `POST_INDUSTRIAL`, attribute `repro`, color `CLEAR`, packaging `gaylords`.
- In the same file, change the approved alias `ld/lldpe thick/stretch` from `LLDPE` to `LDPE_LLDPE`. It is the same blend, already mapped, with no other slots.
- In [plasticos_material_profile/data/material_mapping.csv](plasticos_material_profile/data/material_mapping.csv), set the polymer column to `LDPE_LLDPE` on those two rows (lines 209 and 212).
- In [plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv](plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv), replace the `ldpe/lldpe clear repro` polymer `LLDPE` and the note that says no polyethylene blend exists. The master is `LDPE_LLDPE`.
- Bump [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py) from `19.0.5.11.2` to `19.0.5.11.3`.

## Test

In `test_ledger_phrases_resolve_on_both_importers_and_keep_description_detail` in [plasticos_material_profile/tests/test_material_normalizer.py](plasticos_material_profile/tests/test_material_normalizer.py), assert `normalize_material` of `ldpe/lldpe clear repro` resolves `polymer.code == "LDPE_LLDPE"` and keeps pellets, post-industrial, repro, clear, and gaylords. Assert the CRM alias `ld/lldpe thick/stretch` resolves to `LDPE_LLDPE` and nothing else.

`tests/test_material_mapping_masters.py` already requires every mapped polymer code to be a seeded master, so `LDPE_LLDPE` satisfies it.

## Audit `_merge_ai_and_vision`: bucket, drum, and pallet are grades

`FORM_CODES` in [plasticos_material_profile/form_codes.py](plasticos_material_profile/form_codes.py) is the physical form list (regrind, film, pellets, bales, and the rest). Bucket, drum, and pallet are not on it. They are grades, along with tote, crate, and bottle, in `GRADE_CODES` and `FORMER_FORM_CODES` in [plasticos_material_profile/grade_codes.py](plasticos_material_profile/grade_codes.py).

[plasticos_web_leads/models/web_lead.py](plasticos_web_leads/models/web_lead.py) still treats those words as forms in three places inside `_merge_ai_and_vision`:

- `_FORM_NORMALIZE` (lines 114–129) maps `pallet`, `pallets`, `tote`, `totes`, `crate`, `crates`, `bottle`, `bottles`, `drum`, `drums`, `bucket`, `buckets`, `pail`, and `pails` onto `PALLETS`, `TOTES`, `CRATES`, `BOTTLES`, `DRUMS`, and `BUCKETS`. None of those codes are forms.
- The AI form is read through that map (line 965), so an AI answer of "pallet" becomes `merged["form"]`.
- The seller-text loop (lines 991–1011) writes the same grade codes into `merged["form"]` when the form slot is empty.
- Vision uses the same map and only writes when `merged["form"]` is empty (line 1055), so a grade already sitting there discards regrind or film.
- `split_material_code` (line 1069) then clears that form and keeps only the grade. `_create_intake` falls back to form `other`. [plasticos_material_profile/intake_delta_bridge.py](plasticos_material_profile/intake_delta_bridge.py) copies that `form_id` onto the partner material profile.

Do not add a second map in `web_lead.py`. [plasticos_material_profile/models/material_normalizer.py](plasticos_material_profile/models/material_normalizer.py) already owns phrase resolution, and `normalize_material` returns `form` and `material_grade` as separate slots. The merge's remaining drift is that it classifies words itself.

`normalize_material` matches the whole collapsed phrase against `_SPECS`. A lone word such as `regrind` or `drum` is not one of those phrases, and the worksheet phrase `pallets` means polymer `PLASTIC_PALLETS`, not grade `PALLETS`. Add one word table in the normalizer for that gap:

- Form words are the current `_FORM_NORMALIZE` entries whose code is in `FORM_CODES` (`bale`, `regrind`, `film`, `flake`, `roll`, and the rest). A word resolves to that form and to no grade.
- Grade words are `bucket`, `buckets`, `drum`, `drums`, `pallet`, `pallets`, `pail`, `pails`, `tote`, `totes`, `crate`, `crates`, `bottle`, and `bottles`. A word resolves to that grade and to no form.
- A single collapsed token that misses `_SPECS` uses this table. A multi-word phrase that misses `_SPECS` stays unresolved. The phrase `pallets` stays the existing spec.

`_merge_ai_and_vision` then calls `normalize_material` three times: the seller text, the AI form word, and the vision `observed_form`. Fill `polymer`, `form`, and `material_grade` from the seller text first, then the AI word, then vision. A later call fills only an empty slot. Two calls that set the same slot to different codes leave that slot empty. Do not use the normalizer's whole-identity conflict rule across the three calls: `hdpe drums` (grade `DRUMS`, no form) plus vision `regrind` must keep both. Delete `_FORM_NORMALIZE`, the seller-text loop that writes `merged["form"]`, and the trailing `split_material_code` pass. Import the normalizer inside the function, as the grade-code import already is.

This plan stops at the intake classification. [plasticos_material_profile/intake_delta_bridge.py](plasticos_material_profile/intake_delta_bridge.py) already copies `form_id` and `material_grade_id` from the intake onto the partner material profile. Correcting those intake slots is the bug fix. Do not edit `crm.lead`, the match orchestrator, opportunity snapshot storage, or the match command. That cutover is [docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md](docs/campaigns/11-03-26/PLAN%20Partners%20First%20Native%20Opportunity%20Matching%20Canonical%20Revision.md).

`evaluate_economic_eligibility` already reads `material_grade_code`, so pallets, totes, and crates keep the lower reusable-item threshold. Do not touch the write guard, the unlink guard, or partner deferral. The web lead still creates an intake without a partner.

`tests/test_web_lead_material_identity.py` reads `_FORM_NORMALIZE` and allows its values to be a form or a grade. Point it at the normalizer word table: form words are only `FORM_CODES`, grade words are only `GRADE_CODES`. `scripts/build_material_mapping.py` `load_web_lead_vocabulary` labels every `_FORM_NORMALIZE` word as a form. Point it at the normalizer form words so a drum is not labeled a form.

CRM and ERP already store the two facts separately. Do not merge those slots:

- [plasticos_crm_bridge/models/material_profile.py](plasticos_crm_bridge/models/material_profile.py) `reuse_facility_polymer_profile` writes `form_id` and `material_grade_id` as separate identity fields on the partner profile.
- [plasticos_transaction/models/native_document_import.py](plasticos_transaction/models/native_document_import.py) `_material_line_values` fills `form_id` and `material_grade_id` independently on the sale and purchase lines.

Add tests in [plasticos_web_leads/tests/test_web_lead_material_grade.py](plasticos_web_leads/tests/test_web_lead_material_grade.py):

- Text "HDPE drums" plus vision `observed_form=regrind` yields `material_grade=DRUMS` and `form=REGRIND`. The intake `form_id` is regrind, not `form_other`.
- An AI form `film` plus text "buckets" yields `FILM` and `BUCKETS`.
- An AI form `pallet`, `drum`, or `bucket` yields that grade and an empty form. It must not set `merged["form"]` to `PALLETS`, `DRUMS`, or `BUCKETS`.
- The existing pallet description test stays: grade `PALLETS`, form empty, intake form `other`.

Bump [plasticos_web_leads/__manifest__.py](plasticos_web_leads/__manifest__.py) from `19.0.2.8.7` to `19.0.2.8.8`.

## Branches

The `LDPE_LLDPE` slot change is cut from `origin/fix/material-ledger-normalizer` (PR #365). The normalizer word table and the `_merge_ai_and_vision` change are cut from `origin/feat/web-lead-material-grade` (PR #366). Both edit `material_normalizer.py`, so the #366 branch merges the #365 branch before publish and keeps both edits. Do not add either change to PR #367. Publish only when asked. Upgrade with `make update m=plasticos_material_profile` and `make update m=plasticos_web_leads`. The word table shares the `plasticos_material_profile` patch bump; if the #365 bump is already `19.0.5.11.3`, the #366 branch bumps to `19.0.5.11.4`.
