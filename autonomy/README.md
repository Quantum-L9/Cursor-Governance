# L9 Enforceable Autonomy Control Plane

Wave 1 converts autonomy orchestration from IDE convention into validated,
machine-readable contracts.

## Properties enforced

- Campaigns require resolved base SHAs.
- Autonomous merge, admin merge, and force push are forbidden.
- Executors require synthesis inputs.
- Mutation roles require exclusive write claims.
- Read-only roles cannot request write claims.
- Reviewers must be independent from executors.
- Reviews must consume verifier outputs.
- Every action declares a typed completion artifact.
- Role cardinality is validated before execution.
- Action graphs must be acyclic and dependency-complete.

## Compile the W7 graph

Replace the example base SHA first:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("autonomy/examples/w7-campaign.json")
data = json.loads(path.read_text())
data["base_state"]["commit_sha"] = "YOUR_RESOLVED_BASE_SHA"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
```

Compile:

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

Validate:

```bash
python -m autonomy.validation.graph_linter \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --deployment autonomy/examples/w7-deployment.json
```

Run tests:

```bash
python -m unittest discover -s autonomy/tests -v
```

## Wave boundaries

Wave 1 only compiles and validates authority and topology.

It intentionally does not yet grant leases or mediate tools. Runtime mutation
must remain disabled until Wave 2 is installed and its capability gateway is
active.

---

# Wave 2 — Enforcement Runtime

Wave 2 installs the runtime that enforces the Wave 1 graph.

## Runtime properties

- SQLite-backed durable campaign state.
- Exactly one active lease per action.
- Resource claims are checked transactionally.
- Write claims are exclusive.
- Agent identity is bound to each lease.
- Leases must be acknowledged before tools are authorized.
- Role capabilities are enforced at the tool gateway.
- Campaign operation and path scope are enforced.
- Global merge, force-push, secret, and test-weakening capabilities are denied.
- Heartbeat base-SHA drift revokes the lease.
- Typed artifacts are checked against action completion predicates.
- Dependency artifacts must remain valid.
- Accepted artifacts complete actions and release claims.
- Runtime decisions are appended to a hash-linked receipt chain.
- Optional HMAC receipt signatures use `L9_AUTONOMY_RECEIPT_KEY`.

## Compile the graph

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

## Bootstrap the runtime

```bash
python -m autonomy.runtime.cli \
  --root . \
  bootstrap \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --graph .l9/autonomy/w7-compiled-graph.json
```

## Inspect ready work

```bash
python -m autonomy.runtime.cli \
  --root . \
  ready \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Issue a lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  lease \
  --campaign-id autonomy-w7-mothball-2026-08-02 \
  --action-id campaign-coordinator \
  --agent-id cursor-agent-001
```

## Acknowledge the lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  ack \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect \
  --capability graph.inspect \
  --capability scheduler.request \
  --capability status.inspect
```

## Authorize a tool call

```bash
python -m autonomy.runtime.cli \
  --root . \
  authorize \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect
```

A denied authorization exits non-zero.

## Heartbeat

```bash
python -m autonomy.runtime.cli \
  --root . \
  heartbeat \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --base-sha YOUR_RESOLVED_BASE_SHA \
  --status running \
  --progress-json '{"completed_units":3,"total_units":8}'
```

## Submit a typed artifact

```bash
python -m autonomy.runtime.cli \
  --root . \
  submit \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --artifact path/to/artifact.json
```

The artifact envelope must match:

```json
{
  "artifact_id": "artifact-unique-id",
  "kind": "CampaignStatus",
  "campaign_id": "autonomy-w7-mothball-2026-08-02",
  "graph_id": "compiled-graph-id",
  "action_id": "campaign-coordinator",
  "lease_id": "lease-id",
  "producer_agent_id": "cursor-agent-001",
  "base_sha": "resolved-base-sha",
  "input_artifacts": [],
  "payload": {
    "campaign_id": "autonomy-w7-mothball-2026-08-02",
    "state": "EXECUTING"
  }
}
```

## Sweep stale leases

```bash
python -m autonomy.runtime.cli \
  --root . \
  sweep
```

## Verify receipt integrity

