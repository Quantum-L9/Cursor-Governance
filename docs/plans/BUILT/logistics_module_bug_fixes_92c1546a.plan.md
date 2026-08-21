---
name: Logistics Module Bug Fixes
overview: "Fix 9 bugs in plasticos_logistics module: ACL security holes, SQL bypass in bulk wizard, missing state machine enforcement, dispatch validation gaps, authentication issues, rate memory corruption, dispatch-load linkage, N+1 query performance, and hygiene items."
todos:
  - id: acl-fix
    content: Remove duplicate ACL rows from ir.model.access.csv (lines 9-11)
    status: completed
  - id: state-machine
    content: Wire VALID_TRANSITIONS into _transition() in load.py
    status: completed
  - id: state-machine-exception
    content: Add exception state to VALID_TRANSITIONS in state_machine.py
    status: completed
  - id: bulk-wizard-sql
    content: Replace raw SQL with _transition() in bulk wizard + add ValidationError import
    status: completed
  - id: write-guard-fix
    content: Add cycle_time_hours, sla_breached, message_ids, message_follower_ids to write() allowed set
    status: completed
  - id: dispatch-validation
    content: Add carrier/location/date validation to action_dispatch()
    status: completed
  - id: auth-fix
    content: Fix action_confirm_ready() to use self.env.user
    status: completed
  - id: rate-memory-guard
    content: Guard _store_rate_memory() against bad lane keys
    status: completed
  - id: dispatch-load-link
    content: Add load_id FK to plasticos.dispatch
    status: completed
  - id: batch-compute
    content: Batch _compute_transaction_id to fix N+1 query
    status: completed
  - id: correlation-id
    content: Extract new_correlation_id() to shared module
    status: completed
  - id: button-visibility
    content: Hide email buttons on draft state in load_views.xml
    status: completed
  - id: sla-readonly
    content: Make sla_breached field readonly in load_views.xml
    status: completed
  - id: date-constraint
    content: Add pickup/delivery datetime constraint to load.py
    status: completed
  - id: remove-pdfs
    content: Remove committed PDF files and add .gitignore entry
    status: completed
isProject: false
---

# Logistics Module Bug Fix Plan

## Analysis Summary


| Severity | Count | Issues                                                                       |
| -------- | ----- | ---------------------------------------------------------------------------- |
| CRITICAL | 3     | ACL duplicates, SQL bypass, no state machine                                 |
| HIGH     | 4     | Dispatch validation, auth bypass, lane key corruption, dispatch-load linkage |
| MEDIUM   | 1     | N+1 query performance                                                        |
| HYGIENE  | 4     | Duplicate code, button visibility, readonly field, date constraint           |


---

## Phase 1: Security Fixes (CRITICAL)

### 1.1 Remove Duplicate ACL Rows

**File:** `[plasticos_logistics/security/ir.model.access.csv](plasticos_logistics/security/ir.model.access.csv)`

**Problem:** Lines 9-11 grant `perm_unlink=1` to `base.group_user` for all three models, allowing any user to delete loads, rates, and dispatches.

**Fix:** Delete lines 9-11 (`access_load_all`, `access_rate_memory_all`, `access_dispatch_all`).

**Final file (8 lines):**

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

---

### 1.2 Wire State Machine into `_transition()`

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** `_transition()` (lines 216-227) accepts any state without validation. The `VALID_TRANSITIONS` map in `state_machine.py` exists but is not used.

**Fix:** Import and enforce `VALID_TRANSITIONS` in `_transition()`:

```python
def _transition(self, new_state):
    from odoo.addons.plasticos_logistics.services.state_machine import VALID_TRANSITIONS
    for rec in self:
        allowed = VALID_TRANSITIONS.get(rec.state, [])
        if new_state not in allowed:
            raise UserError(
                f"Cannot move load '{rec.name}' from '{rec.state}' to '{new_state}'. "
                f"Allowed: {allowed or ['none — terminal state']}."
            )
        # ... rest of existing code
```

**ALSO REQUIRED (reviewer addition):** Update `write()` allowed set to include additional fields:

```python
# In write(), update the allowed set:
allowed = {
    "bol_pickup_attached",
    "bol_delivery_attached",
    "state",
    "entered_state_at",
    "dispatched_at",
    "delivered_at",
    "cycle_time_hours",       # computed store=True triggers write
    "sla_breached",           # written by escalation cron
    "message_ids",            # chatter posts
    "message_follower_ids",   # chatter followers
}
```

**Why these additions:**

- `sla_breached` - The escalation cron (`check_escalations()`) writes this on dispatched/picked_up/delivered loads. Without it, cron fails with `UserError`.
- `message_ids` / `message_follower_ids` - `message_post()` in `_transition()` and bulk wizard write to chatter on locked records. Without them, chatter posts fail.

