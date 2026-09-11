---
description: Maximum-velocity is a repo invariant — launch research as concurrent subagents.
---

# Maximum velocity + research fan-out

Committed execution personality is `maximum_velocity` on every surface
(Cursor and Claude): `max_parallel=480`, `max_mutation_lanes=128`,
`native_subagent_limit=480`. That is a repo invariant
(`INVARIANTS.md`, `ops/scripts/validate_max_velocity.py`). Do not
self-throttle to one in-session lane to "be careful."

## Research MUST leave this session

When the next useful work is independent discovery — locate a symbol,
map a flow, audit a residue, read a distant tree, compare two
implementations — **launch it as a Task** (`explore` for read-only,
`generalPurpose` only if the child must edit). Launch every currently
ready research lane in one turn. Main keeps architecture, synthesis,
and user decisions.

Do **not** keep recon in-session because a prior Task failed, because
grep is available, or because launching feels slower. A denied host
admission is a gate defect to report; it is not permission to stay
serial.

## MUST NOT

- Invent a lower cap than the execution profile (`constrained`, 4/2, "just one Task")
- Wait for one research child before launching the next independent one
- Treat `rules/77` (result-bridge orchestration) as required for explore recon
- Skip a Task launch to avoid the Graphiti / lifecycle start hook

<!-- generated-from: rules/07-max-velocity-research.mdc; do-not-edit -->
