---
name: ""
overview: ""
todos: []
isProject: false
---

## PlasticOS Offer Module — Build Plan v1.0

### Repo Ground Truth

The actual codebase has two separate match surfaces :


| Model                    | Purpose                                             | Key Fields                                                                                                                                          |
| ------------------------ | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plasticos.match.result` | L9 engine output with scores, reasoning, confidence | `buyer_partner_id`, `facility_profile_id`, `score`, `confidence`, `score_breakdown`, `match_reasoning`, `state` (pending/accepted/rejected/expired) |
| `plasticos.intake.match` | Lightweight intake-embedded match lines             | `buyer_id`, `match_score`, `match_reason`, `typical_price`, `selected` (boolean checkbox)                                                           |


The match result form already has **Accept** and **Reject** buttons in the header . The `action_accept()` method sets `state='accepted'` and stamps `reviewed_by` / `reviewed_date` . The help text in the match result action literally says *"Review and accept matches to create offers"*  — this is the designed entry point.

The intake's `action_send_offers()` is a secondary convenience: it filters `match_line_ids` by `selected` boolean and currently raises a placeholder error .

**Primary flow:** Match Result (accepted) → Offer Generation Wizard → `plasticos.offer` records
**Secondary flow:** Intake → select match lines → same wizard

---

### Module Structure

```
plasticos_offer/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── offer.py                      # plasticos.offer core model
│   └── match_result_extension.py     # Inherit plasticos.match.result — add "Create Offer" button
├── wizards/
│   ├── __init__.py
│   └── offer_generate_wizard.py      # Batch offer creation from accepted matches
├── views/
│   ├── offer_views.xml               # Form, tree, kanban for offers
│   ├── offer_generate_wizard_views.xml
│   ├── match_result_views_inherit.xml # Inject "Create Offer" button into match result form
│   ├── intake_views_inherit.xml       # Wire action_send_offers() on intake
│   └── menu_views.xml
├── data/
│   ├── email_templates.xml           # Offer email template
│   ├── ir_sequence_data.xml          # OFF-XXXX sequence
│   └── ir_cron_data.xml              # Nightly expiration cron
├── security/
│   ├── ir.model.access.csv
│   └── offer_security.xml            # Record rules
└── tests/
    ├── __init__.py
    ├── test_offer_lifecycle.py
    └── test_offer_generation.py
```

---

### Phase 1: Core Offer Model

**File:** `plasticos_offer/models/offer.py`
**Model:** `plasticos.offer`
**Inherits:** `mail.thread`, `mail.activity.mixin`

#### Fields


| Field                  | Type                                | Details                                                     |
| ---------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `name`                 | Char                                | Computed via `ir.sequence` → `OFF-0001`                     |
| `intake_id`            | Many2one `plasticos.intake`         | Required, indexed, ondelete=restrict, tracking              |
| `match_result_id`      | Many2one `plasticos.match.result`   | Links to source match, ondelete=set null                    |
| `buyer_partner_id`     | Many2one `res.partner`              | Required, indexed, tracking                                 |
| `buyer_facility_id`    | Many2one `res.partner`              | Optional, domain `[('parent_id', '=', buyer_partner_id)]`   |
| `supplier_partner_id`  | Many2one `res.partner`              | Required, related from `intake_id.partner_id`, stored       |
| `polymer_id`           | Many2one `plasticos.polymer`        | Related from `intake_id.polymer_id`, stored                 |
| `form_id`              | Many2one `plasticos.material.form`  | Related from `intake_id.form_id`, stored                    |
| `source_type_id`       | Many2one `plasticos.source.type`    | Related from `intake_id.source_type_id`, stored             |
| `color_id`             | Many2one `plasticos.material.color` | Related from `intake_id.color_id`, stored                   |
| `price_per_lb`         | Float                               | digits=(10,4), required, tracking                           |
| `counter_price_per_lb` | Float                               | digits=(10,4), buyer's counter-offer                        |
| `quantity_lbs`         | Float                               | Default from `intake_id.quantity_per_load_lbs`              |
| `loads_per_month`      | Integer                             | From intake for reference                                   |
| `delivery_terms`       | Selection                           | `fob_origin` / `fob_destination` / `delivered`              |
| `payment_terms`        | Selection                           | `net_30` / `net_45` / `net_60` / `cod` / `prepaid`          |
| `valid_until`          | Date                                | Required, default = today + 14 days                         |
| `state`                | Selection                           | See state machine below                                     |
| `match_score`          | Float                               | Copied from `match_result_id.score` for list-view reference |
| `rejection_reason`     | Text                                | Required on reject                                          |
| `sent_date`            | Datetime                            | Stamped on send                                             |
| `responded_date`       | Datetime                            | Stamped on response                                         |
| `notes`                | Text                                | Internal notes                                              |


#### State Machine

```
draft → sent → responded ──→ accepted
                           └→ rejected
         sent → expired (cron)
         any  → cancelled
