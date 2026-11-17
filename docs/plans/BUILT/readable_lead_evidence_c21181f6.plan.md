---
name: Readable lead evidence
overview: Add a display-only field widget on the first three Web Lead tabs so brokers
  see labeled facts, while the stored JSON fields stay the source triage, retries,
  and snapshots read.
todos:
- id: widget
  content: Add the lead_evidence widget (format.js, OWL template, scss) and register
    it in the web_leads manifest assets.
  status: completed
- id: views
  content: Order the form Contact, Material, Classification, then Links, each a full-width
    section. Label quantity as Quantity in the Material group. Point AI Analysis,
    AI Triage, and Raw Payload at the widget modes; keep triage_log as pre-wrapped
    text; leave Provider Audit on widget=json.
  status: completed
- id: bump-test
  content: Bump plasticos_web_leads to 19.0.2.8.13 and add a pytest that locks the
    three modes, the stored field names, and the redacted technical view.
  status: completed
isProject: false
built: true
status: built
---

# Readable web-lead evidence

Display-only. The Json fields `ai_analysis`, `decision_reasons`, `ai_normalized`, `ai_vision_results`, `image_urls`, and `raw_payload` stay stored and unchanged. Triage, retries, and snapshots keep reading them. The widget never calls `record.update`. An intake-created lead rejects writes of these fields in [`plasticos_web_leads/models/web_lead.py`](plasticos_web_leads/models/web_lead.py).

This stays inside `plasticos_web_leads`. It does not add files to `plasticos_screen_views`.

## Stack

Open pull request [#448](https://github.com/cryptoxdog/IB-Odoo_19/pull/448) (`feat/screen-views`) is the open web-lead change. It inherits `plasticos.web.lead` and replaces `action_web_lead` view modes. It does not edit the web-lead form arch. Branch from `feat/screen-views` and publish with `make pr base=feat/screen-views`. Do not open this work against `Staging` while 448 is open. The other open pull requests do not touch web leads.

## Form order

In [`plasticos_web_leads/views/web_lead_views.xml`](plasticos_web_leads/views/web_lead_views.xml), under the lead title, the sheet order is Contact, Material, Classification, Links, then the notebook. All four are full-width sections, the same sheet-level group pattern Contact and Material use today. Remove the parent group that places Classification and Links in half-width columns. Field lists inside each section stay as they are, except the Material quantity row: set `string="Quantity"` on `quantity_text` so the label drops "(Form Input)". The field name, stored value, and help text stay. Header buttons stay as they are. `group[@name='links']` keeps that name, so the CRM Bridge xpath that injects `crm_lead_id` still matches.

## Widget

Add `lead_evidence` beside the image strip, registered like `lead_image_strip` for type `json`:

- [`plasticos_web_leads/static/src/lead_evidence/format.js`](plasticos_web_leads/static/src/lead_evidence/format.js) — pure formatting
- [`plasticos_web_leads/static/src/lead_evidence/lead_evidence.js`](plasticos_web_leads/static/src/lead_evidence/lead_evidence.js)
- [`plasticos_web_leads/static/src/lead_evidence/lead_evidence.xml`](plasticos_web_leads/static/src/lead_evidence/lead_evidence.xml)
- [`plasticos_web_leads/static/src/lead_evidence/lead_evidence.scss`](plasticos_web_leads/static/src/lead_evidence/lead_evidence.scss)

Register the three files in [`plasticos_web_leads/__manifest__.py`](plasticos_web_leads/__manifest__.py) `web.assets_backend`. Bump that manifest from `19.0.2.8.12` to `19.0.2.8.13`. No migration.

One widget, three modes via `options="{'mode': '...'}"`. OWL text only (`t-esc` / text nodes). No `t-out` of built HTML, no `<a>`, no `t-att-href`.

Accept an object or a JSON string. Null, empty, and missing keys render as **Not stated.** Booleans render Yes / No. Confidence `0.8` renders `80%`. Weights use a thousands separator.

## What each tab shows

In [`plasticos_web_leads/views/web_lead_views.xml`](plasticos_web_leads/views/web_lead_views.xml):

**AI Analysis** (`mode: analysis` on `ai_analysis`). Keep `decision_reasons` in the arch, invisible, so the client loads it. Labeled rows from the merge object: Polymer, Estimated weight (`estimated_lbs`), Plastic, Confidence, Source, Notes, plus known merge keys (form, color, loads per month, frequency, weight source, material summary) as their own rows. `decision_reasons.reasons` is the HOT/COLD bullet list. `review_reasons` is "What still needs a broker." Known gate ids (`weight:below_hot_threshold`, `is_plastic:false`, and the other ids in `classification_engine.py`) get short labels; an unknown gate id is shown as itself. Any other key goes under **Other**.

**AI Triage** (`mode: triage` on `ai_normalized`). Keep `ai_vision_results`, `image_urls`, and `lead_image_ids` available on the record. Show the extraction only: polymer, material description, source, source description, weight, loads per month, plastic, commercial source, confidence, notes, weight source, and inferred fields. Do not paint `raw_form_data` in that list. One card per vision result: form, color, cleanliness, quantity visible, quantity note, contamination, polymer hint, confidence. The photo is the stored `/web/image/<id>` thumbnail when the filename matches `lead_image_ids`; otherwise the filename taken from the URL path. The signed Cognito URL is not rendered. `triage_log` stays a Text field with a monospace `white-space: pre-wrap` class so each pipeline step stays on its own line.

**Raw Payload** (`mode: payload` on `raw_payload`). Two-column seller answers: company (`YourBusinessCompanyName`), contact (Cognito `Name` flattened to FirstAndLast or First + Last), email, phone, material (`WhatMaterialIsItMadeFrom`, else `WhatIsIt`), weight (`WeightPerLoad`), quantity (`WhatIsTheQuantity`), pickup city/state, zip, and photo filenames from `UploadPhotosOfYourScrapUpTo10` / `UploadPhotos` / `Photos` / `Attachments` / `Files`.

## Secrets and leftovers

Signed URLs, query tokens, and transport keys (`File`, `source_url`, `Url`, `AdminLink`, `Document1`, `UserAgent`, `IpAddress`, `token`, `api_key`) never become links and never appear in the open list or under Other.

**Show technical data** is closed by default. It pretty-prints that field's JSON after replacing URL query strings and those secret values with `[redacted]`. On the triage widget, that block is where `raw_form_data` and the Cognito transport fields live. On Raw Payload, the same collapsed block is the full submission.

Provider Audit, Broker Review, and the snapshot JSON stay on `widget="json"`.

## Check

Add a pytest under `tests/` that reads `web_lead_views.xml` and asserts the three pages use `lead_evidence` with the three modes, the six Json field names are still present, Provider Audit still uses `widget="json"`, and the four sheet-level groups are full width in the order Contact, Material, Classification, Links, with the Material quantity label set to Quantity. No Odoo runtime test. After the view change, upgrade only this module with `make update m=plasticos_web_leads`. Publish onto the open web-lead branch with `make pr base=feat/screen-views`.

## Build evidence (auto)

- detected_at: `2026-11-10T17:48:33Z`
- conversation_id: `4e1c2408-29ba-4311-8531-41f108d33c85`
- generation_id: `dc6739af-f90f-48d6-b259-6cecf304eb00`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/4e1c2408-29ba-4311-8531-41f108d33c85/4e1c2408-29ba-4311-8531-41f108d33c85.jsonl`
- todos at build time:
- `widget`: completed
- `views`: completed
- `bump-test`: completed

