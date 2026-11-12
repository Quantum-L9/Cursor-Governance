---
name: coding-agent
version: "1.0.0"
description: "Coding-agent mode — opt-in binding of the coding-agent execution projection"
---

# /coding-agent — Coding-Agent Mode

Turns on coding-agent mode for this session: the canonical execution semantics for bounded
code changes, bound from the admitted `Quantum-L9/.github` projection. It does not invoke or
require the `l9-coding-agent` skill. It is never always on. The operating plane
(`l9.projection/cursor-governance-operating-plane@2`) is not part of it: SessionStart binds
that in every session. Contract: `governance/coding-agent-mode/MODE.yaml`.

## Bound projections (all required)

| Projection | Why |
|---|---|
| `l9.projection/coding-agent-execution@1` | execution invariants, contracts and the authority model for bounded code changes |

It is the predecessor profile of the canonical binding `l9.domain-consumer-binding/coding-agent@1`,
bound through `governance/authority-bindings/coding-agent-execution.yaml`. That canonical
binding's domain set is not bound: its review for authority neutrality is unresolved.

## Execution

1. From the workspace you are working in (do not change directory), run:
   `"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/coding_agent_mode.py" on --workspace "$PWD"`.
   Add `--authority-root <checkout>` (or set `L9_AUTHORITY_ROOT`; a `.github` checkout inside or beside the workspace is found on its own) with a
   `Quantum-L9/.github` checkout whose HEAD is its `main`; admission is resolved there.
   The request is bound to this host session.
2. Read its JSON `mode`:
   - `ACTIVE`: read each file in `load[].views` (one per source class: invariants,
     contracts, authority model) before deciding how to change code. Cite the source class
     and bundle revision for every claim.
   - `BLOCKED`: report every `blockers[]` entry verbatim. Do not cite the execution
     projection and do not reconstruct it from memory, the skill pack or repository reads.
   - `REJECTED` or `STALE`: stop and report. `STALE` means the mode contract changed after
     the request; run `on` again.
   - `OFF` with `SESSION_UNRESOLVED`: pass `--session-id`.
3. `/coding-agent off` runs the same command with `off` in place of `on`.

The mode changes what the session reads, never what it may do. Publication, merge, push and
deploy authority are unchanged.

--- End Command ---
