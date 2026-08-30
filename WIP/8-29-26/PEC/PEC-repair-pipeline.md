# Program Execution repair pipeline — remaining work

**Updated:** 2026-08-29 — W0–W7 landed on this checkout via Cursor Build. W8–W10 not started.
**Machine SSOT:** [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json)
**Cursor Build plan:** [`docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md`](../../docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md)
**PLAN_DOCUMENT:** [`PLAN_DOCUMENT.pec-repair-pipeline.v1.json`](./PLAN_DOCUMENT.pec-repair-pipeline.v1.json)
**Sources:** moved to [`_archive/`](./_archive) and deprecated. Do not execute from archived files.

This folder is no longer a dump of PE research. It is one remaining pipeline.

---

## What this is

PEC already has a strong runtime (Program Lock, authorization, evidence, replan contract, peer execution, `refuse_publication`). Its front half does not yet preserve arbitrary human intent into that runtime.

**Do not build RiskPacket next. Do not `make campaign` next.**

```text
Claude executes an explicit contract
        +
same raw intent → PEC shadow compile → semantic diff
```

until W7 (C5) proves intent → Blueprint → Lock → execution.

---

## Order (do not reorder)

| Wave | Contract | Remaining work | Depends on |
| --- | --- | --- | --- |
| **W0** | `PEC-WORKER-DIAG-001` | **Landed.** FAIL receipts keep bounded stderr/stdout text. Controller owns `candidate_sha` (HEAD). Worker git add/commit stay denied. | — |
| **W1** | `BOOTSTRAP-PEC-000` | **Landed.** `compiler/tests/conformance/` fixtures 01–14 + shadow runner. | W0 |
| **W2** | C0 | **Landed.** `counterexamples.yaml` (AT-002–008). | W1 |
| **W3** | C1 | **Landed.** `--check-input` / `compile_intent_ingress` compiles `program-execution.intent.v1`. Campaign execute still refuses. | W2 |
| **W4** | C2 | **Landed.** Lowercase don't/must survive; bare "never" is not a signal. | W3 |
| **W5** | C3 | **Landed.** `classify_dispositions` on `repo_truth.py`. | W4 |
| **W6** | C4 | **Landed.** No `docs/program-execution/<TASK>.md` fallback; unknown seam is inspection-only. | W5 |
| **W7** | C5 | **Landed (shadow).** Golden journeys: blocking metrics 0. This Build did **not** run `make campaign`. | W0 + W6 |
| **W8** | PE v3 S1–S8 + C6 | Control-plane reconstruction on two planes; new baseline SHA | W7 |
| **W9** | C7–C10 | Assurance RiskPacket → ImpactEngine → enforce → outcome replan | W8 |
| **W10** | C11 | PEC dogfoods the messy RiskPacket objective itself | W9 |

W1 may land characterization failures as expected. W2–W6 exist to turn those failures green. W8+ is forbidden until W7 metrics are zero on the listed dimensions.

---

## Next contract: W8 (not this Build)

W8–W10 stay blocked until a later plan with a fresh baseline SHA. Do not start RiskPacket from this checkout.

### W0 — diagnosable workers

Live facts (re-verify; originally measured at `c3081ee`):

- Peer Execution `TASK-001` → `provider status=FAIL`, `changed_files: []`, `num_turns: 13` regardless of task size.
- `provider.py` stores `stderr_digest`, not stderr text.
- `permission_renderer.py` denies `Bash(git add:*)` and `Bash(git commit:*)` while the contract asks for `candidate_sha`.

Fix retention and the SHA/permission contradiction **before** another campaign run. Then probe one 1-file `local_write` task and keep the logs.

### W1 — `BOOTSTRAP-PEC-000`

Build the bridge named in the archived PEC Contract:

1. Characterization tests for journeys A–J (record current defects; do not “fix while investigating”).
2. Fixture corpus `01`–`14` under a canonical compiler-test path (suggested: `environment/program-execution/compiler/tests/conformance/`).
3. Test-facing semantic expectation format — not a second Blueprint.
4. Shadow runner: compile, **do not execute**, compare, emit dimensioned metrics.