**Also update:** `[plasticos_logistics/services/state_machine.py](plasticos_logistics/services/state_machine.py)` to add `exception` as escape hatch:

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
    "closed": [],
    "exception": ["draft"],
}
```

---

### 1.3 Remove SQL Bypass from Bulk Wizard

**File:** `[plasticos_logistics/wizards/load_bulk_update_wizard.py](plasticos_logistics/wizards/load_bulk_update_wizard.py)`

**Problem:** Lines 96-103 use raw SQL to bypass `write()` guards, allowing illegal state transitions.

**Fix:** Replace SQL with `_transition()` call (which now enforces state machine).

**ALSO REQUIRED (reviewer addition):** Add `ValidationError` to imports:

```python
# BEFORE:
from odoo.exceptions import UserError
# AFTER:
from odoo.exceptions import UserError, ValidationError
```

**New method:**

```python
def action_update_status(self):
    self.ensure_one()
    if not self.load_ids:
        raise UserError(_("No loads selected."))

    errors = []
    updated_count = 0
    for load in self.load_ids:
        old_state = load.state
        try:
            load._transition(self.new_state)
            load.message_post(
                body=_(
                    "Status changed from <b>%(old)s</b> to <b>%(new)s</b><br/>"
                    "Reason: %(reason)s<br/>Updated by: %(user)s (Bulk Update)"
                ) % {"old": old_state, "new": self.new_state,
                     "reason": self.reason, "user": self.env.user.name},
                message_type="notification",
            )
            updated_count += 1
        except (UserError, ValidationError) as e:
            errors.append(f"{load.name}: {e.args[0]}")

    if errors:
        raise UserError(_("Some loads could not be updated:\n%s") % "\n".join(errors[:10]))

    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": _("Bulk Update Complete"),
            "message": _("%d load(s) updated to '%s'") % (updated_count, self.new_state),
            "type": "success",
            "sticky": False,
            "next": {"type": "ir.actions.act_window_close"},
        },
    }
```

---

## Phase 2: Validation Fixes (HIGH)

### 2.1 Add Dispatch Pre-Conditions

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** `action_dispatch()` (lines 204-208) only checks state, not required fields.

**Fix:** Add validation for carrier, locations, and dates:

```python
def action_dispatch(self):
    for rec in self:
        if rec.state not in ["scheduled", "rate_confirmed"]:
            raise UserError("Load must be in Scheduled or Rate Confirmed state to dispatch.")
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

---

### 2.2 Fix `action_confirm_ready()` Authentication

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** `action_confirm_ready(self, user_name)` (line 184) accepts arbitrary string instead of capturing logged-in user.

**Fix:** Remove parameter, use `self.env.user`:

```python
def action_confirm_ready(self):
    for rec in self:
        rec.ready_confirmed_by = self.env.user.name
        rec.ready_confirmed_at = fields.Datetime.now()
        rec._transition("ready_confirmed")
```

**Note:** Check if any view/button passes `user_name` argument and remove it.

---

### 2.3 Guard `_store_rate_memory()` Against Bad Lane Keys

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** `_lane_key()` (lines 242-244) produces `"False-False"` when `sale_order_id` is missing, poisoning rate memory.

**Fix:** Guard in `action_confirm_rate()`:

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
                    "Load %s: rate memory skipped — SO %s has no shipping/invoice partner.",
                    rec.id, rec.sale_order_id.name,
                )
```

---

### 2.4 Link `plasticos.dispatch` to `plasticos.load`

**File:** `[plasticos_logistics/models/dispatch.py](plasticos_logistics/models/dispatch.py)`

**Problem:** `plasticos.dispatch` has no FK to `plasticos.load`, creating parallel lifecycles that can diverge.

**Decision:** Option A selected - Add `load_id` field:

```python
load_id = fields.Many2one("plasticos.load", string="Load", ondelete="restrict")
```

**CRITICAL (reviewer note):** Do NOT add `required=True` to this field. The column is nullable by default, which is correct - existing `plasticos.dispatch` rows (if any) would fail migration if required. The `-u plasticos_logistics` deployment will add the column automatically.

---

## Phase 3: Performance Fix (MEDIUM)

### 3.1 Batch `_compute_transaction_id`

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** `_compute_transaction_id()` (lines 174-182) fires N queries for N records (N+1 problem).

**Fix:** Batch the lookup:

```python
@api.depends("id")
def _compute_transaction_id(self):
    txs = self.env[PLASTICOS_TRANSACTION].search([("load_id", "in", self.ids)])
    tx_map = {tx.load_id.id: tx.id for tx in txs}
    for rec in self:
        rec.transaction_id = tx_map.get(rec.id, False)
```

---

## Phase 4: Hygiene Items

### 4.1 Extract `new_correlation_id()` to Shared Module

**Files:**

- `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)` (lines 17-19)
- `[plasticos_logistics/models/dispatch.py](plasticos_logistics/models/dispatch.py)` (lines 10-12)

**Fix:** Move to `[plasticos_logistics/services/state_machine.py](plasticos_logistics/services/state_machine.py)`.

**CRITICAL (reviewer note):** Import `new_correlation_id` **inline inside method body**, NOT at file top level. This prevents circular import if `state_machine.py` ever imports from models:

```python
# In load.py _transition():
def _transition(self, new_state):
    from odoo.addons.plasticos_logistics.services.state_machine import (
        VALID_TRANSITIONS,
        new_correlation_id,
    )
    for rec in self:
        ...