```


| Transition                     | Method                    | Guard                                               | Side Effects                                                        |
| ------------------------------ | ------------------------- | --------------------------------------------------- | ------------------------------------------------------------------- |
| draft → sent                   | `action_send_email()`     | `state == 'draft'`                                  | Send `mail.template`, stamp `sent_date`, `message_post`             |
| sent → responded               | `action_mark_responded()` | `state == 'sent'`                                   | Stamp `responded_date`, `message_post`                              |
| responded → accepted           | `action_accept()`         | `state == 'responded'`                              | `message_post` ◆ *Price intelligence hook point*                    |
| responded → rejected           | `action_reject()`         | `state == 'responded'`, `rejection_reason` required | `message_post` ◆ *Price intelligence hook point*                    |
| draft/sent/responded → expired | `cron_expire_offers()`    | `valid_until < today`                               | ◆ *Price intelligence hook point* — harvest **before** state change |
| any → cancelled                | `action_cancel()`         | `state != 'cancelled'`                              | `message_post`                                                      |


#### Deduplication Guard

```python
_sql_constraints = [
    ('unique_active_offer',
     'UNIQUE(intake_id, buyer_partner_id)',
     'An active offer already exists for this buyer on this intake. '
     'Cancel the existing offer first.'),
]
```

Note: This constraint allows re-offering after cancellation via a partial unique index if needed in production. For v1, the simple unique is sufficient — users cancel first, then re-create.

#### Sequence Data

**File:** `plasticos_offer/data/ir_sequence_data.xml`

```xml
<record id="seq_plasticos_offer" model="ir.sequence">
    <field name="name">PlasticOS Offer</field>
    <field name="code">plasticos.offer</field>
    <field name="prefix">OFF-</field>
    <field name="padding">4</field>
</record>
```

#### Cron: Expire Offers

**File:** `plasticos_offer/data/ir_cron_data.xml`

```xml
<record id="ir_cron_expire_offers" model="ir.cron">
    <field name="name">PlasticOS: Expire Stale Offers</field>
    <field name="model_id" ref="model_plasticos_offer"/>
    <field name="code">model.cron_expire_offers()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="nextcall">2026-02-24 07:00:00</field>
</record>
```

Implementation:

```python
@api.model
def cron_expire_offers(self):
    """Expire offers past valid_until. Called nightly.
    
    HOOK POINT: plasticos_price_intelligence will override this method
    to harvest expired_offer signals BEFORE state changes.
    """
    today = fields.Date.today()
    offers = self.search([
        ('valid_until', '<', today),
        ('state', 'in', ('draft', 'sent', 'responded')),
    ])
    for offer in offers:
        offer.write({'state': 'expired'})
        offer.message_post(
            body=f"Offer expired (valid until {offer.valid_until})",
            message_type='notification',
        )
    _logger.info("Expired %d offers", len(offers))
