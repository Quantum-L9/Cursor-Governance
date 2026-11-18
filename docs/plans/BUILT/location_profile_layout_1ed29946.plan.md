---
name: Location profile layout
overview: On the location window, stop offering Bales as a material form, show Packaging
  Type in place of Contam %, lift Facility Profile out of the notebook into a section
  under Material Profile, make People and the Enrichment Sources and Runs lists full
  width, save the material line when Open Full Profile is clicked, and keep the location
  dialog open after Save.
todos:
- id: deactivate-bales-form
  content: Deactivate form_bale and move existing Bales form rows onto packaging Bales
    by xmlid. Assert form_bale is inactive.
  status: completed
- id: packaging-column
  content: Replace the Contam % column on the partner material list with Packaging
    Type. Assert the list names packaging_type_id and does not name contamination_percent.
  status: completed
- id: open-profile-save
  content: Make Open Full Profile save the line via open_form_view and a CSS rule
    scoped to o_material_profile_lines. Assert open_form_view="1", the list class,
    and no action_open_profile_form button.
  status: completed
- id: facility-section
  content: Move Facility Profile under Material Profile with no group and delete the
    partner_ux page xpath. Assert the separator sits above Locations and the page
    is gone.
  status: completed
- id: people-width
  content: Make the location People list a full-width separator. Assert People is
    a separator and not a group.
  status: completed
- id: location-save-stays
  content: Make Save on the location dialog store the record and leave the dialog
    open. Assert the patch skips closable only for a company that has a parent.
  status: completed
- id: enrichment-width
  content: Make Enrichment Sources and Runs full-width separators. Assert they are
    separators and not groups.
  status: completed
isProject: false
built: true
status: built
---

# Location window

On the location dialog: stop offering Bales as a form, show Packaging Type in place of Contam %, lift Facility Profile out of the notebook to a section under Material Profile, make People and the Enrichment Sources and Runs lists full width, save the material line when Open Full Profile is clicked, and keep the dialog open after Save.

Contam % stays on the full material profile. Packaging Bales stays in the packaging master. Notes stays where it is. The facility capability list keeps its current Open Full Profile button. Leave [`plasticos_security_base/views/res_partner_views.xml`](plasticos_security_base/views/res_partner_views.xml) unchanged.

The location dialog uses the shared partner form. A parent company that has child locations is not a facility, so the Facility Profile section stays hidden there. The Enrichment width change also shows on that parent. Sales & Purchase and Invoicing stay tabs.

## Form no longer offers Bales

[`plasticos_material_profile/data/material_form_data.xml`](plasticos_material_profile/data/material_form_data.xml) still seeds `form_bale` as an active form, which is why the Form cell shows Bales. That file is `noupdate="0"`. Set `<field name="active" eval="False"/>` on `form_bale`. The packaging record `packaging_bales` stays active.

Keep `BALES` in [`plasticos_material_profile/form_codes.py`](plasticos_material_profile/form_codes.py). Tests and the equipment gate still name that code, and `form_id` is `ondelete="restrict"`, so the master row stays.

`migrations/19.0.5.11.14/post-migrate.py` resolves `plasticos_material_profile.form_bale` and `plasticos_material_profile.packaging_bales` by xmlid. The upgrade deactivates `form_bale` before this script runs, so an active-only search will miss it. For each profile whose `form_id` is that record: when `packaging_type_id` is empty, set it to packaging Bales, then clear `form_id`. A row that already has a packaging type keeps it. The Form cell on that PP line then goes blank, and Packaging Type shows Bales.

Assert `form_bale` is inactive.

## Contam % becomes Packaging Type

In the inline list in [`plasticos_material_profile/views/partner_material_ux.xml`](plasticos_material_profile/views/partner_material_ux.xml), replace the `contamination_percent` column with `packaging_type_id` labeled Packaging Type, in the same position after Source Type.

Assert that list names `packaging_type_id` and does not name `contamination_percent`.

## Open Full Profile saves the line

The expand icon is an object button inside the editable list in [`plasticos_material_profile/views/partner_material_ux.xml`](plasticos_material_profile/views/partner_material_ux.xml). On a new line Odoo never calls it. [`web/static/src/views/list/list_renderer.xml`](web/static/src/views/list/list_renderer.xml) sets that button's click to "Please save your changes first" when the row is still new.

Remove that object button. Set `open_form_view="1"` and `class="o_material_profile_lines"` on the same list. That click is `switchToForm` in [`x2many_field.js`](web/static/src/views/fields/x2many/x2many_field.js): it saves the location, keeps the new profile's id, and opens the profile. The field context already passes `form_view_ref`, and `switchToForm` sends that context, so the full profile form opens. An edited line that already has an id is saved the same way.

The stock control then reads "View". The list class lands on the x2many wrapper in [`x2many_field.xml`](web/static/src/views/fields/x2many/x2many_field.xml), not on the cell inside `web.ListRenderer`. Add a `web.assets_backend` CSS file on `plasticos_material_profile` and style only `.o_material_profile_lines .o_list_record_open_form_view button` so that cell shows the external-link icon and the title "Open Full Profile". Add the manifest `assets` key in the same version bump. Do not inherit `web.ListRenderer`.

