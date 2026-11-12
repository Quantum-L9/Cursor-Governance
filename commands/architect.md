---
name: architect
version: "1.0.0"
description: "Architect mode — opt-in binding of the architecture and strategic-planning projections"
---

# /architect — Architect Mode

Turns on architect mode for this session: canonical architecture and strategic-planning
semantics, bound from admitted `Quantum-L9/.github` domain projections. Use it instead of
`/l9-global-architect` when you need architectural context. It is never always on and it is
not the default operating plane. Contract: `governance/architect-mode/MODE.yaml`.

## Bound projections (all required)

| Projection | Why |
|---|---|
| `l9.projection/architecture@1` | patterns, rules, topology, node and dependency archetypes |
| `l9.projection/governance@1` | authority, ownership, admission and lifecycle law |
| `l9.projection/evidence-provenance@1` | evidence, assurance and provenance |
| `l9.projection/contracts-conformance@1` | global contracts and conformance |
| `l9.projection/capabilities-dependencies@1` | capabilities, resolution and dependencies |
| `l9.projection/strategic-value@1` | qualitative strategic value (strategic planning) |
| `l9.projection/signals@1` | signal propagation and consumption (strategic planning) |

The set is the union of the required domains of the canonical bindings
`l9.domain-consumer-binding/gar@1` and `l9.domain-consumer-binding/strategic-planner@1`.

## Execution

1. From the workspace you are working in (do not change directory), run:
   `"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/architect_mode.py" on --workspace "$PWD"`.
   Add `--authority-root <checkout>` (or set `L9_AUTHORITY_ROOT`; a `.github` checkout inside or beside the workspace is found on its own) with a
   `Quantum-L9/.github` checkout whose HEAD is its `main`; admission is resolved there.
   The request is bound to this host session.
2. Read its JSON `mode`:
   - `ACTIVE`: read each `load[].composed_view` before architectural judgment. Each
     namespace is one source projection exactly as produced. Cite the composition digest
     and source class for every claim.
   - `BLOCKED`: report every `blockers[]` entry verbatim. Do not cite a blocked domain and
     do not reconstruct it from memory or repository reads.
   - `REJECTED` or `STALE`: stop and report. `STALE` means the mode contract changed after
     the request; run `on` again.
   - `OFF` with `SESSION_UNRESOLVED`: pass `--session-id`.
3. `/architect off` runs the same command with `off` in place of `on`.

The mode changes what the session reads, never what it may do. Publication, merge, push and
deploy authority are unchanged.

--- End Command ---
