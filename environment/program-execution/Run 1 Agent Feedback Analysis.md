## PLAN: Run 2 pipeline — concurrent agents → SGD signal → memory distill

### Objective

Upgrade the **Cursor-Governance execution spine** so Run 2 of constellation / program-execution is faster, more autonomous, and less chat-dependent than Run 1 (`COMPLETE_WITH_BLOCKERS`, 29 gates still BLOCKED, high mid-wave compression loss).

Run 1 proved packs + campaign law can merge through W10, but agents invented collectors, dual merge authority, and soft-continued past missing LIVE proof. The CG libraries for concurrent Tasks → structured results → generated-data → memory **exist on `main` but are not wired as an automatic pipeline**. Run 2 must close that loop and bake Run 1’s P0 kill-list into pack/controller contracts.

**Success (falsifiable):**
1. Cold-start Run 2 can fan out a ready wave of ≤4 concurrent Cursor Tasks in one message per `DELEGATION_CONTRACT` + `parallel-nondependent`, with leases from `autonomy/`.
2. Every accepted subagent result becomes an SGD packet (`result_bridge` or `OutcomePublisher`) and reaches `DELIVERY_PENDING` with a receipt — **zero narrative-only PASS**.
3. Memory route delivers candidates to graphite/Graphiti under configured ingest (not silent outbox-only), and a defined **distill → synthesize → promote** curation step runs with receipts.
4. `SESSION_STATE` + single `next_action` + supersession receipts eliminate HANDOFF/PROGRAM_STATUS contradiction and chat-as-SSOT.
5. Unattended Wave-0 readiness score from debrief **58 → ≥85** on the same rubric (next_action, collectors, skill/DB, approvers, SESSION_STATE).
6. No claim of `LIVE_INTEGRATION_PASS` / production without proof_class match.

### Scope

**In:**
- Wire concurrent-agent → SGD → memory path on Cursor-Governance (`environment/agents/*`, `environment/program-execution/*`, `autonomy/`, `skills/l9-bounded-autonomy`, memory adapters).
- Land Phase 0 autonomy rail + LEARNED_LESSONS from `docs/l9-plan-kernel-pipeline` (not on `main` today).
- Align concurrency ceilings (`EXECUTION_CONCURRENCY_POLICY` 4/2 vs controller `global_max_workers: 1`).
- Pack/controller Run 2 prerequisites from debrief §§A–C (next_action, collectors, contracts, supersession, SESSION_STATE, proof_class, merge_authority) — as **inputs to pack author / CP**, wrap-called from CG where CG owns the rail.
- Durable `l9cp` / controller preflight (CP skill discarded; pin `L9CP_HOME` / repo-local bin).
- End-to-end golden: Task return → bridge → processor → memory candidate → distill/promote receipt.
- Keep in tree for evidence: Run 1 debrief + 3 GMP reports (docs ingest as supporting artifacts).

**Out:**
- Re-running full constellation W0–W10 in this plan (execution is a later GMP/campaign).
- Rewriting Claude Code Python scheduler (`environment/claude-code/autonomy/`).
- Restoring discarded `l9-coding-control-plane` skill under `~/.cursor/skills` as the durable home (prefer controller-local / `L9CP_HOME`).
- Dumping `WIP/` packs wholesale into git.
- Auto-merge / deploy / VPS without HITL (human merge remains).
- Collapsing Graphiti tunnel and graphite HTTPS into one client (ADR-0003 / MEMORY_TOPOLOGY — wrap both).
- Odoo enterprise/xmlsec live stack bring-up as a CG change (pack contract + separate TASK; not this spine PR).

### Pre-Validation (mandatory)

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| P0 Target bind | Write root = `Cursor-Governance` on `main` @ `21d4efb`; pack SSOT = Gate_SDK WIP constellation v2.2.0 + controller `/Users/ib-mac/l9-constellation-control`; do **not** mutate pack digests casually | Single authorized CG write root; pack read-only unless pack-author GMP |
| P1 Baseline inventory | Confirm on main: cursor-subagents, SGD under `environment/agents/generated-data/`, PES adapters/registry, `autonomy/`, `l9-bounded-autonomy`; confirm **missing**: Phase 0 rail, live CP skill, auto Task→SGD hook, graphite auto-distill after SGD | Gap list matches explore map |
| P2 Clean gate | Before any code GMP: `make pr-check` on changed files only; **no commit/push** | PASS |
| P3 Wiring / env | Graphiti health; graphite MCP `memory_health`; `L9_SGD_GRAPHITI_*` / `L9_MEMORY_*` env presence; controller `runtime/state.sqlite` vs empty `control.db` | Document PASS/FAIL/SKIPPED; FAIL is baseline not blocker to plan |
| P4 Run 1 bind | Treat `environment/program-execution/Run 1 Agent Feedback.md` as ARTIFACT_BACKED authority for friction/C-backlog | Debrief checklist §E complete |
| P5 Authority wrap/call | Load-map: DELEGATION_CONTRACT, SGD law, MEMORY_TOPOLOGY, ADR-0003, bounded-autonomy parallel/PR-poll, PES registry — **no forks** | Plan cites wrap/call only |

