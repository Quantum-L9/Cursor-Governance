---
description: 'GMP v1.7 action workflow: enforce Phases 0–6, quick actions, and corrective runs for L9 repo changes.'
---

# GMP v1.7 execution rules (L9)

## Phase discipline (0–6)

- Every significant change must follow **GMP Phases 0–6** from GMP-System / Action prompts: Phase 0 (PLAN), 1 (BASELINE), 2 (IMPLEMENT), 3 (ENFORCE), 4 (VALIDATE), 5 (RECURSIVE VERIFY), 6 (FINALIZE).
- For each Cursor task, **state current phase in the prompt** and keep scope aligned with that phase.
- Do not jump directly to Phase 2; always lock a **Phase 0 TODO plan** with file paths, actions, and expected behavior.

❌ **DON'T:**
> “Refactor executor and websocket orchestrator to be cleaner.”

✅ **DO:**
> “Phase 0. Lock TODO plan for `l9/executor.py` and `l9/task_queue.py`: Insert timeout handling and explicit error packets, no API changes.”

---

## Quick actions vs full runs

- Use **GMP_QUICK_ACTIONS** patterns only for **small, low-risk edits** (one file, no behavior change).
- Any change touching **kernels, executor, tool registry, memory substrate, or deployment manifests** must use the **full GMP v1.7 action prompt** flow.
- When using quick actions, explicitly say: `Scope: QUICK_ACTION; No changes to behavior, tests must still pass.`

---

## Corrective runs

- If a previous change caused regressions, initiate a **CORRECTIVE RUN** using the corrective GMP template.
- Explicitly reference the failing behavior and link it to the prior Phase 0 plan in the prompt.
- Corrective runs must:
  - Identify root cause.
  - Amend TODO plan.
  - Add/strengthen regression tests called out in the corrective template.

---

## GMP block structure (Cursor prompts)

- For multi-file work, structure prompts as **GMP blocks**:
  - `PHASE`: current phase (0–6).
  - `SCOPE`: file list and allowed actions (insert/replace/wrap/delete).
  - `CONSTRAINTS`: invariants from STRICT_MODE and L9 global rules.
  - `TESTS`: required checks (unit, integration, critical-path) derived from GMP Action test prompts.
- Never ask Cursor to “do everything”; keep prompts small, single‑objective, and fully aligned with the declared phase.

---

## Phase closure conditions

- A phase is complete only when its **GMP closure conditions** are met (e.g., Phase 4 requires all tests defined in the Action+Tests prompts to pass).
- Do not advance to Phase 6 until:
  - Phase 4 tests (unit + integration + critical-path where applicable) are green.
  - Phase 5 recursive comparison confirms no scope drift vs Phase 0.
- Finalization requires a **signed evidence summary** in commit message or PR description that maps back to phases and test sets.

---

## Testing references

This rule always applies; `50-qa-testing.mdc` is glob-scoped and is only in
context when a matching test file is. A closure condition that could only be
read there was therefore unreadable for most of a session, so the part Phase 4
depends on is stated here and `50` carries the detail.

**Phase 4 closure, self-contained:**

- Every test the Phase 0 plan named is green — unit, integration, and
  critical-path where the change touches one.
- A failing test is evidence and is diagnosed, never skipped, weakened, or
  mocked away (`95-test-fix-policy.mdc`, which always applies).
- Tests actually ran. "Not run" is a reportable state; silence is not.

For the fuller testing contract — coverage thresholds, per-language patterns,
determinism, regression and smoke suites — read `50-qa-testing.mdc` directly
when working in test files, where it auto-attaches.

<!-- generated-from: rules/80-gmp-execution.mdc; do-not-edit -->
