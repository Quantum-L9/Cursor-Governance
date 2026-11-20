---
name: Mapping slot fill
overview: On feat/ld-lld-phrase-map, fill empty mapping slots from words the phrase
  already names, store every named color, and stop storing retired form BALES. Blue
  and white are two colors. The worksheet table stays the importer, so each corrected
  phrase is copied into _SPECS.
todos:
- id: bales
  content: Move every mapped form BALES to packaging bales, and set a real form when
    the phrase names one
  status: completed
- id: slots
  content: Fill empty grade, form, and packaging when the phrase names exactly one
    seeded value, and store every named color, with blue and white as BLUE and WHITE
  status: completed
- id: shrink-wrap
  content: Seed grade Shrink Wrap and set it on every matrix phrase that contains
    shrink
  status: completed
- id: specs
  content: Copy the corrected phrases and the approved 19 into _SPECS, and do not
    retarget the phrases already mapped from the closed ledger
  status: completed
- id: proof
  content: Assert the bales move, blue and white as two colors on the drum regrind,
    and a two-grade skip; bump material_profile to 19.0.5.12.0
  status: completed
isProject: false
built: true
status: built
---

# Correct the material mapping on the seed child

Work stays on `feat/ld-lld-phrase-map` in the worktree `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19-ld-lld`. The open checkout `docs/candidate-add-ons` is left alone. The uncommitted `REPRO` form stays. The uncommitted `BLUE_WHITE` on `ldpe/lldpe blue/white purge` is replaced by the two colors `BLUE` and `WHITE`.

`make import-erp` reads [`plasticos_material_profile/models/material_normalizer.py`](plasticos_material_profile/models/material_normalizer.py) `_SPECS` only. [`plasticos_material_profile/data/material_mapping.csv`](plasticos_material_profile/data/material_mapping.csv) is the committed matrix. A corrected row is written in both places. Do not run [`scripts/build_material_mapping.py`](scripts/build_material_mapping.py).

## Fill rule

Use masters that already exist. Do not add polymers, colors, or forms. The one new grade is Shrink Wrap.

For each mapped material row, fill an empty slot only when the phrase names exactly one seeded value for that slot:

- Grade: `TRAYS`, `SUPERACS`, `STRAPPING`, `TOTERS`, `DUNNAGE`, `PIPE`, `BUCKETS` (including pails), `BOTTLES`, `TUBS_LIDS`, `JERRY_CANS`, `FLOWER_POTS`, `CUPS`, `LINERS`, `CORNERBOARDS`, `DRUMS`, `PALLETS`, `TOTES`, `IBC_TOTES`, `CRATES`, and `SHRINK_WRAP` wherever the phrase contains "shrink".
- Form: `REGRIND`, `SHRED`, `REPRO`, `ROLLSTOCK` (the word rolls, not "roll out"), `PELLETS`, `PURGE`, `FILM`, `FLAKE`, `SHEET`, `PARTS`, `CHOPPED`, `LOOSE`.
- Color: every seeded color the phrase names. Blue and white together are `BLUE` and `WHITE`, not the combined `BLUE_WHITE` master. A third named color is stored too, so `hdpe drum regrind - blue/white/black` is `BLUE`, `WHITE`, and `BLACK`. `MIXED` only for the words "mixed color".
- Packaging: `bales` or `gaylords` when those words are the packaging. "On pallets" and "stacked" are packaging `palletized`, not grade `PALLETS`.
- Attribute: `printed` when the phrase says printed or with print. `reusable` when it says reusable. `non_woven` when it says nonwoven. `full_bottom` when it says full bottom.

A phrase that names two grades, or two real forms, keeps that slot empty. `hmw repro` already has form `PELLETS`, so it does not also become `REPRO`. `hmw dunnage trays` and `hmw drum / ibc tote shred` name two grades and do not gain one.

Color is the exception to the one-value rule. [`plasticos.material.profile`](plasticos_material_profile/models/material_profile.py) `color_id` is a Many2one today, and `_spec.color` holds one code. This change makes the profile color a Many2many of the existing `plasticos.material.color` records, the same shape as attributes, and the normalizer color slot a tuple of codes. The stored single `color` Selection stays for one color and stays empty when more than one color is set. Do not write `BLUE_WHITE` for a phrase that names blue and white. The `BLUE_WHITE` master stays in the seed for rows that already use that single code.

## Bales

Form `BALES` is retired for mapping. On every mapped row whose form cell is `BALES`, clear the form and set packaging `bales` when that cell is empty. If the phrase also names one real form, that form replaces `BALES` and packaging is still `bales`.

