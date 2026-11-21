# Campaign: ib-odoo-dashboard-command-centers

**Status: definition complete, NOT EXECUTED.** Publishing this definition authorizes nothing else: activation, lane launch, IB-Odoo_19 changes, merges, deployment and live DeepSeek calls each need their own operator authorization (`CAMPAIGN_EXECUTION_BINDING.yaml` `activation_boundaries`).

Repair the IB-Odoo_19 dashboards' wrong numbers and broken drills first, then build four native-first role command centers (Logistics, Sales, Admin, Operations Manager) where every actionable KPI opens exactly the records it counts — one routed system in which every exception has exactly one accountable owner who can resolve it, and the wrong role cannot. Native Odoo AI Auto-Sort on DeepSeek `deepseek-flash` classifies, tags and routes incoming documents; nothing more.

## Versions

| Version | Change |
|---|---|
| 1.5.0 | Document AI Prompt Requirements v2.0 adopted as normative (DEC-019, `DOCUMENT_AI_PROMPT_REQUIREMENTS.md`): autonomy-first invariants and P1–P7 specialists; inventory rebuilt; taxonomy extended for the v2.0 distinctions with review signals (Evidence Gap, Duplicate Candidate, Includes Supporting Evidence); TASK-074 evaluation set and replay harness; GATE-006 now also requires measured benefit per specialist; acceptance A33–A37. |
| 1.4.0 | Operator decisions 2026-11-21 resolved (DEC-002, 004, 005, 011, 017, 018); DeepSeek contract corrected (Responses `reasoning.effort: none`, Files API bounded `expires_after` + delete, documents by `file_id` only); seven-prompt inventory with slice-1 Inbox activation and slice-2 loop-safety gate; external-data-processing gate (GATE-005); TASK-065 pending-evidence company isolation; TASK-073 destination prompts. |
| 1.3.0 | DeepSeek `deepseek-flash` through a provider adapter (Odoo 19 supports only OpenAI and Google natively); seven missing document types. |
| 1.2.0 | Native Odoo AI Auto-Sort for Logistics/Operations routing. |
| 1.1.0 | Role-specific exception routing addendum; official Odoo 19.0 sources. |
| 1.0.0 | Dashboard correctness and command centers. |

## Artifacts

| Artifact | Purpose |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Canonical campaign-source v2 (25 tasks, 19 decisions, 7 unknowns, 6 gates). `make campaign-check-input` → SUPPORTED. |
| `source-integrity-receipt.json` | Digest of the source. |
| `DOCUMENT_AI_PROMPT_REQUIREMENTS.md` | Document AI Prompt Requirements v2.0 — normative for every Auto-Sort prompt (DEC-019). |
| `AI_PROMPT_INVENTORY.yaml` | v2.0 mapping of P1–P7 to folders, tags, owners, tools, abilities, prohibitions, acceptance examples, evaluation targets and activation slices. No production prompt text. |
| `CURRENT_STATE.yaml` | Findings re-verified at Staging `c422140`; Enterprise, DeepSeek and official-docs evidence; operator decisions; residual execution prerequisites. |
| `CAMPAIGN_EXECUTION_BINDING.yaml` | Lanes, owned paths, shared-file serialization, publication (IB-Odoo_19 `make pr` → `Staging`), activation boundaries. |
| `ACCEPTANCE.md` | A01–A37 test evidence and S01–S17 operator checks. |
| `lanes/LANE-*.md` (A–E) | Compiled task prompts (MANIFEST → OBJECTIVE → NON-GOALS → ASSETS USED → WORKFLOW → CONSTRAINTS → DONE-CRITERIA → ACTIVATION). |

## Waves

| Wave | Tasks | Exit gate |
|---|---|---|
| W0 proofs | TASK-001 dashboard authoring path, TASK-002 Enterprise capability inventory | GATE-002 |
| W1 correctness, routing, AI foundation | TASK-010 drills, 011 rep aggregation, 013 company scope, 012 period date, 020 payout, 021 navigation, 060 exception routing, 061 Linda authority, 064 service-user verify refusal, 065 pending-evidence isolation, 068 DeepSeek adapter, 069 document types, 070 classification bridge + reasoned correction | GATE-001 |
| W2 command centers + Auto-Sort | TASK-071 P1 Inbox (slice 1), 074 evaluation harness, 073 P2–P7 specialists (slice 2, GATE-006), 040 Ops workbench, 032 Logistics Control Tower, then 031 Admin, 033 Sales | GATE-003, GATE-006 |
| W3 acceptance | TASK-072 accuracy + learning measurement (GATE-005 before real documents), 050 runtime + query plans, 051 operator Staging walk | GATE-004 |

## Decisions (all decided)

| ID | Decision |
|---|---|
| DEC-002 | `commission_earned_date` for closed-deal and earned-commission periods; never `write_date`; operational figures never labelled accounting revenue; aging and cash are separate KPIs with their own dates. |
| DEC-004 | `plasticos_ops_dashboard`: presentation/workflow integration only; no own queue, duplicate records, learning system or second AI engine. |
| DEC-005 | Ops read-only claims; role-restricted workbench menus; Admin KPI company isolation; pending evidence company isolation failing closed; ACL, multi-company and negative-access tests. |
| DEC-011 | Logistics decides routine operational Linda classes, but an approval never overrides a safety gate; still-failing or override-requiring cases go to Operations Manager. |
| DEC-016 | `deepseek-flash`, non-thinking; thinking only by operator decision after measured accuracy. Operator-reported Flash > GPT-4o is recorded as unverified. |
| DEC-017 | Minimal `plasticos_documents_ai` addon, no auto-install, explicit activation; bounded DeepSeek file retention and deletion; synthetic data until GATE-005. |
| DEC-018 | Seven-prompt inventory; Inbox first; specialists tag-only, activated per prompt after GATE-006 (loop safety + measured benefit). |
| DEC-019 | Document AI Prompt Requirements v2.0 normative: decide and route by best supported judgment; Needs Review only without a defensible primary type; Evidence Gap for evidence problems on identified documents; provisional targets ≥80 % auto-routed, ≥90 % primary-family accuracy, ≤20 % human intervention, 0 unauthorized actions, 0 correction overwrites. |
| Others | DEC-001, 003, 006–010, 012, 013 (OPT-C), 014 (OPT-A, extended for v2.0 types and review signals), 015 — see the source. |

## Residual execution prerequisites

See `CURRENT_STATE.yaml` `residual_execution_prerequisites` and the binding's `activation_boundaries`: operator activation; CTO mode (PR #1102); Enterprise runtime parity for install-smoke; TASK-002 settings exports; the synthetic DeepSeek probe; GATE-005; GATE-006; operator merges and the Staging walk.
