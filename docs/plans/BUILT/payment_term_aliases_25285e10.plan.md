---
name: Payment term aliases
overview: Stop the commercial-import payment-term anomalies by aliasing every ERP
  term name from this chat onto an installed Odoo term, and by seeding the one term
  that does not exist yet, 1/10 Net 30.
todos:
- id: seed-term
  content: Seed 1/10 Net 30 beside 2/10 Net 30 and bump plasticos_accounting
  status: completed
- id: alias-map
  content: Add payment_term_name() and use it in the partner and vendor-bill lookups
  status: completed
- id: prove
  content: Cover every accepted alias in a pure-Python test and bump the two changed
    modules
  status: completed
isProject: false
built: true
status: built
---

# Payment term aliases

One Odoo-free name map, used by both existing exact-name lookups. A name already equal to an installed term passes through. An unmapped name still reports the current anomaly and does not create a term.

## Alias decisions

- `N45` → `Net 45`
- `Due on receipt` → `Immediate Payment`
- `Prepayment` → `Prepaid`
- `Net 10` and `Net 14` → `15 Days`
- `Net 20` and `N 25` → `Net 30`
- `Wire Against Docs` → `Immediate Payment`
- `Wire On Documents` → `COD`
- `50% Prepayment` → `50% Down / 50% Net 30`
- `1% 10 Net 30` and `1% Net10` → `1/10 Net 30` (new)

`15 Days` and `Immediate Payment` are the standard Odoo terms. `Net 30`, `Net 45`, `Prepaid`, `COD`, and `50% Down / 50% Net 30` are the records in [plasticos_accounting/data/payment_terms.xml](plasticos_accounting/data/payment_terms.xml).

## New term

Add `1/10 Net 30` beside `2/10 Net 30` in that file: 1% discount if paid within 10 days, 100% due 30 days after the invoice date, `noupdate="1"`. Bump `plasticos_accounting` from `19.0.1.6.1` to `19.0.1.6.2`.

## Lookups

Add `payment_term_name()` next to the other ERP maps in [plasticos_partner_import/erp/mapping.py](plasticos_partner_import/erp/mapping.py).

- [plasticos_partner_import/models/erp_import_service.py](plasticos_partner_import/models/erp_import_service.py) `_resolve_payment_term` searches for the mapped name and writes `property_supplier_payment_term_id` only on a hit. A miss stays an anomaly and the company is still saved.
- [plasticos_transaction/models/native_document_import.py](plasticos_transaction/models/native_document_import.py) `_payment_term` searches for the mapped name. A dated bill whose term now matches follows the existing rule in `vendor_bill_due_terms`: Odoo computes the due date from the term, and the header `DueDate` is not written. An unmatched name still keeps `DueDate` and is reported once.

Update the `TermsCode` row in [plasticos_partner_import/erp/mapping_status.py](plasticos_partner_import/erp/mapping_status.py) so a mapped miss is no longer described as a bare name lookup.

Bump `plasticos_partner_import` and `plasticos_transaction` one patch each from the versions on the branch being changed.

## Proof

A pure-Python test lists every alias above and asserts an unknown name is unchanged. The existing worksheet test that `No Such Term` keeps `DueDate` and is reported once stays as it is.

## Out of scope

No Production replay, no backfill of the partners already imported, and no change to the worksheet, partner-child, or duplicate-order exceptions. Do not commit [docs/evidence/import-commercial-census.json](docs/evidence/import-commercial-census.json).

## Build evidence (auto)

- detected_at: `2026-11-09T22:04:11Z`
- conversation_id: `0c8ef6af-a368-4706-a895-687c72816b29`
- generation_id: `efeb0f65-4379-4825-b003-91c15bad7566`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/0c8ef6af-a368-4706-a895-687c72816b29/0c8ef6af-a368-4706-a895-687c72816b29.jsonl`
- todos at build time:
- `seed-term`: completed
- `alias-map`: completed
- `prove`: completed