Examples: `pet bottles - post consumer bales` keeps `PET`, `BOTTLES`, `POST_CONSUMER`, form empty, packaging `bales`. `ibc tote bales` becomes `HDPE_HMW`, grade `IBC_TOTES`, packaging `bales`. `hdpe pallet bales` becomes grade `PALLETS`, packaging `bales`. `pp bales` becomes packaging `bales` only.

The inactive `form_bale` record in [`material_form_data.xml`](plasticos_material_profile/data/material_form_data.xml) stays, so an old profile can still show the code. No mapped row uses it.

## Shrink Wrap

Add grade `SHRINK_WRAP`, name Shrink Wrap, in [`material_grade_data.xml`](plasticos_material_profile/data/material_grade_data.xml) immediately after `STRETCH_FILM`, and add the same code to [`grade_codes.py`](plasticos_material_profile/grade_codes.py) in that same position. Description: "Shrink wrap film." `STRETCH_FILM` stays the grade for stretch film. A phrase that says stretch and does not say shrink is not changed.

Set `material_grade` to `SHRINK_WRAP` on every matrix row whose phrase contains "shrink":

- `ldpe money bags and shrink wrap.` keeps polymer `LDPE` and gains grade `SHRINK_WRAP`.
- `ldpe shrink pallet wrap rolls` keeps the named row below and gains grade `SHRINK_WRAP`. It does not take grade `PALLETS`.
- `shrink wrap` gains grade `SHRINK_WRAP` and stays unknown. Do not invent a polymer, and do not add it to `_SPECS`.

The two mapped phrases are copied into `_SPECS`.

## What does not move

- Phrases already mapped from the closed ledger, including `hd/pp cornerboards`. The ledger file is deleted. The 19 phrases in [`material_mapping_resolution_remaining.csv`](plasticos_material_profile/data/material_mapping_resolution_remaining.csv) are resolved by the table below, and that file is removed once those matrix rows are written. The live row for `ldpe/lldpe clear repro` stays.
- Rows with no polymer. A grade word alone still creates no profile.
- [`plasticos_crm_sync/services/orchestrator.py`](plasticos_crm_sync/services/orchestrator.py), the Makefile, and the facility-profile migration.

`repro` moves from the attribute cell to form `REPRO` only when the form cell is empty. The attribute master stays for rows that do not get this move.

## Named rows

These win over the word match. `palletized` is the seeded packaging whose name is stacked on pallets. There is no packaging code `stacked`. Form `CORRUGATED` is the seeded corrugated sheet. Attribute `reusable` is the seeded spelling of reusable.

| Phrase | Polymer | Grade | Form | Color | Source type | Packaging | Attribute |
|---|---|---|---|---|---|---|---|
| `ldpe printed rolls` | `LDPE` | | `ROLLSTOCK` | | | | `printed` |
| `super sacks a - reusable from peanuts` | `PP` | `SUPERACS` | | | | | `reusable` |
| `gaylord boxes (full bottom)` | `GAYLORD_BOXES` | | | | | `palletized` | `reusable`, `full_bottom` |
| `shred-it totes; tubs/lids & flip top totes` | `PP` | `TOTES` | | | | | |
| `pp tubs & lids` | `PP` | `TUBS_LIDS` | | | `POST_CONSUMER` | `bales` | |
| `pp tubs and lids` | `PP` | `TUBS_LIDS` | | | `POST_CONSUMER` | `bales` | |
| `ldpe shrink pallet wrap rolls` | `LLDPE` | `SHRINK_WRAP` | `ROLLSTOCK` | | | | |
| `pp corrugated sheet on pallets` | `PP` | | `CORRUGATED` | | | `palletized` | |
| `lldpe clear rolls on pallets` | `LLDPE` | | `ROLLSTOCK` | `CLEAR` | | `palletized` | |
| `pp nonwoven rolls (on pallets)` | `PP` | | `ROLLSTOCK` | | | `palletized` | `non_woven` |
| `pp bottle caps (post industrial)` | `PP` | | `PARTS` | | `POST_INDUSTRIAL` | | |

`gaylord boxes (full bottom)` is not packaging `gaylords`. The shred-it phrase has no form. The two tubs rows drop the stored form `PARTS` and match `spc-a`. Shrink pallet wrap changes polymer from `LDPE` to `LLDPE`, takes grade `SHRINK_WRAP`, and does not take grade `PALLETS`. Bottle caps are form `PARTS`, not grade `BOTTLES`.

## Remaining 19

These win over the word match and over the old unknown or ambiguous matrix cells. Each phrase now has a polymer, so each one is written into the matrix and copied into `_SPECS`. Filler stays empty. `z-bales` matches `z bales`, including color `MIXED`. Every row whose grade is `BOTTLES` has packaging `bales`. `mixed dunnage trays` is polymer `PLASTIC_PALLETS` and grade `DUNNAGE`.