**Planning-only note:** P2–P3 not re-executed this turn; they **must** run before implementation GMPs. Unrelated untracked `WIP/` remains quarantined (do not claim whole-tree clean).

---

### TODO Plan

| # | Task | Files | Effort | Risk |
|---|------|-------|--------|------|
| T01 | Ingest Run 1 debrief + GMP-001 reports as governed evidence (no pipeline logic) | `environment/program-execution/Run 1 Agent Feedback.md`, `reports/GMP-Report-001-*.md` | S | L |
| T02 | Land Phase 0 autonomy rail + LEARNED_LESSONS from docs branch onto main | `environment/program-execution/core/**` (PHASE0_*, AUTONOMY_BRIDGE, `test_autonomy_rail.py`, LEARNED_LESSONS, related manifests) | M | M |
| T03 | Align concurrency: raise/pilot controller parallelism to match registry 4/2 **or** document PE control as serial and Task fan-out as the concurrency plane | `…/policy/parallelism.yaml`, `EXECUTION_CONCURRENCY_POLICY.yaml`, `skills/l9-bounded-autonomy/references/*`, doctrine-map | S | H |
| T04 | Campaign → ready-set → Cursor Task wave compiler (wrap PES readiness + autonomy leases; **no new scheduler**) | `environment/program-execution/integrations/cursor-task-tools/*`, `autonomy/adapters/cursor/adapter.py`, bounded-autonomy prompt templates | L | H |
| T05 | Mandatory result contract on every dispatched Cursor role | `CURSOR_SUBAGENT_ROLES.yaml`, result schema, `autonomy/adapters/cursor/adapter.py` (already partially on main) | M | M |
| T06 | Durable accept path: accepted result → `result_bridge.to_generated_data_packet` → `GeneratedDataProcessor` with receipts | `result_bridge.py`, `integrations/subagent-generated-data/outcome_publisher.py`, orchestration entry CLI/hook | L | H |
| T07 | Configure memory delivery off outbox-default for Run 2: graphite HTTPS primary + Graphiti Cursor path | `adapters/graphiti_memory.py`, `config/instantiation.example.yaml` → real instantiation, `MEMORY_TOPOLOGY.md` | M | H |
| T08 | Add **curation stage** after SGD memory delivery: `memory_distill` → `memory_synthesize_procedures` → gated `memory_promote` with learning_closure linkage | `runtime/learning_closure.py`, new thin orchestrator wrapping MCP (not reimplementing graphite), routes/memory.yaml | L | H |
| T09 | SESSION_STATE writer every task/wave join (compression resilience) | New schema under PES core or controller template; write from OutcomePublisher / wave join | M | M |
| T10 | Single `next_action` generator contract for pack author (CG validator + fixture); equality across HANDOFF/OPERATOR_INDEX/PROGRAM_STATUS | Pack-side files (Gate_SDK WIP) + optional CG `validate_*` helper | M | M |
| T11 | AUDIT/collector I/O schemas + promote Run 1 invented collectors into pack `scripts/collectors/` | Pack `collectors/AUDIT-*.schema.json`, scripts | L | M |
| T12 | Non-null `execution_contract` compile for W≤N; fail pack validation if null | Pack BUILDER_TASK_CARDS / contracts | L | M |
| T13 | Authority supersession + `merge_authority` on campaign packets; dual A1 draft_only + campaign merge becomes explicit | Pack activation + CP authorize schemas; CG `campaign-authorization.schema.json` | M | H |
| T14 | proof_class → allowed status transition table; forbid LIVE from dated pack evidence | CP gate transitions; pack evidence stamps | M | H |
| T15 | Durable controller/runtime pin: `L9CP_HOME`, single DB path (`runtime/state.sqlite`), healthcheck; discard skills.backup dependency | Controller INSTALL/RUNBOOK; CG docs only if bridge | M | H |
| T16 | Preflight doctor: Python, gh scopes, clean repos-root clones, archive SHA, skill/bin path, docker if live-qualify | Pack + CG `autonomy/validation/doctor.py` extension | M | M |
| T17 | Negative test suite from Run 1 workarounds (dirty audit tree, merge without campaign, LIVE from dated, null contract, missing l9cp, DB split) | `environment/agents/**/tests`, autonomy negative tests, pack CI | L | M |
| T18 | End-to-end golden “Run 2 spine”: 2 parallel recon Tasks → bridge → SGD → memory candidate → distill receipt (fixture campaign) | New integration test under `environment/agents/` or `program-execution/tests/` | L | H |
| T19 | Run 2 activation packet template: max_wave, publication ceiling, merge_mode, repos-root, memory ingest mode, concurrency plane | `skills/l9-bounded-autonomy/references/campaign-authorization-packet.md` + PES PHASE0_USER_CONFIG | M | M |
| T20 | Operator Runbook: what is Auto vs HITL for Run 2 (from debrief A3.2) | `environment/program-execution/core/.../RUNBOOK.md`, LEARNED_LESSONS | S | L |