```bash
python -m autonomy.runtime.cli \
  --root . \
  verify-receipts \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Runtime database

The default database is:

```text
.l9/autonomy/runtime.sqlite3
```

Do not commit it. `.l9/` is already gitignored.

## Security boundary

Wave 2 mediates capability decisions in the runtime. The IDE must still be
wired so every relevant tool invocation calls the gateway before execution.
Wave 3 supplies the Cursor and Claude Code adapters, conformance checks,
deployment handshake, pipeline simulator, and negative/chaos validation.

---

# Wave 3 — Mandatory IDE Deployment and Conformance

Wave 3 makes Cursor and Claude Code constrained orchestration clients.

## Enforcement boundary

An IDE may not start autonomous work unless:

1. its adapter configuration passes every blocking conformance check;
2. the requested action is READY in the compiled DAG;
3. the scheduler selects the action under resource capacity;
4. the runtime issues a lease bound to one agent identity;
5. the agent acknowledges the exact role capability set;
6. every tool call passes through the capability gateway;
7. heartbeats preserve lease and base-SHA validity;
8. completion is represented by a valid typed artifact;
9. required verifier and reviewer dependencies complete;
10. human authorization and merge gates remain outside autonomy.

## Adapter doctor

```bash
python -m autonomy.validation.doctor \
  --root . \
  --adapter autonomy/examples/adapters/cursor.json

python -m autonomy.validation.doctor \
  --root . \
  --adapter autonomy/examples/adapters/claude-code.json
```

A missing executable is a blocking failure in production. Do not set
`allow_missing_executable_in_test` outside tests.

## Register an adapter

```bash
python -m autonomy.wave3_cli \
  --root . \
  register-adapter \
  --config autonomy/examples/adapters/cursor.json
```

## Deploy / ack / authorize / heartbeat / submit / status

See `python -m autonomy.wave3_cli --help` for `deploy`, `ack`, `authorize`,
`heartbeat`, `submit`, and `status`. Deploy supports `--render cursor` or
`--render claude-code` and injects `L9_ADAPTER_SESSION_ID`.

## Simulate before execution

```bash
python -m autonomy.wave3_cli \
  --root . \
  simulate \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --output .l9/autonomy/w7-simulation.json
```

## JSON-line bridge and tool hooks

```bash
python -m autonomy.adapters.bridge --root .
python -m autonomy.adapters.tool_hook --phase pre
python -m autonomy.adapters.heartbeat_hook
```

The pre-tool hook requires `L9_ADAPTER_SESSION_ID`, `L9_CAMPAIGN_ID`,
`L9_ACTION_ID`, `L9_AGENT_ID`, `L9_LEASE_ID`, and `L9_BASE_SHA`. Unknown tools
fail closed.

## Production rule

Do not expose direct repository mutation tools alongside the mediated adapter.

```text
IDE task → adapter session → runtime lease → capability gateway → tool
```

A direct side channel around the gateway is a deployment defect and must block
campaign start.

---

# Wave 4 — Swarm Concurrency

Wave 4 removes artificial serialization from the control plane without moving
the authority boundary. The invariant:

```text
MAXIMIZE LEGAL PARALLELISM.

No independent READY action may remain idle while compatible execution
capacity exists.

Read-only work is bounded by available capacity.
Mutation work is bounded by actual claim conflict, not by global serialization.
Concurrency never expands authority.
```

## What bounds a cycle

| Bound | Source | Effect |
|---|---|---|
| Provider ceiling | `resource-classes.json` → `global.provider_concurrency_ceiling` | Absolute upstream slot count (500) |
| Control reservation | `global.reserved_control_slots` | Keeps 20 slots for coordinator/synthesis/retry traffic → 480 worker slots |
| Class capacity | `classes.<name>.capacity` | Per-workload-family pool |
| Campaign budgets | campaign `budgets.max_{read,mutation,poll}_agents` | Campaign authority ceiling on *concurrent* read / mutation / poll workers |
| Role cardinality | deployment `required_roles.<role>.max` | Authorization ceiling on concurrent workers of a role |
| Claims | claim registry | Mutation collision prevention |

`fill_policy: saturate` (the default) means the scheduler admits **every**
remaining legal action until one of those bounds is hit.

Behavioral global fields: `provider_concurrency_ceiling`,
`reserved_control_slots`, `fill_policy`, `adaptive_backpressure`. Descriptive
fields, kept because they document intent: `target_total_concurrency`,
`force_parallel_ready_actions`, `backfill`, `mutation_parallelism`,
`read_parallelism`, and per-class `target_concurrency` / `min_concurrency` —
saturation already admits everything legal, and the scheduler never manufactures
or promotes work to reach a floor.

## Caller batch limits cannot serialize the swarm

```python
scheduler.next_actions(campaign_id, limit=4)  # ignored under saturate
scheduler.next_actions(campaign_id, hard_limit=4)  # explicit safety ceiling
```

`limit` is the legacy caller batch size: under `fill_policy: saturate` it is
recorded in telemetry and ignored. `hard_limit` is a deliberate safety ceiling
and always truncates.

## Mutation concurrency

Mutation actions are limited by claim conflict, not by a global writer count.
Disjoint exclusive claims run concurrently; overlapping ones do not:

```text
mutate-auth  claim repo:addons-auth   ┐
mutate-api   claim repo:addons-api    ├─ all admitted in one cycle
mutate-docs  claim repo:docs          ┘

