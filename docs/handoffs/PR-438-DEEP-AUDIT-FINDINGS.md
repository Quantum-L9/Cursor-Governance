# PR #438 — deep forensic audit findings

**Subject:** `Quantum-L9/Cursor-Governance` PR #438, head `f47e3df60034d5750bb50a1fc1e4b3c89eb5b0e4`,
base `main` @ `da0c7530df837d417a1437f9d08b5d8e61ba4a10`.
**Audit date:** 2026-09-01 · **Mode:** read-only, exact head · **Verdict:** REQUEST_CHANGES.

This document records what the audit found. The stacked PR carrying it also fixes
the subset of findings that had one unambiguous correct answer **and no competing
open PR**; each of those is marked **FIXED HERE**.

Two org-CI findings (F-09, F-13) are marked **ROUTED TO PR #449** instead. The
attempt to land them was blocked by the PR overlap gate: #449 is open on the same
two files on a different lineage. That block was correct, and the fix is described
in full rather than applied, so it can land where the files are already owned.

Everything else is left for the author to decide, on purpose — an auditor picking
between two defensible designs is not a fix.

---

## 1. What PR #438 actually contains

The description says six files, "Documentation", "Low risk". The head carries
**26 files**, two workstreams, and runtime Python.

The second workstream is not rogue: **PR #439 was opened with base
`agent/cursor/cg437-ruleset-kit` and merged into it at 03:26:11** — sanctioned
bottom-up stacking under `rules/48` and `rules/53`. What went wrong is only that
#438's description was never regenerated afterward.

