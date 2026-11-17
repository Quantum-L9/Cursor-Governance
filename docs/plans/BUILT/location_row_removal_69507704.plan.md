---
name: Location row removal
overview: Add a visible trash control on company Locations and Material Profile rows.
  A location or profile with no remaining business reference is deleted. One that
  is still used is archived, so Terre Haute and Rozzeles Ferry leave the list and
  their history stays. Partner delete rights are not widened. Build in a clean worktree
  from PR 461 and publish with make pr-nosmoke stacked on that branch.
todos:
- id: clean-worktree
  content: Add a clean worktree from origin/feat/opportunity-supplier-offer and do
    all edits there
  status: completed
- id: location-action
  content: Add guarded action_remove_location and the Locations trash button
  status: completed
- id: profile-action
  content: Add action_remove_profile and the visible Material Profile trash button
  status: completed
- id: tests-versions
  content: Add TransactionCase plus static view assertions, and bump both module versions
    and READMEs
  status: completed
- id: publish-stacked
  content: Publish with make pr-nosmoke base=feat/opportunity-supplier-offer from
    a clean tree
  status: completed
isProject: false
built: true
status: built
---

# Remove closed locations and material profiles from the company form

## Accepted intent

On a company such as SKY RECYCLING:

- A material profile on the parent company stays valid. Do not force a child partner.
- Each Locations row and each Material Profile row gets one trash icon in the last column, visible without hovering.
- The trash removes that row from the list for every internal user who can already open the company, including Sales, Logistics, and Accounting.
- A row nothing else still uses is deleted. A row that people, profiles, orders, bills, intakes, or an approval still use is archived (`active` false, and for a location `entity_status` `inactive`). Archived rows drop out of the list. The record and its history remain.
- Do not grant `res.partner` unlink to Sales, Logistics, or Accounting. Contact Creation (`base.group_partner_manager`) stays the only general partner-delete right.

`location_child_ids` stays a computed mirror of active company children. The trash is a row button, not an inverse on that field. Odoo already limits `child_ids` to `active = True` (`odoo/addons/base/models/res_partner.py`), so an archived location disappears from [plasticos_facility_profile/views/facility_profile_views.xml](plasticos_facility_profile/views/facility_profile_views.xml).

```mermaid
flowchart TD
  click[Trash on a row]
  readCheck[User can read the company and the row]
  kind{Row kind}
  locRefs{Location still referenced}
  profRefs{Approval still points at the profile}
  hardDelete[Unlink the record]
  archiveLoc["active false and entity_status inactive"]
  archiveProf[active false]
  gone[Row leaves the company form]
  click --> readCheck --> kind
  kind -->|child company| locRefs
  kind -->|material profile| profRefs
  locRefs -->|no| hardDelete --> gone
  locRefs -->|yes| archiveLoc --> gone
  profRefs -->|no| hardDelete
  profRefs -->|yes| archiveProf --> gone
```

## Out of scope

- No change to the parent-company material profile rule, and no change to `partner_id` domain `[('parent_id','!=',False)]` on the profile model. The inline list already creates a profile on the open company.
- No ACL edit in [plasticos_security_base/security/ir.model.access.csv](plasticos_security_base/security/ir.model.access.csv).
- No new model, field, or migration.
- No edit of Terre Haute or Rozzeles Ferry data in this change. After the view loads, the operator uses the trash on those rows.
- No `make update`, no merge, and no deploy. Publication is the stacked `make pr-nosmoke` below. Do not use `make pr` without the nosmoke target, and do not use `make push`.

## File whitelist

Only these paths may be edited:

- [plasticos_facility_profile/models/res_partner.py](plasticos_facility_profile/models/res_partner.py)
- [plasticos_facility_profile/views/facility_profile_views.xml](plasticos_facility_profile/views/facility_profile_views.xml)
- [plasticos_facility_profile/__manifest__.py](plasticos_facility_profile/__manifest__.py) — `19.0.5.4.9` to `19.0.5.4.10`
- [plasticos_facility_profile/README.md](plasticos_facility_profile/README.md) — `module_version` to the same value
- [plasticos_facility_profile/tests/__init__.py](plasticos_facility_profile/tests/__init__.py)
- [plasticos_facility_profile/tests/test_location_removal.py](plasticos_facility_profile/tests/test_location_removal.py) — new
- [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py)
- [plasticos_material_profile/views/partner_material_ux.xml](plasticos_material_profile/views/partner_material_ux.xml)
- [plasticos_material_profile/__manifest__.py](plasticos_material_profile/__manifest__.py) — `19.0.5.11.15` to `19.0.5.11.16`
- [plasticos_material_profile/README.md](plasticos_material_profile/README.md) — `module_version` to the same value
- [plasticos_material_profile/tests/__init__.py](plasticos_material_profile/tests/__init__.py)
- [plasticos_material_profile/tests/test_profile_line_removal.py](plasticos_material_profile/tests/test_profile_line_removal.py) — new
- [tests/test_partner_contact_hierarchy.py](tests/test_partner_contact_hierarchy.py)

## Location behavior

Add `action_remove_location` on `res.partner` in [plasticos_facility_profile/models/res_partner.py](plasticos_facility_profile/models/res_partner.py).

Guard, in order:

1. `ensure_one`.
2. `check_access("read")` on the location and on `parent_id` before any elevated write. A private company the user cannot read never reaches the write.
3. Refuse unless `is_company` and `parent_id` are set. The parent company itself has no parent, so this button cannot remove SKY RECYCLING.
4. A location is still referenced when any of these exist, including archived rows (`active_test=False`): a child partner, `site_person_ids`, `material_profile_ids`, `facility_profile_ids`, a `sale.order` (`partner_id`, `partner_invoice_id`, or `partner_shipping_id`), a `purchase.order` (`partner_id`), an `account.move` (`partner_id`), a `stock.picking` (`partner_id`), a `crm.lead` (`partner_id`), a `plasticos.intake` (`partner_id` or `facility_id` when that field exists), or a `plasticos.opportunity.approval` (`partner_id`). Search a model only when it is installed.
5. Referenced: `write({"active": False, "entity_status": "inactive"})`. Unreferenced: `unlink()`.
6. The write and the unlink run as `sudo()` on that one record only. Put the justification on that same line: the user already passed the read check, the record is a child location, and Sales, Logistics, and Accounting have no partner unlink. Do not sudo the parent, and do not sudo a search that decides the reference check.

In the Locations list in [plasticos_facility_profile/views/facility_profile_views.xml](plasticos_facility_profile/views/facility_profile_views.xml), after the Salesperson column:

```xml
<button name="action_remove_location" type="object" icon="fa-trash"
        title="Remove location"
        confirm="Remove this location? A location that is still in use is archived and kept."
        class="btn-link text-danger p-0"/>
```

The list stays non-editable. Existing columns stay.

## Material profile behavior

Add `action_remove_profile` on `plasticos.material.profile`.

- `ensure_one`, then `check_access("read")` on the profile and on `partner_id`.
- If any `plasticos.opportunity.approval` has `material_profile_id` equal to this profile, set `active` false. That relation is `ondelete="restrict"`, so a real delete would fail and the frozen lot must stay. The partner one2many then hides the row.
- Otherwise `unlink()`. Order lines, intakes, and leads use `ondelete="set null"`; their copied specification fields stay on those documents.
- No sudo. Internal users already have unlink through `base.group_user` in [plasticos_material_profile/security/ir.model.access.csv](plasticos_material_profile/security/ir.model.access.csv). Role rows that say unlink 0 do not remove that grant.

In [plasticos_material_profile/views/partner_material_ux.xml](plasticos_material_profile/views/partner_material_ux.xml), set `delete="0"` on the editable list so the only control is the visible trash, and add the same style of button as the last column with `title="Remove material profile"` and a confirm sentence. Keep `editable="bottom"` and `open_form_view="1"`.

## Tests

Odoo cases use `TransactionCase`, `@tagged("post_install", "-at_install")`, and records created in `setUpClass`. They do not touch seed partners.

Location cases in the new facility test module:

- An unreferenced child company is unlinked and is absent from `parent.location_child_ids`.
- A child with a linked person, and a child used as `sale.order.partner_id`, stay in the database with `active` false and `entity_status` `inactive`, and are absent from `parent.location_child_ids`.
- Calling the method on the parent company raises.
- A user who cannot read the company cannot run the method.

Profile cases in the new material test module:

