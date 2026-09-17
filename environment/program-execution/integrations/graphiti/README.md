# Memory Context Reader

Read-only, **agent-lane** integration with the canonical memory control plane
(ADR-0033, INV-03b). A Program Execution worker reads memory on its own behalf,
so `context_reader.py` calls the package's public `l9-memory search` console
script, located through `ops.memory.runtime_binding.resolve_runtime_binding()`
— it never constructs the hook-lane `MemoryControlPlaneClient` and never spawns
the operator `python -m ops.memory.cli`. It is declared under
`agent_lane_callers` in `ops/config/memory-hook-envelopes.json`, and the lane
scan in `ops/scripts/validate_memory_egress_boundary.py` holds it there.

No write, claim, phase-lock, or memory-promotion command is exposed here, and
no provider is called: memory answers the search and its receipt is the
evidence. A `BINDING_FAILED` runtime is raised as an environment fault, not
read as memory degradation (ADR-0032).
