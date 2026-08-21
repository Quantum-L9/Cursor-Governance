---
name: CRM Lead Form Overhaul
overview: Restructure the CRM lead form view with field repositioning, add a mobile field, improve button layout with tooltips, restrict sales team editing to admins, and move Notes to the main form area.
todos:
  - id: add-mobile-field
    content: Add mobile field to crm.lead in crm_lead.py + wire to partner on conversion
    status: completed
  - id: reposition-fields
    content: "XPath: move source_id, add function/mobile below phone, move probability to bottom"
    status: completed
  - id: promote-notes
    content: Move description (Notes) from tab to main form area below Sales Team
    status: completed
  - id: team-readonly
    content: Make team_id readonly for non-admin users via groups attribute
    status: completed
  - id: button-overhaul
    content: Reposition Convert to Intake between CTO/Enrich, green color, add tooltips to all 3 buttons
    status: completed
  - id: import-mobile
    content: Re-add mobile mapping in crm_lead_import_service.py
    status: completed
  - id: smart-partner-match
    content: Override _find_matching_partner to also match by partner_name (company name)
    status: completed
  - id: dense-list-view
    content: Enhance CRM lead list view with all contact + pipeline columns as optional toggles
    status: completed
  - id: pivot-view
    content: Add pivot view for cross-tab analysis (leads by source x stage)
    status: completed
  - id: calendar-view
    content: Add calendar view for leads by create_date/activity_date
    status: completed
  - id: version-bumps
    content: Bump manifest versions for crm_bridge and partner_import
    status: completed
isProject: false
---

# CRM Lead Form Overhaul

## Scope

All changes go in `plasticos_crm_bridge` (inherits the Odoo core CRM form view `crm.crm_lead_view_form`). The existing file is [`plasticos_crm_bridge/views/crm_lead_views.xml`](plasticos_crm_bridge/views/crm_lead_views.xml).

For the new `mobile` field, we add it to [`plasticos_crm_bridge/models/crm_lead.py`](plasticos_crm_bridge/models/crm_lead.py) since Odoo 19 removed `mobile` from `crm.lead` entirely (confirmed: only `phone` exists in the DB table).

## Changes

### 1. Add `mobile` field to `crm.lead` with E.164 formatting

- Add `mobile = fields.Char(string="Mobile")` to `CrmLeadPlastOS` in `crm_lead.py`
- Add `mobile_sanitized = fields.Char(compute="_compute_mobile_sanitized", store=True)` for clean E.164 storage
- Use Odoo's built-in `_phone_format()` (from `phone_validation` mixin, already on `crm.lead`) to normalize:

```python
@api.depends("mobile")
def _compute_mobile_sanitized(self):
    for lead in self:
        if lead.mobile:
            lead.mobile_sanitized = (
                lead._phone_format(number=lead.mobile, force_format="E164") or lead.mobile
            )
        else:
            lead.mobile_sanitized = False
```

- Add `@api.constrains("mobile")` to reject non-10-digit US numbers:

```python
@api.constrains("mobile")
def _check_mobile_format(self):
    import re

    for lead in self:
        if not lead.mobile:
            continue
        digits = re.sub(r"\D", "", lead.mobile)
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) != 10:
            raise ValidationError("Mobile must be a 10-digit US number (e.g., 555-100-0001).")
```

- On conversion (`action_convert_to_intake` / `_find_or_create_partner_from_lead`), copy `self.mobile` to `partner.mobile`
- In the import service (`crm_lead_import_service.py`), re-add `"mobile": row.get("Mobile 1")` now that the field exists
- Use `widget="phone"` in the form view for click-to-call functionality

### 2. Reposition fields on the CRM Lead Form

Using XPath inheritance on `crm.crm_lead_view_form`:

| Field | Current Position | New Position |
|-------|-----------------|--------------|
| `source_id` | Inside "Extra Info" tab, Marketing group | Below Phone, adjacent to Website |
| `function` (Job Position) | Not visible on form | Below Phone |
| `mobile` (new) | N/A | Below Phone, next to `function` |
| `probability` widget | Top of form (big %) | Move to bottom of the form (below notebook) |
| `description` (Notes) | Inside "Notes" tab in notebook | Promote to main form area, below Sales Team (like we did with `comment` on `res.partner`) |

### 3. Sales Team — read-only for non-admins

- Add `groups="plasticos_security_base.group_system_admin,plasticos_security_base.group_operations_manager"` attribute override on `team_id` field, or use `readonly="not user_has_groups('base.group_system')"` expression

### 4. "Convert to Intake" button repositioning and styling

- Move the button from below `oe_title` to the **button_box area** or the **status bar** between "Convert to Opportunity" and "Enrich"
- Change class to `btn-success` (deep green) instead of `btn-primary` (blue)
- Add a `title=` tooltip explaining: "Create a PlasticOS material intake from this lead. This starts the intake-to-matching-to-offer pipeline. Use 'Convert to Opportunity' for standard Odoo CRM workflow instead."

### 5. Add info tooltips on the three action buttons

- **Convert to Opportunity**: Add `title="Standard Odoo CRM action. Converts this lead into a sales opportunity and creates/links a contact (res.partner). Use for general CRM pipeline tracking."`
- **Convert to Intake**: Add `title="PlasticOS action. Creates a material intake record from this lead, starting the plastics brokerage pipeline: Intake -> Matching -> Offer -> Transaction."`
- **Enrich**: Already has Odoo's built-in tooltip (IAP enrichment)

### 6. Notes promoted to main form

