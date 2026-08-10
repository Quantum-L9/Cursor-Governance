<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/program-execution/adapters/gemini/README.md
layer: program-execution-adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-08-10
/L9_META -->

# Gemini Program Execution adapter (`gemini-review`)

Verifier execution adapter for the `gemini` agent identity (role `reviewer`,
`environment/agents/agent_registry.yaml`). Peer of the Gemini **surface**
adapter at `environment/agents/adapters/gemini/`.

Gemini's role is `reviewer`, so its Program Execution mapping is a
**`verifier`** adapter, not a `worker_host` — it performs independent
verification and can never mutate a worker's worktree (the routing policy
enforces `worker_cannot_self_verify`). This keeps adapter authority within the
declared role: a reviewer verifies, it does not implement.

## Status: dormant (honest coverage)

No automated Gemini verification transport ships in this repository, so the
probe reports `BLOCKED` until a `gemini` executable (or equivalent transport)
is present. The peer is registered for explicit coverage rather than being
silently absent.

| Contract | Value |
|---|---|
| adapter_kind | `verifier` |
| provider.type | `subprocess` |
| actions | `verify` |
| identity.binding | `agent_registry` (`gemini`) |
| receipts | canonical lifecycle + `verification` terminal |

## Promotion path

1. Provision a `gemini` transport on the verifier host.
2. Implement the verification dispatch bridge in `driver.py`.
3. Flip `status.default` to `conditional` in `ADAPTER.yaml` and add the adapter
   to the `verification` preference in `registry/EXECUTION_ROUTING_POLICY.yaml`.
