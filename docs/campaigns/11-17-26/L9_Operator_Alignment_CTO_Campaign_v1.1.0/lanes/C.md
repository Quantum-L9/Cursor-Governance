```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/Cursor-Governance
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/l9-semantic-compiler-engine
  unlisted_repositories: no_access
```

# Lane C | Current strategic-plan skill and Planner mode PR stack

**Objective:** Converge **only** Cursor-Governance #1011 (skill) and its stacked child #1030 (Planner mode, generated bundles) and prepare them for CTO-only merge in dependency order. Do not create another Planner implementation.

**Writable scope:** The **actual live GitHub PR changed-file set** for #1011 and #1030, captured at dispatch, in separate isolated branches/worktrees. A path outside this set needs CTO reassignment before edits. No edits to D's `governance/operator-alignment/**`, operator verifier or shared `ops/autonomy/projection_mode.py` unless CTO explicitly freezes and serializes the changed path.

**Entry gates:** Snapshot live head SHA, changed files, base, CI, reviews and thread status. #1030's parent is `skills/l9-strategic-plan` until safely retargeted. Verify generated projection receipt provenance; do not assume copied receipt filenames prove valid production.

**Work:** Repair issues on original branch only; publish via current SSOT; after #1011 merges (by CTO), re-evaluate child base and merge-safe ancestry, exact child-only diff and current-head checks. Never merge; do not squash stacked parent or use force-push to fix the stack.

**Return:** both current heads and changed-file census, checks/reviews fixed, safe merge order, producer receipts validated or specific Unknown, CTO-STATUS: ready-to-merge for each when eligible.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO must use the exact child-prompt rendered by the current `ops/autonomy/cto_mode.py` and existing `/coding-agent` mode. The first child action is role registration and mode ACTIVE proof, never edits. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test, no raw publication bypass. Repository access headers express intended scope and must be enforced by host permissions to support a technical-isolation claim; headers by themselves grant nothing.

**Publication:** Only current Cursor-Governance SSOT `make pr` transport after checking its actual owner code and L4/gates at the exact checkout. The agent that publishes the PR repairs its CI/review/threads until ready to merge, then returns idle. CTO alone merges when permitted and performs combined integration. Do not invent or run unverified make targets.