```

---

### Phase 2: Match Result → Offer Wizard

**File:** `plasticos_offer/wizards/offer_generate_wizard.py`
**Model:** `plasticos.offer.generate.wizard` (TransientModel)

This wizard is the bridge between accepted match results and offer records.

#### Fields


| Field              | Type                               | Details                                                              |
| ------------------ | ---------------------------------- | -------------------------------------------------------------------- |
| `match_result_ids` | Many2many `plasticos.match.result` | Pre-populated from context, readonly                                 |
| `intake_id`        | Many2one `plasticos.intake`        | Computed from first match result, readonly                           |
| `price_per_lb`     | Float                              | digits=(10,4), required — user sets the offer price                  |
| `delivery_terms`   | Selection                          | `fob_origin` / `fob_destination` / `delivered`, default=`fob_origin` |
| `payment_terms`    | Selection                          | `net_30` / `net_45` / `net_60` / `cod` / `prepaid`, default=`net_30` |
| `valid_until`      | Date                               | default = today + 14                                                 |
| `send_email`       | Boolean                            | default=True — send immediately or create as draft                   |
| `notes`            | Text                               | Optional notes copied to all offers                                  |


#### Action

```python
def action_generate_offers(self):
    """Create one plasticos.offer per accepted match result."""
    self.ensure_one()
    Offer = self.env['plasticos.offer']
    created = Offer
    
    for match in self.match_result_ids:
        offer = Offer.create({
            'intake_id': match.intake_id.id,
            'match_result_id': match.id,
            'buyer_partner_id': match.buyer_partner_id.id,
            'buyer_facility_id': match.buyer_facility_id.id,
            'price_per_lb': self.price_per_lb,
            'quantity_lbs': match.intake_id.quantity_per_load_lbs,
            'loads_per_month': match.intake_id.loads_per_month,
            'delivery_terms': self.delivery_terms,
            'payment_terms': self.payment_terms,
            'valid_until': self.valid_until,
            'match_score': match.score,
            'notes': self.notes,
        })
        if self.send_email:
            offer.action_send_email()
        created |= offer
    
    # Return tree view of created offers
    return {
        'type': 'ir.actions.act_window',
        'name': f'{len(created)} Offers Created',
        'res_model': 'plasticos.offer',
        'view_mode': 'list,form',
        'domain': [('id', 'in', created.ids)],
    }
```

#### Wizard View

**File:** `plasticos_offer/views/offer_generate_wizard_views.xml`

Simple form: material summary at top (readonly, from match results), price/terms fields in the middle, "Generate Offers" primary button and "Cancel" at bottom.

---

### Phase 3: Hook Into Match Results

#### 3.1 Add "Create Offer" Button to Match Result

**File:** `plasticos_offer/models/match_result_extension.py`

```python
class PlasticosMatchResultOfferExtension(models.Model):
    _inherit = "plasticos.match.result"

    offer_ids = fields.One2many(
        'plasticos.offer', 'match_result_id',
        string='Offers',
    )
    offer_count = fields.Integer(
        compute='_compute_offer_count', store=True,
    )
    has_active_offer = fields.Boolean(
        compute='_compute_offer_count', store=True,
        help="True if an active (non-cancelled) offer exists for this match.",
    )

    @api.depends('offer_ids', 'offer_ids.state')
    def _compute_offer_count(self):
        for rec in self:
            active = rec.offer_ids.filtered(lambda o: o.state != 'cancelled')
            rec.offer_count = len(active)
            rec.has_active_offer = bool(active)

    def action_create_offer(self):
        """Open offer generation wizard for accepted match results."""
        accepted = self.filtered(lambda r: r.state == 'accepted')
        if not accepted:
            raise UserError("Select at least one accepted match result.")

        already_offered = accepted.filtered('has_active_offer')
        if already_offered:
            names = ', '.join(already_offered.mapped('display_name'))
            raise UserError(
                f"Active offers already exist for: {names}. "
                "Cancel existing offers first."
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Offers',
            'res_model': 'plasticos.offer.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_match_result_ids': [(6, 0, accepted.ids)],
            },
        }
```

#### 3.2 Inject Button Into Match Result Views

**File:** `plasticos_offer/views/match_result_views_inherit.xml`

Inherit the match result form  to add a "Create Offer" button in the header next to Accept/Reject, visible only when `state == 'accepted'` and `has_active_offer == False`:

```xml
<record id="view_match_result_form_inherit_offer" model="ir.ui.view">
    <field name="name">plasticos.match.result.form.inherit.offer</field>
    <field name="model">plasticos.match.result</field>
    <field name="inherit_id" ref="plasticos_matching.view_match_result_form"/>
    <field name="arch" type="xml">
        <button name="action_reject" position="after">
            <button name="action_create_offer" type="object"
                    string="Create Offer" class="btn-primary"
                    invisible="state != 'accepted' or has_active_offer"/>
            <button name="action_view_offers" type="object"
                    string="View Offers" class="btn-secondary"
                    invisible="offer_count == 0"
                    badge="offer_count"/>
        </button>
    </field>
