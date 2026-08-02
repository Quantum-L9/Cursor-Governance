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
