---
name: planner
version: "1.0.0"
description: "Planner mode — opt-in binding of the strategic-planning projections and Plan Keeper context"
---

# /planner — Planner Mode

Turns on planner mode for this session: L9's strategic navigation plane. It binds the canonical
strategic-planning semantics from admitted `Quantum-L9/.github` projections and drives the
`l9-strategic-plan` skill (`skills/l9-strategic-plan/SKILL.md`) against the persistent Strategic
Plan and current evidence. It is a sibling of `/architect` and `/lcto`, never always on, and
not the default operating plane. Contract: `governance/planner-mode/MODE.yaml`.

## Bound projections (all required)

| Projection | Why |
|---|---|
| `l9.projection/strategic-value@1` | qualitative value, tradeoffs, opportunity cost, prioritization |
| `l9.projection/architecture@1` | architectural constraints and cross-system dependencies |
| `l9.projection/signals@1` | evidence that warrants reconsideration |
| `l9.projection/governance@1` | authority boundaries, commitments, decisions, permissions |
| `l9.projection/evidence-provenance@1` | evidence vs hypothesis vs Unknown vs verified |
| `l9.projection/capabilities-dependencies@1` | capability unlocks, feasibility, blocked paths |
| `l9.projection/strategic-planning-context@2` | Plan Keeper context (read-only): Plan model, graph, closure, episode, revision candidate |

The six domains are the required set of `l9.domain-consumer-binding/strategic-planner@1`. The
Plan Keeper context's declared consumer is `plan_keeper`: reading it confers no Strategic
Authority.

## Execution

1. From the workspace you are working in (do not change directory), run:
   `"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/planner_mode.py" on --workspace "$PWD"`.
   Add `--authority-root <checkout>` (or set `L9_AUTHORITY_ROOT`; otherwise the managed
   `~/.l9/authority/.github` that SessionStart provisions, then a `.github` checkout inside or
   beside the workspace, is found on its own) with a `Quantum-L9/.github` checkout whose HEAD is
   its `main`; admission is resolved there. The request is bound to this host session.
2. Read its JSON `mode`:
   - `ACTIVE`: read each `load[].composed_view` before strategic judgment, then follow
     `skills/l9-strategic-plan/SKILL.md`. Cite the composition digest and source class for
     every claim.
   - `BLOCKED`: report every `blockers[]` entry verbatim. Do not cite a blocked projection and
     do not reconstruct it from memory or repository reads.
   - `REJECTED` or `STALE`: stop and report. `STALE` means the mode contract changed after the
     request; run `on` again.
   - `OFF` with `SESSION_UNRESOLVED`: pass `--session-id`.
3. `/planner status` runs the same command with `status`; `/planner off` runs it with `off`.

## Default screen

Once ACTIVE, open with one compact executive view: the mission root, at most three protected
attention items with their reason, then the independent parallel lanes, the blocked or
waiting items (owner and wake trigger), and the evidence that changed since the last session
(with its affected closure). Classify new work as `ADVANCE`, `PARK` or `ESCALATE` (mode-local
labels, not Plan node types). Retrieve the Plan through the authorized Memory connector; when
graph intelligence reports disabled, use search, hydrate and get only and say so.

The mode changes what the session reads, never what it may do. A Plan change is a
`strategic_plan_revision_candidate`; it is admitted only by the Plan Keeper under explicitly
granted Strategic Authority, never by this mode. Publication, merge, push and deploy authority
are unchanged.
