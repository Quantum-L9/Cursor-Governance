---
name: Lead form layout
overview: Remove Seller Location from the web lead Contact section, keep ZIP, and
  give Material Description a full-width row while dropping the Est. prefix from the
  two weight and load labels.
todos:
- id: drop-seller-location
  content: Remove pickup_location_text from the Contact group and leave ZIP in place
  status: completed
- id: widen-material
  content: Move material_description to a full-width Material row and drop Est. from
    the load labels
  status: completed
isProject: false
built: true
status: built
---

# Lead form layout

The Contact block is uneven because Seller Location is a fourth field on the right. Location (`pickup_place`) already shows the derived city and state. Seller Location (`pickup_location_text`) stays stored; it only leaves this form.

## Contact

In [plasticos_web_leads/views/web_lead_views.xml](plasticos_web_leads/views/web_lead_views.xml), delete the `pickup_location_text` line from `view_web_lead_form`. Leave `pickup_postal_code` (ZIP) where it is.

The section then has three fields in each column, so it lines up with the two-column Material block under it:

- Company, Contact Name, Location
- Contact Email, Contact Phone, ZIP

Do not remove the field from the model, the list, or the raw payload.

## Material

In the same form, take `material_description` out of the left column and place it once, full width, as the first row of the Material group (`colspan="2"`). The left column then starts at Quantity. The right column stays Lbs/Load, the high end when it exists, Loads/Month, and Frequency.

On the model in [plasticos_web_leads/models/web_lead.py](plasticos_web_leads/models/web_lead.py), drop the `Est.` prefix from the two labels the form always shows:

- `estimated_lbs_per_load`: `Lbs/Load`
- `estimated_loads_per_month`: `Loads/Month`

`estimated_lbs_high` is hidden unless a range exists. Drop its prefix too (`Lbs High`) so a range does not put `Est.` back in the row.

## Version

`plasticos_web_leads` is already `19.0.2.10.0` and that version is not on the database in the screenshot. These view and label edits ship in that same unpublished bump. No second bump and no migration.

## Build evidence (auto)

- detected_at: `2026-11-10T22:01:23Z`
- conversation_id: `7a2a9ab9-eb1d-40d7-ae22-0a0744e9f232`
- generation_id: `8d577b50-4a9e-49f1-baaa-5938a49801df`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/7a2a9ab9-eb1d-40d7-ae22-0a0744e9f232/7a2a9ab9-eb1d-40d7-ae22-0a0744e9f232.jsonl`
- todos at build time:
- `drop-seller-location`: completed
- `widen-material`: completed

