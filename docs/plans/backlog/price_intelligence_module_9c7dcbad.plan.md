---
name: Price Intelligence Module
overview: Implement the plasticos_price_intelligence module to auto-harvest pricing signals from offer lifecycle events, provide Quick Quote wizard for external quotes, compute rolling price bands with time-decay weighting, and stub Email AI Agent hooks for future integration.
todos:
  - id: manifest
    content: Create __manifest__.py with dependencies and data files
    status: pending
  - id: price-signal
    content: Implement plasticos.price.signal model with computed decay fields
    status: pending
  - id: price-band
    content: Implement plasticos.price.band model with weighted percentile computation
    status: pending
  - id: offer-hooks
    content: Implement offer lifecycle hooks for auto-harvest on state changes
    status: pending
  - id: email-stub
    content: Stub mail.message hooks for future Email AI integration
    status: pending
  - id: quick-quote
    content: Implement Quick Quote wizard for external quote capture
    status: pending
  - id: views
    content: Create tree/form/search views for price signals and bands
    status: pending
  - id: menus
    content: Create menu structure under Plasticos > Price Intelligence
    status: pending
  - id: security
    content: Create ir.model.access.csv with role-based permissions
    status: pending
  - id: cron
    content: Create nightly cron job for price band recomputation
    status: pending
  - id: migration
    content: Create migration script to backfill from transactions
    status: pending
isProject: false
---

# Price Intelligence Module Implementation Plan

## Overview

Create `plasticos_price_intelligence` module that auto-harvests price signals from offer lifecycle events, computes rolling price bands with time-decay weighting, and provides a Quick Quote wizard for external quote capture.

## Module Structure

```
plasticos_price_intelligence/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── price_signal.py           # plasticos.price.signal model
│   ├── price_band.py             # plasticos.price.band model
│   ├── offer_harvest_hooks.py    # Inherit plasticos.offer for auto-harvest
│   └── mail_message_harvest.py   # Stub for Email AI (hooks only)
├── wizards/
│   ├── __init__.py
│   └── quick_quote_wizard.py     # Quick Quote transient model
├── views/
│   ├── price_signal_views.xml    # Tree, form, search views
│   ├── price_band_views.xml      # Tree, graph views
│   ├── quick_quote_wizard_views.xml
│   └── menu_views.xml            # Menu structure
├── security/
│   └── ir.model.access.csv       # Access control
├── data/
│   └── price_band_cron.xml       # Nightly recompute cron
└── migrations/
    └── 19.0.1.0.0/
        └── post-migrate.py       # Backfill from transactions
```

---

## Phase 1: Core Models

### 1.1 Price Signal Model (`[models/price_signal.py](plasticos_price_intelligence/models/price_signal.py)`)

New model `plasticos.price.signal` with:

**Material Context Fields:**

- `polymer_id` (Many2one to `plasticos.polymer`, required, indexed)
- `form_id` (Many2one to `plasticos.material.form`)
- `source_type_id` (Many2one to `plasticos.source.type`)
- `color_id` (Many2one to `plasticos.material.color`)
- `grade_hint` (Char)

**Party Fields:**

- `buyer_partner_id` (Many2one to `res.partner`)
- `supplier_partner_id` (Many2one to `res.partner`)

**Price Signal Fields:**

- `price_per_lb` (Float, digits=(10,4), required)
- `signal_type` (Selection: closed_deal, accepted_offer, counter_offer, rejected_offer, expired_offer, external_quote, claim_downgrade, market_intel)
- `signal_strength` (Float, computed from signal_type)
- `signal_direction` (Selection: bid, ask, settled)

**Context Fields:**

- `quantity_lbs` (Float)
- `region` (Char, computed from partner state)
- `signal_date` (Date, required, default=today)
- `source_record` (Reference to offer/sale.order/intake/claim)
- `notes` (Text)

**Time Decay Fields (computed, stored):**

- `decay_weight` - Exponential decay: 1.0 at t=0, 0.5 at 90 days
- `effective_weight` - signal_strength * decay_weight

**Computed Methods:**

```python
SIGNAL_WEIGHTS = {
    'closed_deal': 1.0,
    'accepted_offer': 0.9,
    'counter_offer': 0.7,
    'external_quote': 0.6,
    'claim_downgrade': 0.5,
    'rejected_offer': 0.4,
    'expired_offer': 0.3,
    'market_intel': 0.2,
}

def _compute_decay_weight(self):
    # Exponential decay with 90-day half-life
    HALF_LIFE_DAYS = 90.0
    age_days = (today - signal_date).days
    decay_weight = exp(-age_days / HALF_LIFE_DAYS * log(2))
```

