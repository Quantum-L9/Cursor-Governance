# PE / Agent-Swarm / Memory Remediation — Findings

**Plan:** `pe-swarm-memory-remediation-v1` · **Base SHA:** `d20ad7457eae463877425eec863bfc0048f9542c`
**Repository:** `Quantum-L9/Cursor-Governance` · **Executed:** 2026-08-27

Dependency-ordered execution of the seven-task remediation program. Wave 0 and
the trace half of Wave 1 were read-only; Wave 1's worktree proof and Wave 2's
E2E are executed tests, not static reads.

## Disposition summary

| Task | Root cause | Disposition | Code change |
|---|---|---|---|
| TASK-01 | RC-1 parallel distillation pipeline | **DISTINCT_NON_OVERLAPPING** — no duplication | none |
| TASK-02 | RC-2 legacy replay path | **PARTIALLY_CONFIRMED** — `drive` clean, `reset` bypasses | none (guard specified) |
| TASK-03 | RC-4 decorative policy keys | **CONFIRMED** — 12 decorative keys | none (VALIDATE_ONLY) |
| TASK-04 | RC-5 provider fallthrough | **REFUTED** — both adapters fail closed | none |
| TASK-05 | RC-3 outbox drain | **ESCALATED (P0-adjacent)** — no drain exists | none — stop condition fired |
| TASK-06 | RC-6 worktree isolation | **CONFIRMED_CLOSED** — proven live | new test |
| TASK-07 | RC-7 E2E coverage gap | **CLOSED** — E2E written and wired to CI | new test + CI step |

No task introduced a new controller, scheduler, concurrency policy, agent
lifecycle, result gateway, generated-data pipeline, or memory writer.

---

## TASK-01 — RC-1: distillation pipelines are distinct, not duplicated

**Disposition: `DISTINCT_NON_OVERLAPPING`.** No consolidation required; no
canonical owner needs retiring.

The two directories share a shape — a queue ending at Graphiti — and nothing
else. There is not one import edge between them.

| | `ops/graphiti/distill_queue/` | `generated-data/orchestration/delivery_worker.py` |
|---|---|---|
| Input | raw session transcript excerpt | validated generated-data packet |
| Producer | `ops/graphiti/hydration/close_session.py:528-549` (SessionEnd) | `ingress/ingest.py` |
| Schema | `distill_queue_job/v1` | `MemoryCandidate` 1.0.0 |
| Queue substrate | S3 (`MEMORY_DISTILL_S3_BUCKET`) | local filesystem |
| Trigger | SessionEnd hook | campaign outcome publish |
| Drain | `.github/workflows/memory-distill.yml`, cron `0 */6 * * *` | **none — see TASK-05** |
| Terminal write | `graphiti_memory_client.call_tool("add_memory")` (`worker.py:376`) | `GraphitiMemoryAdapter` → transport |

**Evidence:** a repository-wide search for `distill_queue` returns 21 files and
for `delivery_worker` returns 3; the two sets are disjoint.

The asymmetry in the last two rows is the real finding, and it belongs to
TASK-05: the transcript pipeline has a scheduled drain, the generated-data
pipeline does not.

---

## TASK-02 — RC-2: `drive` delegates, `reset` does not

The audit treated `replay_campaign.py` as one undifferentiated legacy path. Its
three subcommands have three different authority postures.

### `drive` — CLEAN, no change needed

`drive_campaign` reaches admission through `run_campaign_until`
(`replay_campaign.py:250-258`), which subprocesses
`run_campaign.py --intent <path> --until execute`. Admission, authority, and
lease checks all run in the canonical front door exactly as `make campaign` runs
them. **This satisfies TASK-02's primary acceptance criterion.**

### `materialize` — SCOPE-BOUNDED, lease-unaware (LOW)

`materialize_task` (`replay_campaign.py:183-229`) writes only into
`workspace/worktrees/<task_id>/`, only to paths listed in the rendered
contract's `writable_paths`, and refuses to run without both an existing
worktree and an existing rendered contract. It writes no runtime state.

Gap: nothing checks that the task is currently leased or dispatched. The
contract bounds *what* may be written; nothing bounds *when*.

### `reset` — CONFIRMED `DIRECT_STATE_BYPASS` (the real RC-2)

`reset_campaign` (`replay_campaign.py:309-357`) performs four destructive
operations with **no guard of any kind** — no confirmation flag, no active
campaign check, no admission path:

1. Relocates the live program directory `~/.l9/programs/<campaign_id>` into
   `stale/` via `shutil.move` — durable Program state moved wholesale
   (lines 327-329).
