<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/program-execution/adapters/codex/README.md
layer: program-execution-adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-08-10
/L9_META -->

# Codex Program Execution adapter (`codex-cloud`)

Worker-host execution adapter for the `codex` agent identity (role
`implementer`, `environment/agents/agent_registry.yaml`). This is the
Controller-side answer to *"how does the Controller execute a task on the
Codex host?"* — the peer of the Codex **surface** adapter at
`environment/agents/adapters/codex/`, which answers *"how does Codex enter
L9?"*.

## Status: dormant (honest coverage)

No automated Codex execution transport ships inside this repository, so the
adapter is registered for **explicit coverage** but its probe reports
`BLOCKED` until a `codex` executable (or an equivalent transport) is present.
This closes the "silent partial coverage" gap: the `codex` peer has a declared
Program Execution mapping and either passes conformance or reports BLOCKED
truthfully — it is never silently absent.

| Contract | Value |
|---|---|
| adapter_kind | `worker_host` |
| provider.type | `subprocess` |
| actions | `inspect`, `local_write`, `artifact_production` |
| identity.binding | `agent_registry` (`codex`) |
| authority | narrows only — never widens Controller authority |
| receipts | canonical lifecycle + `attempt` terminal |

## Promotion path

1. Provision a `codex` transport reachable from the worker host.
2. Implement the dispatch bridge in `driver.py` (render contract → transport →
   map host result to an `attempt` receipt), mirroring
   `adapters/claude-code/driver.py`.
3. Flip `status.default` to `conditional` in `ADAPTER.yaml` and add the adapter
   to the `repository_implementation` preference in
   `registry/EXECUTION_ROUTING_POLICY.yaml`.
