---
name: Normalizer slot order
overview: Reorder the normalizer spec to polymer, material grade, letter grade, form,
  source, attributes, packaging. Record the unfinished sub_grade Char as accepted
  debt in workflow_state.md.
todos:
- id: reorder-spec
  content: Make _spec keyword-only in the order polymer, material_grade, grade, form,
    source, attributes, packaging_type, color, and rewrite every phrase call by name.
  status: completed
- id: builder-pad
  content: Update spec_row's six-tuple pad to the new field order.
  status: completed
- id: tests
  content: Update normalizer and ledger-resolution tests to the new argument order.
  status: completed
- id: debt-note
  content: Append the unfinished sub_grade Char to workflow_state.md as accepted debt.
  status: completed
isProject: false
built: true
status: built
---

# Normalizer slot order

## Where A, B, C live

There is no grade master for A, B, C. The letters exist in two places only:

- A free text field, [`sub_grade`](plasticos_material_profile/models/material_profile.py) (`fields.Char()`, line 114), with the comment `TODO: Define sub-grade logic`. The form hides it (`invisible="1"` in [`material_profile_views.xml`](plasticos_material_profile/views/material_profile_views.xml)).
- String literals `"A"`, `"B"`, `"C"` inside [`material_normalizer.py`](plasticos_material_profile/models/material_normalizer.py). CRM copies `normalized.grade` onto `profile.sub_grade`.

[`plasticos.material.grade`](plasticos_material_profile/models/material_grade.py) is the other thing: what the items were (SUPERACS, BOTTLES, DRUMS). Packaging is [`plasticos.packaging.type`](plasticos_material_profile/models/packaging_type.py) (`bales`, `gaylords`), stored as `packaging_type_id`. Attributes are `plasticos.material.attribute` (many). No new model is added.

`PP Supersacs A - Unlined - Bales` is an example of a filled spec, not a new import phrase. It means polymer `PP`, material grade `SUPERACS`, letter `A`, attribute `unlined`, packaging `bales`. The ledger has no row whose text is that sentence, so no new `_SPECS` key is created for those words. The existing key `pp supersacs (un-lined)` already stores PP, SUPERACS, unlined, and bales, and its letter stays empty because the ledger did not set one.

The letter may stay in the normalizer. The profile field that receives it is unfinished, and that debt is accepted for now. When this plan is executed, append a short **Accepted debt** section to [`workflow_state.md`](workflow_state.md): `plasticos.material.profile.sub_grade` is a free `Char`, hidden on the form, with `TODO: Define sub-grade logic`. A, B, and C are normalizer literals copied onto that field. No grade master is added in this change. Do not rewrite the campaigns already on that page.

## Spec order

Replace the positional `_Spec` / `_spec` in [`material_normalizer.py`](plasticos_material_profile/models/material_normalizer.py) with keyword-only arguments, in this order:

`polymer`, `material_grade`, `grade`, `form`, `source`, `attributes`, `packaging_type`, `color`

- `grade` is only the A/B/C letter.
- `material_grade` is the master code and sits immediately after polymer.
- `color` stays last. The ledger has a color column (`CLEAR` on `ldpe/lldpe clear repro`); dropping it would lose that component. It is not a new slot.
- Every call in `_SPECS`, `_CRM_EXACT`, `_CRM_ALIASES`, and the three post-hoc aliases uses names. The alias comprehension stops being `(polymer, form, letter, material_grade)` stuffed into `None` and `()`.
- Empty means that component is absent. Example: `tubs` is `polymer="PP", material_grade="TUBS_LIDS", source="POST_CONSUMER", packaging_type="bales"`.
- Conflict identity stays polymer, material grade, letter, form, and source. Attributes, packaging, and color still come from the description.

[`scripts/build_material_mapping.py`](scripts/build_material_mapping.py) `spec_row` already reads `_Spec` by field name. Its fallback six-tuple pad still assumes the old order `(polymer, form, source, attributes, grade, material_grade)`. Update that pad to the new order so a builder tuple cannot land the letter in the material-grade slot.

Tests keep asserting the same masters. Update the expected tuples in [`test_material_normalizer.py`](plasticos_material_profile/tests/test_material_normalizer.py) and the spec compare in [`tests/test_material_ledger_resolution.py`](tests/test_material_ledger_resolution.py) to the new argument order. No version bump beyond the one already on this branch: same three modules, no schema change.

## Build evidence (auto)

- detected_at: `2026-11-04T19:41:48Z`
- conversation_id: `db477dbe-3545-4e77-a961-ad3c295fab6c`
- generation_id: `9e65b30d-1e6d-4042-8e2c-e3f81d6c73a7`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/db477dbe-3545-4e77-a961-ad3c295fab6c/db477dbe-3545-4e77-a961-ad3c295fab6c.jsonl`
- todos at build time:
- `reorder-spec`: completed
- `builder-pad`: completed
- `tests`: completed
- `debt-note`: completed