### 1.2 Price Band Model (`[models/price_band.py](plasticos_price_intelligence/models/price_band.py)`)

New model `plasticos.price.band` with:

**Dimension Fields:**

- `polymer_id` (Many2one, required, indexed)
- `form_id` (Many2one, indexed)
- `source_type_id` (Many2one, indexed)
- `region` (Char, indexed)
- `lookback_days` (Integer, default=90)

**Price Band Fields (weighted percentiles):**

- `price_low` (Float, 10th percentile)
- `price_mid` (Float, 50th percentile)
- `price_high` (Float, 90th percentile)
- `sample_size` (Integer)
- `confidence` (Float, computed)
- `computed_date` (Datetime)

**Unique Constraint:**

```sql
UNIQUE(polymer_id, form_id, source_type_id, region, lookback_days)
```

**Methods:**

- `compute_price_bands()` - Cron method to recompute all bands nightly
- `_compute_band_for_combo()` - Compute weighted percentiles for one material combo
- `_weighted_percentiles()` - Numpy-free weighted percentile calculation

---

## Phase 2: Auto-Harvest Hooks

### 2.1 Offer Lifecycle Hooks (`[models/offer_harvest_hooks.py](plasticos_price_intelligence/models/offer_harvest_hooks.py)`)

Inherit `plasticos.offer` to auto-harvest signals on state changes:

```python
class PlasticosOfferPriceHarvest(models.Model):
    _inherit = "plasticos.offer"

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            self._harvest_price_signals(vals['state'])
        return res
```

**Harvest Logic:**

- `state='accepted'` → Create signal with `signal_type='accepted_offer'`, `direction='settled'`
- `state='rejected'` → Create signal with `signal_type='rejected_offer'`, `direction='ask'` or `'bid'`
- `counter_price_per_lb` set → Create signal with `signal_type='counter_offer'`, `direction='bid'`

**Override `cron_expire_offers()`:**

- Harvest `expired_offer` signals BEFORE changing state to expired

### 2.2 Email AI Stub (`[models/mail_message_harvest.py](plasticos_price_intelligence/models/mail_message_harvest.py)`)

Stub for future Email AI integration:

```python
class MailMessagePriceHarvest(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        # Stub: Log that email parsing would happen here
        # Full AI integration deferred to Phase 2
        return messages
```

---

## Phase 3: Quick Quote Wizard

### 3.1 Wizard Model (`[wizards/quick_quote_wizard.py](plasticos_price_intelligence/wizards/quick_quote_wizard.py)`)

Transient model `plasticos.quick.quote.wizard` for 10-second external quote capture:

**Fields:**

- `polymer_id` (Many2one, required)
- `form_id`, `source_type_id`, `color_id` (Many2one, optional)
- `buyer_partner_id` (Many2one, required, domain customer_rank > 0)
- `supplier_partner_id` (Many2one, optional)
- `price_per_lb` (Float, required)
- `quantity_lbs` (Float)
- `quote_date` (Date, default=today)
- `notes` (Text)
- `intake_id` (Many2one, optional link to intake)

**Action:**

```python
def action_log_quote(self):
    # Create price signal with signal_type='external_quote'
    # Return notification: "Quote logged: $X.XXXX/lb for POLYMER"
```

---

## Phase 4: Views and Menus

### 4.1 Price Signal Views (`[views/price_signal_views.xml](plasticos_price_intelligence/views/price_signal_views.xml)`)

- **Tree view:** signal_date, polymer_id, form_id, price_per_lb, signal_type, signal_strength, decay_weight, effective_weight, buyer_partner_id, supplier_partner_id
- **Form view:** Standard layout with readonly for auto_harvested signals
- **Search view:** Filters for Recent (30d), High Confidence (effective_weight > 0.5), By Polymer, By Signal Type

### 4.2 Price Band Views (`[views/price_band_views.xml](plasticos_price_intelligence/views/price_band_views.xml)`)

- **Tree view:** polymer_id, form_id, source_type_id, region, price_low, price_mid, price_high, sample_size, confidence, computed_date
- **Graph view:** Bar chart with polymer on X-axis, price_mid on Y-axis, grouped by region

