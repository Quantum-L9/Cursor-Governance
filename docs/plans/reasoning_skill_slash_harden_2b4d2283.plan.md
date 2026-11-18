---
name: Harden reasoning skill and slash
overview: "Close /reasoning and /ynp percent drift against l9-structured-reasoning. YNP first so auto_chain cannot invent a score. Encode evidence x risk x action as YAML plus ledger checks. Thin the slash. No ECE, no telemetry revival, no INVARIANTS.md."
todos:
  - id: todo-01-ynp-first
    content: "YNP skill + workflow + commands/ynp.md: action enum required; bare percent uncalibrated; delete AUTO-EXECUTE. Add l9-ynp self_test.py."
    status: pending
    phase: execute
    depends_on: []
  - id: todo-02-confidence-policy
    content: "Add confidence-policy.yaml (risk table as data). Cite from SKILL.md; keep SKILL.md under 500 lines."
    status: pending
    phase: execute
    depends_on: [todo-01-ynp-first]
  - id: todo-03-ledger-schema
    content: "Optional ledger fields in evidence-decision-contract.yaml and evidence-ledger.schema.json. sample_ledger.json stays valid."
    status: pending
    phase: execute
    depends_on: [todo-02-confidence-policy]
  - id: todo-04-validate-ledger
    content: "validate_ledger.py enforces the risk-table allow-set and stated_probability rules. Missing new fields PASS."
    status: pending
    phase: execute
    depends_on: [todo-03-ledger-schema]
  - id: todo-05-confidence-fixtures
    content: "fixtures/confidence_cases.json wired from self_test.py (PASS/FAIL cases listed in body)."
    status: pending
    phase: execute
    depends_on: [todo-04-validate-ledger]
  - id: todo-06-thin-reasoning-command
    content: "Thin commands/reasoning.md; keep auto_chain ynp; update commands-index.md; retarget AUTONOMY_MANIFEST reasoning_routing dead refs."
    status: pending
    phase: execute
    depends_on: [todo-01-ynp-first, todo-02-confidence-policy]
  - id: todo-07-needles
    content: "validate_skill.py REQUIRED + command needles. Forbid Confidence: {score}% and AUTO-EXECUTE, not the word confidence."
    status: pending
    phase: execute
    depends_on: [todo-05-confidence-fixtures, todo-06-thin-reasoning-command]
  - id: todo-08-prove
    content: "Both pack self_tests PASS; make pr-check PASS. Pathspecs only."
    status: pending
    phase: validate
    depends_on: [todo-07-needles]
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: reasoning_skill_slash_harden_2b4d2283.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-28T20:40:00Z
    body_sha256: "a21f4e09d04d7b0a67f839549352446a319ef1f08d4bfa4215c8da48fe79e85c"
    deltas:
      - "Locked YNP-first exclusive order so /reasoning auto_chain cannot invent a percent or AUTO-EXECUTE."
      - "Ledger fields stay optional; ECE is not a /reasoning field and is not a gate."
      - "Needles are exact templates, not the word confidence. Pathspecs only on this dirty checkout."
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-28T20:40:30Z
    body_sha256: "a21f4e09d04d7b0a67f839549352446a319ef1f08d4bfa4215c8da48fe79e85c"
    deltas:
      - "Exclusive lock: do not edit commands/reasoning.md until YNP self_test PASS (checkpoint C1)."
      - "U1 accept_bounded: uncalibrated alias allowed; number must not select action."
      - "No exclusive-list ellipsis. Todos stay pending until Build."
---

# PLAN: Harden structured-reasoning and thin /reasoning

**kind:** `simple` · **execute_via:** `cursor-build` · **skill:** `l9-plan-simple`
**plan_id:** `plan.skills.reasoning_slash_harden.v1` · **schema_version:** `1.0.0` · **status:** `executable`

Machine SSOT: [`docs/plans/reasoning_skill_slash_harden_2b4d2283.plan.json`](reasoning_skill_slash_harden_2b4d2283.plan.json) (`validate_plan_document.py` PASS).

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.
- Pathspecs only. This checkout is dirty with remediator and other WIP. Do not `git add -A`.

## Architect framing

| Field | Value |
|---|---|
| planning_ssot | `skills/l9-structured-reasoning/SKILL.md` + `references/risk-and-autonomy-policy.md` |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | The skill already replaced arbitrary percents with evidence x risk x action (`TRANSFORMATION_REPORT.md`). `/reasoning` v6.0.0 and `/ynp` v8.1.0 reintroduced the old table. Close that drift. Do not invent ECE. |

## Immutable baseline

