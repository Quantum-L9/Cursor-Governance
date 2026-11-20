# Campaign: ib-odoo-dashboard-command-centers

Repair the IB-Odoo_19 dashboards' wrong numbers and broken drills first, then build four native-first role command centers (Logistics, Sales, Admin, Operations Manager) where every actionable KPI opens exactly the records it counts.

| Artifact | Purpose |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Canonical campaign-source v2. `make campaign-check-input` → SUPPORTED. |
| `source-integrity-receipt.json` | Digest of the source. |
| `CURRENT_STATE.yaml` | Findings F-001..F-010 re-verified at Staging `c422140`, plus N-001..N-003. |
| `CAMPAIGN_EXECUTION_BINDING.yaml` | Swarm lanes, paths, publication (IB-Odoo_19 `make pr` → `Staging`), launch preconditions. |
| `ACCEPTANCE.md` | Done-criteria matrix: A01–A12 test evidence, S01–S10 operator Staging walk. |
| `lanes/LANE-*.md` | Compiled task prompts (MANIFEST → OBJECTIVE → NON-GOALS → ASSETS USED → WORKFLOW → CONSTRAINTS → DONE-CRITERIA → ACTIVATION). |

## Waves

| Wave | Tasks | Exit gate |
|---|---|---|
| W0 spike | TASK-001 native dashboard as module data | GATE-002 |
| W1 correctness | TASK-010 drills, 011 rep aggregation, 013 company scope, 012 period date, 020 payout, 021 navigation | GATE-001 |
| W2 command centers | TASK-031 Admin, 032 Logistics, 033 Sales, 040 Ops Manager | GATE-003 |
| W3 acceptance | TASK-050 runtime + query plans, 051 operator Staging walk | GATE-004 |

## Operator decisions needed

| ID | Question | Recommendation | Blocks |
|---|---|---|---|
| DEC-002 | Business date for closed-deal periods | `commission_earned_date` | TASK-012 |
| DEC-004 | Ops Manager host | new module `plasticos_ops_dashboard` | TASK-040 |
| DEC-005 | Security: Ops claims read, Ops menu groups, admin.kpi company rule | approve all three | TASK-040 |

Everything else is decided in the source (DEC-001, 003, 006–009) or proven by the TASK-001 spike.

## Launch preconditions

1. CTO mode ACTIVE (the identity-attribution bundle is stale; a coding agent is regenerating it).
2. Operator go. Production is never touched; merges are operator-only.

**Not started.** No Odoo branch, no `pec` bootstrap.
