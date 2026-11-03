---
name: Close the weak cron tests
overview: Close the weak-cron campaign on the current workspace. tests/cron_contract.py
  must pass the suite naming test. Offer and load fail-closed counts must be the rows
  that sort before the fixture. The claim reminder must be created once, or the test
  fails closed when that batch cannot reach the claim. Midnight recompute, logistics
  escalation, and monthly audit must fail if the method returns immedia...
todos:
- id: suite-name
  content: Add cron_contract.py to NON_TEST_FILES in tests/test_suite_structure.py.
    Do not rename the module and do not give it a test_ function.
  status: completed
- id: sort-prefix
  content: After the fixture exists, fail closed when the count of rows that sort
    strictly before it is already at the cron limit. Offer includes same valid_until
    with a lower id. Load SLA includes null entered_state_at and the same timestamp
    with a lower id. Do not assert the write when that count is at the limit.
  status: completed
- id: claim-reminder
  content: Count the pending sort prefix after create and fail closed at 300 before
    asserting escalated. Count the reminder sort prefix and fail closed at 300 before
    asserting the activity. Otherwise require exactly one Open Claim Reminder for
    that claim after the first call and the same count after the second. Invalidate
    the resolved claim before the last state read. Pass a non-empty resolution_note
    on every resolved claim create.
  status: completed
- id: live-effects
  content: 'Midnight: on the test-owned claim, SQL-set stored is_overdue false while
    opened_at stays in the past, then the cron must set it true; fail closed when
    open claims are already at 1000. On the test-owned document, SQL-set expiry_date
    to yesterday and is_expired false, then the cron must set is_expired true; fail
    closed when that document search is already at 1000. Do not assert days_open;
    it is not stored. Escalation: one awaiting_ready load created with the freight
    write token and entered_state_at 100 hours ago becomes sla_breached true and stays
    in that state; fail closed when SLA-state loads are already at 500. Audit: when
    commission_locked is on plasticos.transaction, a closed transaction this test
    creates must produce a WARNING containing Monthly audit:; when the field is absent,
    fail with that fact and do not skip. A draft transaction''s name must not appear
    in that warning.'
  status: completed
- id: unreachable
  content: Add UNREACHABLE_IN_DOMAIN on the Odoo-free registry for cron_check_missing_docs,
    cron_check_scale_tickets, and cron_geo_backfill, each with the reason create_date
    cannot be aimed or the path calls Nominatim. The XML lock asserts that set equals
    those three methods. Keep the Odoo tests negative-only and state that reason in
    the test docstring. Do not add a positive assert for those three.
  status: completed
- id: prove
  content: Run ruff check and ruff format on the edited test files, ci/weak_test_fixer.py,
    the suite naming test, the XML lock, the four validator modules, and tests/test_weak_test_authority.py.
    Do not run Docker.
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Close the weak cron tests

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `close-the-weak-cron-tests_ae3b04e1.plan.md`

## Objective (from PLAN_DOCUMENT)

Close the weak-cron campaign on the current workspace. tests/cron_contract.py must pass the suite naming test. Offer and load fail-closed counts must be the rows that sort before the fixture. The claim reminder must be created once, or the test fails closed when that batch cannot reach the claim. Midnight recompute, logistics escalation, and monthly audit must fail if the method returns immediately, by asserting the stored field or log the live method changes. Missing-docs, scale-ticket, and geo backfill stay negative-only and are named unreachable. No production cron edit, addon loader, Docker run, or scanner change.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | tests/test_suite_structure.py::TestTestFileNaming::test_test_files_start_with_test passes with cron_contract.py listed in NON_TEST_FILES | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | Offer and load fail-closed counts include every row that sorts before the fixture, including same-key lower ids and null entered_state_at | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | The claim SLA test requires one Open Claim Reminder activity, or fails closed with the reminder-batch count, and invalidates the resolved claim before the last state read | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | A no-op midnight recompute leaves is_overdue false and is_expired false; the live cron sets both true on the test-owned stale rows | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | A no-op _cron_escalation_check leaves sla_breached false; the live method sets it true on the SLA load | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | A no-op run_monthly_audit emits no Monthly audit warning; the live method emits that warning when commission_locked exists | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-07 | UNREACHABLE_IN_DOMAIN is exactly cron_check_missing_docs, cron_check_scale_tickets, and cron_geo_backfill, and the XML lock asserts that set | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-08 | python3 ci/weak_test_fixer.py reports no assertion-free tests, and pytest passes the XML lock, the four validator modules, and tests/test_weak_test_authority.py | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** tests/test_suite_structure.py NON_TEST_FILES entry for cron_contract.py, tests/cron_contract.py unreachable-effect registry, tests/test_cron_xml_lock.py lock of that registry, tests/integration/test_cron_idempotency.py sort-prefix counts and reachable effects, tests/test_cron_runtime.py out-of-domain pairs, resolution_note, and negative-only reasons

