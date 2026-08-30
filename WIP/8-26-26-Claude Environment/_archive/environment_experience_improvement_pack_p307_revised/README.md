# Environment Experience Improvement Pack — Canonical, revision **r2**

## What this revision is

A current-state reconciliation of `environment_experience_improvement_pack_p307` against
**`Quantum-L9/Cursor-Governance` main@`59f03a5d4460b939360bc2fd5dd85239d47416a5`**.

It is not a counter update. Every one of the 38 records was re-judged against the tree and
the live container; none carries a prior judgement forward unexamined; and the remaining
program's dependency graph and execution order were re-derived from current repository
truth rather than inherited from the predecessor's ordering.

This pack is **self-contained** — it is a complete successor, not a delta. Six artifacts
are revised; fourteen are carried forward byte-identical to the predecessor and are
verified as such in `INHERITED.yaml`.

| | |
|---|---|
| Predecessor | `WIP/8-26-26/environment_experience_improvement_pack_p307` |
| Predecessor binding | `main@30c6ecd4`, 2026-08-27, scope **targeted** |
| This binding | `main@59f03a5d`, 2026-08-28, scope **full** |
| Distance | 59 commits, 514 files, +62811 / −8528 |
| Records | 38, unchanged. No ID renumbered, no record dropped. |

## Status

Two bindings, kept separate on purpose.

| Binding | Counts | Queue |
|---|---|---|
| **Assessment** — `main@59f03a5d`, 2026-08-28 | 2 done · 16 partial · 16 not started · 1 blocked · 3 unknown | 27 active, 6 external-blocked, 3 needing an attachment, 2 closed |
| **After execution wave 1** — PR#360, 2026-08-29 | **7 done · 15 partial · 12 not started · 1 blocked · 3 unknown** | **20 active**, 8 external-blocked, 3 needing an attachment, 7 closed |

Of 38, unchanged. Predecessor: 4 · 15 · 19 of 38, all in three buckets, with no separation
between work this org can start and work it cannot.

The two figures answer different questions and collapsing them is precisely how the
predecessor came to carry three counts in three stores. `progress.yaml`'s stated `counts` and
the tally over its records agree by construction, and `improvements.yaml` is written from the
same source — CI-035's failure mode does not recur.

## Execution wave 1

Branch `claude/cursor-governance-pack-reconcile-9d4c9v`, forked from `0fc6ee6f`, head
`8d812336`, published as **PR#360 — open, mergeable, not merged**. `make pr-check` green:
628 tests, 0 failures.

Seven of 26 execution units shipped across eight records. **CI-027, CI-030, CI-025, CI-018,
CI-014** are done. **CI-003** and **CI-036** close their in-repo legs and leave the active
queue as external-blocked. **CI-016** ships IMP-14 and stays active on I-BS-09.

Three repairs outside the pack were red on `main` and are in scope under rule 42/3:
`run_pr_precommit.sh`'s staged-mode exemption, the swallow ratchet's unjustified bump, and
the debt gate's satisfiability defect.

Four findings are deferred to a human — chief among them **OD-002**, which this revision
moves from `RESOLVED` back to **`REOPENED`** on an operator correction that contradicts
`surface_profile.yaml`, CLAUDE.md, rules 48/88 and a test. No doctrine was changed; the
correction was scoped behaviour-only.

Full detail: `PROGRESS.md` → *Execution wave 1*, and `progress.yaml` → `execution`.

## What changed, in one paragraph

Three records were misjudged, and two were misjudged in the direction that hides work.
**CI-007** was marked done on evidence about a different question and is a live standing
breakglass grant over the publish plane — it is now the first item in the queue.
**CI-026** was marked done on session configuration rather than on any delivered change,
and that configuration is absent at this binding. **CI-003** was marked not started when
most of its in-repo lever already existed and was documented. Separately, the pack's own
named next slice — ownership-aware writes — rests on a premise that does not survive
inspection, and would have been rework on correct code; CI-002 drops from headline to
leverage rank 23 of 27, with one of its legs invalidated outright.

