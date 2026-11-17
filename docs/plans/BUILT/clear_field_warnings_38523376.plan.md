---
name: Clear field warnings
overview: Remove the four registry warnings by giving colliding fields distinct labels
  and dropping tracking on the two freight models that do not keep a chatter. No workflow,
  stored data, or view layout changes.
todos:
- id: relabel-people
  content: Rename contact_header_name to People and bump plasticos_facility_profile
  status: completed
- id: relabel-draft-reason
  content: Split Override Reason and Draft Override Reason on both document models
    and bump both modules
  status: completed
- id: drop-dead-tracking
  content: Remove tracking from freight estimate status and quote selected, then bump
    plasticos_logistics
  status: completed
isProject: false
built: true
status: built
---

# Clear the Staging field warnings

The pasted lines are registry warnings, not the load failure. Build `40247740` is already serving login. These field definitions were already on `Staging` before pull requests 409–416; a full registry load is what printed them. The fix is the field metadata, not a new model.

## What changes

- [`plasticos_facility_profile/models/res_partner.py`](plasticos_facility_profile/models/res_partner.py): `contact_header_name` is labeled `Contact`, the same label as base `res.partner.child_ids`. The form renders it with `nolabel="1"`, so the screen stays the same. Set `string="People"`, which matches the existing help. `res.users` only repeats the partner field, so that warning goes away with it.
- [`plasticos_documents/models/document.py`](plasticos_documents/models/document.py): `override_reason` has no `string`, so Odoo titles it `Override Reason`, and `override_reason_draft` uses that same string. Keep the recorded field as `Override Reason` by setting that string explicitly. Label the draft `Draft Override Reason`. The form already shows the draft only before an override and the recorded reason after.
- [`plasticos_documents_native/models/document_native.py`](plasticos_documents_native/models/document_native.py): the same pair exists on `documents.document`. Apply the same two labels so the next full load does not grow a fifth warning.
- [`plasticos_logistics/models/freight_estimate.py`](plasticos_logistics/models/freight_estimate.py) and [`plasticos_logistics/models/freight_quote.py`](plasticos_logistics/models/freight_quote.py): `status` and `selected` pass `tracking=True`, but neither model inherits `mail.thread`. Odoo ignores the parameter and warns. Remove only those two arguments. Leave `plasticos.freight.quote.request.state` tracked; that model does inherit `mail.thread`.

## What stays

Do not retitle `plasticos.partner.phone`, CRM sync contact fields, load override reasons, or view group labels. Do not add `mail.thread` to the estimate or quote models. That would create chatter tables for a parameter that never recorded anything.

## Versions

Bump the patch segment and the matching README `module_version`:

- `plasticos_facility_profile` `19.0.5.4.1` to `19.0.5.4.2`
- `plasticos_documents` `19.0.2.1.16` to `19.0.2.1.17`
- `plasticos_documents_native` `19.0.1.2.12` to `19.0.1.2.13`
- `plasticos_logistics` `19.0.1.14.18` to `19.0.1.14.19`

## Check

`ruff format` the four manifests. Confirm no test asserts these labels or the dropped `tracking` flags. Publish with `make pr` into `Staging`. The warning is gone when the next Odoo.sh `update.log` no longer contains these four field messages.

## Build evidence (auto)

- detected_at: `2026-11-09T14:29:47Z`
- conversation_id: `fb74a9c0-78cb-4d65-bc35-e5884acca853`
- generation_id: `fdffadf5-b0ec-45d4-a130-d4fd3aa77a8c`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/fb74a9c0-78cb-4d65-bc35-e5884acca853/fb74a9c0-78cb-4d65-bc35-e5884acca853.jsonl`
- todos at build time:
- `relabel-people`: completed
- `relabel-draft-reason`: completed
- `drop-dead-tracking`: completed