- A profile with no approval is unlinked and leaves `partner.material_profile_ids`.
- A profile referenced by `plasticos.opportunity.approval` becomes inactive and leaves the partner's active list. The approval row remains.
- A profile created on a parent company with no child still saves. That locks the accepted parent-profile behavior.

Extend [tests/test_partner_contact_hierarchy.py](tests/test_partner_contact_hierarchy.py) so the Locations list source contains `action_remove_location` after the Salesperson field, and the material list source contains `action_remove_profile` and `delete="0"`. This file is what `pytest tests/` runs in GitHub `ci.yml`. This publish skips install-smoke and the runtime tests, so the TransactionCase modules are not executed by `make pr-nosmoke`. Do not start `make test-module` or `make test-odoo` ad hoc. Run the static file with `pytest tests/test_partner_contact_hierarchy.py` in the worktree before the commit.

## Definition of done

- Locations and Material Profile each show one trash button in the last column, with `title` and `confirm`.
- Clicking it on an unused location deletes that partner. Clicking it on Terre Haute or Rozzeles Ferry, or any location that still has people or commercial documents, archives it. The name is gone from the company's Locations list. The parent company is unchanged.
- Clicking it on an unused material profile deletes that profile. Clicking it on a profile tied to an opportunity approval archives it. The line is gone from the company form. The approval remains.
- A parent company can still receive a material profile with no child location.
- Sales, Logistics, and Accounting partner ACL rows are unchanged. The location method is the only elevated write, and only after the read check on a child location.
- Both manifests and both README `module_version` lines are the next patch versions above. No other module version changes.
- `ruff check` and `ruff format` are clean on the edited Python. `python3 ci/check_odoo19_xml.py` is clean on the edited XML.
- The new static assertions in `tests/test_partner_contact_hierarchy.py` pass under `pytest` in the worktree.
- The diff against `origin/feat/opportunity-supplier-offer` touches only the whitelist.
- The worktree is clean before the first edit and again after the commit. The operator checkout is not switched, stashed, reset, or cleaned.
- `make pr-nosmoke` opens one pull request whose base is `feat/opportunity-supplier-offer` (PR 461). It does not target `Staging` directly.

## Build

Do not edit the operator checkout. It is already `feat/opportunity-supplier-offer`, the head of [PR 461](https://github.com/cryptoxdog/IB-Odoo_19/pull/461). A commit there would land on 461. PR 461’s base is `feat/profile-derived-fields`. Its chain ends at `Staging`. Its tip already has facility profile `19.0.5.4.9` and material profile `19.0.5.11.15`.

From the repo root, fetch that tip and add a new worktree. Do not use raw `git worktree add`. Refuse the path if it already exists.

```bash
git fetch origin feat/opportunity-supplier-offer
bash .cursor-commands/ops/scripts/worktree_add_wired.sh \
  -b feat/location-row-removal \
  "../IB-Odoo_19-location-row-removal" \
  origin/feat/opportunity-supplier-offer
```

All edits, the pytest run, the commit, and the publish happen in `../IB-Odoo_19-location-row-removal`. Before the first edit, `git status --porcelain` is empty. Do not carry untracked files, a stash, or a dirty index into that tree. If porcelain is not empty, stop.

## Publish

Commit only the whitelist on `feat/location-row-removal`. After the commit, `git status --porcelain` is empty again. Then, from that worktree:

```bash
make pr-nosmoke reason="Location and material-profile row removal, stacked on PR 461. Install-smoke is skipped for this publish." base=feat/opportunity-supplier-offer
```

`make pr-nosmoke` runs `make pr` with install-smoke skipped and posts that reason. `base=` stacks the new pull request onto PR 461. HEAD must contain `origin/feat/opportunity-supplier-offer`. Do not publish onto `Staging`, and do not add these commits to `feat/opportunity-supplier-offer`.

## Build evidence (auto)

- detected_at: `2026-11-11T00:09:25Z`
- conversation_id: `aabb1368-3124-435f-9a10-04f2ebaac463`
- generation_id: `6ba816f6-c2e9-4429-8fb9-15598bf0ad6a`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/aabb1368-3124-435f-9a10-04f2ebaac463/aabb1368-3124-435f-9a10-04f2ebaac463.jsonl`
- todos at build time:
- `clean-worktree`: completed
- `location-action`: completed
- `profile-action`: completed
- `tests-versions`: completed
- `publish-stacked`: completed

