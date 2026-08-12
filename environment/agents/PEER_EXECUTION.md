<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/PEER_EXECUTION.md
layer: contract
owner: governance-control-plane
status: active
version: 3.0.0
updated: 2026-08-12
/L9_META -->

# Executable Peer Contract v2

> One governance. One Program Controller. One autonomy plane. Many executable
> peers. Zero copied brains. One topology SSOT.

An **executable agent** is not an agent with shell access. It is an active
registry identity with a peer binding that declares `execution.required: true`,
a valid surface→Program-adapter binding, access to the canonical autonomy
enforcement plane, and fresh machine-verifiable readiness evidence:

```
active agent
  + PEER_RUNTIME_BINDINGS execution.required
  + valid surface -> Program adapter binding
  + canonical autonomy available
  + fresh readiness evidence
  = ROUTABLE EXECUTABLE PEER
```

This **extends** the identity/memory adapter contract — it does not replace it.

## Authority boundaries

```
agent_registry.yaml          WHO is this? which surfaces? (identity only)
        │
PEER_RUNTIME_BINDINGS.yaml   WHICH planes must be connected? (topology SSOT)
        │
environment/program-execution/   HOW does work execute? is the adapter conformant?
        │
autonomy/   MAY this leased agent perform this operation? (gateway / leases)
        │
provider / host / tool
```

Program Execution remains the controller. Root `autonomy/` is subordinate and
declares `owns_program_state: false`; its lease may not outlive the
authoritative Program lease.

`agent_registry.yaml` MUST NOT declare `execution:` — topology lives only in
`PEER_RUNTIME_BINDINGS.yaml`. Dual-read shims are forbidden.

## Peer runtime bindings (topology plane)

`PEER_RUNTIME_BINDINGS.yaml` declares each peer's cross-plane relationship —
never implementation paths, autonomy versions, or runtime health:

```yaml
cursor:
  agent_ref: cursor
  execution:
    required: true
    bindings:
      - surface: cursor-ide
        adapter_id: cursor-foreground
      - surface: cursor-ide
        adapter_id: cursor-background
  autonomy:
    required: true
    provider_id: root-autonomy-control-plane
codex:
  agent_ref: codex
  execution:
    required: false
    bindings: []
```

`execution.required: true` asserts at least one surface is backed by a sealed,
non-dormant `worker_host` adapter with a resolvable `agent_ref`. It never means
"we intend to support this." Every active registry agent MUST appear in the
bindings file, even when capabilities are explicitly disabled.

`*.readiness_required` switches stay `false` until the PR that lands their
satisfier flips them (activation law). Cursor `subagents.deployment` is
activated by Patch B (`environment/agents/deployment/`).

## agent_ref foreign key (execution plane)

Each Program adapter descriptor that binds to the registry carries the foreign
key:

```yaml
# environment/program-execution/adapters/cursor-foreground/ADAPTER.yaml
identity:
  binding: agent_registry
  agent_ref: cursor
  memory_write: via_generated_data_pipeline
```

The spec schema requires `agent_ref` whenever `binding == agent_registry`;
`controller_contract` / `external_receipt` adapters (CI, GitHub, ChatGPT
manual-handoff) omit it. Rule E11 proves it equals the peer `agent_ref`.

## Two gates (never combined)

**Gate A — peer/session readiness** answers *"can this peer currently accept
Program work?"* independent of any task. It produces an
`l9.executable-peer-readiness.v1` receipt per `(agent_ref, surface, adapter_id)`
binding. Canonical storage is `$L9_RUNTIME_ROOT/agents/readiness/` (default
`~/.l9/agents/readiness/`); legacy `$L9_PROGRAM_HOME/_peer-readiness` remains
discoverable.

**Gate B — task admission** answers *"can this READY peer execute this specific
Controller contract?"* — the existing Program-Lock-digest-bound, TTL-fresh
capability receipt checked before `prepare()`/`dispatch()`.

```
peer readiness -> router selects binding -> Program Lock / task contract
  -> adapter capability probe -> fresh digest-bound capability receipt
  -> prepare -> dispatch -> autonomy gateway -> execution
```

