---
name: Logistics Bug Fixes
overview: Fix 11 confirmed bugs in plasticos_logistics module covering security (ACL), state machine enforcement, validation, performance, and hygiene issues. Evaluator amendments incorporated.
todos:
  - id: phase-1-security
    content: "Phase 1: Security fixes - ACL cleanup, state machine wiring, write() deadlock fix, wizard SQL bypass removal"
    status: completed
  - id: phase-2-validation
    content: "Phase 2: Validation fixes - dispatch pre-conditions, action_confirm_ready auth, rate memory guard, dispatch.load_id FK"
    status: completed
  - id: phase-3-performance
    content: "Phase 3: Performance fix - batch _compute_transaction_id"
    status: completed
  - id: phase-4-hygiene
    content: "Phase 4: Hygiene - button visibility, sla_breached readonly, date constraint, PDF cleanup"
    status: completed
isProject: false
---

# Logistics Bug Fix Plan (Amended)

## Evaluator Verification Summary

All findings confirmed against live code:
- ACL duplicate rows: Lines 9-11 confirmed with `perm_unlink=1`
- SQL bypass in wizard: Lines 95-103 confirmed
- State machine not wired: `_transition()` has no validation
- `cycle_time_hours` deadlock: BLOCKER - must add to `write()` allowed set
- PDF files: 3 files confirmed present
- `action_confirm_ready`: No view button found - method only

## Files to Modify

1. [plasticos_logistics/security/ir.model.access.csv](plasticos_logistics/security/ir.model.access.csv)
2. [plasticos_logistics/services/state_machine.py](plasticos_logistics/services/state_machine.py)
3. [plasticos_logistics/services/utils.py](plasticos_logistics/services/utils.py) (NEW)
4. [plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)
5. [plasticos_logistics/models/dispatch.py](plasticos_logistics/models/dispatch.py)
6. [plasticos_logistics/wizards/load_bulk_update_wizard.py](plasticos_logistics/wizards/load_bulk_update_wizard.py)
7. [plasticos_logistics/views/load_views.xml](plasticos_logistics/views/load_views.xml)
8. [plasticos_logistics/.gitignore](plasticos_logistics/.gitignore) (NEW)

---

## Phase 1: Security Fixes (CRITICAL)

### 1.1 - Remove Duplicate ACL Rows

Delete lines 9-11 (`access_load_all`, `access_rate_memory_all`, `access_dispatch_all`).

Final file (8 lines):
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_load_user,plasticos.load.user,plasticos_logistics.model_plasticos_load,base.group_user,1,1,1,0
access_load_manager,plasticos.load.manager,plasticos_logistics.model_plasticos_load,base.group_system,1,1,1,1
access_rate_memory_user,plasticos.rate.memory.user,plasticos_logistics.model_plasticos_rate_memory,base.group_user,1,0,0,0
access_rate_memory_manager,plasticos.rate.memory.manager,plasticos_logistics.model_plasticos_rate_memory,base.group_system,1,1,1,1
access_dispatch_user,plasticos.dispatch.user,plasticos_logistics.model_plasticos_dispatch,base.group_user,1,1,1,0
access_dispatch_manager,plasticos.dispatch.manager,plasticos_logistics.model_plasticos_dispatch,base.group_system,1,1,1,1
access_load_bulk_wizard_user,plasticos.load.bulk.update.wizard.user,model_plasticos_load_bulk_update_wizard,base.group_user,1,1,1,1
```

### 1.2 - Wire State Machine + Fix write() Deadlock

**A. Update state_machine.py** - Add `exception` state and `closed: []` terminal:
```python
VALID_TRANSITIONS = {
    "draft": ["awaiting_ready"],
    "awaiting_ready": ["ready_confirmed", "exception"],
    "ready_confirmed": ["rate_confirmed", "exception"],
    "rate_confirmed": ["scheduled", "exception"],
    "scheduled": ["dispatched", "exception"],
    "dispatched": ["picked_up", "exception"],
    "picked_up": ["delivered", "exception"],
    "delivered": ["closed", "exception"],
    "closed": [],  # Terminal - no transitions
    "exception": ["draft"],  # Recovery path
}
```

**B. Create services/utils.py** - Extract `new_correlation_id()`:
```python
import uuid