## Canonical structure

Artifacts **revised in r2**:

- `README.md` — this file
- `PROGRESS.md` — human view: what moved, what reproduces, the optimized order, full status
- `progress.yaml` — machine view: per-record disposition, evidence, lane, schedule slot, effort, leverage
- `improvements.yaml` — canonical records with re-derived `dependencies` and rewritten `progress:` blocks
- `IMPROVEMENT_PLAN.md` — the 27-record active queue in optimized execution order
- `OPEN_DECISIONS.yaml` — re-checked at this binding

Artifacts **new in r2**:

- `INHERITED.yaml` — which artifacts are carried forward unchanged, and why each is
- `_reconciliation/CURRENT_STATE_RECONCILIATION.yaml` — the audit ledger: binding, method, per-record disposition class, and every corrected or invalidated claim

Artifacts **carried forward byte-identical** from the predecessor:

`ARCHITECTURE.md`, `LAWS_AND_INVARIANTS.md`, `EXPERIENCE_REPORT.md`,
`FRICTION_AND_FAILURES.md`, `environment_inventory.yaml`, `experience.yaml`,
`failures.yaml`, `friction.yaml`, and `_reconciliation/{CORPUS,LINEAGE,SOURCE_MAP,
COMPLETENESS_MATRIX,RECONCILIATION_LEDGER,CONFLICTS}.yaml`.

They are unchanged because this revision reconciles *delivery state*, not the source-pack
reconciliation those files record. Their provenance is untouched, and `INHERITED.yaml`
states the reason for each individually rather than as a blanket claim.

## Architecture summary

Unchanged from the predecessor, and re-confirmed by this pass: the most damaging recurring
seam is coarse state. One-word `READY`/`DEGRADED` hides transport-specific and
ownership-specific reality. Four of this pass's live findings are that same seam —
`memory: DEGRADED` collapsing a working CLI transport and a 502ing MCP transport
(CI-005); `toolchain ready` over a log with no exit code (CI-009); five components
reporting bare `DEGRADED` with no reason or log path (CI-004); and skill-usage logging
reporting nothing because it is enabled and reaching no disk (CI-021).

## Current status

**CANONICAL_PACK_RECONCILED_AT_59f03a5d_WAVE_1_PUBLISHED_PR360_OPEN.** No conflict was
silently resolved. Three completion claims were tested against their own acceptance criteria
and did not survive; each demotion is recorded with the evidence rather than applied quietly.
Wave 1's delivery is recorded as a second, separately stamped binding — the assessment's
fields keep their original meaning, and each touched record retains its
`residual_as_assessed` beside the delivered one.

## Current roadmap

Four lanes open at once. **L0** takes the critical chain — `CI-004` then `CI-005`, the two
heaviest records, one gating the other. **L1** leads with `CI-012`. **L2** opens with
`CI-002`. **L3** opens with **CI-007**, the live standing breakglass grant and the queue's
highest-leverage item. Makespan 11 effort units at 4 lanes, 7 at 6 lanes, saturating at 7.
Full schedule and every dropped edge: `PROGRESS.md` → *Optimized execution order*.

After wave 1 the critical path is unchanged — `CI-004` → `CI-005`, weight 6, neither touched
— and **35 of 42** effort units remain across **19 of 26** execution units. The makespan
lower bound at 4 lanes falls to **9**; the achievable makespan is not restated, because
removing seven units changes which pairs collide and that needs the scheduler re-run rather
than an arithmetic adjustment.

## Provenance

Every record retains its predecessor ID, its `previous_progress`, and its source-record
lineage into `_reconciliation/SOURCE_MAP.yaml`. Every status change carries the evidence
that produced it. Every removed dependency edge carries the reason it no longer holds.
Nothing was renumbered to express the new order — order lives in `optimized_sequence`.
