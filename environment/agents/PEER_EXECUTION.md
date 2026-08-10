<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/PEER_EXECUTION.md
layer: contract
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-08-10
/L9_META -->

# Universal Agent Peer Execution

> One governance. One Program Controller. One autonomy plane. Many executable
> peers. Zero copied brains.

Every registered L9 agent surface can participate in Program Execution from the
**same** canonical governance and workspace state. A peer deterministically
discovers the same governance SSOT, the same Program Execution subsystem, the
same autonomy control plane, and the same target workspace revision — then
executes through a surface-specific adapter. Adapters translate capabilities to
a surface; **no adapter becomes an alternative Controller.**

## Two roots (never conflated)

| Root | Meaning | Resolution |
|---|---|---|
| `L9_GOVERNANCE_ROOT` | canonical L9 infrastructure (`autonomy/`, `environment/`, `skills/`, `rules/`, `commands/`, `ops/`) | governance clone (`$HOME/.cursor-governance`) |
| `L9_WORKSPACE_ROOT` | the product/program repository being modified | `L9_WORKSPACE_ROOT` env; Controller-resolved repo + SHA per task |

Cursor-Governance stays governance infrastructure; product code stays in the
consumer repository. The peer probe verifies both roots resolve independently.

## Two adapter planes, one cross-link

```
Agent Surface Adapter                 Program Execution Adapter
environment/agents/adapters/<x>       environment/program-execution/adapters/<x>
  "how does this agent enter L9?"        "how does the Controller execute here?"
        │                                         │
        └── program-execution.yaml ───────────────┘
              (binding, cross-validated)
```

- **Identity plane** — `agent_registry.yaml`. Each agent carries an optional
  `program_execution: {enabled, adapters}` block: the peer's declared execution
  participation.
- **Execution plane** — `environment/program-execution/registry/EXECUTION_ADAPTER_REGISTRY.yaml`.
  The Controller-side adapters that run a task on a host.
- **Cross-link** — each surface adapter ships a `program-execution.yaml`
  binding naming its program adapter(s). `make peer-execution-conformance`
  proves identity ↔ binding ↔ execution registry all agree.

## Ownership (unchanged)

`environment/program-execution/` remains the **single** Program Execution
Controller and the only owner of program state, Program Locks, leases, task
state, canonical receipts, and convergence decisions. Root `autonomy/` remains
the subordinate mediated-execution provider — reachable by every peer, **never
copied** into an adapter.

## Coverage matrix

`enabled` peers must pass conformance or probe BLOCKED honestly; a dormant
program adapter is registered coverage, not silent absence.

| Surface | Role | Env adapter | Program adapter | Kind | Program status |
|---|---|---|---|---|---|
| Cursor foreground | orchestrator | `.cursor` activation | `cursor-foreground` | worker_host | conditional |
| Cursor background | orchestrator | `.cursor` activation | `cursor-background` | worker_host | conditional |
| Claude Code | implementer | `environment/claude-code/` | `claude-code-direct` | worker_host | conditional |
| Claude Code (bounded) | implementer | `environment/claude-code/` | `claude-code-bounded-autonomy` | worker_host | conditional |
| Codex | implementer | `adapters/codex/` | `codex-cloud` | worker_host | dormant |
| Gemini | reviewer | `adapters/gemini/` | `gemini-review` | verifier | dormant |
| Manus | researcher-builder | `adapters/manus/` | `manus-cloud` | worker_host | dormant |
| ChatGPT | (external) | surface/runtime | `chatgpt-manual-handoff` | worker_host | dormant |
| Generic shell | (template) | `adapters/generic/` | `ci-generic-shell` | verifier | active |
| CI / GitHub | (service) | machine | `ci-github-actions`, `github-*` | verifier / remote | conditional |

`codex-cloud`, `gemini-review`, and `manus-cloud` are **dormant**: registered
for explicit coverage, probing BLOCKED until a transport is provisioned. Their
promotion paths live in each adapter's README.

## Authority is narrowed, never widened (section 14)

Adapter capabilities may narrow the Controller contract; they never widen it.
The role → adapter-kind mapping is enforced by `peer-execution-conformance`:

| Role | Permitted adapter kinds |
|---|---|
| orchestrator | worker_host, verifier |
| implementer | worker_host |
| researcher-builder | worker_host |
| reviewer | verifier |
| observer | (none — read-only) |

## Runtime state stays outside Git

Mutable execution state — attempts, leases, worktrees, task claims, mutable
receipts, worker/health state — lives under `$HOME/.l9/programs/` and
`$HOME/.l9/program-worktrees/`. Git holds contracts and code only. The peer
probe asserts the runtime root is external to the governance tree.

## Prove the whole topology

```bash
make agents-env                       # identity plane
make program-execution-adapters       # execution plane descriptors
make program-execution-conformance    # adapter-layer conformance (64 tests)
make program-execution-probe          # per-adapter capability probes
make peer-execution-conformance       # cross-registry: the 10 rules
make peer-execution-probe             # universal per-peer readiness probe
make peer-execution                   # all of the above in one target
```

### Peer-execution conformance rules (`peer_execution_conformance.py`)

1. Every executable agent has an environment (surface) adapter.
2. Every program-enabled agent maps to registered program adapter(s).
3. Every adapter-binding references a registered agent (unless a template) and
   agrees with `agent_registry.yaml`.
4. No adapter copies root `autonomy/`.
5. No adapter copies the Program Execution core or a second agent registry.
6. Adapter authority never exceeds the agent's declared role.
7. Every program adapter emits canonical lifecycle receipts.
8. Every program adapter declares a cancellation posture honestly.
9. Every program adapter reports health (registry status + health entry).
10. Every executable peer's program adapter ships conformance tests.

### Universal peer probe (`peer_execution_probe.py`)

Emits, per peer: agent identity resolved · governance root present · workspace
root present · workspace SHA resolved · Program Execution core validated ·
autonomy provider available · execution adapter registered · adapter
capabilities declared · permissions do not exceed Controller authority · receipt
mapping available · cancellation supported honestly · mutable runtime external
to Git · peer ready → `PROGRAM_EXECUTION_READY`. A peer that is not ready must
not be scheduled by the router.