2. Renames every `pec/*` branch to `retired/*` (lines 335-341).
3. Rewinds the target to a base SHA with a branch-recreating checkout
   (lines 342-344).
4. Forcibly repoints `campaign/<id>` at that base (line 347).

It is directly invokable and will silently diverge campaign state from the
canonical stage machine if a campaign is live.

**Specified guard** (implementation deferred — TASK-02 is `VALIDATE_ONLY`, and
the plan routes any resulting change to a separately authorized task):

> In `reset_campaign`, before the relocation at line 327, require both:
> (a) an explicit `--confirm-destructive` flag on the `reset` subparser, and
> (b) a check that `~/.l9/programs/<campaign_id>` holds no campaign in a
> non-terminal state — read the PEC status already available through
> `pec_status_tasks()` and refuse with `ReplayError` when any task is not
> `COMPLETED`.
> Both conditions use machinery already present in the module. No new
> architecture is required.

Note also that `pec_status_tasks` sets `L9_ALLOW_PEC_DIRECT=1` (line 232). That
call is read-only (`pec status`) and therefore acceptable, but the module does
hold a bypass token.

---

## TASK-03 — RC-4: 12 decorative resource-class policy keys

**First, an audit-premise correction.** The plan records four keys as "confirmed
live": `max_mutation_agents`, `max_poll_agents`, `max_read_agents`,
`provider_concurrency_ceiling`. Only the last is a resource-classes key. The
three `max_*_agents` keys belong to a different config plane entirely — campaign
budgets, declared in `autonomy/schemas/campaign-authorization.schema.json:114-116`
and read at `scheduler.py:373` via `campaign.get("budgets", {})`. They never
appear in `autonomy/policies/resource-classes.json`.

`load_policy("resource-classes")` resolves to
**`autonomy/policies/resource-classes.json`** — RC-4's stated unknown, resolved.

### Live keys

| Key | Consumer |
|---|---|
| `global.provider_concurrency_ceiling` | `scheduler.py:92`, `simulator.py:107` |
| `global.reserved_control_slots` | `scheduler.py:77`, `simulator.py:113` |
| `global.fill_policy` | `scheduler.py:73` |
| `global.adaptive_backpressure.enabled` | `scheduler.py:116` |
| `global.adaptive_backpressure.decrease_factor` | `scheduler.py:128` |
| `classes.<c>.capacity` | `scheduler.py:281`, `simulator.py:110,122` |
| `classes.<c>.mutation` | `graph_linter.py:377` (`_check_resource_classes`) |

### `DECORATIVE_POLICY` — zero non-test consumers

| Key | Risk | Proposed disposition |
|---|---|---|
| `classes.<c>.preemptible` (15 classes) | **Highest.** No preemption exists anywhere in the scheduler. An operator reading policy would believe read classes yield under pressure. They do not. | remove, or implement |
| `classes.<c>.min_concurrency` (15 classes) | A floor guarantee never honored; only `capacity` gates admission. | remove |
| `classes.<c>.target_concurrency` (15 classes) | Implies a target distinct from `capacity`; only `capacity` is read. | remove |
| `classes.<c>.fill_policy` | Only the *global* `fill_policy` is read. | remove |
| `classes.<c>.conflict_policy` | Decorative but **safe**: the scheduler enforces claim conflicts unconditionally via `_claims_conflict`, stricter than the declared value. Asserted only by `test_policy_embedding.py:68`. | remove, or document as descriptive |
| `global.target_total_concurrency` | Never read; the effective ceiling is `provider_concurrency_ceiling - reserved_control_slots`. | remove |
| `global.force_parallel_ready_actions` | Behavior is unconditional under `fill_policy: saturate`. | remove, or document |
| `global.backfill` | Never read. | remove |
| `global.mutation_parallelism` | Descriptive label; actual behavior is claim-based. | document as descriptive |
| `global.read_parallelism` | Descriptive label. | document as descriptive |
| `global.adaptive_backpressure.on_429` | Descriptive; `record_provider_throttle` hardcodes multiplicative decrease. | document as descriptive |
| `global.adaptive_backpressure.recovery` | Descriptive; `record_provider_recovery` hardcodes `step = ceiling // 50`. | document as descriptive |

Every decorative key's *named* behavior matches what the code actually does,
except `preemptible` and `min_concurrency`, which name behavior that does not
exist at all. Those two are the ones that can mislead an operator about an
enforced ceiling.

The second declaration of these values embedded in
`autonomy/policy_loader.py:200-295` is a fallback copy, not a consumer.

---