def new_correlation_id():
    """Generate correlation ID (stub for l9_trace)"""
    return str(uuid.uuid4())
```

**C. Update load.py**:

1. Module-level import (NOT function-level):
```python
from odoo.addons.plasticos_logistics.services.state_machine import VALID_TRANSITIONS
from odoo.addons.plasticos_logistics.services.utils import new_correlation_id
```

2. Add `cycle_time_hours` to `write()` allowed set (BLOCKER fix):
```python
allowed = {
    "bol_pickup_attached",
    "bol_delivery_attached",
    "state",
    "entered_state_at",
    "dispatched_at",
    "delivered_at",
    "cycle_time_hours",  # Computed field - must be writable
}
```

3. Enforce state machine in `_transition()`:
```python
def _transition(self, new_state):
    for rec in self:
        allowed = VALID_TRANSITIONS.get(rec.state, [])
        if new_state not in allowed:
            raise UserError(
                f"Cannot move load '{rec.name}' from '{rec.state}' to '{new_state}'. "
                f"Allowed next states: {allowed or ['none — terminal state']}."
            )
        correlation_id = new_correlation_id()
        old = rec.state
        vals = {"state": new_state, "entered_state_at": fields.Datetime.now()}
        if new_state == "dispatched":
            vals["dispatched_at"] = fields.Datetime.now()
        if new_state == "delivered":
            vals["delivered_at"] = fields.Datetime.now()
        rec.write(vals)
        _logger.info("Load %s: %s -> %s (correlation: %s)", rec.id, old, new_state, correlation_id)
```

### 1.3 - Replace SQL Bypass in Wizard (Option A: All-or-Nothing)

Replace `action_update_status()` with validate-then-execute pattern:
```python
def action_update_status(self):
    self.ensure_one()
    if not self.load_ids:
        raise UserError(_("No loads selected."))

    # Validate ALL transitions first — fail fast before any writes
    from odoo.addons.plasticos_logistics.services.state_machine import VALID_TRANSITIONS
    errors = []
    for load in self.load_ids:
        allowed = VALID_TRANSITIONS.get(load.state, [])
        if self.new_state not in allowed:
            errors.append(
                f"{load.name}: Cannot move from '{load.state}' to '{self.new_state}' "
                f"(allowed: {allowed or ['none — terminal']})"
            )
    if errors:
        raise UserError(_("Invalid transitions:\n%s") % "\n".join(errors))

    # All valid — execute
    for load in self.load_ids:
        old_state = load.state
        load._transition(self.new_state)
        load.message_post(
            body=_("Status changed from <b>%(old)s</b> to <b>%(new)s</b><br/>"
                   "Reason: %(reason)s<br/>Updated by: %(user)s (Bulk Update)")
            % {"old": old_state, "new": self.new_state,
               "reason": self.reason, "user": self.env.user.name},
            message_type="notification",
        )

    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": _("Bulk Update Complete"),
            "message": _("%d load(s) updated to '%s'") % (len(self.load_ids), self.new_state),
            "type": "success",
            "sticky": False,
            "next": {"type": "ir.actions.act_window_close"},
        },
    }
```

Add `ValidationError` import if missing.

---

## Phase 2: Validation Fixes (HIGH)

### 2.1 - Add Dispatch Pre-Conditions

Update `action_dispatch()` - tighten to `scheduled` only per evaluator:
```python
def action_dispatch(self):
    for rec in self:
        if rec.state != "scheduled":
            raise UserError(f"Load {rec.name} must be in Scheduled state before dispatch.")
        if not rec.carrier_id:
            raise UserError(f"Load {rec.name}: Carrier is required before dispatch.")
        if not rec.pickup_partner_id:
            raise UserError(f"Load {rec.name}: Pickup location is required before dispatch.")
        if not rec.delivery_partner_id:
            raise UserError(f"Load {rec.name}: Delivery location is required before dispatch.")
        if not rec.pickup_datetime:
            raise UserError(f"Load {rec.name}: Pickup date/time is required before dispatch.")
        rec._transition("dispatched")