**Out:**
- Production cron bodies, manifests, ACL, and module version bumps
- ci/weak_test_fixer.py and the extended-audit baseline
- An addon test loader or any edit that puts these files on --test-enable
- A Docker or make test-module run as proof
- SQL backdating of create_date for missing docs or scale tickets
- An addressed partner or a Nominatim call for geo backfill
- Mocking pg_try_advisory_lock
- tests/integration/test_offer_state_machine.py TestOfferCronExpiry
- pipeline_v2.py and plasticos_base production code
- Unrelated dirty files already in this detached checkout

## Critical path (seed)

sort-prefix → claim-reminder → live-effects → unreachable → prove

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Five test files. No model, cron XML, manifest, or scanner. Rollback is restoring those paths.
- Rollback: git restore -- tests/test_suite_structure.py tests/cron_contract.py tests/test_cron_xml_lock.py tests/integration/test_cron_idempotency.py tests/test_cron_runtime.py

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: Design is closed. P3 is the known naming failure this plan fixes, and V1-V4 run at Build. U1 and U2 are accept_bounded.
- execute_via: cursor-build

---

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.
- After Build todos complete: scoped-commit of the five `may_modify` paths only, `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply must display the opened PR URL. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.plasticos.close-weak-cron-tests.v1` |
| name | Close the weak cron tests |
| overview | Close the weak-cron campaign: suite naming, sort-prefix fail-closed counts, reachable effects, and a named unreachable set |
| schema_version | `1.0.0` |
| status | `current` |
| is_project | false |
| owner | cursor-build |
| created_at | 2026-10-28 |
| updated_at | 2026-10-28 |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `l9-plan-simple` cursor-build, GAR 0.8.4 upstream |
| plan_class | `remediation_plan` |
| redesign_allowed | false |
| follow_on_schema_evolution_separate | true |
| framing_notes | First-Order looked for one change that would make the rest unnecessary. None exists: the suite allowlist, each cron search order, and each stored effect have different owners. The intervention stays test-contract repair. The L9 architecture profile was loaded and is not PlasticOS inventory. Depth is standard. Memory prefetch HIT, conflicts 0, digest `84285faaaf0ae34c9b231c0df0fb2c0098797dc2f04b98b31dc5e64450f3ee44`. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | 2026-10-28T21:49-04:00 |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| ssot_clone | `~/.cursor-governance` |
| branch | detached HEAD |
| commit_sha | `079a13df3c4c963a7c16bcb3f07f9cf32a8b5cd7` |
| dirty | true |
| artifact_hashes | PLAN_DOCUMENT validated by `validate_plan_document.py` |
| allowed_local_dirt | The five `may_modify` paths may already be dirty from this campaign. Every other dirty path stays unstaged. |
| overlap_policy | `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make the cron tests fail when the live method is a no-op or when the fixture is outside the batch, and name the three methods whose in-domain write cannot be reached.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | `cron_contract.py` is an allowed non-test module | quality_gate | `pytest tests/test_suite_structure.py::TestTestFileNaming::test_test_files_start_with_test` exits 0 | true |
| SP-02 | Offer and load fail-closed counts are the sort prefix | structural | The count domain in each test matches the cron `order` and `limit` | true |
| SP-03 | Claim reminder is one activity, or the test fails closed | structural | First activity count is 1 and the second equals it, unless the reminder prefix is already 300 | true |
| SP-04 | Midnight stale `is_overdue` and `is_expired` become true | structural | Pre-call reads are false; post-call reads are true | true |
| SP-05 | Escalation sets `sla_breached` on the SLA load | structural | Pre-call false, post-call true, state stays `awaiting_ready` | true |
| SP-06 | Monthly audit emits its warning | structural | `assertLogs` sees `Monthly audit:` when `commission_locked` exists | true |
| SP-07 | The unreachable set is exactly three methods | quality_gate | `tests/test_cron_xml_lock.py` exits 0 | true |
| SP-08 | Scanner and pure pytest stay green | quality_gate | V1, V2, V3, and V4 exit 0 | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.plasticos.close-weak-cron-tests.v1` |
| source_ref | `plan.plasticos.close-weak-cron-tests.v1` |
| phase_id | `preflight` |
| blocking | true |
| immutable_baseline_ref | detached `079a13df3c4c963a7c16bcb3f07f9cf32a8b5cd7` |
| baseline_verified | true at plan time |
| drift_detected | false |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P3 | suite naming | `python3 -m pytest tests/test_suite_structure.py::TestTestFileNaming::test_test_files_start_with_test -q` | Fails today on `cron_contract.py`. Passes after `suite-name`. | true |
| P4 | hook catalog | `.pre-commit-config.yaml` is the catalog for V4 | File present at the workspace root | true |

