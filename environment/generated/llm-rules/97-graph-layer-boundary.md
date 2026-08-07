---
description: Keep structural code graphs, episodic memory, repository resume state, and static law distinct.
---

# Graph Layer Boundary

| Layer | Tool | Answers |
|---|---|---|
| Structural | `code-graph-rag` MCP | Where in code? Who imports it? What is the blast radius? |
| Episodic | `graphiti-memory` MCP / CLI | What was decided? Which ADR or operating lesson applies? |
| Session resume | Graphiti `inject` / PICKUP | Where did the repository session stop? |
| Static law | Rules and `AGENTS.md` | Which constraints are non-negotiable? |

`memory-bank/` is deprecated/archival and is not a resume layer.

Repository overlays may add domain-specific structural-graph procedures without changing these global boundaries.

## Must not

- Use episodic memory as a substitute for symbol or import discovery.
- Use a structural code graph as a substitute for decisions, provenance, or temporal history.
- Collapse distinct MCP servers into one authority model.
- Treat local `memory-bank/` or other resume files as canonical global memory.

<!-- generated-from: rules/97-graph-layer-boundary.mdc; do-not-edit -->