# In dispatch.py action_transition():
def action_transition(self, new_state):
    from odoo.addons.plasticos_logistics.services.state_machine import (
        ALLOWED_TRANSITIONS,
        new_correlation_id,
    )
    for rec in self:
        ...
```

**Never import at module top level** - always inline inside the method.

---

### 4.2 Hide Email Buttons on Draft State

**File:** `[plasticos_logistics/views/load_views.xml](plasticos_logistics/views/load_views.xml)`

**Problem:** Email send buttons (lines 173-184) are always visible, even on draft loads with no data.

**Fix:** Add `invisible="state == 'draft'"` to all four buttons:

```xml
<button name="action_send_dispatch_packet" type="object" class="oe_stat_button" icon="fa-paper-plane"
        invisible="state == 'draft'">
    <span>Send Dispatch Packet</span>
</button>
```

---

### 4.3 Make `sla_breached` Readonly

**File:** `[plasticos_logistics/views/load_views.xml](plasticos_logistics/views/load_views.xml)`

**Problem:** `sla_breached` field (line 283) is editable by users; should only be set by cron.

**Fix:** Add `readonly="1"`:

```xml
<field name="sla_breached" readonly="1"/>
```

---

### 4.4 Add Date Constraint

**File:** `[plasticos_logistics/models/load.py](plasticos_logistics/models/load.py)`

**Problem:** No constraint prevents `delivery_datetime < pickup_datetime`.

**Fix:** Add constraint:

```python
@api.constrains("pickup_datetime", "delivery_datetime")
def _check_datetime_order(self):
    for rec in self:
        if rec.pickup_datetime and rec.delivery_datetime:
            if rec.delivery_datetime < rec.pickup_datetime:
                raise ValidationError(
                    f"Load {rec.name}: Delivery date/time cannot be before pickup date/time."
                )
```

---

### 4.5 Remove Committed PDF Files

**Files in repo root:**

- `plasticos_logistics/BOL - DELIVERY-59422.pdf`
- `plasticos_logistics/BOL - PICKUP-59422.pdf`
- `plasticos_logistics/DELIVERY ORDER-59422.pdf`

**Fix:**

```bash
git rm "plasticos_logistics/BOL - DELIVERY-59422.pdf" \
       "plasticos_logistics/BOL - PICKUP-59422.pdf" \
       "plasticos_logistics/DELIVERY ORDER-59422.pdf"
```

Add to `plasticos_logistics/.gitignore`:

```
*.pdf
```

---

## Execution Order (Dependency Chain)

The reviewer identified this strict dependency chain:

```
1.2 (state_machine.py) → must be done BEFORE →
1.3 (wizard uses _transition()) → must be done AFTER →
2.1 (action_dispatch uses _transition())
```

**Recommended single-pass execution order:**

1. `security/ir.model.access.csv` - delete 3 rows
2. `services/state_machine.py` - add exception state + move `new_correlation_id()`
3. `models/load.py` - all changes in one edit:
  - `write()` allowed set (add `cycle_time_hours`, `sla_breached`, `message_ids`, `message_follower_ids`)
  - `_transition()` validation + inline import of `VALID_TRANSITIONS` and `new_correlation_id`
  - `action_dispatch()` validation
  - `action_confirm_ready()` auth fix
  - `action_confirm_rate()` rate guard
  - `_compute_transaction_id()` batch
  - `@api.constrains` date check
  - Remove top-level `new_correlation_id()` function (now imported inline)
4. `wizards/load_bulk_update_wizard.py` - replace SQL, fix import
5. `models/dispatch.py` - add `load_id` FK (no `required=True`!), inline import `new_correlation_id` in method body
6. `views/load_views.xml` - button visibility + sla_breached readonly
7. `git rm` the three PDFs + add `.gitignore`

---

## Deployment

After all changes:

```bash
docker compose run --rm odoo -u plasticos_logistics
```

---

## File Summary


| File                                 | Changes                                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------------------------- |
| `security/ir.model.access.csv`       | Delete 3 duplicate ACL rows                                                              |
| `models/load.py`                     | State machine, dispatch validation, auth fix, rate guard, batch compute, date constraint |
| `services/state_machine.py`          | Add exception state, move `new_correlation_id()`                                         |
| `wizards/load_bulk_update_wizard.py` | Replace SQL with `_transition()`                                                         |
| `models/dispatch.py`                 | Add `load_id` FK (or remove model)                                                       |
| `views/load_views.xml`               | Button visibility, readonly `sla_breached`                                               |
| `.gitignore`                         | Add `*.pdf`                                                                              |