Task SHA / lease / Program Lock never live in the long-lived peer bootstrap.

## Readiness is binding-level

Readiness is computed per `(agent_ref, surface, adapter_id)`, not per agent. A
broken `cursor-background` transport never disables a healthy
`cursor-foreground` peer; the aggregate agent status may read `PARTIAL` while
the router still schedules the healthy binding.

Only peers with `execution.required: true` participate in Program-execution
readiness probing.

## Coverage matrix

| Surface | Role | Program adapter | Kind | Registry status | `execution.required` |
|---|---|---|---|---|---|
| Cursor foreground | orchestrator | `cursor-foreground` | worker_host | conditional | **true** |
| Cursor background | orchestrator | `cursor-background` | worker_host | conditional | **true** |
| Claude Code | implementer | `claude-code-direct` | worker_host | conditional | **true** |
| Claude Code (bounded) | implementer | `claude-code-bounded-autonomy` | worker_host | conditional | **true** |
| Codex | implementer | `codex-cloud` | worker_host | dormant | false (Wave B) |
| Gemini | reviewer | `gemini-review` | verifier | dormant | false (Wave C) |
| Manus | researcher-builder | `manus-cloud` | worker_host | dormant | false (Wave D) |

## Validate the whole topology

```bash
make agents-env                         # identity plane
make agents-runtime-bindings-validate   # bindings schema
make program-execution-adapters         # execution plane descriptors + spec schema
make program-execution-conformance      # adapter-layer conformance
make peer-execution-validate            # Executable Peer Contract E1-E15
make peer-execution-probe               # binding-level readiness receipts
make peer-execution-conformance         # composes all of the above
```

### Cross-registry rules (`validate_executable_peers.py`)

- **E1** `PEER_RUNTIME_BINDINGS.yaml` exists and parses.
- **E2** bindings document validates against `peer-runtime-bindings.schema.json`.
- **E3** every active `agent_registry` agent has a peer entry.
- **E4** `peer.agent_ref` resolves in `agent_registry` (unknown agent_ref).
- **E5** `peer.agent_ref` equals the peer map key.
- **E6** `execution.required` is boolean; active + required requires ≥1 binding.
- **E7** `binding.surface` exists in the agent's `surfaces` (unknown surface).
- **E8** `binding.adapter_id` exists exactly once in the execution registry.
- **E9** bound adapter is `worker_host`.
- **E10** bound descriptor validates; `identity.binding == agent_registry`.
- **E11** descriptor `identity.agent_ref` equals the peer `agent_ref`.
- **E12** bound adapter is not `dormant`/`non_routable`.
- **E13** `autonomy.required` peers resolve provider; `owns_program_state: false`.
- **E14** no adapter copies `autonomy/`; bootstrap carrier; roles manifest when enabled.
- **E15** no duplicate peer bindings; `agent_registry` must not declare `execution:`.

### Readiness receipt (`l9.executable-peer-readiness.v1`)

Per-binding checks — `identity_binding`, `adapter_conformance`, `adapter_probe`,
`autonomy_provider`, `autonomy_conformance`, `execution_gateway` — all PASS ⇒
`status: READY`; otherwise `BLOCKED` with the first failing check as
`blocked_reason`. `probe_executable_peers.py` exits non-zero if any
`execution.required` peer has no READY binding, while still emitting every
binding receipt so partial availability stays visible.

## Runtime model

```
agent_registry.yaml (identity)
  -> PEER_RUNTIME_BINDINGS.yaml (topology)
  -> Executable Peer Binder
  -> (agent identity + PE adapter + root autonomy) -> readiness evaluator
  -> readiness receipt -> BLOCKED | READY
  READY -> router eligible -> Controller contract -> Program Lock probe
    -> capability receipt -> prepare/dispatch -> autonomy gateway -> execution
```

**Ownership invariant.** Agent Registry declares who may participate. Peer
Runtime Bindings declare which planes must be connected. Program Execution
determines how work executes. Root Autonomy constrains what leased execution
may do. Readiness proves the path currently works. Mutable runtime state stays
outside Git under `$L9_RUNTIME_ROOT` (default `~/.l9`), resolved by
`environment/agents/runtime_paths.py`.