## Execution envelope

Mutations outside this envelope are forbidden.

### Filesystem

- **write_allow:** `tests/test_suite_structure.py`, `tests/cron_contract.py`, `tests/test_cron_xml_lock.py`, `tests/integration/test_cron_idempotency.py`, `tests/test_cron_runtime.py`
- **write_deny:** production cron Python, cron XML, manifests, `ci/weak_test_fixer.py`, `tests/conftest.py`, `tests/__init__.py`, `tests/integration/test_offer_state_machine.py`, `pipeline_v2.py`
- **delete_allow:** none

### Commands

- **allow:** `ruff check`, `ruff format`, `python3 ci/weak_test_fixer.py`, `python3 -m pytest` on the modules named in V3, `pre-commit run --config .pre-commit-config.yaml --files` on the five paths
- **deny:** Docker test targets, `make update`, raw `git push`, and a campaign run

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | none |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | true |

### Autonomous merge

`autonomous_merge:` false. This plan publishes with `make pr` and does not merge.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| suite-name | filesystem_mutation | safe_to_repeat | retry_once | git restore of that file | false |
| sort-prefix | filesystem_mutation | safe_to_repeat | retry_once | git restore of that file | false |
| claim-reminder | filesystem_mutation | safe_to_repeat | retry_once | git restore of those files | false |
| live-effects | filesystem_mutation | safe_to_repeat | retry_once | git restore of those files | false |
| unreachable | filesystem_mutation | safe_to_repeat | retry_once | git restore of those files | false |
| prove | filesystem_read | safe_to_repeat | retry_once | none | false |

