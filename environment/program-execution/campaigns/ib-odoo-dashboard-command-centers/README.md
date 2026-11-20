# Campaign: ib-odoo-dashboard-command-centers

Repair the IB-Odoo_19 dashboards' wrong numbers and broken drills first, then build four native-first role command centers (Logistics, Sales, Admin, Operations Manager) where every actionable KPI opens exactly the records it counts — operating as one routed system in which every exception has exactly one accountable owner who can resolve it, and the wrong role cannot.

**v1.2.0** adds native Odoo AI Auto-Sort for Logistics/Operations routing (operator second addendum 2026-11-20; Enterprise internals in `CURRENT_STATE.yaml` `enterprise_ai_evidence`). **v1.1.0** incorporated the operator's Role-Specific Exception Routing Addendum (2026-11-20), re-verified against Staging `c422140` (`CURRENT_STATE.yaml` N-004..N-011), and the official Odoo 19.0 dashboard, Documents AI and activity sources (EVID-007).

| Artifact | Purpose |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Canonical campaign-source v2. `make campaign-check-input` → SUPPORTED. |
| `source-integrity-receipt.json` | Digest of the source. |
| `CURRENT_STATE.yaml` | Findings F-001..F-010 re-verified at Staging `c422140`, plus N-001..N-003. |
| `CAMPAIGN_EXECUTION_BINDING.yaml` | Swarm lanes, paths, publication (IB-Odoo_19 `make pr` → `Staging`), launch preconditions. |
| `ACCEPTANCE.md` | Done-criteria matrix: A01–A12 test evidence, S01–S10 operator Staging walk. |
| `lanes/LANE-*.md` (A–E) | Compiled task prompts (MANIFEST → OBJECTIVE → NON-GOALS → ASSETS USED → WORKFLOW → CONSTRAINTS → DONE-CRITERIA → ACTIVATION). |

## Waves

| Wave | Tasks | Exit gate |
|---|---|---|
| W0 proofs | TASK-001 dashboard authoring path, TASK-002 Enterprise capability inventory | GATE-002 |
| W1 correctness + routing | TASK-010 drills, 011 rep aggregation, 013 company scope, 012 period date, 020 payout, 021 navigation, 060 exception routing, 061 Linda authority, 064 service-user verify refusal, 070 classification bridge + reasoned correction | GATE-001 |
| W2 command centers | TASK-071 native AI Auto-Sort on existing folders, TASK-040 Ops AI & Transaction Review Workbench, 032 Logistics Live Control Tower, then 031 Admin Business Health, 033 Sales | GATE-003 |
| W3 acceptance | TASK-072 AI learning verification + prompt-revision loop, TASK-050 runtime + query plans, 051 operator Staging walk | GATE-004 |

## Operator decisions needed

| ID | Question | Recommendation | Blocks |
|---|---|---|---|
| DEC-002 | Business date for closed-deal periods | `commission_earned_date` | TASK-012 |
| DEC-004 | Ops Manager host | new module `plasticos_ops_dashboard` | TASK-040 |
| DEC-005 | Security: Ops claims read, Ops menu groups, admin.kpi company rule, company isolation for pending document rows | approve all four | TASK-040 |
| DEC-011 | Which Linda command classes Logistics Ops may decide | execution-timing classes to Logistics; fact corrections, VGM, tare, regulatory parties, unit mismatch, refusal retry stay Ops | TASK-061 |
| DEC-014 | Add Purchase Order, Packing List, Receiving Report types (native tag + doc_type; legacy PO tag) | add them; until then those documents fall back to Needs Review | none |
| DEC-016 | Approve OpenAI gpt-4.1 via Odoo AI (document content leaves Odoo), key set in Odoo settings only, host glue module `plasticos_documents_ai` | approve, Staging first | TASK-071, TASK-072 |

Everything else is decided in the source (DEC-001, 003, 006–010, 012, 013 OPT-C, 015) or proven by TASK-001 and TASK-002.

## Launch preconditions

1. CTO mode ACTIVE (the identity-attribution bundle is stale; a coding agent is regenerating it).
2. Operator go. Production is never touched; merges are operator-only.

**Not started.** No Odoo branch, no `pec` bootstrap.
