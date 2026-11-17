---
name: Contact hierarchy UI
overview: Audit cut the extra copies. First and last name are projections of the contact
  name. The company salesperson stays on the company and Odoo pushes it to children.
  A location shows the linked person's email and mobile without storing a second copy.
  The form changes are view placement only.
todos:
- id: name-parts
  content: Add readonly first_name and last_name on the contact, computed from name,
    and show them on the Contacts list
  status: completed
- id: salesperson
  content: Extend Odoo's user_id compute so a company salesperson is the salesperson
    on its locations and people, then recompute existing children
  status: completed
- id: material-profile
  content: Move Material Profile out of the notebook to a full-width block above Locations
  status: completed
- id: locations-width
  content: Make the Locations list full width and add the address columns
  status: completed
- id: payment-label
  content: Rename the contact-card label from Supplier Payment Terms to Payment Terms
  status: completed
- id: location-channels
  content: Show the linked person's email and mobile on the location when the location's
    own values are empty
  status: completed
- id: versions-tests
  content: Bump facility and material versions and run the view test
  status: completed
- id: clean-tree-publish
  content: Start in a clean worktree from origin/Production, then make pr-nosmoke
    with base Production
  status: completed
isProject: false
built: true
status: built
---

# Contacts, locations, and people

## Start in a clean worktree

Do not edit the current checkout. Before any whitelist file changes:

- `git fetch origin Production`
- Add a new worktree from `origin/Production` on a new feature branch. Do not copy uncommitted files into it.
- All edits, the commit, and the publish command run in that worktree.

`make pr` refuses a dirty tree and does not commit. The worktree must be clean at the start, and clean again after the commit, before publish.

## Audit

The previous plan treated six separate screen gaps as one facility-profile feature and then added a second writer for each fact. That is the slop. A facility profile does not inherit a contact's name, email, or salesperson.

These six items do not collapse into one change. They do collapse into three owners:

- The contact name stays on `res.partner.name`. First and last name are a readonly split of that name.
- The salesperson stays on the company's `user_id`. Odoo already has a stored compute for this field. Children read the company. The importer does not grow a second copy step.
- The person's email and mobile stay on the person. The location screen shows them. They are not written onto the location.

What this removes from the earlier plan: no new name module, no import change, no `mapping_status` edit, no partner-import migration, no context flag, and no SQL copy of `user_id`.

L9 architecture profile does not apply. This is a PlasticOS contact form. Nothing here crosses Gate.

What else changes, and what does not:

- A salesperson typed on a location or a person is not kept. The company value replaces it when the compute runs. The child field is readonly when it has a parent. This matches the request that children carry the parent's salesperson.
- Mail and search on a location still use the location's own email. Showing the person's email does not make the location record that address. A stored copy was rejected because the two values would drift.
- The Notes block above the notebook is [plasticos_security_base/views/res_partner_views.xml](plasticos_security_base/views/res_partner_views.xml) at priority 99. It is not edited. Material Profile is inserted at priority 10 and Locations stay at priority 16, so the order is Material Profile, then Locations, then Notes.

## 1. First name and last name

The Contacts column picker has no First Name or Last Name. ERP stores one `ContactNm` in `name`. There is no second source.

On the existing contact extension in [plasticos_facility_profile/models/res_partner.py](plasticos_facility_profile/models/res_partner.py), add stored computed `first_name` and `last_name`:

- Company or location: blank. `48 FORTY SOLUTIONS - IB` is not a person.
- Person: first word and last word. `Eric Melendrez` is Eric / Melendrez. A middle word stays in `name`. One word fills first name only.
- Readonly. `name` remains the only edited name.

Show both on the Contacts list in [plasticos_facility_profile/views/partner_ux.xml](plasticos_facility_profile/views/partner_ux.xml), after Name, `optional="show"`. Show them on the person form, hidden for companies.

That class is where this screen's contact fields already live. The fields are not facility-profile fields, and they are not added to `plasticos.facility.profile`.

## 2. Salesperson

Odoo `res.partner.user_id` is stored and computed. The base method copies it only onto a person, and only when the person is created after the parent already has a salesperson. Locations are companies, so they are skipped. People are imported before the sales-rep step, so they are skipped too.

Override `_compute_user_id` on the same contact extension. Depend on `parent_id` and `parent_id.user_id`. When a partner has a parent and that parent has a salesperson, the partner's salesperson is the parent's. Walk one more step so a contact under a location follows the location, which follows the company. A company with no parent keeps the salesperson the import already wrote. Do not clear a child when the parent has no salesperson.

On the location and person form, the salesperson widget is readonly when `parent_id` is set.

Existing rows do not recompute just because the method changed. [plasticos_facility_profile/migrations/19.0.5.4.4/post-migrate.py](plasticos_facility_profile/migrations/19.0.5.4.4/post-migrate.py) recomputes `user_id` for partners that have a parent. It does not assign the field by SQL.

Do not change [plasticos_partner_import/models/erp_import_service.py](plasticos_partner_import/models/erp_import_service.py). Writing the company salesperson is enough once the compute depends on `parent_id.user_id`.

## 3. Material Profile above Locations

