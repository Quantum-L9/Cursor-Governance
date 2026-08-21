---
name: Sale Order Partner Reassign
overview: Add unconditional sale order partner reassignment to pre_init_hook so _process_end() can delete partners without FK violations.
todos:
  - id: add-reassign
    content: Add unconditional sale order reassignment before the PLASTICOS_PARTNER_WIPE guard in pre_init_hook
    status: pending
isProject: false
---

# Sale Order Partner Reassignment in pre_init_hook

## Problem

Partner 2820 (and potentially others) in the base DB snapshot has sale orders. When `_process_end()` tries to delete partners whose XML IDs were removed from `plasticos_partner_import`, it fails with FK constraint violations because `sale_order.partner_id` still references them.

## Solution

Add an **unconditional** (not env-var guarded) UPDATE statement at the start of `pre_init_hook` that reassigns sale orders from partners-to-be-deleted to partner 3 (safe system partner).

## File to Modify

- [plasticos_partner_import/**init**.py](plasticos_partner_import/__init__.py)

## Change

Insert this block **before** the `PLASTICOS_PARTNER_WIPE` guard (around line 20), so it runs on every build:

```python
# Always reassign sale orders from partners this module will delete
# This prevents FK violations when _process_end() removes partner XML IDs
cr.execute("""
    UPDATE sale_order
    SET partner_id = 3, partner_invoice_id = 3, partner_shipping_id = 3
    WHERE partner_id IN (
        SELECT res_id FROM ir_model_data
        WHERE module = 'plasticos_partner_import'
        AND model = 'res.partner'
    )
""")
reassigned = cr.rowcount
if reassigned:
    _logger.info("Reassigned %d sale orders from partners to be deleted", reassigned)
```

## Why This Works

- Runs on EVERY build (not just when `PLASTICOS_PARTNER_WIPE=1`)
- Only affects sale orders referencing partners that this module owns (via `ir_model_data`)
- Partner 3 is a safe target (system partner, won't be deleted)
- `_process_end()` can then delete the orphaned partners without FK errors