### Depth

**Root cause (not symptoms):** Run 1 treated constellation CP + chat as the orchestration plane. CG already has the correct split — main launches/synthesizes; `autonomy/` leases; PES owns campaign gates when active; SGD owns packet→promotion→delivery; graphite owns distill/promote. Those planes were **under-connected**. Friction #1–#4 (next_action, collectors, null contracts, dual merge law) burned wall-clock; compression loss was HIGH because SESSION_STATE never existed.

**Target data flow for Run 2:**

```text
PHASE0 config + campaign packet
  → PES ready set ∩ autonomy leases
  → Main agent launches ≤4 Tasks (one message) per DELEGATION_CONTRACT
  → Structured result docs (schema-required)
  → result_bridge / OutcomePublisher
  → SGD: validate → harvest → classify → route → promotion_gate
  → memory route → candidate queue → configured ingest (graphite HTTPS / Graphiti)
  → curation: distill → synthesize_procedures → (HITL or policy) promote
  → SESSION_STATE + receipts update next_action
```

**Contracts preserved:**
- Subagents must not write Graphiti/memory directly (`DELEGATION_CONTRACT` excluded).
- Producers cannot self-promote (`routes/memory.yaml`, SGD law).
- Human merge only (`join-and-merge-gate`).
- Do not rewrite Claude scheduler from Cursor.
- Wrap/call existing authority — no forked pattern catalogs.

**Evidence sources:** Run 1 debrief §§0–E; explore map of main pipeline; `MEMORY_TOPOLOGY.md`; ADR-0003; pack SHA / program-lock digests in debrief (re-verify at Run 2 start).

**Unknowns (ask before filling as facts):**
1. Is Run 2 **constellation v2.3.0 re-run**, **program-execution-system v2**, or both sequenced?
2. Memory curation: auto-distill on every delivery, or batch at wave seal only?
3. Concurrency plane: raise PES `global_max_workers`, or keep PE serial and concurrency only via Cursor Tasks?

### Dependencies

```text
T01 (docs evidence)
T02 (Phase 0 rail) ──┬──► T03 (ceiling align) ──► T04 (wave→Task compiler) ──► T05 (result contract)
                     │                                    │
                     └──► T19 (activation packet) <───────┘
T06 (bridge→SGD) ◄── T04,T05
T07 (ingest config) ◄── T06
T08 (distill/promote) ◄── T07
T09 (SESSION_STATE) ◄── T06
T10–T15 (pack/CP P0) parallel after T02; hard-gate Run 2 start
T16 doctor ◄── T15
T17 negatives ◄── T06–T08,T13–T14
T18 e2e golden ◄── T06–T09,T17
T20 runbook ◄── T02,T19
```

Pack P0s (T10–T15) can proceed in parallel with CG wiring but **Run 2 campaign must not start** until T10, T12, T13, T15, T18 PASS (or explicit waiver receipt).

### Milestones

| Milestone | Outcome | Unlocks |
|-----------|---------|---------|
| M0 Evidence bind | Debrief + GMP reports in-repo; baseline gaps recorded | Honest planning / audits |
| M1 Autonomy rail on main | Phase 0 + LEARNED_LESSONS + tests green; ceilings coherent | Campaign packet for Run 2 |
| M2 Concurrent launch spine | Ready-set → leased Task wave → required result docs | Parallel agent utilization |
| M3 Signal closed loop | Result → SGD receipts → non-outbox memory candidates | Learning data flow |
| M4 Memory curation | Distill/synthesize/promote receipts tied to learning_closure | “Pushes into memory pipeline” DoD |
| M5 Pack/CP P0 kill-list | next_action, collectors, contracts, supersession, proof_class, L9CP_HOME | Unattended W0 ≥85 readiness |
| M6 Run 2 go / no-go | E2E golden + doctor + activation packet | Authorized Run 2 campaign |

### Checkpoints