[plasticos_material_profile/views/partner_material_ux.xml](plasticos_material_profile/views/partner_material_ux.xml) puts Material Profile inside the notebook at priority 30. Locations are inserted before the notebook at priority 16.

Change that material view to priority 10 and insert it before the notebook, as a separator plus the existing list and empty-state alert. Not a `<page>`, and not a `<group>`, so the list is full width. Keep `invisible="not is_company"`. Same `material_profile_ids` field. The CRM bridge xpath on that field still matches. Do not edit the bridge.

Priority 10 is the placement contract. Locations are 16. Notes are 99. Do not raise the material priority above 16.

## 4. Locations list

The Locations list sits in a `<group>` in [plasticos_facility_profile/views/facility_profile_views.xml](plasticos_facility_profile/views/facility_profile_views.xml), so it uses half the form.

Replace that group with a separator and the field, still hidden unless this is a company with no parent. Columns from fields the location already has:

- Name, Address Type, Street, City, State, ZIP, Country, Phone, Email, Salesperson

Email in that list is the display field from section 6, so a blank location email shows the linked person's email. Salesperson is `user_id`.

Do not change the Sites list or the People list.

## 5. Payment Terms

Both contact-card labels on `property_supplier_payment_term_id` change from `Supplier Payment Terms` to `Payment Terms`. Same field and same visibility. Do not relabel the Invoicing tab or the bulk-update wizard.

## 6. Location email and mobile

Eric's email and mobile are on Eric. Fontana's phone is the site phone. The link is `site_person_ids`.

Add two readonly, non-stored fields on the contact extension: `linked_person_email` and `linked_person_mobile`. For a location (company with a parent), each one is the location's own value when that value exists, otherwise the first linked person who has one. Other records stay empty.

On the location header, show those fields instead of the empty native Email and Mobile lines. Leave Phone as the location phone. Do not write the person's email or mobile onto the location during import.

## Versions

- `plasticos_material_profile` `19.0.5.11.12` to `19.0.5.11.13`
- `plasticos_facility_profile` `19.0.5.4.3` to `19.0.5.4.4`

Do not bump `plasticos_partner_import`. Format the two manifests. Upgrade only those two: `make update m=plasticos_material_profile,plasticos_facility_profile`.

## Tests

[tests/test_partner_contact_hierarchy.py](tests/test_partner_contact_hierarchy.py) asserts the views and the compute contract:

- Contacts list has `first_name` and `last_name` after Name
- Material Profile is priority 10, is not a notebook page, and is inserted before the notebook
- Locations is not inside a `<group>` and lists the columns above
- The card says `Payment Terms`
- `_compute_user_id` depends on `parent_id.user_id` and assigns the parent's salesperson
- The location email and mobile displays are computed and are not written by `erp_import_service.py`

Run that pytest module. Do not run `make test-module` or `make import-erp`.

## Publish

Commit the whitelist files on the feature branch in the clean worktree. Then publish with install-smoke skipped. The command waits attached for 10 minutes. It is not started in the background.

```bash
make pr-nosmoke reason="contact form layout and parent salesperson; operator skipped install-smoke" base=Production
```

`scripts/pr_stack_parent.sh` refuses a destination of Production before any push (`destination must be Staging or a stacked parent branch`). `make pr` also refuses to publish from a branch named Production. The command above is the one to run. If it exits 1 on that refusal, stop. Do not retarget the pull request at Staging, and do not merge into Production by another path.

## File whitelist

Only these paths. Every other file stays as it is, including the importer, `mapping_status.py`, the CRM bridge, and the security layout.

- [plasticos_facility_profile/models/res_partner.py](plasticos_facility_profile/models/res_partner.py)
- [plasticos_facility_profile/views/partner_ux.xml](plasticos_facility_profile/views/partner_ux.xml)
- [plasticos_facility_profile/views/facility_profile_views.xml](plasticos_facility_profile/views/facility_profile_views.xml)
- [plasticos_facility_profile/__manifest__.py](plasticos_facility_profile/__manifest__.py)
- [plasticos_facility_profile/migrations/19.0.5.4.4/post-migrate.py](plasticos_facility_profile/migrations/19.0.5.4.4/post-migrate.py) (new)
- [plasticos_material_profile/views/partner_material_ux.xml](plasticos_material_profile/views/partner_material_ux.xml)
- [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py)
- [tests/test_partner_contact_hierarchy.py](tests/test_partner_contact_hierarchy.py) (new)

## Build evidence (auto)

- detected_at: `2026-11-09T19:19:19Z`
- conversation_id: `7af2c599-35cd-448b-8441-144aabe5efb5`
- generation_id: `cd2c1f20-6abc-4f60-ac3f-dda5da9a0dfe`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/7af2c599-35cd-448b-8441-144aabe5efb5/7af2c599-35cd-448b-8441-144aabe5efb5.jsonl`
- todos at build time:
- `name-parts`: completed
- `salesperson`: completed
- `material-profile`: completed
- `locations-width`: completed
- `payment-label`: completed
- `location-channels`: completed
- `versions-tests`: completed
- `clean-tree-publish`: completed
