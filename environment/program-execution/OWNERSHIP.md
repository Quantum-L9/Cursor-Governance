# Ownership

| Concern | Canonical owner |
|---|---|
| Program Lock, task state, Program leases, canonical receipts | `core/` |
| Local mediated agent actions and subordinate leases | root `autonomy/` |
| Claude Code internal worker lanes | `environment/program-execution/peer_execution/autonomy/` |
| Agent and memory identity | `environment/agents/agent_registry.yaml` |
| Graphiti transport | `ops/graphiti/` |
| Generated-data processing and delivery | `environment/agents/generated-data/` |
| Host translation, lifecycle evidence, routing, remote actions | this layer |

Adapters may narrow authority. They may never widen it, verify their own work,
or declare program convergence.
