# Program Execution repair pipeline — remaining work

**Updated:** 2026-08-30 — W0–W7 **complete** at `e8785018` (HEAD `35880e70`). Next = **W8**.
**Machine SSOT:** [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json)
**Cursor Build plan (W0–W7 done):** [`docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md`](../../../docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md)
**PLAN_DOCUMENT (W8-forward):** [`PLAN_DOCUMENT.pec-repair-pipeline.v1.json`](./PLAN_DOCUMENT.pec-repair-pipeline.v1.json)
**Sources:** moved to [`_archive/`](./_archive) and deprecated. Do not execute from archived files.
**Live SSOT is this trio** — `PEC-repair-pipeline.md` (narrative), `PEC-repair-pipeline.json`
(machine), `PLAN_DOCUMENT.pec-repair-pipeline.v1.json` (W8-forward plan). `_archive/DEPRECATED.md`
says the `.md` / `.json` "are gone" and names the PLAN_DOCUMENT the sole SSOT; that sentence was
never true — both files exist at every commit from `e8785018` onward and were re-synced by
`2dec45c`. The archive is immutable provenance, so the correction is recorded here, not there.

This folder is no longer a dump of PE research. It is one remaining pipeline.

---

## What this is

PEC already has a strong runtime (Program Lock, authorization, evidence, replan contract, peer execution, `refuse_publication`). W0–W7 closed the compiler front half through shadow graduation.

**Do not build RiskPacket next. Do not `make campaign` next.**

W8+ requires a **new plan** bound to a fresh `origin/main` SHA after W7 merges.

---

## Order (do not reorder)

| Wave | Contract | Status | Depends on |
| --- | --- | --- | --- |
| **W0** | `PEC-WORKER-DIAG-001` | **Complete** | — |
| **W1** | `BOOTSTRAP-PEC-000` | **Complete** | W0 |
| **W2** | C0 | **Complete** | W1 |
| **W3** | C1 | **Complete** (execute residual) | W2 |
| **W4** | C2 | **Complete** | W3 |
| **W5** | C3 | **Complete** (thin microscope) | W4 |
| **W6** | C4 | **Complete** | W5 |
| **W7** | C5 | **Complete** (shadow only) | W0 + W6 |
| **W8** | PE v3 S0–S8 + C6 | **Open** | W7 |
| **W9** | C7–C10 | **Open** | W8 |
| **W10** | C11 | **Open** | W9 |

W8+ is forbidden until a separate plan with a fresh baseline SHA.

---

## Verified at HEAD (`35880e70`)

| Check | Evidence |
| --- | --- |
| W0 worker diagnosability | `provider.py` retains `stderr_excerpt` / `stderr_text` on FAIL; `test_driver.py` 12 passed |
| W1–W2 shadow harness | `compiler/tests/conformance/` fixtures 01–14, `shadow_runner.py`, `counterexamples.yaml` |
| W3 compile ingress | `compile_intent_ingress()` + `--check-input`; campaign execute still refuses `intent.v1` (intentional) |
| W7 shadow graduation | `test_graduation.py` 1 passed — zero blocking metrics on golden journeys |

**Residual (not stale defects):**

- W3: `PROGRAM_INTENT_V1` ∉ `SUPPORTED_KINDS` for campaign **execute** until a post-W8 `make campaign` plan.
- W7: Spine execute / Lock / 10-run repeatability not proven; `make campaign` was not invoked.

---

## Next: W8 (v3 control-plane)

Start only via a new plan after W7 lands on `origin/main`. Do not reopen the W0–W7 Build.

### W8 prep (from PE-PE 1 — harvested 2026-08-30)

- **v3 surfaces:** `program-execution-system.v3`, `program-execution-blueprint.v3`, `program-execution-controller.v3`; v2 receipts stay v2 forever.
- **Two planes:** pinned v2 orchestrator checkout (A) orchestrates repair of editable implementation (B). Freeze **fresh** baseline at W8 start — `0db3fed` in the v2 registry is forensic only.
- **S0 counterexamples SSOT:** [`environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml`](../../../environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml) — S8 exit = zero hardening xfails.
- **S1 semantic conservation:** `PROGRAM_SEMANTICS.yaml` canonical model; projections derive from SemanticModel; split semantic prohibitions from `filesystem_scope` paths.

See [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json) W8 `subwaves` for S0–S8 acceptance bullets.

### Campaign activation (when W8+ admits campaigns)

Use live skill **`skills/l9-pe-campaign-activate`** — not WIP template copies under `_archive/`.

---

## Already done — do not rebuild

- Compiler module in-tree (`environment/program-execution/compiler/**`).
- W0–W7 spine (commit `e8785018`).
- Campaign front door for brief / plan / activate / campaign-source.v2 / architecture-intent.
- `run_campaign.py` `refuse_publication` — runner cannot push, open, or merge.
- Campaigns: `bounded-replanning-v1` (PR 149), `l9-devpack-program-execution-hardening` (PR 150) — CONVERGED;
  `level3-make-pr-single-path` (PR 187) — CONVERGED_WITH_NON_BLOCKING_RISKS. Verdicts are the
  `CAMPAIGN_STATUS.yaml` ledger's own strings; do not flatten the qualified one to CONVERGED.
- `cc-pe-intent-compiler-v1` — registered/archival; not the graduation test.
- Skill `l9-pe-campaign-activate` — live.
- Graphiti is resume SSOT.

---

## Parked — not this pipeline

| Item | Why it is out |
| --- | --- |
| Environment-experience 8-release brief | Different program. Failed run is W0 evidence only. |
| Perplexity PR pack v2 | Host overlay after W7. |
| PE Memory cutover docs | Later, if W7 still lacks evidence/memory projection. |
| Draft `canonical.schema.*.yaml` family | Live plan schema: `skills/l9-plan/schemas/plan-document.schema.json`. |
| `pe-v3-hardening` campaign source | Forensic, `operator_intake`. W8 takes its *intent*, fresh baseline. |
| `WIP/PROGRAM EXECUTION PIPELINE/` | Harvested into W8 prep 2026-08-30; deleted. |

---

## How to execute W8+ (when authorized)

Every W8 job remains a bootstrap pack, not a chat prompt:

```text
bootstrap/<work-id>/
  00-source-intent.md     # immutable, hashed
  01-intent-ir.yaml
  02-grounding.yaml
  03-requirements.yaml
  04-execution-contract.yaml
  05-evidence/
  06-completion.yaml
```

Stop on `CONTRACT_DRIFT`. Do not invent a second controller, transport, replanner, authorization model, or evidence model.

W8 uses two planes: pinned v2 orchestrator (A) vs editable implementation (B).

---

## Graduation (W7 done) — dogfood (W10)

W7 shadow graduation is complete when golden-journey blocking metrics are zero (see `test_graduation.py`). Full spine execute/Lock/repeatability is a W8+ concern.

W10 is trusted enough for Risk-bearing work when PEC, given the original messy RiskPacket request, concludes on its own: harden replanner, preserve auth/evidence/Gate, create ImpactEngine + RiskPacket, duplicate nothing.

---

## If you must hand-author `campaign-source.v2`

Prefer the brief/intent route or `l9-pe-campaign-activate`. If it fails, the archived HANDOFF gotchas still hold: `plan_status`, `risks[].owner`, admitted `input_evidence_ids` only, per-task `paths:`, single-op validation commands, numeric TASK/GATE ids, never reuse a failed `campaign_id`.