| Field | Value |
|---|---|
| captured_at | 2026-08-28T20:33:00Z |
| repository | Quantum-L9/Cursor-Governance |
| workspace | current checkout (this folder) |
| branch | `main` |
| commit_sha | `a2eee3a6eedd8635ecf94f7e23022aab60187a5b` |
| dirty | `true` (remediator pack, other plans, generated registries — out of this envelope) |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` only if `may_modify` paths changed under you from another agent |

## Objective

`/reasoning` still requires `Confidence: {score}%` and auto-chains to `/ynp`, which still requires a percent and says **AUTO-EXECUTE** at ≥90%. `l9-structured-reasoning` already forbids arbitrary confidence percentages and uses `evidence_quality` / `decision_risk` / `action`. `validate_ledger.py` checks the action enum and blocking claims only — not the risk table and not a percent ban.

**It is:** encode the live skill contract as YAML + ledger rules; update YNP first so the chain stays valid; thin the slash; needle the exact old templates.

**It is not:** ECE, a decision-outcome log, `telemetry/` revival, an `INVARIANTS.md` row, or a new skill compile.

### Success properties

| id | property | evidence_type | proof | blocking |
|---|---|---|---|---|
| SP-01 | `/reasoning` delegates; no live percent template | `structural` | `rg -n 'Confidence: \{score\}%' commands/reasoning.md` empty; file cites `l9-structured-reasoning` and `evidence_quality` | true |
| SP-02 | YNP action enum; no AUTO-EXECUTE | `structural` | `rg -n AUTO-EXECUTE commands/ynp.md skills/l9-ynp/` empty; `action:` present | true |
| SP-03 | Policy file cited; SKILL.md ≤500 lines | `filesystem` | `references/confidence-policy.yaml` exists; `wc -l SKILL.md` ≤500 | true |
| SP-04 | Ledger fail-open for old fixtures; fail-closed for illegal `p` | `runtime_behavior` | `validate_ledger.py fixtures/sample_ledger.json` PASS; confidence fixture with `stated_probability` + `none` FAIL | true |
| SP-05 | Pack tests + PR gate | `quality_gate` | both `self_test.py` PASS; `make pr-check` PASS | true |

## Capability preflight

| id | capability | command_or_action | pass_criteria | blocking |
|---|---|---|---|---|
| P0 | branch_and_HEAD_resolution | `git rev-parse HEAD` | recorded SHA above; pathspecs if dirty | true |
| P1 | reasoning pack green | `.venv/bin/python skills/l9-structured-reasoning/scripts/self_test.py` | PASS (already observed) | true |
| P2 | defect still present | `rg` percent / AUTO-EXECUTE on both slash files | hits exist before Build | true |
| P3 | plan depth | `route_plan.py --risk medium --evidence partial` | `depth=standard` | true |

## Execution envelope

**write_allow:** `skills/l9-ynp/**`, `skills/l9-structured-reasoning/**` except `schemas/run-metrics.schema.json`, `commands/ynp.md`, `commands/reasoning.md`, `commands/commands-index.md`, `skills/AUTONOMY_MANIFEST.yaml` (`reasoning_routing` keys only).

**write_deny:** `telemetry/`, `INVARIANTS.md`, `ORG_INVARIANTS.yaml`, `CANONICAL_LAW.md`, `AGENTS.md`, `kernels/`, `environment/program-execution/`, remediator WIP, other plans.

**commands allow:** pack self_tests, `validate_ledger.py`, `rg`, `make pr-check`, scoped `git add` / `git commit` of this envelope.

**commands deny:** `make campaign`, `git add -A`, force-push, merge.

**network:** `none`. **secrets:** `none`. **autonomous_merge:** `false`.

## Side effects and idempotency

| todo_id | side_effects | idempotency | irreversible |
|---|---|---|---|
| todo-01-ynp-first | filesystem_mutation | safe_with_dedupe | false |
| todo-02-confidence-policy | filesystem_mutation | safe_with_dedupe | false |
| todo-03-ledger-schema | filesystem_mutation | safe_with_dedupe | false |
| todo-04-validate-ledger | filesystem_mutation | safe_with_dedupe | false |
| todo-05-confidence-fixtures | filesystem_mutation | safe_with_dedupe | false |
| todo-06-thin-reasoning-command | filesystem_mutation | safe_with_dedupe | false |
| todo-07-needles | filesystem_mutation | safe_with_dedupe | false |
| todo-08-prove | filesystem_read | safe_to_repeat | false |

## Architecture impact

Control-plane skill + slash only. Owner: `l9-structured-reasoning` for the contract; `l9-ynp` for the chain hop. Prohibited: a second confidence SSOT, ECE under `run-metrics.schema.json` `calibration`, host telemetry.

`AUTONOMY_MANIFEST.yaml` `reasoning_routing` today points at missing files (`reasoning-protocol.md`, `technical-operations-reasoning.md`, `reasoning-modes.md`, `persona-lenses.md`). Retarget to live refs (`reasoning-router.yaml`, `risk-and-autonomy-policy.md`, `document-corpus-reasoning.md`). Do not rewrite `claude_routing`.

## Rollback

Revert the `may_modify` pathspec set. If `sync_generated_artifacts.py` ran because `AUTONOMY_MANIFEST.yaml` changed, revert those generated companions in the same revert.

## Complexity and uncertainty

Standard depth. One bounded unknown (U1): out-of-repo parsers of `Confidence: N%`. Accept: YNP may show `calibration_status: uncalibrated` if a number is still present; the number must not choose `action`.

## Execution DAG

```text
todo-01-ynp-first
    ├─► todo-02-confidence-policy ─► todo-03-ledger-schema ─► todo-04-validate-ledger ─► todo-05-confidence-fixtures ─┐
    └─► todo-06-thin-reasoning-command ──────────────────────────────────────────────────────────────────────────────┴─► todo-07-needles ─► todo-08-prove
```

Checkpoint C1 after todo-01: if YNP still has AUTO-EXECUTE or lacks `action:`, **stop** — do not edit `commands/reasoning.md`.

## Locked contracts (Build)

1. **YNP first.** `/reasoning` keeps `auto_chain: ynp`. Removing percents from `/reasoning` before YNP accepts `action` lets the chain invent a score or AUTO-EXECUTE.
2. **Enums, not percents.** `evidence_quality: high|medium|low|unknown`. `decision_risk: reversible|guarded|irreversible`. `action: proceed|proceed_with_validation|bounded_probe|block`. Map for display alias only: proceed≈old ≥90 slot, proceed_with_validation≈80–89, bounded_probe≈70–79, block≈&lt;70. Do not compute those percents.
3. **Fail-open on ordinary runs.** `calibration_status` defaults to `none`. `stated_probability` must be null unless `calibration_status=calibrated` and `window`/`n`/`ece` are present. ECE is not a `/reasoning` field and is not a gate.
4. **Needles are exact.** Forbid `Confidence: {score}%` and `AUTO-EXECUTE`. Do not forbid the word `confidence` (benchmark contract and expertise model use it correctly). Do not reuse `run-metrics.schema.json` `calibration`.
5. **Thin slash.** `commands/reasoning.md` reads like `/l9-pr-remediation`: read the skill, emit the enums, keep abductive/deductive/inductive as methods the skill already lists (`epistemic_methods`). No ceremonial Confidence heading.

## Property evidence matrix

| After | Evidence |
|---|---|
| todo-01 | `skills/l9-ynp/scripts/self_test.py` PASS |
| todo-04 | `validate_ledger.py fixtures/sample_ledger.json` PASS |
| todo-05 | confidence fixture FAIL case exits 1 |
| todo-06 | `rg` empty for percent template on `commands/reasoning.md` |
| todo-08 | both self_tests + `make pr-check` PASS |

## Stress and disconfirm

- If a consumer parses `Confidence: N%`, keep an uncalibrated alias line; still do not let it select action.
- If new ledger fields are required, `sample_ledger.json` goes red — keep them optional.
- If needles match `confidence` anywhere, the already-green pack fails — keep needles exact.
- Blast radius: `/reasoning` and `/ynp` agent output only.
- Rollback: revert the envelope pathspecs.

## Out of scope

ECE / MCE / drift. `telemetry/`. Gold Nugget compile. `INVARIANTS.md` / org YAML / law. PE / `make campaign` / Program Lock. Turning off `auto_chain`. Merging. Remediator WIP on this checkout.

## Convergence

| Field | Value |
|---|---|
| status | `partial` (plan ready; Build not run) |
| remaining_unknown_ids | `U1` |
| next_skill | Build on this checkout |
| execute_via | Cursor Build on the current checkout |
| stop_reason | Do not implement until Build. YNP first. |

```yaml
evidence_quality: high
decision_risk: reversible
action: proceed_with_validation
calibration_status: none
stated_probability: null
```

## Validation (Build)

```bash
"$PWD/.venv/bin/python" skills/l9-ynp/scripts/self_test.py
"$PWD/.venv/bin/python" skills/l9-structured-reasoning/scripts/self_test.py
make pr-check
```

Falsifiable read-backs:

- `rg -n 'Confidence: \{score\}%' commands/reasoning.md` → no match
- `rg -n 'AUTO-EXECUTE' commands/ynp.md skills/l9-ynp/` → no match
- `rg -n 'l9-structured-reasoning' commands/reasoning.md` → match
- `test -f skills/l9-structured-reasoning/references/confidence-policy.yaml`
- `rg -n 'calibration_status' skills/l9-structured-reasoning/scripts/validate_ledger.py` → match
