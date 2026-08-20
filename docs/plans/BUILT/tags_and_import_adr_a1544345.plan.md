---
name: Tags and import ADR
overview: Create an ADR documenting the contact import configuration, and wire up automatic tag assignment during partner import so every imported contact gets properly tagged based on its CSV role.
todos:
  - id: adr-003
    content: Create ADR-003 documenting the contact import configuration, hierarchy, and field mappings
    status: completed
  - id: resolve-tags
    content: Add _resolve_tags method to partner_import_service.py that maps CSV roles to partner_tags.xml tag IDs
    status: completed
  - id: wire-tags
    content: Wire category_id into _import_corporate_row vals dict
    status: completed
  - id: expand-roles
    content: Expand _parse_role to detect Expense, Broker, Carrier, Processor in addition to Supplier/Customer
    status: completed
  - id: extra-tags
    content: (Optional) Add Partner Status and Payment Behavior tag categories to partner_tags.xml
    status: completed
isProject: false
---

# Contact Import ADR and Tag Strategy

## 1. Create ADR-003: Contact Import Configuration

New file: [docs/adr/ADR-003-contact-import-configuration.md](docs/adr/ADR-003-contact-import-configuration.md)

Document the import hierarchy, CSV-to-Odoo field mapping, and the mental model:

```
Corporate CSV → res.partner (is_company=True, parent_id=False)
Facility CSV  → res.partner children:
  - Inv/Remit → is_company=False, type=invoice
  - Location  → is_company=True, type=contact
  - Contact   → is_company=False, type=contact/invoice (AR/AP logic)
```

Include: CSV column mappings, role parsing, payment term assignment, deduplication strategy, the two-step import order (corporate first, then facilities).

## 2. Wire up tag assignment during import

In [plasticos_partner_import/models/partner_import_service.py](plasticos_partner_import/models/partner_import_service.py), the `_import_corporate_row` method needs to:

- Parse the `role` column (already done via `_parse_role`)
- Map roles to existing tags from [plasticos_base/data/partner_tags.xml](plasticos_base/data/partner_tags.xml):
  - CSV "Customer" → `plasticos_base.tag_buyer`
  - CSV "Supplier" → `plasticos_base.tag_supplier`
  - CSV "Expense" → `plasticos_base.tag_expense`
- Write `category_id` into the `vals` dict using `[(4, tag_id)]` for each matching tag

The `role` column supports comma-separated values (e.g. "Customer,Supplier,Expense"), so a single corporate can get multiple tags. The existing `_parse_role` only checks for supplier/customer — it needs to also detect Expense, Broker, Carrier, Processor.

### Role-to-tag mapping

- `Customer` → `tag_buyer` (Buyer)
- `Supplier` → `tag_supplier`
- `Expense` → `tag_expense`
- `Broker` → `tag_broker`
- `Carrier` → `tag_carrier`
- `Processor` → `tag_processor`

### Code change in `_import_corporate_row`

Add a `_resolve_tags` method that looks up tag IDs by XML ref and returns the `category_id` value. Add the result to `vals`:

```python
vals["category_id"] = self._resolve_tags(row.get("role", ""))
```

## 3. Consider additional tag categories

The current tags only cover partner roles. Additional categories worth adding to `partner_tags.xml`:

- **Partner Status**: Active, On Hold, Prospect, Inactive — useful for filtering the contact list
- **Payment Behavior**: Good Standing, Slow Pay, COD Only — useful for credit decisions

These would be manual-assignment tags (not auto-imported), but having them defined means users can start using them immediately.

## Summary of file changes

- **New**: `docs/adr/ADR-003-contact-import-configuration.md`
- **Edit**: `plasticos_partner_import/models/partner_import_service.py` — add `_resolve_tags`, wire into `_import_corporate_row`
- **Edit**: `plasticos_partner_import/models/partner_import_service.py` — expand `_parse_role` to detect all role keywords
- **Optional edit**: `plasticos_base/data/partner_tags.xml` — add Status and Payment tag categories