## TASK-04 — RC-5: no provider fallthrough; both adapters fail closed

**Disposition: `AMBIGUOUS_PROVIDER_FALLTHROUGH` REFUTED. No fix required.**

The audit's framing assumed the adapters contain "provider/model resolution
functions". They do not. Neither adapter binds a model at all — each emits a
`subagent_type` and leaves model selection to the host. `no_provider_default_is_invented`
and `no_role_model_binding_is_invented` therefore hold structurally: there is
nothing to invent. The only `model` reference in the layer is a nullable
telemetry column (`host_bridge.py:55,277,318`), never a selection input.

Every resolution branch raises:

| Site | Behavior |
|---|---|
| `claude_code/adapter.py:36` | `ValueError` on adapter_type mismatch |
| `claude_code/adapter.py:129` | `ValueError` on unknown role — no default |
| `cursor/adapter.py:55` | `ValueError` on adapter_type mismatch |
| `cursor/adapter.py:124` | `ValueError` on unknown role — no default |
| `cursor/adapter.py:91-93` | `ValueError` on missing required task field |
| `protocol.py:51,55,58` | `ValueError` on empty field, unsupported type, bad metadata |

Both adapters read contract fields with bracket subscript (`contract["role"]`),
raising `KeyError` on absence. No `.get()` with a default appears on any
authority-bearing field. This matches the `identity_binding.py` precedent the
audit named as the required standard.

### The permissive-looking default is correct

`protocol.py:65-66` defaults `direct_tool_access` and `autonomous_merge` to
`True` when absent, while every `supports_*` flag defaults to `False`. That
reads backwards but composes correctly, and deliberately so:

- `adapter-config.schema.json:13-14` marks both fields **required**.
- Conformance `ADAPTER-004` / `ADAPTER-005` (`conformance.py:105,113`) require
  each to be exactly `False`.

An omitted field therefore yields `True`, which **fails** conformance and denies
admission. Had it defaulted to `False`, an omitted field would silently pass.
The default direction is the fail-closed one.

### Two LOW observations (no action taken)

1. **Prompt/enforcement divergence.** `cursor/adapter.py:162` renders claims with
   `claim.get("exclusive", False)`; the scheduler uses
   `claim.get("exclusive", mode == "write")` (`scheduler.py:416`). An agent is
   told a write claim is non-exclusive while the scheduler treats it as
   exclusive. Enforcement is on the stricter side, so this is a truthfulness
   defect in the contract text, not a mutation-safety defect.
2. **Dead mapping entries.** `CURSOR_ROLE_TO_RESULT_KIND` contains `test`,
   `documentation`, and `verifier_reviewer`, none of which appear in
   `_cursor_subagent_type`'s mapping — such a role raises at line 124 before
   `_result_contract` is ever reached. Unreachable entries.

---

## TASK-05 — RC-3: **ESCALATED.** No memory-outbox drain exists

**The plan's stop condition fired. `campaign_summary.py` was deliberately NOT
modified.**

> TASK-05 stop condition: *"If no drain mechanism exists at all, stop before
> implementing the summary change and escalate — this is a P0-adjacent finding
> (silent memory loss risk) requiring its own dedicated remediation task, not a
> summary cosmetic fix."*

### Finding: `FIRE_AND_FORGET_MEMORY` is realized, not theoretical

Nothing in the repository reads
`environment/agents/generated-data/.runtime/memory-outbox`. An exhaustive search
across every file type returns five references, all writers or configuration:

| Reference | Role |
|---|---|
| `adapters/graphiti_memory.py:23` | outbox path constant |
| `adapters/graphiti_memory.py:83` | `FileOutboxTransport.__init__` |
| `orchestration/delivery_worker.py:48` | config default |
| `orchestration/delivery_worker.py:550,620` | transport wiring |
| `integration/end_to_end_golden.py:104` | test harness (also a writer) |
| `config/instantiation.example.yaml:14` | example config |

Corroborating negatives: no `drain` keyword anywhere in source; no cron, hook,
launchd unit, or GitHub workflow references `generated-data` except
`l9-lint-test.yml`; no Make target invokes `delivery_worker`.

### Why this matters

`memory_mode` defaults to `"outbox"` (`delivery_worker.py:45`). In the default
configuration a promoted memory candidate is written to local disk and stays
there permanently. `campaign_summary.py:185-186` then counts receipt status
`enqueued` / `already_enqueued` as `memory_candidates_submitted`. A stalled
pipeline and a healthy one are indistinguishable in the operator summary — the
exact condition RC-3 predicted.

