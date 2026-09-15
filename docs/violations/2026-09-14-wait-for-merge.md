# Violation — wait-for-merge treated as a finish (2026-09-14)

**Invariant:** maximum velocity (`rules/07-max-velocity-research.mdc`,
`INVARIANTS.md`); overlap (`rules/53-pr-overlap-guardrail.mdc` § preferred
order item 1).
**Surface:** Cursor agent session `01ef4963-f9d1-4b7d-ba73-3d5cad73bb9c`
**Severity:** critical
**Type:** anti-pattern / velocity

## What happened

GMP #594 (`agent/cursor/memory-doc-adr0031`) hit `PR_OVERLAP=block` on
`commands/start-session.md` vs open PR #593. The gate printed routing
option 1: commit into the overlapping open PR. The agent instead reverted
the file, published the sibling, and told the human the work was
**deferred until #583 / #584 / #593 merge**.

The same session treated "do not append AGENTS.md in this PR" as "do not
touch AGENTS.md in any open PR," then offered a later follow-up.

That is wait-for-merge. It is not a routing option. The human is not a
queue.

## What allowed it

1. `AGENTS.md` §4.1 still said "else wait" (historical; additive_only).
2. `rules/07` only forbade serial *research* Tasks, not serial overlap
   mutation.
3. `rules/53` listed commit-into-PR first but did not forbid finishing
   with defer-until-merge after a sibling publish.
4. `validate_max_velocity.py` checked profile numbers only.

## Required action (this turn)

- Forbid wait-for-merge in rules 07 and 53; latch the phrase in
  `validate_max_velocity.py`.
- Append `OVERLAP_NO_WAIT_V1` on `AGENTS.md` / `INVARIANTS.md` on the
  open PR that already owns those files (#593).
- Print the forbid line from `pr_overlap_check.py`.
- Do not leave the dropped `start-session.md` work parked as a later
  GMP — that follow-up is the same violation and is a separate turn
  only after this latch exists.

## Prevention

An overlap block plus a user "not in this PR" is a same-turn commit
into the owning open PR. Dropping the path to unblock a sibling and
calling the remainder "deferred" is the violation.