| CP | After | Evidence required | No-go action |
|----|-------|-------------------|--------------|
| CP1 | M1 | `test_autonomy_rail` PASS; concurrency policy decision recorded | Halt T04 until ceilings explicit |
| CP2 | M2 | Fixture campaign launches ≥2 parallel Tasks; leases held; no lock overlap | Fix compiler; no Run 2 |
| CP3 | M3 | Packet IDs + processing receipts; memory destination ≠ silent empty outbox | Fix adapter env/commands |
| CP4 | M4 | Distill + synthesize receipts; promote only with policy/HITL evidence | Keep candidates queued; no fake promote |
| CP5 | M5 | Validators: next_action equality; null execution_contract count=0 for W≤N; merge without campaign refuses; LIVE from dated refuses | Pack author rework |
| CP6 | M6 | T18 golden PASS; doctor PASS; supersession chain ready; human admits Run 2 packet | Do not start Run 2 |

### Checklist

- [ ] T01 docs ingested (or explicitly deferred with path kept untracked — currently kept in tree)
- [ ] T02 Phase 0 rail on main + tests
- [ ] T03 concurrency plane decision written into PHASE0 / doctrine
- [ ] T04–T05 Task wave + result contracts
- [ ] T06–T08 SGD + memory + curation closed loop
- [ ] T09 SESSION_STATE rolling artifact
- [ ] T10–T15 pack/CP P0s addressed or waived with receipts
- [ ] T16–T18 doctor + negatives + e2e golden
- [ ] T19–T20 Run 2 activation packet + Auto/HITL runbook
- [ ] Pre-Validation recorded at GMP start
- [ ] Final Validation (`make pr-check`) PASS per CG PR
- [ ] No commit/push unless explicitly requested
- [ ] No `LIVE_INTEGRATION_PASS` without proof_class

### Risks

| Risk | Mitigation |
|------|------------|
| Rebuilding a second scheduler | Wrap PES ready-set + Cursor Task tools + autonomy leases only |
| Outbox mistaken for memory success | Delivery receipts must show ingest command exit or graphite write id |
| Distill auto-spam / wrong namespace | Batch at wave seal; namespace from PHASE0; HITL for promote |
| Concurrency ceiling thrash (1 vs 4) | Explicit PHASE0 `concurrency_plane` enum |
| Pack mutation during run (PACK_028) | Pack immutability + write only to controller |
| Authority supersession informal again | Require WAVE_PROMOTION_RECEIPT before ceiling raise |
| CP skill absence | `L9CP_HOME` / controller-local bin; doctor fails closed |
| Collapsing Graphiti vs graphite | MEMORY_TOPOLOGY + ADR-0003 wrap/call |
| Scope explosion into full constellation rewrite | M5 pack P0 only; full v2.3.0 is pack-author track |

### Estimate

**Total:** ~3–5 GMPs on CG spine (M1–M4/M6), plus 1–2 pack/CP GMPs (M5), before Run 2 launch
**GMPs:** 4–7 depending on pack-author ownership
**Wall-clock to Run 2 ready:** order-of-magnitude days if P0 pack work is parallelized; not a same-session campaign start

### Final Validation (mandatory)

| Check | Command | Pass criteria |
|-------|---------|---------------|
| V1 Plan completeness | Review vs plan-workflow template | Pre/Final validation, milestones, checkpoints, checklist, scoped TODOs present |
| V2 Per-GMP scanners | `make pr-check` after each CG code GMP | PASS; changed-files; no commit/push unless asked |
| V3 Spine e2e | T18 golden | Concurrent Tasks → SGD → memory candidate → distill receipt |
| V4 Doctor | T16 | l9cp/DB/SHA/repos-root/memory env PASS or waived |
| V5 Honesty | Status claims | Only PASS/FAIL/SKIPPED/N/A/Unknown for checks actually run |
| V6 Run 2 admit | Human + activation packet | Supersession + merge_mode + concurrency_plane + memory mode bound |

---

### Recommend (l9-ynp stance)

**Do not skip to PR cleanup or Run 2 launch.** Next highest leverage:

1. Confirm the three Unknowns (Run 2 target product; distill timing; concurrency plane).
2. Chain **GMP-0**: T01 evidence commit (optional) + T02 Phase 0 rail land on main — unlocks everything else.
3. Then **GMP-1**: T03–T06 concurrent launch + SGD closed loop.
4. Then **GMP-2**: T07–T09 memory ingest + curation + SESSION_STATE.
5. Pack-author track in parallel: T10–T15 from debrief Section C.

Say which Run 2 target (constellation / PES / both) and concurrency plane preference, and we lock those into PHASE0 before any implementation GMP.