### 4.3 Menu Structure (`[views/menu_views.xml](plasticos_price_intelligence/views/menu_views.xml)`)

```
Plasticos (root)
└── Price Intelligence (sequence=50)
    ├── Price Signals
    ├── Price Bands
    └── Log Quick Quote (wizard action)
```

---

## Phase 5: Security and Cron

### 5.1 Access Control (`[security/ir.model.access.csv](plasticos_price_intelligence/security/ir.model.access.csv)`)


| Model                        | Group                          | Create | Read | Write | Unlink |
| ---------------------------- | ------------------------------ | ------ | ---- | ----- | ------ |
| plasticos.price.signal       | base.group_system              | 1      | 1    | 1     | 1      |
| plasticos.price.signal       | sales_team.group_sale_salesman | 1      | 1    | 1     | 0      |
| plasticos.price.signal       | base.group_user                | 0      | 1    | 0     | 0      |
| plasticos.price.band         | base.group_system              | 1      | 1    | 1     | 1      |
| plasticos.price.band         | base.group_user                | 0      | 1    | 0     | 0      |
| plasticos.quick.quote.wizard | sales_team.group_sale_salesman | 1      | 1    | 1     | 1      |


### 5.2 Cron Job (`[data/price_band_cron.xml](plasticos_price_intelligence/data/price_band_cron.xml)`)

```xml
<record id="ir_cron_compute_price_bands" model="ir.cron">
    <field name="name">Price Intelligence: Recompute Price Bands</field>
    <field name="model_id" ref="model_plasticos_price_band"/>
    <field name="code">model.compute_price_bands()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="nextcall">2026-02-24 07:00:00</field>  <!-- 2 AM EST -->
</record>
```

---

## Phase 6: Migration (Transaction Backfill)

### 6.1 Migration Script (`[migrations/19.0.1.0.0/post-migrate.py](plasticos_price_intelligence/migrations/19.0.1.0.0/post-migrate.py)`)

Backfill price signals from existing `plasticos.transaction` records:

```python
def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Transaction = env['plasticos.transaction']
    Signal = env['plasticos.price.signal']

    # Find completed transactions with pricing
    transactions = Transaction.search([
        ('state', 'not in', ['cancel', 'draft']),
        ('unit_price', '>', 0),
    ])

    for tx in transactions:
        # Create closed_deal signal (highest weight)
        Signal.create({
            'polymer_id': tx.polymer_id.id,
            'form_id': tx.form_id.id,
            'price_per_lb': tx.unit_price,
            'signal_type': 'closed_deal',
            'signal_direction': 'settled',
            'buyer_partner_id': tx.buyer_id.id,
            'supplier_partner_id': tx.supplier_id.id,
            'signal_date': tx.create_date.date(),
            'source_record': f'plasticos.transaction,{tx.id}',
            'notes': 'Backfilled from historical transaction',
            'auto_harvested': True,
        })

    # Trigger initial price band computation
    env['plasticos.price.band'].compute_price_bands()
```

---

## Dependencies

**Module Manifest:**

```python
{
    "name": "PlasticOS Price Intelligence",
    "version": "19.0.1.0.0",
    "depends": [
        "plasticos_offer",      # For offer lifecycle hooks
        "plasticos_intake",     # For intake reference
        "plasticos_matching",   # For future graph integration
        "plasticos_material_profile",  # For polymer/form/source_type
        "sale_management",      # For sale.order reference
        "mail",                 # For mail.thread inheritance
    ],
    ...
}
```

---

## Future Work (Deferred)

1. **Graph Integration (w5_price):** Add price scoring dimension to `graph_service.py` Cypher queries
2. **Email AI Agent:** Full Odoo 19 AI module integration for auto-parsing Gmail
3. **Intake Smart Button:** Add "Market Price" button showing price_band_mid
4. **Sale Order Hooks:** Harvest `closed_deal` signals from confirmed sale orders
5. **QC Claim Hooks:** Harvest `claim_downgrade` signals from quality claims

---

## Testing Checklist

- Offer accepted → signal created with correct type/direction
- Offer rejected → signal created with correct direction (ask vs bid)
- Counter-offer recorded → signal with bid direction
- Expired offers harvested via cron
- Quick quote wizard creates external_quote signal
- Weighted percentile calculation accuracy
- Time decay applied correctly (90-day half-life)
- Band confidence increases with sample size
- Migration backfills from transactions correctly
