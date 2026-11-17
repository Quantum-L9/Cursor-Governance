---
name: AI normalizer prompt
overview: Update only the `_SYSTEM_PROMPT` rules in `plasticos_web_leads` so Mixed/quality-tier/Gaylord/process
  wording is explicit. Keep the material-profile catalog untouched (`GAYLORD_BOXES`
  stays a polymer code). Verify with the existing prompt unit test plus a flash re-run
  of the first 50 ERP products.
todos:
- id: prompt-rules
  content: Rewrite Mixed / quality-tier / Gaylord / process rules in ai_normalizer
    _SYSTEM_PROMPT
  status: completed
- id: bump-test
  content: Bump plasticos_web_leads to 19.0.2.11.6 and extend prompt unit assertions
  status: completed
- id: flash-rerun
  content: Re-run first 50 on deepseek-flash and compare to pre-change flash results
  status: completed
isProject: false
built: true
status: built
---

# AI normalizer prompt rules

## Scope (locked)

- Edit **only** [`plasticos_web_leads/models/ai_normalizer.py`](plasticos_web_leads/models/ai_normalizer.py) `_SYSTEM_PROMPT` (and the prompt assertion test that locks those phrases).
- **Do not** touch `plasticos_material_profile` seeds, polymers, grade templates, or `ERP-Products.csv`.
- `GAYLORD_BOXES` remains a polymer catalog code; behavior is corrected by prompt rules only.

## Prompt changes

In `_SYSTEM_PROMPT` (around the Mixed Color / quality-tier / packaging rules at lines 103–111), replace/extend so the model is told:

1. **Mixed attribute vs color**
   - Bare `Mixed` / `mixed` after a material or grade word → attribute `mixed`.
   - Only `Mixed Color` / `mixed color` → color `MIXED`.
   - Retire or narrow the current line that says “Color Mixed Color is the color, not attribute mixed” so it no longer suppresses bare `Mixed`.

2. **Quality tier must fire**
   - When the phrase contains `Grade A`, `Grade B`, `Grade C`, `Reusable`, `Reuseable`, or `Standard`, set `quality_tier` to the listed code (`GRADE_A` / `GRADE_B` / `GRADE_C` / `REUSABLE` / `STANDARD`).
   - Never leave `quality_tier` null when those words appear.
   - Keep the existing rule that crate/bottle/utility/injection “grade” are not quality tiers.

3. **Gaylord Boxes product (prompt-only)**
   - When the phrase is essentially gaylord boxes as the product (and not “regrind … gaylords” / “in gaylords” packaging language): set `quality_tier=REUSABLE`.
   - Do not set `is_plastic=true` from that phrase alone (null/false is fine; virgin plastic is not proven).
   - “Regrind in gaylords” still means packaging `gaylords`, not the Gaylord Boxes product rule.

4. **Process mapping**
   - Stated `compression molded` / `compression mold` → `process_type=compression_mold`.
   - Stated `injection` / `injection molded` → `process_type=injection` (still not a quality tier).
   - Stated `blow molded` / `blow mold` → `process_type=blow_mold`.

## Module / tests

- Bump [`plasticos_web_leads/__manifest__.py`](plasticos_web_leads/__manifest__.py) `19.0.2.11.5` → `19.0.2.11.6` (mandatory for runtime Python change).
- Extend [`tests/test_triage_pipeline.py`](tests/test_triage_pipeline.py) `test_prompt_rules_name_quality_tier_and_printed_film` (or a sibling) to assert the new phrases appear in `system_prompt()`: bare Mixed → attribute, Mixed Color → color, quality-tier must-fill wording, Gaylord Boxes → REUSABLE / not virgin plastic, compression/injection/blow → process.

## Verification (after implement)

- Run the focused prompt unit test (pure pytest; no Odoo runtime).
- Re-run the first 50 ERP products on Infisical **`deepseek-flash`** with the updated prompt and compare to the pre-change flash cache (`/tmp/erp_products_deepseek_flash50.jsonl`), especially rows 11, 16, 18, 21, 35.
- Do not write those probe results into `ERP-Products.csv` unless you ask for that separately.

## Build evidence (auto)

- detected_at: `2026-11-12T21:01:51Z`
- conversation_id: `27792525-282a-4aff-b042-4834fac6e9de`
- generation_id: `8035798c-d357-4860-a0d3-3fc595c4d93c`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/27792525-282a-4aff-b042-4834fac6e9de/27792525-282a-4aff-b042-4834fac6e9de.jsonl`
- todos at build time:
- `prompt-rules`: completed
- `bump-test`: completed
- `flash-rerun`: completed