</record>
```

Also inject into the list view for multi-select: add `action_create_offer` as a server action available from the list's action dropdown when multiple accepted results are selected.

#### 3.3 Wire Intake's `action_send_offers()`

**File:** `plasticos_offer/views/intake_views_inherit.xml` + model inheritance

Inherit `plasticos.intake` to replace the placeholder :

```python
class PlasticosIntakeOfferExtension(models.Model):
    _inherit = "plasticos.intake"

    offer_ids = fields.One2many(
        'plasticos.offer', 'intake_id',
        string='Offers',
    )
    offer_count = fields.Integer(
        compute='_compute_offer_count',
    )

    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    def action_send_offers(self):
        """Override placeholder to open offer wizard for selected match lines."""
        self.ensure_one()
        selected = self.match_line_ids.filtered('selected')
        if not selected:
            raise UserError("Please select at least one buyer to send offers to.")

        # Find corresponding match results for selected match lines
        # match_line buyer_id → match.result buyer_partner_id for same intake
        MatchResult = self.env['plasticos.match.result']
        match_results = MatchResult.search([
            ('intake_id', '=', self.id),
            ('buyer_partner_id', 'in', selected.mapped('buyer_id').ids),
            ('state', '=', 'accepted'),
        ])

        if not match_results:
            raise UserError(
                "No accepted match results found for selected buyers. "
                "Accept match results before creating offers."
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Offers',
            'res_model': 'plasticos.offer.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_match_result_ids': [(6, 0, match_results.ids)],
            },
        }
```

---

### Phase 4: Email Template

**File:** `plasticos_offer/data/email_templates.xml`

```xml
<record id="mail_template_plasticos_offer" model="mail.template">
    <field name="name">PlasticOS: Offer to Buyer</field>
    <field name="model_id" ref="model_plasticos_offer"/>
    <field name="subject">{{ object.supplier_partner_id.name }} - 
        {{ object.polymer_id.name }} {{ object.form_id.name or '' }} 
        Available | {{ object.name }}</field>
    <field name="email_from">{{ (object.create_uid.email_formatted or 
        object.company_id.email_formatted) }}</field>
    <field name="email_to">{{ object.buyer_partner_id.email }}</field>
    <field name="body_html" type="html">
        <!-- Professional tone, material details, pricing, 
             expiration, CTA for buyer response -->
    </field>
</record>
```

The `action_send_email()` method on the offer:

```python
def action_send_email(self):
    """Send offer email and transition to sent state."""
    self.ensure_one()
    if self.state != 'draft':
        raise UserError("Only draft offers can be sent.")
    
    template = self.env.ref('plasticos_offer.mail_template_plasticos_offer')
    self.message_post_with_source(
        source_ref=template,
        subtype_xmlid='mail.mt_comment',
    )
    self.write({
        'state': 'sent',
        'sent_date': fields.Datetime.now(),
    })
