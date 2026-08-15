<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-08-12
/L9_META -->

# Agent surface adapter contract

Every agent surface adapter is thin. Claude Code is not a gold-standard thick
adapter and no peer catches up by copying Claude implementation.

## Surface responsibilities

A surface adapter may carry only surface discovery/bootstrap, memory endpoint
configuration, identity environment examples, and references to canonical
shared policy. It MUST NOT own Program lifecycle, scheduler logic, autonomy
policy, memory semantics, execution budgets, canonical receipts, or duplicated
execution machinery.

## Memory carrier

Cloud Graphiti endpoint:

```text
https://memory.quantumaipartners.com/graphiti/mcp
```

Authentication uses `GRAPHITI_MCP_TOKEN`. Writer identity is separate and comes
from `agent_registry.yaml` through `USER_ID`, `L9_MEMORY_AGENT_ID`, and
`L9_MEMORY_SOURCE`. Surface adapters never invent a second `agent_id`.

## Secret carrier

`ops/secrets/` is the SSOT inventory for every surface. Adapters resolve through
it and keep no inventory of their own.

The bootstrap is shared, not per-surface. Every adapter calls the identical
entrypoint and passes its own surface id:

```bash
bash ops/secrets/bootstrap_agent_env.sh --check --surface <surface-id> \
  --require SONAR_TOKEN,SEMGREP_APP_TOKEN
eval "$(bash ops/secrets/bootstrap_agent_env.sh --export SONAR_TOKEN)"
```

Credential precedence is fixed by that script: `INFISICAL_CLIENT_ID` /
`INFISICAL_CLIENT_SECRET` from the surface environment first (for sandboxes with
no AWS CLI), otherwise the AWS bootstrap ref
`openclaw-igorbot/infisical-cursor-governance`.

Rules binding on every surface, present and future:

- An adapter environment file carries **bootstrap credentials only**. Adding a
  capability means registering its secret in `ops/secrets` — never appending a
  downstream token to an adapter env file.
- No adapter implements its own resolver, vault path, or bootstrap script. A
  surface-specific copy of this bootstrap is a contract violation.
- Values never reach git, logs, receipts, or chat. `--check` reports names and
  availability only.
- A provider that cannot be reached is **DEGRADED, reported, and non-fatal** —
  adapters degrade and continue rather than aborting the session.
- Refs in `openclaw-igorbot.registry.yaml` marked `provisioned: true` exist.
  A failure to resolve one is a *delivery* problem for that surface; do not ask
  a human to mint a replacement secret (`l9-aws-secrets`, CANONICAL_LAW §14).

## Executable peer carrier

Execution topology lives only in `environment/agents/PEER_RUNTIME_BINDINGS.yaml`.
Each binding declares:

```yaml
surface: claude-cli
provider_ref: claude-code-direct
execution_profile_ref: worker-default
```

`agent_ref` belongs to the peer entry, not the provider descriptor. Program
Execution resolves the binding, applies the execution profile, and invokes the
provider through `environment/program-execution/peer_execution/`.

Provider-specific Program modules are thin. Shared lifecycle, permissions,
context, budgets, transports, telemetry, receipts, and admitted-dispatch
concurrency live upstream.

## Autonomy

Root `autonomy/` is the canonical authorization/control plane and never owns
Program state. Shared bounded-concurrency mechanics live at
`environment/program-execution/peer_execution/autonomy/`, not under a provider adapter.

## Validation

```bash
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
make program-execution-conformance
make peer-execution-validate
make peer-execution-probe
make peer-execution-conformance
```

Thin-provider violations are merge-blocking.