| Phrase | Polymer | Grade | Form | Color | Source | Process | Attributes | Packaging |
|---|---|---|---|---|---|---|---|---|
| `z bales` | `HDPE` | `BOTTLES` | | `MIXED` | `POST_CONSUMER` | | | `bales` |
| `z-bales` | `HDPE` | `BOTTLES` | | `MIXED` | `POST_CONSUMER` | | | `bales` |
| `1 & 2 bottles` | `1_2_COMMINGLED_BOTTLES` | `BOTTLES` | | | `POST_CONSUMER` | | | `bales` |
| `bottles (hd/pet)` | `1_2_COMMINGLED_BOTTLES` | `BOTTLES` | | | `POST_CONSUMER` | | | `bales` |
| `1 & 2 bottles (pet/hdpe)` | `1_2_COMMINGLED_BOTTLES` | `BOTTLES` | | | `POST_CONSUMER` | | | `bales` |
| `1 & 2 pet & hdpe co-mingled bottles (post consumer)` | `1_2_COMMINGLED_BOTTLES` | `BOTTLES` | | | `POST_CONSUMER` | | | `bales` |
| `commingled bottles 1&2` | `1_2_COMMINGLED_BOTTLES` | `BOTTLES` | | | `POST_CONSUMER` | | | `bales` |
| `ldpe/hdpe grocery film` | `MIXED` | | `FILM` | | | | | |
| `mixed hd/pp pallets and knockdowns` | `PP_PE` | `PALLETS` | | | | | | |
| `pe / pp regrind mixed` | `PP_PE` | | `REGRIND` | | | | `mixed` | |
| `hdpe / ldpe regrind` | `MIXED` | | `REGRIND` | | | | | |
| `compression molded regrind` | `PLASTIC_PALLETS` | | `REGRIND` | | | `compression_mold` | | |
| `hd and pp purge/regrind/fluff` | `PP_PE` | | | | | | `mixed` | |
| `compression molded` | `PLASTIC_PALLETS` | `PALLETS` | | | | `compression_mold` | | |
| `mixed dunnage trays` | `PLASTIC_PALLETS` | `DUNNAGE` | | | | | | |
| `red totes on casters` | `HDPE` | `TOTERS` | | `RED` | | | | |
| `plastic totes / trash cans (empty and clean)` | `HDPE` | `TOTES` | | | | | `clean` | |
| `gaylords of amazon returns` | `MIXED` | `RETURNS` | | | | | | `gaylords` |
| `mixed plastic pallets - pp skids` | `PP` | `PALLETS` | | | | | | |

Color `MIXED` on the two Z-bale rows is the operator color even though the phrase does not say "mixed color". Grade `PALLETS` on `mixed hd/pp pallets and knockdowns` wins even though the phrase also names knockdowns. The purge/regrind/fluff phrase names three forms, so the form cell stays empty and the attribute is `mixed`. `ldpe/hdpe grocery film` uses polymer `MIXED` and form `FILM`. The CRM alias that maps that phrase to `HDPE` is superseded by the `_SPECS` entry.

## Proof

Add the corrected phrases, including the 19 rows above, to `_SPECS` with the same cells. Extend [`plasticos_material_profile/tests/test_material_normalizer.py`](plasticos_material_profile/tests/test_material_normalizer.py) with the bales move, one dropped grade beside a kept form (`hdpe blue/white drum regrind` → `HDPE`, `DRUMS`, `REGRIND`, colors `BLUE` and `WHITE`), the named rows above, the 19 rows, and one two-grade phrase that still has no grade. [`tests/test_material_ledger_resolution.py`](tests/test_material_ledger_resolution.py) stops requiring those 19 to be unknown with an empty polymer, because the remaining file is removed.

Add a pure test that no mapped matrix row has form `BALES`, that each changed `_SPECS` entry matches its matrix row, and that every phrase containing "shrink" has grade `SHRINK_WRAP` while `ldpe stretch film` stays `STRETCH_FILM`.

The new color relation is a field, so [`plasticos_material_profile`](plasticos_material_profile/__manifest__.py) and the README `module_version` go to `19.0.5.12.0`. The working tree is `19.0.5.11.21` for the unpublished `REPRO` seed and the injection process on `hdpe crates`.

## Build evidence (auto)

- detected_at: `2026-11-12T15:17:09Z`
- conversation_id: `24515ea1-fd20-49bc-87d9-9898de8ab129`
- generation_id: `aa3b92e4-8818-490a-b268-64c8c58a91ba`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/24515ea1-fd20-49bc-87d9-9898de8ab129/24515ea1-fd20-49bc-87d9-9898de8ab129.jsonl`
- todos at build time:
- `bales`: completed
- `slots`: completed
- `shrink-wrap`: completed
- `specs`: completed
- `proof`: completed
