# Claude Code bounded-concurrency runtime

This directory turns the Claude Code environment from a single-lane session into
a resumable, policy-bounded campaign runtime. It does not create unbounded agent
freedom. It makes independent, dependency-ready work executable concurrently
when authority, isolation, validation, recovery, and durable state are present.

**Cursor SOP:** for Composer/Agent parallel Tasks and background PR-poll while
the main agent continues, use
[`skills/l9-bounded-autonomy/`](../../skills/l9-bounded-autonomy/) and `/autonomy`
(campaign authorization packet). Do not reimplement this Python scheduler in
Cursor — map the same invariants onto Task tools.

## Core invariants

1. Dependency readiness is computed from the action graph, never guessed.
2. Every mutation action declares at least one write lock.
3. Conflicting locks serialize. Distinct explicit isolation keys permit isolated lanes.
4. Waiting on CI or another external system releases a compute lane but preserves locks.
5. Campaign state is atomically persisted with a canonical SHA-256 digest.
6. Completed operation IDs are never replayed.
7. Every lane has a renewable lease and resumable cursor.
8. Parallel outputs pass a fan-in assurance barrier before downstream promotion.
9. Merge eligibility is tied to the current exact PR head SHA and all required gates.
   The runtime **proves** eligibility (`merge_coordinator`) but does **not** merge
   autonomously: `autonomous_merge=false` and `merge_pull_request` is omitted from
   the settings allow-list, so a human approves every merge. Remediation to green is
   autonomous via the `l9-pr-remediation` skill; pressing merge is not.
10. SessionStart is fail-open: degraded autonomy context never blocks Claude Code startup.

## Runtime map

| File | Responsibility |
|---|---|
| `models.py` | Typed action, runtime, resource, campaign, budget, and barrier contracts |
| `readiness.py` | Dependency validation, cycle detection, and action readiness |
| `resource_locks.py` | Read/write conflict detection and isolated-write rules |
| `scheduler.py` | Critical-path-aware, conflict-aware ready-set selection |
| `state_store.py` | Atomic durable state, digest verification, checkpoints |
| `claim_lease.py` | Renewable action leases with expiry and holder enforcement |
| `worker_lane.py` | Isolated Git worktree creation and argv-only command execution |
| `join_controller.py` | Fan-in proof, conflict, and integration validation barrier |
| `merge_coordinator.py` | Exact-SHA, required-check, review, dependency, and protection gate |
| `bootstrap.py` | Compact SessionStart campaign reconstruction and next-action summary |
| `cli.py` | Initialize campaigns, inspect durable status, compute ready sets, and evaluate merge gates |
| `profiles/pr-convergence.json` | Default campaign authority, concurrency, and merge policy |

## State location

By default, consumer repositories persist state under:

```text
.l9/autonomy/
├── campaigns/<campaign-id>.json
├── campaigns/<campaign-id>.json.lock
└── leases.json
```

Override with `L9_AUTONOMY_STATE_DIR`. Relative paths resolve inside the current
consumer workspace. Shared memory may mirror state and claims, but local state
remains digest-verified and must never be treated as authoritative after GitHub
or target identity drift.

## Default concurrency

```text
Total active compute lanes: 4
Mutation lanes:            2
```

Read-only inspections may fill remaining lanes. Mutation lanes require declared
write locks and isolated state. The scheduler is deterministic: equal scores are
resolved by `action_id`.

## Validate

```bash
python3 environment/agents/adapters/claude-code/autonomy/validate_autonomy.py

# Example campaign
python3 environment/agents/adapters/claude-code/autonomy/cli.py init \
  environment/agents/adapters/claude-code/autonomy/examples/pr-convergence-campaign.json
python3 environment/agents/adapters/claude-code/autonomy/cli.py plan example-pr-convergence
```

The validator parses all JSON contracts, compiles all Python modules, checks the
SessionStart hook, scans for unfinished implementation markers, runs the full
unittest suite, and exercises the bootstrap path.