AT-002…AT-008 will fail on current HEAD. That is the baseline report, not a reason to skip the harness.

---

## Live defects this pipeline still owns

| Defect | Evidence | Wave |
| --- | --- | --- |
| Operator must pick an internal PEC input kind | `campaign_input.py` `SUPPORTED_KINDS` omits `PROGRAM_INTENT_V1`; reject at lines 343–358 tells the human to convert | W3 |
| Lowercase “don't replace assurance” can vanish | `test_normative_signals_are_case_sensitive` **asserts** this | W4 |
| Grounding too thin for KEEP vs CREATE | `repo_truth.py` exists; no disposition IR before lowering | W5 |
| Lowering follows document sections | `architecture_to_campaign.py`; missing `paths:` historically defaulted to `docs/program-execution/<TASK>.md` | W6 |
| No shadow / conformance harness | zero live hits for BOOTSTRAP-PEC / shadow compiler | W1 |
| Worker FAIL undiagnosable | digest-only stderr; git commit denied vs `candidate_sha` | W0 |

---

## Already done — do not rebuild

These were in the archived corpus as if still open. They are not remaining pipeline work.

- Compiler module in-tree (`environment/program-execution/compiler/**`).
- Campaign front door for brief / plan / activate / campaign-source.v2 / architecture-intent.
- `run_campaign.py` `refuse_publication` — runner cannot push, open, or merge. C0 containment from the v3 INTENT is closed (dead code after the raise is residue).
- Campaigns: `bounded-replanning-v1`, `l9-devpack-program-execution-hardening`, `level3-make-pr-single-path` — CONVERGED.
- `cc-pe-intent-compiler-v1` — registered/archival; AUTH-001 already bound the compiler to this repo. It is not the graduation test.
- Skill `l9-pe-campaign-activate` — live. The WIP activation kit is a copy.
- Graphiti is resume SSOT. Do not start a PE-memory cutover to get compiler repair.

---

## Parked — not this pipeline

| Item | Why it is out |
| --- | --- |
| Environment-experience 8-release brief | Different program. The failed `make campaign` of that brief is W0 evidence only. |
| Perplexity PR pack v2 | Merge queue, provenance, feature trees, preview leases — host overlay after W7. |
| PE Memory cutover docs | Later, if W7 still lacks an evidence/memory projection. |
| Draft `canonical.schema.*.yaml` family | Live plan schema is `skills/l9-plan/schemas/plan-document.schema.json`. Land a schema only when a remaining wave needs it. |
| `pe-v3-hardening` campaign source | Forensic, `operator_intake`. Do not rewrite. W8 takes its *intent*, with a fresh baseline SHA. |
| `pe-v3-control-plane-convergence` prep | Never admitted. Pins `7517f377` / `0db3fed` are stale. Re-prep at W8. |

---

## How to execute (until W7)

Every job is a bootstrap pack, not a chat prompt:

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

Production lane: Claude executes `04`. Shadow lane: PEC compiles `00`, no execution, semantic diff against `01`–`04`.

Stop on `CONTRACT_DRIFT`. Do not invent a second controller, transport, replanner, authorization model, or evidence model.

W8+ uses two planes: pinned v2 orchestrator (A) vs editable implementation (B). Activation of v3 is a follow-on after S8, not this pipeline's last wave.

---

## Graduation (W7) — then dogfood (W10)

W7 is trusted enough to dogfood the **spine** when:

- ordinary human intent needs no schema homework
- material-intent loss, false CREATE, authority widening, manual IR edits, and private-stage bypasses are **0**
- restart/resume does not corrupt Program truth
- provider identity does not leak into Program truth

W10 is trusted enough for Risk-bearing work when PEC, given the original messy RiskPacket request, concludes on its own: harden the existing replanner, preserve auth/evidence/Gate, create ImpactEngine + RiskPacket, duplicate nothing.

---

## If you must hand-author `campaign-source.v2`

Prefer the brief/intent route. If it fails, the archived HANDOFF gotchas still hold: `plan_status`, `risks[].owner`, admitted `input_evidence_ids` only, per-task `paths:`, single-op validation commands, numeric TASK/GATE ids, never reuse a failed `campaign_id`.
