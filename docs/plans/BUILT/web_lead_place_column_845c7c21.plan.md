---
name: Web lead place column
overview: Show the web lead’s name, phone, and email after the company, then Location,
  then the two load columns before Decision. Location is the stored “City, ST” derived
  from the pickup ZIP.
todos:
- id: place-fields
  content: Add pickup_postal_code, pickup_location_text, and stored pickup_place;
    fill them when a packet is admitted
  status: completed
- id: zip-table
  content: Resolve Location only from an exact 5-digit ZIP match against one preferred
    city and a USPS state code. 28277 is Charlotte, NC. Seller text never fills or
    overrides it.
  status: completed
- id: list-column
  content: List order after Company is Name, Phone, Email, Location, Est. Lbs/Load,
    Est. Loads/Month, Decision; form shows ZIP and seller location text
  status: completed
- id: backfill
  content: Bump plasticos_web_leads to 19.0.2.9.0 and SQL-backfill existing leads,
    including intake_created rows
  status: completed
- id: tests
  content: Cover the anchor ZIP, ZIP+4, leading zero, unknown, non-US, contradictory
    seller text, a raw Cognito key, and the list column
  status: completed
isProject: false
built: true
status: built
---

# Web lead location from ZIP

The two location values already arrive on every Cognito lead and are stored only inside `canonical_payload`: `pickup_postal_code` (`LocationOfPickUpZip`) and `pickup_location_text` (`LocationOfPickUpCityState` / `WhereIsItLocated`). Neither is a list column. [plasticos_web_leads/adapters/cognito.py](plasticos_web_leads/adapters/cognito.py) reads them; [plasticos_web_leads/views/web_lead_views.xml](plasticos_web_leads/views/web_lead_views.xml) never shows them.

Add one list column whose value is the preferred city and state for that ZIP. `28277` displays as `Charlotte, NC`.

## Fields

On `plasticos.web.lead` in [plasticos_web_leads/models/web_lead.py](plasticos_web_leads/models/web_lead.py):

- `pickup_postal_code` — the seller’s ZIP as submitted, trimmed. The lookup key is derived from it and is not a second stored field.
- `pickup_location_text` — the seller’s own location words, kept so that answer is not dropped. It is never parsed into Location.
- `pickup_place` — stored, readonly, string `Location`. A resolved value is exactly `City, ST`, as in `Charlotte, NC`. Empty when the ZIP does not resolve.

Set all three in `create_from_packet` from the packet, before triage. A lead that already has an intake cannot be updated through `write` ([the intake guard](plasticos_web_leads/models/web_lead.py) around line 488), so the upgrade backfill uses SQL, the same way `submitted_at` was filled in [migrations/19.0.2.8.12/post-migrate.py](plasticos_web_leads/migrations/19.0.2.8.12/post-migrate.py).

## Lookup

One Python function is the only writer of `pickup_place`. Admission and the SQL backfill both call it, so the two paths cannot diverge. It does not call a geocoder, an LLM, or the network. It does not read `pickup_location_text`.

The key is built only from the ZIP digits:

- Trim the submitted value, then keep digits. `28277`, `28277-1234`, `282771234`, and `ZIP 28277` all key to `28277`.
- A 5-digit key, including a leading zero such as `00501`, is the lookup key. A 9-digit string uses its first five. Four digits, six digits, an empty value, and a Canadian code such as `K1A 0A6` are misses.
- Match that key exactly. A shorter key must not hit a longer ZIP, and there is no nearest ZIP.

The table is one preferred city and one state abbreviation per ZIP, packaged in the module. It is not CSV or XML seed. The file stays under the 1000 KB hook, gzipped if the plain file is larger. A source note records where the preferred-city file came from and which vintage it is. A ZIP with more than one preferred city is not a row.

A hit is written only when the city is non-empty and contains no comma, and the state is one of the USPS abbreviations (the 50 states, DC, and the populated territories the file actually contains). The stored text is `f"{city}, {state}"` with that single comma and space. A malformed row is a miss.

A miss stores the trimmed ZIP and the seller’s words, and leaves Location empty. Seller text that names a different city does not win: ZIP `28277` with text `Miami, FL` is still `Charlotte, NC`.

Loading the table checks that it is non-empty and that `28277` is `Charlotte, NC`. If that anchor is absent, the resolver writes no Location for any lead. Lead admission still succeeds. The unit test fails when the packaged table fails the anchor.

## Screens

`contact_name`, `contact_phone`, and `contact_email` already exist on the lead. The list omits them. `estimated_lbs_per_load` and `estimated_loads_per_month` are currently after State.

Reorder [plasticos_web_leads/views/web_lead_views.xml](plasticos_web_leads/views/web_lead_views.xml) so the list is:

- `submitted_at`, `lead_id`, `company_name`
- `contact_name` with string `Name`, `contact_phone` with string `Phone` and `widget="phone"`, `contact_email` with string `Email` and `widget="email"`
- `pickup_place` with string `Location`
- `estimated_lbs_per_load`, `estimated_loads_per_month`
- `decision`, `review_status`, `lead_source_id`, `state`
- `frequency`, `partner_id`, `intake_id`, `create_date`

Name, Phone, and Email sit directly after Company. Location sits directly after Email and directly before Est. Lbs/Load. The two load columns sit directly before Decision. On the form, under Contact, show Location (readonly), the ZIP, and the seller’s location text. The form keeps the existing Contact Name, Contact Phone, and Contact Email labels.

## Version and proof

Bump `plasticos_web_leads` from `19.0.2.8.13` (the version on pull request 449) to `19.0.2.9.0` and add `migrations/19.0.2.9.0/post-migrate.py`. The migration reads `canonical_payload.pickup_postal_code`, then raw `LocationOfPickUpZip`, and the matching location-text keys.

Tests call the same resolver the admission path uses. `28277`, `28277-1234`, and `282771234` are `Charlotte, NC`. A leading-zero ZIP keeps those zeros in the key. An unknown ZIP, a 4-digit ZIP, and `K1A 0A6` store the submitted value and leave Location empty. Seller text `Miami, FL` on ZIP `28277` does not change `Charlotte, NC`, and seller text with no ZIP does not fill Location. A payload with only `LocationOfPickUpZip` still fills the column. The list arch order after `company_name` is `contact_name`, `contact_phone`, `contact_email`, `pickup_place`, `estimated_lbs_per_load`, `estimated_loads_per_month`, `decision`.

Stack on pull request 449. The base branch is `feat/web-lead-readable-evidence`. Start from a new branch at that pull request's clean tip, with no uncommitted files, so release authorization can see a clean worktree. Publication is `make pr base=feat/web-lead-readable-evidence`. Do not stack on 448 and do not branch from `origin/Staging`. Upgrade only `plasticos_web_leads` when the change is published.

## Build evidence (auto)

- detected_at: `2026-11-10T18:08:38Z`
- conversation_id: `27247fbd-94e5-4645-973e-c6e39f694e8d`
- generation_id: `51acb01c-75bb-4047-819b-792ef7320cf2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/27247fbd-94e5-4645-973e-c6e39f694e8d/27247fbd-94e5-4645-973e-c6e39f694e8d.jsonl`
- todos at build time:
- `place-fields`: completed
- `zip-table`: completed
- `list-column`: completed
- `backfill`: completed
- `tests`: completed
