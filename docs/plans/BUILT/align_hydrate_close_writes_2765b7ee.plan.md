---
name: Align hydrate/close/agent writes
overview: "Unify SessionStart and sessionEnd on one session-task string, prefetch last-24h repo-scoped agent-lane writes, and enrich the close capsule from those writes. Package recorded_after is the selector that makes the window real."
status: built
todos:
  - id: package-recorded-after
    content: l9-graphite-memory recorded_after selector + relevance skip (ADR-0035)
    status: completed
  - id: unify-session-objective
    content: session_task_objective helper + compile/close call sites
    status: completed
  - id: agent-lane-classifier
    content: ops/memory/agent_lane.py
    status: completed
  - id: prefetch-24h
    content: canonical_hydrate call 4 + packet stats
    status: completed
  - id: enrich-capsule
    content: session-end search + capsule enrich; envelopes allow search
    status: completed
  - id: create-adrs
    content: ADR-0034 and ADR-0035
    status: completed
  - id: doctrine-tests
    content: AGENTS fragment, skill, tests
    status: completed
  - id: l4-publish
    content: Real kernel apply-report, L4 authorize, stacked PR, plan to BUILT/
    status: in_progress
isProject: false
---

# Align hydrate / close / agent-lane writes

**Status: built** (2026-09-19) on `agent/cursor/align-hydrate-close`.

## What landed

- `session_task_objective` → `Continue work in {name}` for SessionStart and sessionEnd.
- `canonical_hydrate` call 4: `--recorded-after <now-24h>` on the primary namespace; fail-open.
- `ops/memory/agent_lane.py` classifies mid-session writes without opening the store.
- sessionEnd enriches the capsule from the same window; envelopes allow `search`.
- ADR-0034, ADR-0035, AGENTS `HYDRATE_CLOSE_AGENT_LANE_V1`, skill 2.4.0.
- Package work for `recorded_after` lives in the l9-graphiti-memory tree; CG fail-opens until the sealed pin includes the flag (ADR-0035).

## Constraints kept

Do not constrain `write_agent`. No cross-repo grants. No invented Manus connector. INV-03: no sqlite from Cursor-Governance.
