---
name: Partner Resolution Strategy
overview: Corrected partner resolution strategy for cieTrade transaction import. CSV has NO partner columns. Buyer partially resolvable from SPo prefix (TNT = buyer name). Supplier NOT resolvable from CSV -- all 35 transactions need post-import bulk assign for supplier_id.
todos:
  - id: write-guard-bypass
    content: "GMP-TXI-02: Add import_mode bypass to _validate_state_transition and _validate_write_immutability in transaction.py write()"
    status: pending
  - id: wizard-fix
    content: "GMP-TXI-01: Add import_mode context, buyer_id from SPo prefix, weight fields, commission_locked to wizard action_import()"
    status: pending
  - id: service-fix
    content: "GMP-TXI-04: Add historical totals, weight fields, buyer_id from SPo prefix, import_mode to service _import_transaction()"
    status: pending
  - id: view-improvement
    content: "GMP-TXI-03 (low priority): Add historical totals to main form area with conditional visibility"
    status: pending
  - id: bulk-assign-post-import
    content: "Post-import: Use bulk assign wizard with import_mode to set supplier_id on all 35 transactions, buyer_id on unresolved ones"
    status: pending
isProject: false
---

# Partner Resolution Strategy for cieTrade Transaction Import

## v2 -- Corrected after feedback review (2026-03-16)

---

## Data Reality

The cieTrade `WksDetail.csv` has 104 columns but **ZERO partner name or partner ID columns**.

### Columns examined

- `DesignatedCpID` -- empty in ALL 50 rows
- `ForeignID` -- literal "NULL" in all rows
- `DesignatedSONO` -- empty in all rows
- `SPO_ID` / `PPO_ID` -- cieTrade internal PO record IDs (NOT partner refs)
- `SPo` (Sale PO) -- 11 unique values, 2 prefix patterns: `TNT`* and `UCS`*
- `PPo` (Purchase PO) -- 35 unique values, 2 prefix patterns: `UCS*` and `9930`

### Igor's clarifications

- **TNT** = a customer/buyer company name
- **9930** = looks like a PO/SO number, not a partner identifier
- **UCS** = ref 1433 in corporate partner CSV (role: Customer,Supplier)

### Column-to-role mapping

- `SPo` (Sale PO) = PO the **buyer** gave to UCS --> prefix may identify buyer
- `PPo` (Purchase PO) = PO UCS issued to **supplier** --> prefix is UCS's own numbering, does NOT identify the supplier

### Conclusion

- **Buyer resolution**: PARTIALLY possible from `SPo` prefix. `TNT`* --> search `res.partner` by name "TNT". `UCS`* --> ref 1433.
- **Supplier resolution**: NOT possible from this CSV. All `PPo` values are UCS's own PO numbers (`UCS9`*) or a standalone number (`9930`). The supplier identity is not encoded anywhere in the file.

---

## Verified Model Fields

`supplier_id` and `buyer_id` confirmed on `plasticos.transaction` (lines 31-44 of `transaction.py`):

```
supplier_id = fields.Many2one("res.partner", domain=[("supplier_rank", ">", 0)])
buyer_id = fields.Many2one("res.partner", domain=[("customer_rank", ">", 0)])
```

`create()` (line 759) does NOT call `_validate_state_transition` or `_validate_write_immutability` -- those guards are exclusively in `write()` (line 769). So `create({"state": "closed"})` works without `import_mode`. However, `import_mode=True` should still be added defensively for any downstream `write()` triggered by stored computed field recomputes.

---

## Strategy: Two Phases

### Phase 1 -- Automated (during import)

Add to both wizard and service:

**Buyer resolution from SPo prefix:**

```python
def _resolve_buyer_from_spo(self, lines):
    """Extract buyer from SPo prefix. Returns partner ID or False."""
    for line in lines:
        spo = (line.get("SPo") or "").strip()
        if not spo:
            continue
        match = re.match(r"^([A-Z]+)", spo)
        if not match:
            continue
        prefix = match.group(1)
        if prefix == "UCS":
            continue  # UCS is self -- skip
        # TNT is a buyer name per Igor
        partner = self.env["res.partner"].search(
            [("name", "ilike", prefix), ("is_company", "=", True), ("customer_rank", ">", 0)],
            limit=1,
        )
        if partner:
            return partner.id
    return False
```

**No supplier resolution** -- the CSV does not encode supplier identity. Leave `supplier_id` empty.