mutate-a     claim repo:shared        ┐
mutate-b     claim repo:shared        ┴─ one admitted, one stays READY
```

`autonomy.runtime.claims.claims_collide` is the single compatibility rule:
the registry enforces it transactionally at lease time (and stays
authoritative), the scheduler pre-filters admission with it, and the linter uses
it to tell a real ordering constraint from a serialization-only edge.

**Known limitation:** claim keys are opaque identifiers, so `repo:addons/auth`
and `repo:addons/auth/security.py` do **not** collide. Overlapping scopes must
be declared under the same claim key to serialize.

## Bottleneck telemetry

Silent underutilization is a scheduler defect, so every cycle attributes every
non-admitted READY action:

```python
cycle = runtime.scheduler.next_cycle(campaign_id)
print(cycle.render())
```

```text
ready=287 running=191 selected=224 available_global_slots=289
blocked_dependency=31 blocked_claim=12 blocked_resource_capacity=20
blocked_campaign_budget=0 blocked_role_cardinality=0 blocked_global_capacity=0
blocked_unknown_resource_class=0 blocked_human_gate=0
```

`cycle.underutilized()` is true when READY work was left idle while global
capacity remained. `AutonomyRuntime.status()` publishes the same counters under
`scheduling`.

## Provider backpressure

When the provider throttles (HTTP 429), report it instead of shrinking batch
sizes locally:

```python
runtime.scheduler.record_provider_throttle()  # multiplicative decrease
runtime.scheduler.record_provider_recovery()  # additive increase
```

Both are governed by `global.adaptive_backpressure` and only ever move the
effective provider ceiling — never a capability, scope, or claim.

## Wide graphs, not deep graphs

A 480-slot scheduler is worthless against a chain. The compiler publishes
`parallel_layers`, `max_parallel_width`, and `serial_depth` on every compiled
graph, and the linter fails closed on serialization-only edges:

| Code | Severity | Meaning |
|---|---|---|
| `PIPE-SERIAL-SIBLING` | ERROR | Same role and kind, no conflicting claim: emit as siblings, or declare `metadata.serialization_justification` |
| `PIPE-RESOURCE-CLASS-UNKNOWN` | ERROR | Action names a class the resource policy does not declare |
| `PIPE-RESOURCE-CLASS-MUTATION` | ERROR | Mutation action parked in a read-only class |
| `PIPE-RESOURCE-CLASS-WIDTH` | WARNING | Read-only action occupying a mutation class |

Human gates, cross-kind pipeline steps, and genuinely conflicting claims are
never flagged.

## Background execution

`autonomy.adapters.claude_code.adapter.BACKGROUND_ROLES` runs every
parallel-safe analytical role in the background: `context_compiler`, `recon`,
`synthesis`, `verifier`, `reviewer`, `failure_classifier`, `poller`, `sentinel`,
`evidence_writer`.

Mutation roles (`MUTATION_ROLES`) are foreground by default and background on
request:

```python
build_claude_task(deployment, background_mutation_roles=True)
```

That flag only decides whether one orchestrating session detaches its writers —
the scheduler already admits non-conflicting mutations concurrently either way.
Leases, mandatory hooks, heartbeats, claims, and `L9_DIRECT_TOOL_ACCESS=0` /
`L9_AUTONOMOUS_MERGE=0` are identical in both modes.

## Editing policies

`autonomy/policy_loader.py` is generated — the JSON under `autonomy/policies`,
`autonomy/examples`, and `autonomy/tests/golden` is the source of truth:

```bash
make autonomy-policy-embed   # re-embed after editing any of that JSON
make autonomy-policy-check   # fail on drift (also covered by the test suite)
```

## Authority is unchanged

Nothing in Wave 4 touches capability enforcement, filesystem containment, lease
validation, claim validation, mandatory hooks, campaign authorization,
direct-tool restrictions, or the human-only merge gate. Concurrency increases
throughput only.