- Use XPath to inject `description` field above the notebook (below Sales Team area)
- Optionally hide the "Notes" tab in the notebook since the content is now on the main form (same pattern as `res.partner` in `view_partner_form_plasticos_layout`)

## Files Modified

| File | Change |
|------|--------|
| `plasticos_crm_bridge/models/crm_lead.py` | Add `mobile` field definition |
| `plasticos_crm_bridge/views/crm_lead_views.xml` | All XPath view changes (repositioning, button styling, tooltips, team readonly, notes promotion, probability move) |
| `plasticos_partner_import/models/crm_lead_import_service.py` | Re-add `mobile` mapping from CSV |
| `plasticos_crm_bridge/__manifest__.py` | Version bump |
| `plasticos_partner_import/__manifest__.py` | Version bump |

### 7. Smart partner matching for Convert to Opportunity

Odoo's `_find_matching_partner()` only matches by **email**. When our VanillaSoft imports set `partner_name` (company name) but the email doesn't exist in `res.partner`, the wizard defaults to "Create a new customer" even when a company with that exact name already exists.

**Fix:** Override `_find_matching_partner` in `plasticos_crm_bridge/models/crm_lead.py` to also try matching by `partner_name`:

```python
def _find_matching_partner(self):
    partner = super()._find_matching_partner()
    if not partner and self.partner_name:
        partner = self.env["res.partner"].search(
            [
                ("name", "=ilike", self.partner_name.strip()),
                ("is_company", "=", True),
                ("parent_id", "=", False),
            ],
            limit=1,
        )
    return partner
```

This makes the wizard auto-select "Link to an existing customer" and pre-fill the partner when the company name matches.

## Files Modified

| File | Change |
|------|--------|
| `plasticos_crm_bridge/models/crm_lead.py` | Add `mobile` field, override `_find_matching_partner` |
| `plasticos_crm_bridge/views/crm_lead_views.xml` | All XPath view changes (repositioning, button styling, tooltips, team readonly, notes promotion, probability move) |
| `plasticos_partner_import/models/crm_lead_import_service.py` | Re-add `mobile` mapping from CSV |
| `plasticos_crm_bridge/__manifest__.py` | Version bump |
| `plasticos_partner_import/__manifest__.py` | Version bump |

### 8. Dense List View with Toggleable Columns

Enhance the existing `crm_lead_plastos_bridge_list` (inherits `crm.crm_case_tree_view_leads`) to add all useful columns as `optional="show"` or `optional="hide"`. Users can toggle columns via the column picker (gear icon), then save as their default via Favorites.

**Columns to add (all `optional`):**

Contact info group:
- `phone` (show), `mobile` (show), `function` (hide)
- `city` (show), `state_id` (show), `country_id` (hide)
- `source_id` (show), `vanillasoft_id` (hide)

Pipeline stats (from crm_bridge computed fields):
- `material_profile_count` (show), `total_match_count` (show)
- `total_transaction_count` (show), `partner_total_revenue` (hide)
- `partner_last_pickup` (show), `intake_count` (show)
- `web_lead_count` (hide), `delivery_term` (hide)

**Save as default:** Built into Odoo natively. In the search bar, click the star (Favorites) -> "Save current search" -> check "Use by default". This persists per-user. No custom code needed, just needs the columns to be available.

### 9. Pivot View

Add a pivot view definition in `crm_lead_views.xml`:

```xml
<record id="crm_lead_plastos_pivot" model="ir.ui.view">
    <field name="name">crm.lead.plastos.pivot</field>
    <field name="model">crm.lead</field>
    <field name="arch" type="xml">
        <pivot string="CRM Leads Analysis">
            <field name="source_id" type="row"/>
            <field name="stage_id" type="col"/>
            <field name="expected_revenue" type="measure"/>
        </pivot>
    </field>
</record>
```

Register the pivot view in the CRM lead action (via `ir.actions.act_window` view_mode addition or a separate action).

### 10. Calendar View

Add a calendar view keyed on `create_date` (or `date_deadline` / `activity_date_planned`):

```xml
<record id="crm_lead_plastos_calendar" model="ir.ui.view">
    <field name="name">crm.lead.plastos.calendar</field>
    <field name="model">crm.lead</field>
    <field name="arch" type="xml">
        <calendar string="CRM Leads" date_start="create_date" color="stage_id"
                  event_open_popup="1" quick_create="0">
            <field name="partner_name"/>
            <field name="contact_name"/>
            <field name="stage_id" filters="1"/>
            <field name="user_id" filters="1" invisible="1"/>
        </calendar>
    </field>
</record>
```

### Adding views to the CRM action

Inject `pivot` and `calendar` into the existing CRM action's `view_mode` via an `ir.actions.act_window` record that extends the default CRM pipeline action, or create a dedicated "PlasticOS Leads Analysis" menu item with these views.

## Files Modified (final)

| File | Change |
|------|--------|
| `plasticos_crm_bridge/models/crm_lead.py` | Add `mobile` field, override `_find_matching_partner` |
| `plasticos_crm_bridge/views/crm_lead_views.xml` | Form XPaths, dense list, pivot view, calendar view, action wiring |
| `plasticos_partner_import/models/crm_lead_import_service.py` | Re-add `mobile` mapping from CSV |
| `plasticos_crm_bridge/__manifest__.py` | Version bump |
| `plasticos_partner_import/__manifest__.py` | Version bump |

## Not in Scope

- Priority stars (keeping as-is per your instruction)
- Armed Forces states (Odoo base data, not removable)
- Graph/chart view (can add later if needed)