**Additional fields to populate in `tx_vals`:**

- `buyer_id` -- from SPo prefix resolution above
- `supplier_weight` -- sum of `SWeight` (same as `expected_weight`)
- `buyer_weight` -- sum of `PWeight`
- `commission_locked: True` -- required for closed-state write guard compatibility
- `commission_locked_amount: 0.0`

**Context:** Both wizard and service must use `.with_context(import_mode=True, tracking_disable=True)` on `create()`.

### Phase 2 -- Manual (post-import)

After import completes:

1. Filter: transactions where `supplier_id` is empty (all 35) and/or `buyer_id` is empty (those where TNT lookup failed)
2. Use existing `TransactionBulkAssignWizard` to assign partners
3. The bulk assign wizard calls `tx.write()` which hits `_validate_write_immutability` on closed records -- so GMP-TXI-02 (import_mode bypass) MUST be done first
4. Bulk assign wizard needs to use `.with_context(import_mode=True)` when writing to closed transactions

---

## Revised GMP Execution Plan

### GMP-TXI-02 -- Write guard bypass (DO FIRST)

**File:** [plasticos_transaction/models/transaction.py](plasticos_transaction/models/transaction.py)

Add `import_mode` escape hatch to both guard methods:

```python
def _validate_state_transition(self, rec, vals):
    if self.env.context.get("import_mode"):
        return
    # ... existing logic ...

def _validate_write_immutability(self, rec, vals):
    if self.env.context.get("import_mode"):
        return
    # ... existing logic ...
```

Requires: `docker compose run --rm odoo -u plasticos_transaction`

### GMP-TXI-01 -- Wizard fixes (ADDITIVE only)

**File:** [plasticos_transaction/wizards/transaction_import_wizard.py](plasticos_transaction/wizards/transaction_import_wizard.py)

Changes to `action_import()`:

1. ADD `_resolve_buyer_from_spo()` method (new, no existing method to remove)
2. ADD `buyer_id`, `supplier_weight`, `buyer_weight`, `commission_locked`, `commission_locked_amount` to `tx_vals`
3. ADD `.with_context(import_mode=True, tracking_disable=True)` to `Transaction.create()` call

No restart needed (TransientModel).

### GMP-TXI-04 -- Service fixes (ADDITIVE only)

**File:** [plasticos_transaction/models/transaction_import_service.py](plasticos_transaction/models/transaction_import_service.py)

1. ADD `_resolve_buyer_from_spo()` method
2. ADD `historical_sale_total`, `historical_purchase_total`, `expected_weight`, `actual_weight`, `supplier_weight`, `buyer_weight`, `buyer_id`, `commission_locked`, `commission_locked_amount` to `tx_vals` (service currently sets only `name` and `state`)
3. Note: `historical_sale_total` is a computed field from `line_ids` so setting it in `tx_vals` is redundant but harmless -- it gets overwritten when lines are created

No restart needed (AbstractModel).

### GMP-TXI-03 -- View improvement (LOW PRIORITY)

**File:** [plasticos_transaction/views/transaction_views.xml](plasticos_transaction/views/transaction_views.xml)

Historical totals are already visible in the "Historical Lines" tab (line 184-207). Optional improvement: add a conditional group in the main form showing historical totals when `customer_invoice_id` is empty (no live invoice data).

Requires: `docker compose run --rm odoo -u plasticos_transaction`

### GMP-TXI-05 -- DROPPED

The static mapping file approach is unnecessary. TNT is a buyer name searchable via `ilike`. UCS is ref 1433. No mapping file needed -- inline logic in `_resolve_buyer_from_spo()` is sufficient.

---

## Execution Order

```
GMP-TXI-02 (write guards)     --> -u plasticos_transaction
GMP-TXI-01 (wizard fixes)     --> no restart
GMP-TXI-04 (service fixes)    --> no restart
GMP-TXI-03 (view, optional)   --> -u plasticos_transaction
Post-import: bulk assign       --> manual via UI
```

---

## What NOT to Do

- Do NOT add fuzzy name matching -- there are no names to match against (except TNT which is exact)
- Do NOT resolve `SPO_ID`/`PPO_ID` as partner refs -- they are cieTrade PO record IDs
- Do NOT fabricate `BuyerName`/`SellerName` column references -- those columns don't exist
- Do NOT attempt supplier resolution from `PPo` -- the prefix is UCS's own numbering
