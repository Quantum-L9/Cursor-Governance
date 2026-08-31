---
name: Evaluation readiness checklist
overview: "Before committing to staging for human testing, address several gaps: assign PlasticOS security groups to test users, add missing top-level menus for Transactions and Web Leads, add .gitkeep files to empty test dirs, and optionally seed demo records so testers don't face an empty system."
todos:
  - id: user-groups
    content: Add PlasticOS security groups (group_system_admin, group_sales_rep) to Igor and Arthur in res_users_admin.xml
    status: completed
  - id: transaction-menu
    content: Add a menuitem for Transactions under the PlasticOS root menu
    status: pending
  - id: web-leads-menu
    content: Add a menuitem for Web Leads (under PlasticOS or as top-level)
    status: pending
  - id: gitkeep
    content: Add .gitkeep to all 24 empty tests/ directories
    status: completed
  - id: demo-data
    content: (Optional) Add demo data with sample partners/intakes/offers for testers
    status: pending
isProject: false
---

# Evaluation Readiness Checklist

## Critical Issues

### 1. Test users lack PlasticOS-specific security groups

Both Igor and Arthur only have base Odoo groups. Your system defines custom roles in `plasticos_security_base` (Sales Rep, Logistics, Accounting, Operations Manager, System Admin). Without these, testers may not see PlasticOS menus or may hit access errors on custom models.

**Fix in** [plasticos_base/data/res_users_admin.xml](plasticos_base/data/res_users_admin.xml):
- **Igor** (superadmin): add `plasticos_security_base.group_system_admin` — this inherits Operations Manager, which inherits Logistics Ops, QC Manager, and Accounting Ops. Combined with `base.group_system`, he gets full access.
- **Arthur** (tester): add `plasticos_security_base.group_sales_rep` — this is the primary end-user role for the sales workflow (intakes, offers, transactions, partners). This lets him test the core flow without admin powers.

### 2. No menu for Transactions

`plasticos_transaction` defines `action_transaction` but has **no menuitem** linking to it. Testers cannot navigate to transactions from the main menu. Only reachable via smart buttons on other records.

**Fix**: Add a menuitem in [plasticos_transaction/views/transaction_views.xml](plasticos_transaction/views/transaction_views.xml) under the PlasticOS root menu.

### 3. No menu for Web Leads

`plasticos_web_leads` defines `action_web_lead` but has **no menuitem**. Only the config screen is accessible under Settings.

**Fix**: Add a menuitem in [plasticos_web_leads/views/web_lead_views.xml](plasticos_web_leads/views/web_lead_views.xml).

---

## Important (but not blocking)

### 4. Empty test directories need .gitkeep

Git doesn't track empty directories. After deleting all test files, the 24 empty `tests/` folders will vanish on the next clone/checkout. Add a `.gitkeep` to each if you want them preserved.

### 5. No demo/sample data

No module has demo data. Testers will log into a system with seed reference data (polymers, colors, forms, etc.) but **zero business records** — no partners, intakes, transactions, offers, or loads.

Options:
- **Manual**: Testers create records by hand (tests the full create flow but is slow)
- **Demo XML**: Add a `demo/` data file to key modules with sample partners, intakes, and offers so testers have something to click through immediately
- **Hybrid**: Start manual for now, add demo data later based on what testers need

### 6. Commission has no standalone UI

`plasticos_commission` defines models but has no views or menus. Commission rules are only accessible via a tab inside transaction forms. This may be fine if that's the intended UX, but testers won't discover it without guidance.

---

## Not actionable from your codebase

- **wkhtmltopdf warnings** during build: Odoo.sh platform issue (already discussed)
- **0 tests warning**: Odoo core behavior with empty test suite
