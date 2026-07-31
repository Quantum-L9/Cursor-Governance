<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/WORK_CLAIM_PROTOCOL.md
layer: protocol
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Work-Claim Protocol — how N agents share one memory without duplicating work

Namespace grants (the hard layer, enforced server-side by l9-graphiti-memory's
`NamespacePolicy`) decide **where** an agent may write. This protocol (the soft
layer, enforced by every adapter's session bootstrap) decides **what** an agent
may start, so two agents holding the same namespace never do the same task twice.

## 1. The claim episode

Before starting any discrete unit of work, an agent writes a claim episode to the
repo's shared `group_id`:

| Field | Value | Rule |
|---|---|---|
| kind | `procedure` | claims are procedural memory |
| source | the agent's registry `source` | attribution |
| claim_key | `sha256(group_id + "\n" + normalized_title)` | deterministic; `normalized_title` = lowercase, trimmed, whitespace-collapsed task title |
| body | JSON: `{"type":"task-claim","claim_key":...,"task":...,"agent_id":...,"role":...,"status":"claimed","expires_at":<ISO8601, now+TTL>}` | status transitions below |
| TTL | 4h default, 24h max | stale claims are reclaimable |

The `claim_key` doubles as the idempotency key. The memory server's deterministic
admission and idempotency layer returns a **`duplicate` outcome** for a second
identical claim — the losing agent gets a definitive, race-safe signal that the
task is taken. No new server feature is required; this rides entirely on
guarantees the control plane already ships (deterministic admission, idempotency,
supersession).

## 2. Status transitions

```
claimed ──▶ in_progress ──▶ done
   │              │
   └──▶ released ◀┘        (agent gives the task back)
   (expired: expires_at passed — anyone may reclaim)
```

Transitions are written as **supersession** episodes carrying the same
`claim_key`, so the graph keeps full bi-temporal lineage of who held what, when.
Only the claim holder (matching `agent_id`) or an `orchestrator` role may
supersede a live claim; the orchestrator is the arbiter for conflicts and
stale-claim cleanup.

## 3. The mandatory pre-work search

Every session bootstrap (all adapters) injects this rule into the agent context:

> Before starting a task: (1) `search` the repo `group_id` for `task-claim`
> episodes matching the task; (2) if an unexpired claim by another agent exists,
> DO NOT start — pick other work or coordinate through the orchestrator; (3)
> otherwise write your claim and verify the outcome is `complete`, not
> `duplicate`; (4) on `duplicate`, re-search — you lost the race; (5) write
> `done` (with a short result summary) or `released` when you stop.

## 4. Role-based division of work

Overlap is further reduced by routing work types to roles at claim time:

| Work type | Eligible roles |
|---|---|
| Architecture / plan / promotion decisions | orchestrator |
| Code implementation, PR remediation | implementer |
| Research, analysis, cross-repo builds, docs | researcher-builder |
| PR review, CI triage episodes | reviewer |
| (read-only surfaces never claim) | observer |

An agent MUST NOT claim work outside its role's row. The orchestrator may
explicitly delegate across rows by writing the claim itself with an
`assigned_to: <agent_id>` field; the assignee then supersedes it to
`in_progress`.

## 5. Attribution invariants (why duplication stays detectable)

Every episode any agent writes carries its registry identity (`user_id`,
`agent_id`, `source`) under its own bearer token. Because identities are unique
and tokens are never shared (validated by `validate_agents.py`; authenticated
per-token by the memory server), any duplicated artifact in the graph is
attributable to exactly one agent — making duplication auditable and the claim
protocol enforceable after the fact, not just by convention.
