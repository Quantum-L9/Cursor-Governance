<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/PEER_EXECUTION.md
layer: contract
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-08-10
/L9_META -->

# Executable Peer Contract v1

> One governance. One Program Controller. One autonomy plane. Many executable
> peers. Zero copied brains.

An **executable agent** is not an agent with shell access. It is an active
registry identity with a valid surface→Program-adapter binding, access to the
canonical autonomy enforcement plane, and fresh machine-verifiable readiness
evidence:

```
active agent
  + execution enabled
  + valid surface -> Program adapter binding
  + canonical autonomy available
  + fresh readiness evidence
  = ROUTABLE EXECUTABLE PEER
```

This **extends** the identity/memory adapter contract — it does not replace it.

## Authority boundaries (unchanged)

```
agent_registry.yaml   WHO is this? which surfaces? is execution enabled?
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

## Execution bindings (identity plane)

`agent_registry.yaml` (schema v2) declares each peer's executable relationship —
never implementation paths, autonomy versions, or runtime health:

```yaml
cursor:
  role: orchestrator
  surfaces: [cursor-ide]
  adapter: cursor
  execution:
    enabled: true
    bindings:
      - surface: cursor-ide
        adapter_id: cursor-foreground
      - surface: cursor-ide
        adapter_id: cursor-background
codex:
  execution:
    enabled: false      # codex-cloud worker adapter is dormant (Wave B)
    bindings: []
```

`execution.enabled: true` asserts at least one surface is backed by a sealed,
non-dormant `worker_host` adapter with a resolvable `agent_ref`. It never means
"we intend to support this."

## agent_ref foreign key (execution plane)

The hardcoded adapter→agent map is gone. Each Program adapter descriptor that
binds to the registry carries the foreign key:

```yaml
# environment/program-execution/adapters/cursor-foreground/ADAPTER.yaml
identity:
  binding: agent_registry
  agent_ref: cursor
  memory_write: via_generated_data_pipeline
```

The spec schema requires `agent_ref` whenever `binding == agent_registry`;
`controller_contract` / `external_receipt` adapters (CI, GitHub, ChatGPT
manual-handoff) omit it. `identity_binding.agent_ref_for()` resolves it, and
rule E8 proves it equals the registry agent key.

## Two gates (never combined)

**Gate A — peer/session readiness** answers *"can this peer currently accept
Program work?"* independent of any task. It produces an
`l9.executable-peer-readiness.v1` receipt per `(agent_id, surface, adapter_id)`
binding, stored outside Git under `$HOME/.l9/programs/_peer-readiness/`.

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

Readiness is computed per `(agent_id, surface, adapter_id)`, not per agent. A
broken `cursor-background` transport never disables a healthy
`cursor-foreground` peer; the aggregate agent status may read `PARTIAL` while
the router still schedules the healthy binding.

## Coverage matrix

| Surface | Role | Program adapter | Kind | Registry status | `execution.enabled` |
|---|---|---|---|---|---|
| Cursor foreground | orchestrator | `cursor-foreground` | worker_host | conditional | **true** |
| Cursor background | orchestrator | `cursor-background` | worker_host | conditional | **true** |
| Claude Code | implementer | `claude-code-direct` | worker_host | conditional | **true** |
| Claude Code (bounded) | implementer | `claude-code-bounded-autonomy` | worker_host | conditional | **true** |
| Codex | implementer | `codex-cloud` | worker_host | dormant | false (Wave B) |
| Gemini | reviewer | `gemini-review` | verifier | dormant | false (Wave C) |
| Manus | researcher-builder | `manus-cloud` | worker_host | dormant | false (Wave D) |

Only peers whose worker adapter is sealed, registered, non-dormant, and
readiness-probed are flipped to `enabled: true`. This keeps `execution.enabled`
a trustworthy architectural assertion, not a roadmap flag.

## Validate the whole topology

```bash
make agents-env                    # identity plane
make program-execution-adapters    # execution plane descriptors + spec schema
make program-execution-conformance # adapter-layer conformance (70 tests)
make peer-execution-validate       # Executable Peer Contract E1-E15
make peer-execution-probe          # binding-level readiness receipts
make peer-execution-conformance    # composes all of the above
```

### Cross-registry rules (`validate_executable_peers.py`)

- **E1** `execution.enabled` is boolean.
- **E2** active + enabled requires ≥1 binding.
- **E3** `binding.surface` exists in the agent's `surfaces`.
- **E4** `binding.adapter_id` exists exactly once in the execution registry.
- **E5** bound adapter is `worker_host`.
- **E6** bound descriptor validates against `execution-adapter-spec.schema.json`.
- **E7** descriptor `identity.binding == agent_registry`.
- **E8** descriptor `identity.agent_ref` equals the registry agent key.
- **E9** bound adapter is not `dormant`/`non_routable`.
- **E10** root autonomy resolves from `COMPATIBILITY.yaml`.
- **E11** `PROVIDER.yaml` exists and declares `owns_program_state: false`.
- **E12** canonical autonomy path resolves inside the governance root.
- **E13** no adapter copies an `autonomy/` implementation.
- **E14** every executable peer has a bootstrap/readiness carrier.
- **E15** no readiness state is statically asserted in `agent_registry.yaml`.

### Readiness receipt (`l9.executable-peer-readiness.v1`)

Per-binding checks — `identity_binding`, `adapter_conformance`, `adapter_probe`,
`autonomy_provider`, `autonomy_conformance`, `execution_gateway` — all PASS ⇒
`status: READY`; otherwise `BLOCKED` with the first failing check as
`blocked_reason`. `probe_executable_peers.py` exits non-zero if any enabled
agent has no READY binding, while still emitting every binding receipt so
partial availability stays visible.

## Runtime model

```
agent_registry.yaml -> execution bindings -> Executable Peer Binder
  -> (agent identity + PE adapter + root autonomy) -> readiness evaluator
  -> readiness receipt -> BLOCKED | READY
  READY -> router eligible -> Controller contract -> Program Lock probe
    -> capability receipt -> prepare/dispatch -> autonomy gateway -> execution
```

**Ownership invariant.** Agent Registry declares who may participate. Program
Execution determines how work executes. Root Autonomy constrains what leased
execution may do. Readiness proves the path currently works. Mutable runtime
state stays outside Git under `$HOME/.l9/programs/`.