Contrast with the transcript pipeline (TASK-01), which has a scheduled GHA drain
every six hours. The generated-data pipeline was built with the same
enqueue-before-network discipline and never received its drain.

### Partial credit where due

`campaign_summary.py` is honest about what it does *not* measure:
`memory_units_persisted` and `memory_units_retrievable` are `None`, rendered as
`UNKNOWN` (lines 56-60, 253-256), as is `distilled_units`. The module never
claims persistence. The gap is that it cannot distinguish *enqueued and
progressing* from *enqueued and abandoned* — and today every candidate is the
latter.

### Recommended dedicated task (out of this plan's scope)

1. Decide the drain owner. The `distill_queue` GHA worker is the closest
   precedent; a scheduled workflow draining the outbox through
   `HttpJsonTransport` would reuse the proven shape without adding a pipeline.
2. Only then extend `campaign_summary.py`'s memory section with a
   backlog/staleness indicator, following the existing `None` → `UNKNOWN`
   pattern. Adding that field first would be a speculative field over an unfixed
   pipeline.

**Guarded meanwhile:** `test_enqueued_is_not_reported_as_persisted`
(`tests/hardening/test_real_campaign_e2e.py`) asserts the current truthful state
— `enqueued` never presented as accepted or persisted — so a regression that
starts claiming persistence fails CI. That test is the one to revisit when a
drain lands.

---

## TASK-06 — RC-6: worktree isolation proven live

**Disposition: `CONFIRMED_CLOSED`. No shared worktree and no shared git index
observed. No P0 halt.**

New: `environment/program-execution/tests/hardening/test_concurrent_worktree_isolation.py`
— 7 tests, all passing.

### Correction to the plan's isolation unit

The plan names `run_campaign.py::isolate_worktree` as the per-child boundary. It
is not. `isolate_worktree` (`run_campaign.py:596-647`) creates **one worktree per
campaign** (`feat/<campaign_id>`), isolating a campaign from the primary clone.
The per-action boundary for concurrent children is `GitWorktreeLane`
(`peer_execution/autonomy/worker_lane.py`), whose path is
`lane_root/<campaign_id>/<action_id>`. The proof targets the latter — proving
concurrency on `isolate_worktree` would have proven the wrong invariant.

### What was executed

Two lanes created on separate threads released by a `threading.Barrier`, in a
disposable sandbox repository. Without the barrier the threads would serialize on
scheduling alone and the test would pass for the wrong reason.

| Assertion | Result |
|---|---|
| Two children hold distinct worktrees simultaneously | PASS |
| Distinct resolved gitdirs; distinct `index` files; neither is the primary clone's index | PASS |
| Concurrent commits do not cross-contaminate — each lane's `HEAD` tree holds only its own file | PASS |
| Duplicate lane claim raises `FileExistsError`, never silently reuses | PASS |
| `../escape` as an `action_id` raises `ValueError` | PASS |
| Two disjoint mutation claims admitted in one cycle, `blocked_claim == 0` | PASS |
| Overlapping claim: one admitted, the other attributed under `blocked_claim`, nothing dropped | PASS |

### On "rejected" versus "serialized"

RC-6's `required_end_state` asks that an overlapping claim be "rejected (not
silently serialized without a rejection receipt)". The scheduler **serializes
with attribution**: one claimant proceeds, every other is counted under the
`blocked_claim` cycle counter. That is the correct behavior for a resource claim
— outright rejection would drop legitimate work — and the structured counter is
the receipt the requirement is really asking for. The test asserts
serialization-with-attribution, and additionally that no READY action vanishes
between admission and a terminal disposition.

---

## TASK-07 — RC-7: real campaign E2E written and wired

**Disposition: `CLOSED`.**

New: `environment/program-execution/tests/hardening/test_real_campaign_e2e.py`
— 13 tests, all passing.

### Coverage against the runbook's required scenario

| Required | Test |
|---|---|
| campaign admission | `test_campaign_admission_yields_a_scheduled_graph` |
| ≥2 concurrent same-repo disjoint children | `test_two_disjoint_children_are_admitted_in_one_bounded_cycle` |
| mutation authority before dispatch | `test_unacknowledged_lease_cannot_mutate` |
| bounded concurrency | selected ≤ `worker_concurrency_ceiling` |
| distinct worktrees, no shared git index | `test_children_execute_in_distinct_worktrees` |
| one child failure, sibling survives | `test_one_child_failure_does_not_take_down_its_sibling` |
| result harvesting, raw evidence preserved | `test_valid_generated_data_packet_is_admitted_and_harvested` |
| generated-data packet validation | `test_invalid_generated_data_packet_is_refused` |
| memory-candidate submission status | `test_memory_candidate_reaches_a_submission_status` |
| structured trace/receipt reference | delivery receipt + candidate payload assertions |
| **zero push / PR / merge** | three tests, below |

