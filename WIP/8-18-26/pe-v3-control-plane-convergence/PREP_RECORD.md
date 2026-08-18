# pe-v3-control-plane-convergence — Campaign Prep Record

**Prepared:** 2026-08-18 by campaign_execution_agent (session ffc6852f, read-only prep)
**Status:** PREP COMPLETE — NOT admitted, NOT executed. Awaiting operator go + claude-code-env-contract-v1 publication.

## 1. Source documents

| Doc | Role |
|---|---|
| `WIP/8-18-26/PE PRogram Executio .md` | Microscope verdict defining this follow-on campaign (§1–§50) |
| `WIP/PROGRAM EXECUTION PIPELINE/PE-PE 1.md` | v3 architecture design (S0–S8, task decomposition, invariant registry) |
| `WIP/8-18-26/PE Claude Code Environment.md` | Operator directive: park PE until Claude env contract fixed (now in execution by session website-bot-70) |
| `environment/program-execution/core/shared/schemas/campaign-source.schema.json` | Authoring schema (v2 — the campaign must run on the pinned v2 plane) |
| `environment/program-execution/campaigns/pe-v3-hardening/CAMPAIGN_SOURCE.yaml` | Structural exemplar (immutable forensic artifact — NOT rewritten, per directive) |

## 2. Artifacts in this directory

| File | Purpose | Validated |
|---|---|---|
| `CAMPAIGN_SOURCE.yaml` | Authoritative campaign definition (39 tasks, 9 waves, 10 gates, 38 dependency edges, 29 invariants) | YAML parse + schema keys + full cross-reference check: **PASS** (no stubs) |
| `source-integrity-receipt.json` | sha256 receipt over the source (digest `f11e155d…`) | written by prep |
| `INTENT.yaml` | Operator front-door record (wave-level seed) | — |

## 3. Pins (from the microscope verdict — not invented)

- **Implementation baseline:** `7517f377ab202bf39a351f634eacb9860bc414e0` (verified present in checkout; campaign pinned to it).
- **Historical v2 characterization baseline:** `0db3fedf697b263a3b8bd9ea8ce40113f999b67d` (pe-v3-hardening S0 artifact; inherited as EVID-003 input, never rewritten).
- **Target repo:** `Quantum-L9/Cursor-Governance` (verified remote on the checkout).
- **Two planes:** A = pinned immutable v2 orchestrator checkout (TARGET-002); B = editable implementation (TARGET-001). A orchestrates; B never self-modifies A.

## 4. Structure (faithful to source docs)

| Wave | Tasks | Exit gate |
|---|---|---|
| C0 | TASK-001..003 — baseline freeze + C0-A runner disarm, C0-B stacked make-pr publishing, C0-C Autonomy command broker | GATE-C0-CONTAINED |
| S1 | TASK-004..008 — semantic model, IR compiler, conservation validator, atomic acceptance, typed splits + measured collectors | GATE-S1-SEMANTIC-CONSERVATION |
| S2 | TASK-009..012 — generations, immutable candidates, promotion, generation-bound contracts | GATE-S2-EXACT-LINEAGE |
| S3 | TASK-013..016 — evidence split, admissibility, append-only artifacts, proof obligations | GATE-S3-PROOF-ADMISSIBILITY |
| S4 | TASK-017..019 — authority registry, principals/grants, approvals/decisions/unknowns | GATE-S4-AUTHORITY-BOUND |
| S5 | TASK-020..026 — UoW+events, CAS, fencing, hard-stop kernel, Autonomy atomicity, PE→Autonomy bridge, crash suite | GATE-S5-LINEARIZABLE-RUNTIME |
| S6 | TASK-027..031 — derived gates, constrained verifier + path grammar, replan, retry, promotion scheduling | GATE-S6-EXECUTION-SEMANTICS |
| S7 | TASK-032..035 — convergence report, final handoff, owner verdict, INCONCLUSIVE | GATE-S7-OWNER-CLOSEOUT |
| S8 | TASK-036..039 — migration, vertical conformance, shadow/self-host, parity audit | GATE-S8-V3-CONFORMANCE + GATE-CLOSE |

## 5. Done conditions (terminal)

- All 10 gates PASS; zero hardening xfails; all v2 counterexamples blocked; semantic conservation 100%.
- Migration repeatable; legacy v2 artifacts cannot privilege-escalate.
- Shadow and self-host fixtures converge.
- Campaign ends **activation-ready** — activation is a separate follow-on campaign. Self-activation is out of scope by design.

## 6. Campaign's own execution law (encoded in operator_directive)

One worker max · one writer per repo · local mutation only · no push during execution · no PR/merge/publish/deploy from Controller · no destructive runtime migration until S8 · no auto-retry reliance before S6 · no orchestrator switch mid-campaign · halt before merge · publish only through sanctioned make pr · merge authority is external landing authority only.

## 7. Execution gating (what must be true before admission/execution)

1. **claude-code-env-contract-v1 published** by session website-bot-70 (the sanctioned front door is being repaired by that campaign; running this one first would collide in the same checkout and on the lock).
2. **Operator go** — this is a major contract-hardening campaign touching the PE control plane; admission requires explicit operator authorization.
3. **Memory phase-lock acquired** for namespace cursor-governance by the executing session (machine-global lock; coordinate with sibling sessions).
4. **Admission** (after go): copy the `CAMPAIGN_SOURCE.yaml` + `source-integrity-receipt.json` pair into `environment/program-execution/campaigns/pe-v3-control-plane-convergence/`, patch the four host files (COMPILE_ALLOWLIST.yaml, CAMPAIGN_EXECUTION_POLICY.yaml, ops/autonomy/surface_profile.yaml, CAMPAIGN_STATUS.yaml) — the seed compiler flattens wave structure, so admission is drop-in, NOT `compile_activation_files.py` over this intent.
5. **Orchestrator freeze** at 7517f377 as TASK-001's first action (Plane A), before any Plane B edit.

## 8. Known risks carried into the source

- Bootstrap paradox (two-plane mitigation) — RISK-001.
- Machine-global phase-lock contention among live sibling sessions (observed live 2026-08-18; short acquire→commit windows) — RISK-002.
- Additive-only root files (Makefile/ops boundary edits need ALLOW-ROOT-DELETION markers) — RISK-003.
- Unrepresentable governing law ⇒ CompileError + operator decision — RISK-004.

## 9. Honest unknowns (encoded, non-blocking except UNK-001)

- UNK-001: shadow/self-host fixture repository identity — blocks only TASK-038, resolved by bounded probe at S8.
- UNK-002: final placement of new v3 runtime modules inside the pec package — wave-local decision, bounded to the pec package.

## 10. What this prep did NOT do

- No repo files touched (all artifacts under untracked `WIP/8-18-26/`).
- No lock acquired, no admission, no execution, no push, no completion claims.
- pe-v3-hardening source not rewritten (immutable forensic artifact).
