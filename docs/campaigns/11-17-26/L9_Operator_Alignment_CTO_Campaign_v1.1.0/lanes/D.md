```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cursor-Governance
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/l9-semantic-compiler-engine
  unlisted_repositories: no_access
```

# Lane D | Cursor alignment consumers, existing modes, fail-closed role access

**Objective:** Bind operator-owned, source-verifiable views to existing Cursor modes, with no second projection compiler, no invented Meta Planner mode, and **no** Coding Agent upstream-secret PASS while that actor can read `.github/strategy/`.

**Writable scope:** `governance/operator-alignment/**`, `ops/autonomy/*operator_alignment*`, `tests/ops/autonomy/*operator_alignment*`, producer-emitted verified `generated/governance/operator_alignment/**`; additionally only if compatibility demands: `ops/autonomy/projection_mode.py`, `governance/cto-mode/MODE.yaml`, `governance/architect-mode/MODE.yaml`, `governance/coding-agent-mode/MODE.yaml`, `commands/lcto.md`, `commands/architect.md`. Do not touch any currently changed #1011/#1030 path, especially `tools/authority/produce_projection_bundle.py`, `governance/planner-mode/MODE.yaml`, `commands/planner.md` or existing planner bundles. Planner integration is deferred until C merges; then assigned to an idle pool slot under fresh brief.

**Entry gates:** Freeze C's exact live changed-file census and show disjointness. Verify current `ops/autonomy/projection_mode.py` and global binding verifier before any shared change. Read `PRODUCER_CONSUMER_HANDOFF.md`; do not implement producer-dependent interface before CTO supplies Lane B's exact confirmed contract/artifacts.

**Work:** Build or extend only the owner-correct consumer verifier and mode integration. Existing global required profiles stay intact and independently verified. Where missing source or rights make a role ineligible, return typed BLOCKED not fake active. CTO/Architect can be prepared first; Meta Planner advisory only if existing consumer known; Coding Agent context can be minimized but privacy remains blocked pending actual ACL denial.

**Return:** exact branch and source read-only pins, producer receipt coordinates, independent verifier tests and failures, scoped modes/roles (CTO,Architect,Planner,Meta Planner,Coding Agent), ACL witness result or `BLOCKED_PRIVACY`, PR ready-to-merge status. Child does not assert integration PASS.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO must use the exact child-prompt rendered by the current `ops/autonomy/cto_mode.py` and existing `/coding-agent` mode. The first child action is role registration and mode ACTIVE proof, never edits. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test, no raw publication bypass. Repository access headers express intended scope and must be enforced by host permissions to support a technical-isolation claim; headers by themselves grant nothing.

**Publication:** Only current Cursor-Governance SSOT `make pr` transport after checking its actual owner code and L4/gates at the exact checkout. The agent that publishes the PR repairs its CI/review/threads until ready to merge, then returns idle. CTO alone merges when permitted and performs combined integration. Do not invent or run unverified make targets.
