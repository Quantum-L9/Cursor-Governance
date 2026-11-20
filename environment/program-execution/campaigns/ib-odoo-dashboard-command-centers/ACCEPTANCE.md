# Acceptance — ib-odoo-dashboard-command-centers

Each row needs PASS with evidence, or a named defect. Rows A01–A26 are runtime/test evidence (GATE-001/003/004). Rows S01–S15 are the operator's Staging walk (TASK-051, GATE-004). Code review alone never passes a row.

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
| A13 | Confidently attributed BOL and scale-ticket exceptions create exactly one Logistics activity with one-click navigation to the exact load and original | TASK-060, TASK-032 tests | 001/003 |
| A14 | Ambiguous classification goes to Operations Manager even when one candidate is logistics-related | TASK-060 test | 001 |
| A15 | One combined or multi-load original keeps one file and separately attributable obligations, each with its own owner | TASK-060 test | 001 |
| A16 | A digitized vendor bill with mismatched amounts appears in the Operations inbox and stays unposted until the existing guard is satisfied | TASK-040 test | 003 |
| A17 | Linda decisions succeed only for the role authorized for that exact (command, edge_case); every other role, Linda and a plain Logistics user fail at the server | TASK-061 tests | 001 |
| A18 | Repeated processing, reassignment, resolution and reload never duplicate, lose or wrongly close an exception activity | TASK-060, TASK-061 tests | 001 |
| A19 | Linda and the cron user cannot verify business evidence; a human Documents User on an exact accepted scope can | TASK-064 tests | 001 |
| A20 | Admin drills from a department bottleneck (funnel stage, exceptions by owner) to the correct source records and accountable owner | TASK-031 tests | 003 |
| A21 | Auto-Sort (mocked model): BOL → Bills of Lading + BOL tag + one Logistics activity; scale ticket → Scale Tickets; ambiguous or contradictory → stays in Inbox + Needs Review + one Operations activity | TASK-071 tests | 003 |
| A22 | The Auto-Sort rule carries only move-in-folder and add-tags; no bill/invoice creation, activity or code tool | TASK-071 test + inspection | 003 |
| A23 | A single type tag reaches business evidence (doc_type + one sync); conflicting type tags give Needs Review and no doc_type | TASK-070 tests | 001 |
| A24 | A human correction keeps the original file, records classification, decision and required reason, is never overwritten by a later tag, re-syncs evidence and re-routes the activity | TASK-070 tests | 001 |
| A25 | Verified cannot be added by Auto-Sort or any write outside verification | TASK-070 test | 001 |
| A26 | Invoice learning measured (edits per bill across repeats) and shipping confusion counts reported; any prompt revision shows before/after replay accuracy | TASK-072 report | 004 |
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
| S11 | Document-review path end to end: a real BOL exception and a real ambiguous document reach the right inbox, are resolved by the right person, and the wrong person is refused | operator walk | 004 |
| S12 | Linda-resolution path end to end for one Logistics-authorized class and one Operations-only class | operator walk | 004 |
| S13 | Auto-Sort runs only with move/tag tools; no bill auto-post or new external sender was activated (compare TASK-002 inventory) | operator walk | 004 |
| S14 | Staging: upload one real BOL, one scale ticket, one packing list and one ambiguous document into Inbox; each lands with the right owner; correct one with a reason and see it persist on the original | operator walk | 004 |
| S15 | Staging repeat-upload protocol for invoice learning (3 vendors × 3 bills) recorded | operator walk | 004 |
