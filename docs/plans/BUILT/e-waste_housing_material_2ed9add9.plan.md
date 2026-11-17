---
name: E-Waste housing material
overview: Record Electronic Computer Housing as the description of the existing E-Waste
  polymer, and apply a bales packaging default only inside the ERP-product classification
  exercise.
todos:
- id: seed-description
  content: Set polymer_ewaste description to Electronic Computer Housing and bump
    plasticos_material_profile to 19.0.5.13.2
  status: cancelled
- id: exercise-bales
  content: In the ERP probe only, show that description and default the two housing
    phrases to EWASTE plus bales, clearing PARTS
  status: cancelled
- id: rerun-two-rows
  content: Reclassify only the two Electronic Plastic Housing rows and write them
    into ERP-Products.csv
  status: cancelled
isProject: false
built: true
status: built
---

# E-Waste computer housing

E-Waste already exists as polymer `EWASTE` in [`plasticos_material_profile/data/polymer_data.xml`](plasticos_material_profile/data/polymer_data.xml) (`full_name`: Electronic Waste Plastics). It has no description, and a polymer has no packaging field, so nothing can default this material to bales in production.

The ERP exercise cache shows why the two housing rows are incomplete:

- Row 18, `Electronic Plastic Housing - Grade A (Light Colors)`: polymer empty, form `PARTS`, quality `GRADE_A`, packaging empty. The model said the polymer was not specified.
- Row 19, `Electronic Plastic Housing - Grade B (Mixed Color)`: polymer `EWASTE`, form `PARTS`, color `MIXED`, quality `GRADE_B`, packaging empty.

`PARTS` came from the form master line “Whole or broken plastic parts…”. The prompt the model saw was `EWASTE — E-Waste — Electronic Waste Plastics`, which never says computer housing. Production prompts are built by `labeled_list` in [`plasticos_web_leads/models/material_catalog.py`](plasticos_web_leads/models/material_catalog.py), which shows code, name, and `full_name` only. Descriptions are not in that prompt. Web-lead triage in [`plasticos_web_leads/models/web_lead.py`](plasticos_web_leads/models/web_lead.py) will not be changed.

## Catalog identity

On the existing `polymer_ewaste` record, set `description` to `Electronic Computer Housing`. Leave `code` `EWASTE`, `name` `E-Waste`, and `full_name` `Electronic Waste Plastics`. Do not mention bales in that description.

Bump [`plasticos_material_profile/__manifest__.py`](plasticos_material_profile/__manifest__.py) from `19.0.5.13.1` to `19.0.5.13.2`. The polymer file is `noupdate="0"`, so a later scoped upgrade refreshes the description. The exercise reads the XML file, so the CSV correction does not wait on `make update`.

## Exercise-only bales default

Only [`/tmp/erp_products_ai_full.py`](/tmp/erp_products_ai_full.py) changes behavior for this run:

- For the in-memory catalog passed to `normalize_lead`, append the polymer description to the E-Waste prompt label so the model sees Electronic Computer Housing. Do not change `labeled_list` or `ai_normalizer.py`, so a live web lead still sees `EWASTE — E-Waste — Electronic Waste Plastics`.
- After classification, for a phrase that is electronic plastic or computer housing: set polymer `EWASTE` when it is empty, set packaging `bales` when it is empty, and clear form `PARTS` (housing is the product, not that form). Leave Grade A / Grade B and the Grade B `MIXED` color as the model returned them.
- Re-run only those two phrases and write them back into [`plasticos_material_profile/data/ERP-Products.csv`](plasticos_material_profile/data/ERP-Products.csv). Do not restart the other 195 rows.

No packaging default is added to `web_lead.py`, `material_catalog.py`, or `material_mapping.csv`. A seller who does not say bales still gets an empty packaging slot in production.

## Build evidence (auto)

- detected_at: `2026-11-12T20:51:17Z`
- conversation_id: `4f327f21-ed57-41ba-b175-0cfb4019464e`
- generation_id: `a587db77-46e3-4078-b942-fa24b30bd68a`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/4f327f21-ed57-41ba-b175-0cfb4019464e/4f327f21-ed57-41ba-b175-0cfb4019464e.jsonl`
- todos at build time:
- `seed-description`: cancelled
- `exercise-bales`: cancelled
- `rerun-two-rows`: cancelled