```

### 2.2 - Fix action_confirm_ready() Authentication

Remove parameter, use `self.env.user.name`:
```python
def action_confirm_ready(self):
    for rec in self:
        rec.ready_confirmed_by = self.env.user.name
        rec.ready_confirmed_at = fields.Datetime.now()
        rec._transition("ready_confirmed")
```

NOTE: No view button calls this - method-only change.

### 2.3 - Guard _store_rate_memory() Against Bad Lane Keys

Update `action_confirm_rate()`:
```python
def action_confirm_rate(self, rate):
    for rec in self:
        rec.rate_amount = rate
        rec.rate_confirmed_at = fields.Datetime.now()
        rec.rate_auto_reused = False
        rec._transition("rate_confirmed")
        if rec.sale_order_id and rec.carrier_id:
            ship = rec.sale_order_id.partner_shipping_id.id
            inv = rec.sale_order_id.partner_invoice_id.id
            if ship and inv:
                rec._store_rate_memory()
            else:
                _logger.warning(
                    "Load %s: rate memory skipped — sale order %s has no shipping/invoice partner.",
                    rec.id, rec.sale_order_id.name,
                )
```

### 2.4 - Add load_id FK to dispatch.py

Add field (state sync is separate ticket per evaluator):
```python
load_id = fields.Many2one(
    "plasticos.load",
    string="Load",
    ondelete="restrict",
    index=True,
)
```

Update import to use shared `new_correlation_id`:
```python
from odoo.addons.plasticos_logistics.services.utils import new_correlation_id
```

Remove local `new_correlation_id()` function.

---

## Phase 3: Performance Fix (MEDIUM)

### 3.1 - Batch _compute_transaction_id

Replace N+1 pattern with batched lookup:
```python
@api.depends("id")
def _compute_transaction_id(self):
    """Reverse lookup: find transaction that references this load.
    Batched to avoid N+1 queries on list view.
    """
    txs = self.env[PLASTICOS_TRANSACTION].search([("load_id", "in", self.ids)])
    tx_map = {tx.load_id.id: tx.id for tx in txs}
    for rec in self:
        rec.transaction_id = tx_map.get(rec.id, False)
```

---

## Phase 4: Hygiene

### 4.1 - Hide Email Buttons on Draft State

Add `invisible` to all 4 stat buttons in load_views.xml (lines 173-184):
```xml
<button name="action_send_dispatch_packet" type="object" class="oe_stat_button" icon="fa-paper-plane"
        invisible="state in ('draft', 'awaiting_ready', 'ready_confirmed')">
```

### 4.2 - Make sla_breached Readonly

Line 283 - add `readonly="1"`:
```xml
<field name="sla_breached" readonly="1"/>
```

### 4.3 - Add Date Constraint

Add to load.py:
```python
@api.constrains("pickup_datetime", "delivery_datetime")
def _check_delivery_after_pickup(self):
    for rec in self:
        if rec.pickup_datetime and rec.delivery_datetime:
            if rec.delivery_datetime < rec.pickup_datetime:
                raise ValidationError(
                    f"Load {rec.name}: Delivery date cannot be before pickup date."
                )
```

### 4.4 - Remove PDF Files + Add .gitignore

```bash
git rm "plasticos_logistics/BOL - DELIVERY-59422.pdf"
git rm "plasticos_logistics/BOL - PICKUP-59422.pdf"
git rm "plasticos_logistics/DELIVERY ORDER-59422.pdf"
```

Create `plasticos_logistics/.gitignore`:
```
*.pdf
```

---

## Deployment

```bash
odoo-bin -u plasticos_logistics -d plasticos --stop-after-init
```

## Risk Assessment

- **Phase 1**: CRITICAL security + state machine - test thoroughly
- **Phase 2**: Validation tightening - may surface existing bad data
- **Phase 3**: Performance - safe, no behavior change
- **Phase 4**: Hygiene - low risk cosmetic changes