```

---

### Phase 5: Offer Views

**File:** `plasticos_offer/views/offer_views.xml`

#### Form View

Header: state-dependent buttons (`Send Email`, `Mark Responded`, `Accept`, `Reject`, `Cancel`) + statusbar widget on `state`.

Sheet layout:

- Top group: supplier (readonly) + buyer + polymer/form (readonly from intake)
- Second group: price_per_lb + counter_price_per_lb + quantity_lbs + match_score
- Third group: delivery_terms + payment_terms + valid_until
- Notebook: page "Details" (notes, rejection_reason), page "Source Match" (match_result_id link, score_breakdown)
- Chatter at bottom

#### Tree View

Fields: `name`, `intake_id`, `polymer_id`, `buyer_partner_id`, `price_per_lb`, `counter_price_per_lb`, `match_score`, `valid_until`, `state` (badge widget). Decorations: success for accepted, danger for rejected/expired, muted for cancelled.

#### Kanban View

Grouped by `state`. Cards show buyer name, polymer, price, score, valid_until.

---

### Phase 6: Security

**File:** `plasticos_offer/security/ir.model.access.csv`


| Model                             | Group                            | C   | R   | W   | D   |
| --------------------------------- | -------------------------------- | --- | --- | --- | --- |
| `plasticos.offer`                 | `base.group_system`              | 1   | 1   | 1   | 1   |
| `plasticos.offer`                 | `sales_team.group_sale_salesman` | 1   | 1   | 1   | 0   |
| `plasticos.offer`                 | `base.group_user`                | 0   | 1   | 0   | 0   |
| `plasticos.offer.generate.wizard` | `sales_team.group_sale_salesman` | 1   | 1   | 1   | 1   |


**File:** `plasticos_offer/security/offer_security.xml`

Record rule: Sales users can only see offers where `create_uid` is in their sales team, or they are the assigned user on the intake. System group sees all.

---

### Phase 7: Manifest

**File:** `plasticos_offer/__manifest__.py`

```python
{
    "name": "PlasticOS Offers",
    "version": "19.0.1.0.0",
    "summary": "Offer lifecycle: generate, send, track, close",
    "license": "LGPL-3",
    "author": "PlasticOS",
    "category": "Plasticos/Sales",
    "depends": [
        "mail",
        "plasticos_intake",
        "plasticos_matching",
    ],
    "data": [
        "security/offer_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "data/email_templates.xml",
        "views/offer_views.xml",
        "views/offer_generate_wizard_views.xml",
        "views/match_result_views_inherit.xml",
        "views/intake_views_inherit.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
```

---

### Menu Structure

```
Plasticos (root)
└── Offers (sequence=25, between Matching at 20 and Price Intelligence at 50)
    ├── All Offers (tree/kanban/form)
    ├── Pipeline (kanban, grouped by state)
    └── Expiring Soon (tree, domain: valid_until within 3 days, state in sent/responded)
```

---

### Integration Surface for Price Intelligence

These are the exact methods that `plasticos_price_intelligence` will later `_inherit` to harvest signals:


| Method                                    | Signal Type      | Direction                              |
| ----------------------------------------- | ---------------- | -------------------------------------- |
| `action_accept()`                         | `accepted_offer` | `settled`                              |
| `action_reject()`                         | `rejected_offer` | `ask` or `bid` (inferred from context) |
| `cron_expire_offers()`                    | `expired_offer`  | `ask`                                  |
| `write()` when `counter_price_per_lb` set | `counter_offer`  | `bid`                                  |


No price intelligence code ships in this module. The methods are clean, the hooks are implicit via Odoo's standard `_inherit` + `super()` pattern.

---

### Files Summary


| File                                                    | Action     |
| ------------------------------------------------------- | ---------- |
| `plasticos_offer/__init__.py`                           | **CREATE** |
| `plasticos_offer/__manifest__.py`                       | **CREATE** |
| `plasticos_offer/models/__init__.py`                    | **CREATE** |
| `plasticos_offer/models/offer.py`                       | **CREATE** |
| `plasticos_offer/models/match_result_extension.py`      | **CREATE** |
| `plasticos_offer/wizards/__init__.py`                   | **CREATE** |
| `plasticos_offer/wizards/offer_generate_wizard.py`      | **CREATE** |
| `plasticos_offer/views/offer_views.xml`                 | **CREATE** |
| `plasticos_offer/views/offer_generate_wizard_views.xml` | **CREATE** |
| `plasticos_offer/views/match_result_views_inherit.xml`  | **CREATE** |
| `plasticos_offer/views/intake_views_inherit.xml`        | **CREATE** |
| `plasticos_offer/views/menu_views.xml`                  | **CREATE** |
| `plasticos_offer/data/email_templates.xml`              | **CREATE** |
| `plasticos_offer/data/ir_sequence_data.xml`             | **CREATE** |
| `plasticos_offer/data/ir_cron_data.xml`                 | **CREATE** |
| `plasticos_offer/security/ir.model.access.csv`          | **CREATE** |
| `plasticos_offer/security/offer_security.xml`           | **CREATE** |
| `plasticos_offer/tests/__init__.py`                     | **CREATE** |
| `plasticos_offer/tests/test_offer_lifecycle.py`         | **CREATE** |
| `plasticos_offer/tests/test_offer_generation.py`        | **CREATE** |


All files are **CREATE** — nothing modifies existing files. The intake's `action_send_offers()` override and the match result button injection both happen via Odoo's inheritance mechanism from *within* this new module. No existing module files touched.

---

### Testing Checklist

- Wizard with 3 accepted match results → creates 3 `plasticos.offer` records with correct intake/buyer linkage
- Wizard with `send_email=True` → offers in `sent` state, emails in mail queue
- Wizard with `send_email=False` → offers in `draft` state
- Wizard rejects match results that already have active offers (dedup guard)
- Wizard rejects non-accepted match results
- `action_send_email()` → draft to sent, `sent_date` stamped, chatter logged
- `action_mark_responded()` → sent to responded
- `action_accept()` → responded to accepted
- `action_reject()` without reason → `UserError`
- `action_reject()` with reason → responded to rejected
- `cron_expire_offers()` → expired state for past-due offers, non-expired untouched
- `action_cancel()` → any state to cancelled
- Intake `action_send_offers()` → routes to wizard with correct match results
- Match result "Create Offer" button → opens wizard
- Unique constraint prevents duplicate active offers per intake+buyer