| Workstream | Files | Content |
|---|---|---|
| A — org-CI ruleset activation kit | 11 | `RUNBOOK.md` (new, replaces `README.md`), hardened `apply.sh` / `verify.sh`, regenerated evaluate payload, 5 evidence artifacts |
| B — PE unified-loop seams (from #439) | 14 | `pec/dispatch.py`, `pec/signals.py`, controller call sites, routing policy row, `collect_evidence --memory-lookup`, 2 test files, 3 manifests |
| C — CI config | 1 | `.l9/ci.json` — `repo_class: python` |

---

## 2. Governing trackers

Two authorities, resolved separately rather than collapsing them into one.

| Workstream | Tracker | How authority was established |
|---|---|---|
| A | **Issue #437** (closed `completed`), 10 acceptance criteria | The only tracker naming the kit. No JSON tracker exists; the machine claims file (`l9-ci-core/.l9/org-runtime-interface.yaml`) lives in another repository. |
| B | **`docs/plans/backlog/pe_unified_loop_8-20-26.plan.json`**, SC-01…SC-08 / todo-01…todo-08 | Title matches the head commit; `receipts/unified-loop-baseline.json` records `GMP-133` and `origin_main: da0c7530…`, which **is** this PR's base SHA. |

**No handoff document existed.** The de facto handoff is the PR body plus six PR
comments. This file is the first written handoff for the work.

---

## 3. Tracker reconciliation — 18 items, 7 correct, 11 mismatched

### B — `pe_unified_loop_8-20-26.plan.json`

| ID | Status | Note |
|---|---|---|
| SC-01 | PARTIAL | Baseline SHA correct; branch deviation documented in the receipt. But the shipping branch carries the whole org-CI kit, so "clean tree, no foreign files" is not met. |
| SC-02 | **NOT_IMPLEMENTED** | The 8 admission/gate fixes are absent. Markers `named_roots`, `heredoc`, `session_id` are absent at base and no golden admission loop test exists. **todo-02 is on the declared `critical_path` and is a declared dependency of todo-05 and todo-06.** |
| SC-03 | PARTIAL | Probe / invoke / map / `worker_cannot_self_verify` all real. Missing: `identity_binding`/`peer_readiness` profile resolution, `peer_execution.runner` subprocess thin providers, Worker Brief, context manifest. |
| SC-04 | **CONTRADICTED_BY_CODE** | See F-02. |
| SC-05 | COMPLETE_AND_PROVEN | |
| SC-06 | IMPLEMENTED_NOT_PROVEN | Emission works; the test asserted key presence only. Carried defect F-01. |
| SC-07 | PARTIAL | Codex row and `CAPABILITY_UNSUPPORTED` are real; `peer_execution/tests/` was not extended. |
| SC-08 | COMPLETE_AND_PROVEN | |

**The tracker itself was never advanced.** At head the plan is still in
`docs/plans/backlog/`, `convergence.status` is `"partial"`, and FV-00…FV-04 all
read `status: "pending"`. Implementation is ahead of the tracker — the safer
direction, but unreconciled.

### A — Issue #437

Correct: 3 (ruleset applied/visible), 4 (head-SHA correlation), 5 (ACTIVE only
after clean evaluation), 7 (evidence committed), 10 (one ruleset, one ID).

Not met at close: **2** (no dry-run artifact), **6** (see F-04), **8**
(`org-runtime-interface.yaml` untouched — it is in `l9-ci-core`), **9** (rollback
recorded but never rehearsed). Criterion 1 rests on an unverified premise (U1).

The issue was closed `completed` at 03:19:26 with those four open.

---

## 4. Findings

### F-01 — CRITICAL · confirmed · **FIXED HERE**
`pec/controller.py` — `_claim_autonomy_projection` caught only `ImportError`, but
`map_program_contract` calls `require_coherent_actions`, which deliberately raises
`ContractActionError(ValueError)` on an incoherent action set. The call sits
**after** `db.transition_task(…, "LEASED")` and `ledger.append("TASK_LEASED", …)`,
and `Ledger.append` writes and closes immediately, so the event is durable.

Reproduced before the fix:

```
claim_task RAISED: ContractActionError - contract requests 'commit' without 'local_write'.
ledger events.jsonl: [... 'TASK_BECAME_ELIGIBLE', 'TASK_LEASED']
next_tasks: {"in_progress": [{"id": "TASK-001", ...}]}
```

The task is durably leased and `in_progress`; the caller receives an exception and
no lease token, branch, or worktree. Unclaimable by anyone, recoverable only by
hand. A projection the plan explicitly scopes as emission-only must never be able
to fail a claim that already committed.

**Fix:** the mapper call is wrapped so it cannot raise out. It records
`autonomy_projection_error` on the lease rather than returning silently — the
Validate & Repair kernel's "prefer explicit errors over silent failure", satisfied
without reintroducing the raise that was the defect, so a broken mapper and "this
task has no contract to project" no longer look identical.
Regression: `test_claim_survives_a_projection_that_raises` — raises from
`contract_mapper` itself rather than patching the guard away, and asserts the lease
returns, the task is `in_progress` under *this* caller, and the error is recorded.

### F-02 — HIGH · confirmed · **NOT fixed — author's call**
`pec/signals.py` docstrings claim *"optional OutcomePublisher projection"* and
*"OutcomePublisher is best-effort projection."* Neither is true: the module never
imports or calls it. The real class exists at
`integrations/subagent-generated-data/outcome_publisher.py` and `run_campaign.py`
uses it, so this is not a missing dependency — the seam was simply not wired.
`receipt_projection`, also named in todo-04, is likewise unused.

SC-04 requires the call explicitly. **Either wire `outcome_publisher` at the four
call sites so SC-04 is genuinely met, or delete both claims and mark SC-04
partial.** That choice commits the tracker to an interpretation, so the author
makes it. A docstring asserting a projection that does not exist is worse than an
absent one; this should not be left as-is.

### F-03 — HIGH · confirmed · **FIXED HERE**
`pec/signals.py` serialized `"receipt_keys": sorted(receipt)` — the receipt's key
*names*. An actual job:

```json
{"accepted": false, "event": "record-attempt",
 "receipt_keys": ["attempt","receipt","status","task_id"]}
```

No `task_id` value, no digest, nothing distillable. The only test asserted a
filename substring, so it passed regardless.

**Fix:** jobs now carry a bounded `subject` (whitelisted scalar fields only, so a
job never becomes a second copy of controller state) plus `receipt_digest`.
`receipt_keys` is retained. Regression: `test_distill_job_carries_a_usable_subject`.

### F-04 — HIGH · confirmed · **NOT fixed — needs a live re-run**
Neither committed evidence artifact was produced by the code at head.

| Time | Event | Code in force |
|---|---|---|
| 03:15:41 | advisory canary captured (head `919b2e37`) | pre-guard `verify.sh` |
| 03:17:28 | `promoted-at` value | — |
| 03:19:04 | **LIVE_CANARY_PASS** captured (head `4e2d4e9d`, new run) | **pre-guard `verify.sh`** |
| 03:21:18 | `724f20b6` adds the `promoted-at` guard **and hand-writes `evidence/promoted-at`** | — |

`apply.sh` only began writing `promoted-at` in `724f20b6`; the promotion at
03:17:28 ran the earlier version, which wrote nothing. The file is a hand-authored,
backdated reconstruction committed alongside the guard that consumes it.

The substance is sound — the post-promotion canary genuinely used a **new head and
a new run** (`4e2d4e9d` / `33353393558`, distinct from the advisory `919b2e37` /
`33353209085`), and the value sits one second before the `LIVE_ENFORCING` capture.
But the guard has never gated anything and its input is not machine-generated.
**Re-run `bash verify.sh --pr Quantum-L9/l9-observability-core 4` at this head** to
convert it into real evidence.

### F-05 — HIGH · confirmed · **NOT fixed — operational**
Check run `99372135089` on head `f47e3df6`, `Analyze (central Core)` — **failure**:

```
error[unresolved_strict_contract]: strict mode requires a policy for non-empty findings
MODE: blocking   LANGUAGE: python   exit code 6
```

`.l9/ci.json` worked (language resolved). The failure is a missing semgrep policy.
This is the workflow the ruleset requires, now **ACTIVE across `~ALL` repositories
on `~DEFAULT_BRANCH` with `bypass_actors: []`**.

The runbook's own Phase 3 STOP reads: *"If it appears and fails … **STOP. Do not
activate organization-wide blocking enforcement.**"* At 03:12 the record shows
org-ci failing on **both** this PR and the canary. The canary cleared by 03:15:41;
this repository did not — it was red at promotion time (03:17:28) and is red now.
A single designated canary was used to justify a `~ALL` blast radius while a
second known-failing repository was in view.

**Either supply the semgrep policy, or demote to `evaluate`
(`ALLOW_DEMOTE=1 DRY_RUN=0 MODE=evaluate bash apply.sh`) until the governance
repo's own org-ci is green.**

### F-09 — MEDIUM · confirmed · **ROUTED TO PR #449**
`verify.sh` wrote `remote-end-to-end-run.json` **unconditionally** — including on a
failed conclusion, a non-Actions app, or a failed post-promotion clock check — and
wrote `organization-ruleset-live-enforcement.json` from inside `check_ruleset`,
before `check_run` could fail. `evidence/README.md` then tells an operator to
promote those files into liveness claims.

**PR #449 (`agent/cursor/org-ci-closure-ev`) does not fix this** — it enriches both
payloads with schema, source_type, check_run_id and Actions run/job ids, but keeps
`organization-ruleset-live-enforcement.json` inside `check_ruleset` and
`remote-end-to-end-run.json` unconditional at the end of `check_run`. Richer
evidence written on the same failing paths.

**Proposed fix, not applied here.** This audit's own attempt to land it was
correctly blocked by the PR overlap gate: #449 is open on the same two files on a
different lineage, and a sibling PR would have been the split-ownership the gate
exists to prevent. The change belongs on #449:

- move both `jq` writes into one `write_evidence` function;
- call it only after `FAILED` is final **and** the enforcement state has been
  named, so an indeterminate state writes nothing either;
- have the failure paths print `no evidence written` so the operator sees why.

### F-13 — LOW · **ROUTED TO PR #449**
`evidence/README.md` omits `promoted-at` from its "written by / when" table, though
it is load-bearing for `LIVE_CANARY_PASS`. Same file collision as F-09, same
routing. Add the row, and state the write discipline above alongside it.

### F-12 — MEDIUM · confirmed · **FIXED HERE**
`tests/test_unified_loop_seams.py` asserted
`assertIn(status, {"ROUTED", "UNSUPPORTED"})` — the only two values the function
can return. It could not fail.

**Fix:** the assertion names the real behavior. Doing so surfaced something the
tautology had hidden: the standard fixture contract declares no `action_class`, so
the CLI dispatch plan is `UNSUPPORTED` with `fallback: manual_worker_brief` — the
render-contract dispatch seam never actually routes under the test fixture. That
is now asserted explicitly rather than obscured.

### F-14 — LOW · confirmed · **FIXED HERE**
Distill job filenames used one-second granularity, so two same-event signals inside
one second silently overwrote each other. Now microsecond-stamped. Regression:
`test_two_signals_in_one_second_do_not_overwrite`.

### Also fixed here — signal writes are fail-soft
Same defect class as F-01: all four `publish_controller_event` call sites run after
the controller has transitioned state and appended its ledger event. A queue write
that raised — full disk, read-only mount, an uncanonicalisable receipt — would
surface as a failed controller operation that in fact succeeded. Observability is
not authority. Regression: `test_signal_failure_never_fails_the_operation`.

### Remaining, not fixed here

| ID | Sev | Finding |
|---|---|---|
| F-06 | MEDIUM | SC-02 / todo-02 unimplemented while on the critical path |
| F-07 | MEDIUM | PE plan tracker never advanced (`backlog/`, `partial`, all FV `pending`) |
| F-08 | MEDIUM | PR #438 description: 6 files, "Documentation", "Low risk" — all wrong at head |
| F-10 | MEDIUM | SC-03 / SC-07 partial: no profile resolution, no thin providers, `peer_execution/tests/` not extended |
| F-11 | MEDIUM | `.l9/ci.json` — `l9.ci-consumer/v1` and `repo_class` appear nowhere else in this repo: no schema, no validator, no test |
| F-15 | LOW | `apply.sh` post-write invariant counts the exact name only, not the legacy-decorated family the read path matches |
| F-16 | LOW | `apply.sh` ID-receipt assertion is skipped when `EXISTING` is empty — a recorded id plus a deleted ruleset falls through to CREATE |
| F-17 | LOW | `verify.sh` selects `.[0]` from a display-name regex; ordering is not guaranteed latest-first and the name is not proof the run came from the required workflow |
| F-18 | INFO | `sys.path` mutation at call/import time in `controller.py` and `dispatch.py` |

---

## 5. Handoff / PR-description corrections required

| Claim | Verdict |
|---|---|
| "Changed files" — 6 listed | **CONTRADICTED** — 26 |
| "Type of Change: Documentation" | **CONTRADICTED** — ships runtime Python, routing policy, CI config |
| "Risk: Low — additive, reversible, no contract change" | **CONTRADICTED** — activated org-wide blocking enforcement; modified the controller claim path |
| "L4 receipt present: head=`b746ae74`" | **STALE** — 7 commits behind head `f47e3df6` |
| "Do not run MODE=active without a new human letter" (03:16:48) → ACTIVE at 03:17:28 | **UNSUPPORTED** — no letter appears in the record |
| "All main-protection required checks are green" | **PARTIALLY_CONFIRMED** — true for main-protection; `Analyze (central Core)` is failing |
| "CI green — not measured … do not treat as verified" | **CONFIRMED** — accurate and appropriately hedged |
| "Unresolved threads: 0" | **CONFIRMED** — both Codex threads resolved with real fixes |
| "#439 merged into this branch" | **CONFIRMED** |
| "Language detect unblocked via `.l9/ci.json`" | **CONFIRMED** — CI log shows `LANGUAGE: python` |

---

## 6. What was good

Worth recording, because the findings above are not the whole picture:

- The ruleset **identity defect the kit set out to fix is genuinely fixed** — both
  payloads carry one `.name` and differ only in `.enforcement`, and `apply.sh`
  refuses to run if that stops being true.
- `apply.sh` fails closed at eight distinct preconditions and its `MODE=active`
  may-not-create rule is exactly right: promotion is never a first write.
- `verify.sh` naming four states instead of a bare `PASS` is the correct fix for
  "an advisory ruleset reported as live enforcement."
- `org-rulesets.before.json` proves no canonical ruleset pre-existed, so the
  CREATE was legitimate and no split identity ever occurred.
- Both Codex review findings were resolved with real code, not acknowledgement.
- The three generated manifests verify byte-exact at head.
- The runbook correctly moved the canary **before** promotion, and records the
  org-wide direct-push blast radius as a Phase 0 precondition.

---

## 7. Validation evidence

Executed locally at head (three declared dependencies — `structlog`, `jsonschema`,
`pydantic`, all in `pyproject.toml` — were absent from the sandbox and installed;
no test was altered to accommodate the environment):

| Command | Result |
|---|---|
| `pytest tests/` — controller-template/scripts | 116 passed (pre-fix) |
| `pytest tests/ops/autonomy/` (FV-02, criterion "56+") | 602 passed, 2 subtests |
| `pytest tests/` — PE/scripts | 380 passed, 25 subtests |
| `validate_manifest.py` | `{"status": "PASS", "errors": []}` |
| `validate_pair.py … --mode template` | `{"status": "PASS", "mode": "template", "errors": []}` |
| Manifest recomputation | `MANIFEST.json` 563/563, `core` 199/199, template 98/98 — zero drift |

Remote CI at head `f47e3df6`: 22 check runs — 20 success, 1 skipped, **1 failure**
(`Analyze (central Core)`, see F-05).

Each fix in this PR was verified by reverting it and confirming its regression test
fails, then restoring it.

---

## 8. Unresolved UNKNOWNs

- **U1** — The claim *"every `/orgs/{org}/rulesets` endpoint, GET included, requires
  organization `Administration: write`, so the read succeeding IS the authority
  proof"* (asserted in `apply.sh`, `verify.sh` and `RUNBOOK.md` Phase 0) could not
  be verified: the GitHub REST docs page does not render the per-endpoint
  fine-grained-permission block. If GET requires only `read`, the gate is a weaker
  proof than documented. Practical risk is low — a false positive still fails at
  `POST`/`PUT` rather than writing anything wrong — but the wording would be wrong.
- **U2** — `Quantum-L9/l9-observability-core` is outside the audit session's
  repository scope, so check run `33353393558` on head `4e2d4e9d` could not be
  independently confirmed to have `started_at` ≥ `2026-08-31T03:17:28Z`. The
  distinct head SHA and run ID are consistent with a genuine post-promotion run.
- **U3** — Whether the eight admission/gate fixes of todo-02 landed via some other
  PR. Three of four distinctive markers are absent at base and no golden admission
  loop test exists, so the balance of evidence is that they did not; the eight were
  not exhaustively enumerated.
