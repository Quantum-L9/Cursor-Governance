# Remediation Design — l9-devpack-compiler → Program Execution v2

Derived from `PROGRAM_SOURCE.md` (TASK_CARDS + DECISION_REGISTER +
CURRENT_STATE_DELTA). Each task below is reversible, repo-local, and gated. File
paths are the Blueprint's declared outputs; reconcile against the actual repo
tree at bind time (`TASK-001`) before editing.

## Ordering (from EXECUTION_WAVES / DEPENDENCY_GRAPH)

```
W0  TASK-001  bind target + governing contract        → GATE-001  (blocked: UNK-001)
W1  TASK-002  authority hierarchy + role boundary      → GATE-002
    TASK-003  provenance-backed defaults               → GATE-002
    TASK-004  structural vs runtime proof semantics     → GATE-003
W2  TASK-005  Program Execution v2 emitter             → GATE-004
    TASK-006  provenance / scoped-Unknown / ceilings    → GATE-004
W3  TASK-007  full regression + official validation     → GATE-005
```
Parallelizable: `{TASK-002, TASK-003, TASK-004}` then `{TASK-005, TASK-006}`.
Hard rule: no successor may bypass a predecessor by reproducing its output.

---

## TASK-002 — Align DPK authority hierarchy and role boundary (DEC-001, DEC-002)

**Files:** `SKILL.md`, `references/dpk-layer-contract.md`, `expertise_model.yaml`,
`skill_intelligence_report.yaml`.

- Rewrite DPK role language from "programmatic execution / control plane" to
  **compiler / design-time authority** upstream of Program Execution v2.
- Place **accepted architecture and contracts above** approved Task Contract
  authority; redefine a Task Contract as a **narrowing** scope projection that
  may narrow but never widen upstream authority.
- Explicitly disclaim Controller-owned runtime state, gate evaluation, attempts,
  approvals, leases, and receipts.
- Add regression checks asserting no rule permits Task-Contract-over-architecture
  precedence.

**Acceptance:** AC-003 (no Task Contract overrides accepted architecture/
contracts), AC-004 (DPK disclaims runtime authority).
**Negative cases:** legacy Task-Contract precedence still active; DPK still
claims mutable runtime state; an example contradicts the canonical authority
order.

## TASK-003 — Replace implicit autofix with provenance-backed derivation (DEC-003)

**Files:** `scripts/validate_devpack.py`, `references/quality-gates.md`.

- Remove unconditional missing-`operational_owner` auto-fill (e.g. `quantum-ai`)
  and unconditional library-rollback auto-pass.
- Derive an authority-affecting default **only** from an explicit governing
  policy with recorded provenance (source id + revision) in machine output;
  otherwise leave the fact **Unknown** / fail closed.
- Add negative fixtures: missing owner, missing rollback, missing policy source.

**Acceptance:** AC-005 (missing owner cannot pass via a hard-coded org default),
AC-006 (derived values record governing provenance).
**Negative cases:** owner/rollback passes with no policy source; provenance only
in prose, absent from machine output.

## TASK-004 — Separate structural compile-readiness from runtime proof (DEC-004)

**Files:** `scripts/validate_devpack.py`, `references/quality-gates.md`.

- Scope validator output to **structural compile-readiness**. Presence of a
  tests dir ≠ tests passed; presence of a rollback command ≠ dry-run succeeded;
  presence of a repo-map ≠ architecture aligned.
- Every readiness result must **declare its evidence level**; version/migrate any
  label that currently implies runtime operability.
- Add presence-only negative fixtures.

**Acceptance:** AC-007 (structural evidence never shown as executed proof),
AC-008 (evidence level declared per result).

## TASK-005 — Versioned Program Execution v2 emitter (DEC-006, DEC-007)

**Files (new):** `references/program-execution-v2-projection.md`,
`schemas/program-execution-v2-target.schema.json`,
`scripts/emit_program_execution_v2.py` + deterministic fixture.

- Map DPK IR to **all** Blueprint v2 `EXECUTION_INDEX` required sources; preserve
  source evidence + authority provenance; emit **definitions only** (no
  Controller runtime state / gate results / receipts).
- Keep target-specific fields in a **versioned overlay**, not the generic core
  spec.

**Acceptance:** AC-009 (emits every required Blueprint source), AC-010 (no
Controller-owned runtime state emitted).
**Negative cases:** a required source omitted; emitter invents owner/repo URL;
emits runtime/gate state; unresolved cross-file references.

## TASK-006 — Provenance, scoped-Unknown, and authorization-ceiling projection (DEC-005–007)

**Files:** `schemas/program-execution-v2-target.schema.json`, projection tests/
fixtures.

- Stable source-evidence → emitted-field **provenance edges**.
- Map unresolved facts to named `UNKNOWN_REGISTER` records; each Unknown blocks
  **only** the tasks that consume it.
- Require the exact **canonical ten-action authorization ceiling** on every
  emitted task; forbid widening by omission.

**Acceptance:** AC-011 (exact ten-action ceiling, no authority by omission),
AC-012 (scoped Unknown blocking), AC-013 (material authority traceable to
evidence / decision / policy).

## TASK-007 — Full regression + official Blueprint validation + handoff review (all DECs)

**Files:** `tests/`, fixtures, final changed-file set.

- `python3 -m py_compile scripts/*.py`
- `python3 -m unittest discover -s tests -p 'test_*.py'`
- `python3 scripts/validate_exemplary_skill.py .`
- Emit a representative Blueprint v2 fixture and validate it with the **exact
  EVID-006 revision** of `validate_blueprint.py --mode instantiated`.
- Inspect the final diff for scope creep, weakened tests, authority widening, and
  runtime ownership.

**Acceptance:** AC-014…AC-017 (regression PASS; exemplary PASS; official
instantiated validation PASS; diff free of unauthorized/weakened changes).

---

## Red-lines (DO_NOT_BUILD) that apply while executing

- No DPK-owned runtime task state, leases, attempts, gate results, or receipts.
- No Task Contract authority above accepted architecture / public contracts.
- No implicit owner / rollback / repository / credential / branch facts.
- No runtime-operable verdict from artifact presence alone.
- No remote mutation or embedded credentials.
- No tests or red-lines weakened merely to obtain PASS.
