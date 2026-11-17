---
name: Material profile editor
overview: Change only the material profile screens from this chat. Add a line stays
  inline and autosaves. Buyer fields move onto Profile. Picture icons attach photos
  and those photos copy onto the intake and onto offers created from the opportunity.
  Bales leaves the Form dropdown. Two profile labels change. Latitude and Longitude
  leave the profile. Nothing else is edited.
todos:
- id: profile-screens
  content: Autosave, buyer fields, picture icons, Bales dropdown, Material Type, Weight
    Per Load, and removal of profile latitude and longitude
  status: completed
- id: photo-handoff
  content: Copy profile photos onto a linked intake and onto offers created from the
    opportunity, and delete the profile coordinate reads that would crash
  status: completed
- id: bumps-tests
  content: Bump the three touched modules and add only the tests those changes require
  status: completed
isProject: false
built: true
status: built
---

# Material profile editor

## What changes

- **Add a line** stays on the contact list. It does not open the full profile. On a saved contact it stores the new profile immediately. A later committed edit on that row, and a committed edit on the full profile, is stored without pressing Save. A number writes when the cell closes, not on each keystroke. A second Add a line, while a blank profile for that contact exists, returns that row. An unsaved contact cannot own a profile yet.
- **Buyer fields** move onto the Profile page. The Buyer Fields page is deleted. Food Grade, Medical Grade, Certification Notes, and Color Flexibility are the only fields that move.
- **Pictures.** A camera icon on the contact list, beside Open Full Profile, and a camera icon on the full profile header open one small dialog with the existing image widget. The list icon does not open the full profile. Photos stay on the profile.
- **Create Intake.** When an intake is linked to the profile, copy the profile photos onto that intake. When `action_create_offers_from_results` creates offers, copy the profile photos onto those new offers. The same checksum is not copied twice. No other image path changes. The opportunity form does not gain an image field.
- **Bales** is deactivated on the Form master, so the Form dropdown stops offering it. Packaging Bales stays. Rows that already have form Bales are left as they are.
- **Material Grade** displays as **Material Type** on the profile field. The contact column uses that same string. The field name stays `material_grade_id`.
- **Quantity per Load (lbs)** displays as **Weight Per Load** on the profile field. The field name stays `quantity_per_load_lbs`.
- **Latitude and Longitude** are removed from the profile form and from `plasticos.material.profile`. The four existing reads of those profile fields are deleted so intake creation, lot approval, and the intake-to-profile bridge do not crash. No coordinate is written anywhere else.

## What does not change

Intake labels, intake Coordinates, order lines, menus, the grade master, the normalizer, web leads, enrichment, historical form values, partner coordinates, the opportunity form, and the existing commercial image sync.

## Whitelist

Only these paths. One patch each: `plasticos_material_profile` `19.0.5.11.12` to `19.0.5.11.13`, `plasticos_intake` `19.0.5.4.2` to `19.0.5.4.3`, `plasticos_crm_bridge` `19.0.3.4.23` to `19.0.3.4.24`.

- [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py)
- [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py)
- [plasticos_material_profile/intake_delta_bridge.py](plasticos_material_profile/intake_delta_bridge.py)
- [plasticos_material_profile/views/material_profile_views.xml](plasticos_material_profile/views/material_profile_views.xml)
- [plasticos_material_profile/views/partner_material_ux.xml](plasticos_material_profile/views/partner_material_ux.xml)
- [plasticos_material_profile/data/material_form_data.xml](plasticos_material_profile/data/material_form_data.xml)
- [plasticos_material_profile/static/src/js/material_profile_autosave.js](plasticos_material_profile/static/src/js/material_profile_autosave.js)
- [plasticos_material_profile/tests/__init__.py](plasticos_material_profile/tests/__init__.py)
- [plasticos_material_profile/tests/test_profile_editor_repairs.py](plasticos_material_profile/tests/test_profile_editor_repairs.py)
- [plasticos_material_profile/tests/test_material_profile_intake_delta_contract.py](plasticos_material_profile/tests/test_material_profile_intake_delta_contract.py)
- [tests/test_material_profile_intake_delta_bridge_pure.py](tests/test_material_profile_intake_delta_bridge_pure.py)
- [plasticos_intake/__manifest__.py](plasticos_intake/__manifest__.py)
- [plasticos_intake/models/intake.py](plasticos_intake/models/intake.py)
- [plasticos_crm_bridge/__manifest__.py](plasticos_crm_bridge/__manifest__.py)
- [plasticos_crm_bridge/models/crm_lead.py](plasticos_crm_bridge/models/crm_lead.py)
- [plasticos_crm_bridge/models/opportunity_approval.py](plasticos_crm_bridge/models/opportunity_approval.py)
- [plasticos_crm_bridge/tests/__init__.py](plasticos_crm_bridge/tests/__init__.py)
- [plasticos_crm_bridge/tests/test_profile_image_handoff.py](plasticos_crm_bridge/tests/test_profile_image_handoff.py)

A file that is not on this list is not edited. If a listed test fails for a reason that needs another file, stop and add that file here first.

## Done

- Add a line on a saved contact stores a profile before the contact Save button is pressed, and does not open the full profile.
- A committed edit on the row or the full profile is stored without pressing Save.
- The profile has no Buyer Fields page. The four buyer fields are on Profile.
- Both camera icons open the picture dialog. A saved photo belongs to that profile.
- A linked intake receives those photos. Offers created by `action_create_offers_from_results` receive them. The same checksum is not stored twice.
- Form no longer offers Bales. Packaging still offers Bales.
- The profile says Material Type and Weight Per Load.
- The profile has no Latitude or Longitude field. Creating an intake from a profile and approving a lot still succeed.
- The diff is only the whitelist. `ruff check` and `ruff format` are clean on the edited Python.

## Build evidence (auto)

- detected_at: `2026-11-09T19:55:11Z`
- conversation_id: `fc5042d8-150f-4014-b3e4-3de5e26e4638`
- generation_id: `87a7ba4a-0f3e-4847-ba29-88cba0da3073`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/fc5042d8-150f-4014-b3e4-3de5e26e4638/fc5042d8-150f-4014-b3e4-3de5e26e4638.jsonl`
- todos at build time:
- `profile-screens`: completed
- `photo-handoff`: completed
- `bumps-tests`: completed