Assert `open_form_view="1"`, the class `o_material_profile_lines`, and no `action_open_profile_form` button on this list. Assert the manifest assets entry names the CSS file.

## Facility Profile leaves the notebook

The `facility_profile` page in [`plasticos_facility_profile/views/facility_profile_views.xml`](plasticos_facility_profile/views/facility_profile_views.xml) holds Partner Type and the `facility_profile_ids` list (Process Type, Feedstock Type, Capacity, Has Horizontal Baler, Has Wash Line, Handles Bales). The page shows only when `is_facility` is set, which is already true for a location.

Take that page out of the notebook. Place the same fields in the block that already sits before the notebook, ahead of Locations and People. Material Profile is inserted by a priority-10 view, so the location reads Material Profile, then Facility Profile, then People. Partner Type is a field under the separator, with no `<group>`, so it uses the same full-width seam as the list.

```xml
<separator string="Facility Profile" invisible="not is_facility"/>
<field name="partner_type_id" options="{'no_create': True}" invisible="not is_facility"/>
<field name="facility_profile_ids" nolabel="1" invisible="not is_facility"
       context="{'default_partner_id': id, 'form_view_ref': 'plasticos_facility_profile.view_facility_profile_form'}">
```

The list stays editable and keeps its columns and its current Open Full Profile button.

[`plasticos_facility_profile/views/partner_ux.xml`](plasticos_facility_profile/views/partner_ux.xml) targets `//page[@name='facility_profile']` only to repeat `invisible="not is_facility"`. Delete that xpath. The gate stays on the separator, Partner Type, and the list.

Assert there is no `facility_profile` notebook page, and that a Facility Profile separator with `invisible="not is_facility"` sits above Locations. Assert `partner_ux.xml` no longer selects that page.

## People spans the window

People is a `<group>`, so Odoo gives it half the dialog. Material Profile and Locations are a separator plus a list, which is full width. In [`plasticos_facility_profile/views/facility_profile_views.xml`](plasticos_facility_profile/views/facility_profile_views.xml), use that same shape for People and keep `invisible="not is_company or not parent_id"`:

```xml
<separator string="People" invisible="not is_company or not parent_id"/>
<field name="site_person_ids" nolabel="1" invisible="not is_company or not parent_id">
```

Assert People is a separator and not a group.

## Save stays on the location

The location opens as a dialog. Its footer Save calls `saveButtonClicked({closable: true})` in [`web/static/src/views/form/form_controller.xml`](web/static/src/views/form/form_controller.xml). For a dialog, [`action_service.js`](web/static/src/webclient/actions/action_service.js) closes the window when `params.closable` is set. That is why Save stores the facility and then closes it.

A `web.assets_backend` patch in `plasticos_facility_profile` changes only that case. The main partner form already includes `parent_id`, so the dialog record has it. When the dialog record is `res.partner`, `is_company` is set, and `parent_id` is set, Save calls `saveButtonClicked` without `closable`. The record is stored and the location window stays open. Discard still closes. Other dialogs, including the company form itself, keep the normal Save. Add the manifest `assets` key in the same version bump.

Assert the patch skips `closable` only for a company that has a parent, and that the manifest assets entry names the patch.

## Enrichment spans the window

Sources and Runs on the Enrichment tab are each a `<group>` in [`plasticos_enrichment/views/res_partner_enrichment.xml`](plasticos_enrichment/views/res_partner_enrichment.xml), so each list takes half the dialog. Use the same separator-plus-list shape as Material Profile. The columns, the editable Sources list, and `invisible="not is_company"` stay as they are.

```xml
<separator string="Sources"/>
<field name="enrichment_source_ids" nolabel="1">
...
<separator string="Runs"/>
<field name="enrichment_run_ids" nolabel="1">
```

Assert Sources and Runs are separators and not groups.

## Versions and checks

Static assertions live in [`tests/test_partner_contact_hierarchy.py`](tests/test_partner_contact_hierarchy.py). Each todo above names the assertion it owns.

- `plasticos_material_profile` `19.0.5.11.13` to `19.0.5.11.14`, including [`README.md`](plasticos_material_profile/README.md), `migrations/19.0.5.11.14/post-migrate.py`, and a new `assets` → `web.assets_backend` CSS file. This module has no `assets` key today.
- `plasticos_facility_profile` `19.0.5.4.8` to `19.0.5.4.9`, including its README and a new `assets` → `web.assets_backend` JS patch. No migration. This module has no `assets` key today.
- `plasticos_enrichment` `19.0.2.5.8` to `19.0.2.5.9`, including its README. No migration. View layout only.

## Build evidence (auto)

- detected_at: `2026-11-10T22:48:52Z`
- conversation_id: `5edc190e-fb6f-4be2-a3ed-b42655d981f9`
- generation_id: `a927cd12-7909-4988-ab99-816e21001226`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/5edc190e-fb6f-4be2-a3ed-b42655d981f9/5edc190e-fb6f-4be2-a3ed-b42655d981f9.jsonl`
- todos at build time:
- `deactivate-bales-form`: completed
- `packaging-column`: completed
- `open-profile-save`: completed
- `facility-section`: completed
- `people-width`: completed
- `location-save-stays`: completed
- `enrichment-width`: completed
