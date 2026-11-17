---
name: Blank GL vendor bills
overview: Write the 615 blank-account vendor bills as normal material bills. A negative
  amount is a vendor credit. No account-code list and no holding account.
todos:
- id: write-blank-gl-bills
  content: In _quarantine_outside_universe, write a blank-GL payable with an imported
    vendor and a non-zero amount through the same purchase-bill writer as a material
    bill.
  status: completed
- id: update-test
  content: 'Update the outside-universe test: blank GL becomes a bill, a negative
    amount becomes a credit, material-code rows stay quarantined.'
  status: completed
- id: bump-version
  content: Bump plasticos_transaction to 19.0.2.3.63.
  status: completed
isProject: false
built: true
status: built
---

# Blank-account vendor bills

The 615 rows are payables whose deal number has no worksheet lines and whose account code is empty. Each already has a vendor and an amount. They are dropped in [`_quarantine_outside_universe`](plasticos_transaction/models/native_document_import.py) before any bill is written.

## Change

In that function only, when the account code is blank, the vendor was imported, the amount is not zero, and a purchase journal exists:

- Write one draft vendor bill through the same writer a material bill uses, identity `legacy_erp_ininv_<PayableID>`, on Material Cost (`50100`).
- Positive amount: vendor bill. Negative amount: vendor credit (`in_refund`), line price is the absolute amount.
- Keep the odd deal number (such as `52948INV`) on the bill reference. Do not create a worksheet and do not attach it to a deal.
- Count the row as billed so it leaves the quarantine.

Leave every other row on the current path: material and freight codes, `50300`, `50600`, a blank deal number, a missing vendor, and a blank account code on a real worksheet.

A second run finds the same bill and writes nothing.

## Proof

Update the outside-universe case in [`plasticos_transaction/tests/test_erp_worksheet_import.py`](plasticos_transaction/tests/test_erp_worksheet_import.py): the blank-account row with a vendor becomes a draft bill, and a negative amount becomes a vendor credit. The material-code row with no deal number stays quarantined.

Bump [`plasticos_transaction/__manifest__.py`](plasticos_transaction/__manifest__.py) to `19.0.2.3.63`. No schema change.

## Build evidence (auto)

- detected_at: `2026-11-09T22:21:50Z`
- conversation_id: `598ec124-81a2-45f0-ad52-5d6561a9c38e`
- generation_id: `daa0ce09-a937-47e6-b3a0-1bb5adf08ad2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/598ec124-81a2-45f0-ad52-5d6561a9c38e/598ec124-81a2-45f0-ad52-5d6561a9c38e.jsonl`
- todos at build time:
- `write-blank-gl-bills`: completed
- `update-test`: completed
- `bump-version`: completed

