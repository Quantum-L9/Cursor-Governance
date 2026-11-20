# Acceptance — ib-odoo-dashboard-command-centers

Each row needs PASS with evidence, or a named defect. Rows A01–A12 are runtime/test evidence (GATE-001/003/004). Rows S01–S10 are the operator's Staging walk (TASK-051, GATE-004). Code review alone never passes a row.

| ID | Criterion | Evidence | Gate |
|---|---|---|---|
| A01 | Every Admin urgency drill domain validates on its `res_model` and `search_count == KPI value` | TASK-010 parity tests | 001 |
| A02 | Admin menu opens the stored per-company KPI record, never an unsaved form | TASK-010 test | 001 |
| A03 | Rep view on the 2 closed / 3 open / 2×2 offers fixture: revenue 30k, pipeline 15k, deals_open 3 | TASK-011 test | 001 |
| A04 | Two-company fixture: each company's Admin KPIs count only its own records | TASK-013 test | 001 |
| A05 | Editing a closed deal does not move it between periods | TASK-012 test (after DEC-002) | 001 |
| A06 | Sales payout state/locked amount follow payout records across unpaid/confirmed/paid/cancelled | TASK-020 tests | 001 |
| A07 | Multi-load Track Load opens exactly that deal's loads; Open Deal respects ACL | TASK-021 tests | 001 |
| A08 | No actionable Admin KPI is display-only; unavailable renders distinct from 0 | TASK-031 tests + view inspection | 003 |
| A09 | Logistics counters reconcile with drills; company + rep isolation hold | TASK-032 tests | 003 |
| A10 | Sales counters reconcile for the logged-in rep, never include another rep | TASK-033 tests | 003 |
| A11 | Ops queues reconcile; sales rep cannot open Ops menu; no cross-company items | TASK-040 tests | 003 |
| A12 | Runtime tests green on the integrated Staging stack; EXPLAIN plans recorded for every rewritten KPI query | TASK-050 report | 004 |
| S01 | Logistics: each counter click lands on the matching filtered load list; breadcrumb returns to the dashboard | operator walk | 004 |
| S02 | Sales (as a rep): each counter click; Track Load on a multi-load deal; Open Deal | operator walk | 004 |
| S03 | Admin: every KPI clickable; numbers match a manual count of the drill list for 5 sampled KPIs | operator walk | 004 |
| S04 | Ops Manager: each queue click; approve/reject reachable from a Linda item | operator walk | 004 |
| S05 | Company switcher: Admin and Ops numbers change with the active companies | operator walk | 004 |
| S06 | Role isolation: rep cannot see Admin/Ops menus; Ops cannot see another company | operator walk | 004 |
| S07 | Mobile width: all four dashboards usable, no horizontal scroll on counters | operator walk | 004 |
| S08 | Refresh: Admin cron refresh and manual refresh show the same values | operator walk | 004 |
| S09 | Native Admin dashboard (if shipped) installs/upgrades from module data on Staging with no manual edits | operator walk | 004 |
| S10 | Production untouched by the campaign | branch check | 004 |
