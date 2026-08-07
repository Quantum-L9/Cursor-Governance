---
description: Keep structural code graphs, episodic memory, repository resume state, and static law distinct.
---

# Graph Layer Boundary

| Layer | Tool | Answers |
|---|---|---|
| Structural | `code-graph-rag` MCP | Where in code? Who imports it? What is the blast radius? |
| Episodic | `graphiti-memory` MCP | What was decided? Which ADR or operating lesson applies? |
| Git resume | `memory-bank/` | Where did the repository session stop? |
| Static law | Rules and `AGENTS.md` | Which constraints are non-negotiable? |

Repository overlays may add domain-specific structural-graph procedures without changing these global boundaries.

## Must not

- Use episodic memory as a substitute for symbol or import discovery.
- Use a structural code graph as a substitute for decisions, provenance, or temporal history.
- Collapse distinct MCP servers into one authority model.
- Treat local resume files as canonical global memory.

<!-- generated-from: rules/97-graph-layer-boundary.mdc; do-not-edit -->