The SQL updates inside `live-effects` run only when an Odoo test later loads the file. They update the row that test created, by primary key, and TransactionCase rolls them back. They are not part of this plan's filesystem proof.

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| suite-name | test suite naming | assurance | `tests/test_suite_structure.py` NON_TEST_FILES | renaming the registry into a fake test |
| sort-prefix | cron batch reachability | assurance | offer `valid_until ASC, id ASC` limit 500; load `entered_state_at ASC, id ASC` limit 500 | asserting a write the prefix cannot reach |
| claim-reminder | claim SLA cron | assurance | pending limit 300 and reminder limit 300 | treating two zero counts as idempotency |
| live-effects | midnight, escalation, audit | assurance | stored `is_overdue`, stored `is_expired`, `sla_breached`, audit warning | asserting `days_open` or document `name` |
| unreachable | missing docs, scale tickets, geo | assurance | `UNREACHABLE_IN_DOMAIN` | a positive assert or a Nominatim call |
| prove | pure pytest | assurance | V1-V4 | Docker as a substitute proof |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.plasticos.close-weak-cron-tests.v1` |
| source_execution_ref | `plan.plasticos.close-weak-cron-tests.v1` |
| supported | true |
| automatic_allowed | false |
| approval_required | false |
| trigger_conditions | A proof command fails, or a may_modify diff touches a denied path |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | the five may_modify paths |
| data | `none` | no database migration |
| external_state | `none` | no network |
| local_state | `git_restore_scoped_paths` | same five paths |

### Irreversible operations

- None. Do not publish unrelated dirty files from this detached checkout.

### Rollback verification

- `git diff --` the five paths is empty after restore, and the other dirty paths are unchanged.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | medium |
| uncertainty | medium |
| blast_radius | low |
| architectural_boundaries_crossed | none |
| external_systems_touched | none |
| migration_required | false |
| unknown_dependency_count | 2 |

U1 is whether the first read after the SQL update recomputes the stored field. U2 is whether an open PR exists at Build. Both are accept_bounded.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.plasticos.close-weak-cron-tests.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| suite-name | tests | assurance | none | NON_TEST_FILES contains `cron_contract.py` |
| sort-prefix | tests | assurance | none | offer and load counts match the sort prefix |
| claim-reminder | tests | assurance | sort-prefix | reminder count is 1, or fail closed at 300 |
| live-effects | tests | assurance | claim-reminder | stale stored fields and the audit warning |
| unreachable | tests | assurance | live-effects | the three-method set is locked |
| prove | tests | assurance | suite-name, unreachable | V1-V4 |

`suite-name` may run beside `sort-prefix`. The cron test files are edited in the chain `sort-prefix` then `claim-reminder` then `live-effects` then `unreachable`.

**Critical path:** sort-prefix → claim-reminder → live-effects → unreachable → prove

**Forbidden edges:** any edge into a production cron, cron XML, manifest, scanner, or addon `__init__.py`

### Sort prefix

Offer, after the past-due offer exists. Fail with the count and do not assert `expired` when the count is at least 500.

```python
[
    ("state", "in", ("draft", "sent", "responded")),
    ("id", "!=", past_offer.id),
    "|",
    ("valid_until", "<", past),
    "&",
    ("valid_until", "=", past),
    ("id", "<", past_offer.id),
]
```

Load SLA, after the load exists. Null `entered_state_at` sorts first. Fail with the count and do not assert `sla_breached` when the count is at least 500.

```python
[
    ("state", "in", ("awaiting_ready", "ready_confirmed", "rate_confirmed", "scheduled", "dispatched")),
    ("id", "!=", load.id),
    "|",
    ("entered_state_at", "=", False),
    "|",
    ("entered_state_at", "<", entered),
    "&",
    ("entered_state_at", "=", entered),
    ("id", "<", load.id),
]
```

### Claim

Pass `resolution_note="Cron test resolution"` on every resolved create. Invalidate that claim before the state read that follows the second call.

Pending prefix, after create, before asserting `escalated`. Fail closed at 300.

```python
[
    ("state", "=", "pending"),
    ("id", "!=", claim.id),
    "|",
    ("opened_at", "<", opened),
    "&",
    ("opened_at", "=", opened),
    ("id", "<", claim.id),
]
```

Reminder prefix, after the first call has escalated the claim. Fail closed at 300 and do not assert the activity. Otherwise the activity count for summary `Open Claim Reminder: {name}` and `date_deadline` today is 1, and the second call leaves it at 1.

```python
[
    ("state", "in", ("pending", "in_progress", "escalated")),
    ("id", "!=", claim.id),
    ("last_reminder_at", "=", False),
    "|",
    ("opened_at", "<", claim.opened_at),
    "&",
    ("opened_at", "=", claim.opened_at),
    ("id", "<", claim.id),
]
```

### Midnight, escalation, audit

`days_open` is computed and not stored. Do not assert it.

Claim staleness, only when open claims before create are under 1000. The table name must be `plasticos_claim`. Parameterize the id. No f-string SQL.

```python
self.env.cr.execute(
    'UPDATE "plasticos_claim" SET is_overdue = FALSE WHERE id = %s',
    [claim.id],
)
```

Invalidate, read `is_overdue`, and require false. Then `_cron_midnight_recompute` must set it true.

Document staleness, only when documents with `expiry_date <= today`, `is_expired` false, and `active` true are under 1000. The table name must be `plasticos_document`. Set `expiry_date` to yesterday and `is_expired` false. A document expiring today stays false, because `_compute_is_expired` uses a strict less-than.

```python
self.env.cr.execute(
    'UPDATE "plasticos_document" SET expiry_date = %s, is_expired = FALSE WHERE id = %s',
    [fields.Date.today() - timedelta(days=1), document.id],
)
```

Invalidate, read `is_expired`, and require false. Then the cron must set it true. If either pre-call read is already true, stop at checkpoint C2.

Escalation uses the freight token imported inside the test function. Create `state="awaiting_ready"` and `entered_state_at` 100 hours ago. Fail closed when SLA-state loads are already 500 before create. The first `_cron_escalation_check` sets `sla_breached` true. The state stays `awaiting_ready`. The second call leaves both. The draft-load test stays the out-of-domain pair.

Audit copies the cron domain, including `commission_locked` when that field is on `plasticos.transaction`. Fail closed when that violation count is already 500 before create. A closed transaction this test creates must make `assertLogs` on `odoo.addons.plasticos_transaction.models.audit_cron` see a WARNING containing `Monthly audit:`. If `commission_locked` is absent, fail with that fact. Do not skip. A draft transaction keeps its state, and its name is absent from that warning.

### Unreachable set

`UNREACHABLE_IN_DOMAIN` is exactly:

- `cron_check_missing_docs` — `create_date` cannot be aimed, and the status rule needs age
- `cron_check_scale_tickets` — same `create_date` order, and a new row is not old enough
- `cron_geo_backfill` — an addressed partner calls Nominatim

The lock test asserts set equality. The Odoo tests for those methods stay negative and say so in the docstring. Do not SQL-backdate `create_date`. Do not create an addressed partner.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E1 | SP-01 | quality_gate_evidence | pytest | the suite naming test | exit 0 | not_run |
| E2 | SP-02 SP-03 SP-04 SP-05 SP-06 | structural_evidence | source read | the count domains and SQL statements above are in the test files | present | not_run |
| E3 | SP-07 SP-08 | quality_gate_evidence | pytest and ruff | V1 V2 V3 V4 | exit 0 | not_run |

The Odoo cron files stay unloaded. E2 is the contract those files enforce when Odoo loads them. Do not claim a Docker run.

## Stress and disconfirm

### Disconfirming cases

- One registry constant does not fix the search orders or the stored effects. Those stay separate todos.
- Expiry of today does not flip `is_expired`. The compute is `expiry_date < today`. The stale date is yesterday.
- `days_open` cannot prove the cron. It is recomputed on read.
- An audit warning about other rows does not name this test's row. The 500 fail-closed count is what puts the new closed row inside the batch. The no-op failure is the missing warning.
- The three unreachable methods have no honest positive assert without backdating `create_date` or calling Nominatim. Both are refused.

### Assumption failure conditions

- If the pre-call read of `is_overdue` or `is_expired` is already true, C2 stops that test.
- If `commission_locked` is absent, the audit test fails closed.
- A resolved claim with an empty `resolution_note` raises the existing constraint.
- Staging any path outside `may_modify` publishes unrelated dirt from this detached checkout.

### Blast radius notes

- Five test files. No model, cron XML, manifest, or scanner.

### Rollback constraints

- Restore only those five paths. Leave the rest of the dirty tree as it was.

## Out of scope

- Production cron bodies, manifests, ACL, and module version bumps
- `ci/weak_test_fixer.py` and the extended-audit baseline
- An addon test loader, or any edit that puts these files on `--test-enable`
- A Docker or `make test-module` run as proof
- SQL backdating of `create_date` for missing docs or scale tickets
- An addressed partner or a Nominatim call for geo backfill
- Mocking `pg_try_advisory_lock`
- `TestOfferCronExpiry`
- `pipeline_v2.py` and `plasticos_base` production code
- Unrelated dirty files in this detached checkout
- Architecture redesign
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening a scanner or a gate to obtain a pass

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.plasticos.close-weak-cron-tests.v1` |
| source_ref | `plan.plasticos.close-weak-cron-tests.v1` |
| current_state | `partial` |
| implementation_ready | true for the five test files. Proof commands run at Build. |