### The no-publication boundary is proven, not assumed

Three independent assertions:

1. **A live subprocess tripwire.** An autouse fixture wraps `subprocess.run`,
   `Popen`, `check_output`, and `call`, recording every argv launched anywhere in
   the module and failing the test at teardown if any matches a publication
   signature. It observes; it does not stub — a test that stubbed git would prove
   nothing about the boundary.
   `test_the_run_recorded_no_publication_subprocess` additionally asserts the
   tripwire *saw real git traffic*, so a silently broken wire fails loudly.
   Negative control executed during development: the ledger flags a remote push,
   a PR create, a PR merge, an absolute-path forced push, and a `make push`,
   while passing `git status`, a local commit, and a forced worktree removal.
2. **`refuse_publication` refuses every verb**, and `release_authorized()` is
   `False` — `test_program_execution_refuses_every_publication_verb`.
3. **No role holds a publication capability** —
   `test_no_role_may_hold_a_publication_capability` asserts that
   `pr.merge`, `pr.admin_merge`, and the forced-push capability are globally
   forbidden and that no role grants `git.push` or `pr.create`. The executor
   lease is separately proven to be denied all five.

### CI wiring — and a deliberate deviation

Added as the final step of `.github/workflows/peer-execution.yml`.

The plan specifies gating the step to PRs touching
`environment/program-execution/**` or `autonomy/**`, citing an "existing
changed-path-scoped CI pattern in this workflow". **That pattern does not exist**
— `peer-execution.yml` runs on every pull request, with only a `paths-ignore`
for `WIP/**`. Adding a `paths` selector would have *narrowed* coverage, and the
E2E also exercises `environment/agents/generated-data/**`, which neither proposed
path covers. The step therefore runs unconditionally, matching the workflow's
actual convention. The rationale is recorded inline in the workflow.

### Bonus: 9 orphaned tests recovered

`environment/program-execution/tests/hardening/` was collected by **nothing**:
root pytest ignores `environment/program-execution/tests` (`conftest.py`
`collect_ignore`), and `run_conformance.py:13` globs `tests/test_*.py`
non-recursively, missing the subdirectory. The four pre-existing counterexample
modules (9 `xfail(strict=True)` tests) had no CI runner at all. The new step is
the first thing to execute them; all 9 xfail cleanly, confirming their
counterexamples still hold.

---

## Validation evidence

```
$ PYTHONPATH=environment/program-execution python -m pytest \
    environment/program-execution/tests/hardening -q
20 passed, 9 xfailed, 2 warnings in 2.90s

$ ruff check   <both new test modules>   -> All checks passed!
$ ruff format --check <both>             -> 2 files already formatted
$ yaml.safe_load(peer-execution.yml)     -> 12 steps, valid
```

## Open items carried out of this plan

| Item | Severity | Next step |
|---|---|---|
| **No memory-outbox drain** (TASK-05) | **P0-adjacent** | dedicated task; do not fix by editing the summary |
| `replay_campaign.py reset` unguarded destructive rewind (TASK-02) | Medium | guard specified above; implementation deferred |
| 12 decorative resource-class policy keys (TASK-03) | Medium (`preemptible`, `min_concurrency`); Low (rest) | remove or implement per table |
| `materialize` is lease-unaware (TASK-02) | Low | — |
| Cursor prompt renders write claims as non-exclusive (TASK-04) | Low | — |
| Dead `CURSOR_ROLE_TO_RESULT_KIND` entries (TASK-04) | Low | — |

---

## GMP-C addendum (2026-08-30)

**Plan:** `plan.sgd.gmp_c_promotion_admission.v1` · stacked Build on unique GitHub tip PR 431.

Promotion: `routes/memory.yaml` `independent_validation_required` is `true`.
`PromotionGate.evaluate` reads `routing_decision.requires_independent_validation`.
Confidence floors `0.75` / `0.5` and high-risk designated-authority stay
unchanged. Failed PE publish does not invent `recurrence_counts`.

Cursor admission: `autonomy/adapters/cursor/mint_admission.py` wraps
`CursorHostBridge.create_admission` only. No second token store.
`ops/graphiti/distill_queue/` untouched.

Note: GitHub PR bases 429→430→431 do not match git ancestry on this tip.
GMP-A/B (`compile_units.py`, `ingest_memory_candidate.py`) are not present
here and were not re-landed.