### Gates

- **executable_when:**
  - baseline reverified at Build start
  - DAG acyclic
  - envelope limited to the five paths
  - U1 and U2 remain accept_bounded
- **complete_when:**
  - V1, V2, V3, and V4 exit 0
  - the diff is only the five paths
  - `make pr` has displayed a PR URL
- **blocking_conditions:**
  - a pre-call stale read is already true
  - a denied path is edited
  - baseline of a may_modify file drifted from this campaign's edits
  - a proof command fails

### Evidence

- **required_evidence_refs:** E1, E2, E3
- **observed_evidence_refs:** P3 failed at plan time on `cron_contract.py`; `validate_plan_document.py` passed
- **missing_evidence:** E1, E2, E3 until Build

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | A flush may recompute the stored field before the cron | accept_bounded |
| unknown | U2 | An open PR may exist when Build starts | accept_bounded |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | V1 through V4 during Build |
| minimum_safe_next_action | Press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| broader_work_requires_separate_contract | true for any cron body change, addon loader, or Docker proof |

## Build evidence (auto)

- detected_at: `2026-10-29T01:58:09Z`
- conversation_id: `07d954b9-d92d-4df5-a528-abd67ec58f69`
- generation_id: `8f30a271-66e0-4b25-8c44-2e28532ea665`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/07d954b9-d92d-4df5-a528-abd67ec58f69/07d954b9-d92d-4df5-a528-abd67ec58f69.jsonl`
- todos at build time:
- `suite-name`: completed
- `sort-prefix`: completed
- `claim-reminder`: completed
- `live-effects`: completed
- `unreachable`: completed
- `prove`: completed
