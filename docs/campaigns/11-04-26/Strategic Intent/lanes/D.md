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

**Writable scope:** `governance/operator-alignment/**`, `ops/autonomy/*operator_alignment*`, `tests/ops/autonomy/*operator_alignment*`, producer-emitted verified `generated/governance/operator_alignment/**`. Projection-binding edits are allowed in `ops/autonomy/projection_mode.py`, `governance/cto-mode/MODE.yaml`, `governance/architect-mode/MODE.yaml`, `governance/coding-agent-mode/MODE.yaml`, `commands/lcto.md`, and `commands/architect.md` only when compatibility demands them. Those edits must not change `operating_protocol`, `child_system_prompt`, `child_brief_must_include`, `child_launch_rules`, or `transport`. An edit that would touch those keys is a `CTO-QUESTION` before the write. Do not touch any currently changed #1011/#1030 path, especially `tools/authority/produce_projection_bundle.py`, `governance/planner-mode/MODE.yaml`, `commands/planner.md` or existing planner bundles. Planner integration is deferred until C merges; then assigned to an idle pool slot under fresh brief.

**Entry gates:** Freeze C's exact live changed-file census and show disjointness. Verify current `ops/autonomy/projection_mode.py` and global binding verifier before any shared change. Read `PRODUCER_CONSUMER_HANDOFF.md`; do not implement producer-dependent interface before CTO supplies Lane B's exact confirmed contract/artifacts.

**Work:** Build or extend only the owner-correct consumer verifier and mode integration. Existing global required profiles stay intact and independently verified. Where missing source or rights make a role ineligible, return typed BLOCKED not fake active. CTO/Architect can be prepared first; Meta Planner advisory only if existing consumer known; Coding Agent context can be minimized but privacy remains blocked pending actual ACL denial.

**Return:** exact branch and source read-only pins, producer receipt coordinates, independent verifier tests and failures, scoped modes/roles (CTO, Architect, Planner, Meta Planner, Coding Agent), ACL witness result or `BLOCKED_PRIVACY`, then `CTO-STATUS: stood-down`. Child does not assert integration PASS. Merge waits for the integration-test train.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO renders `cto_mode.py child-prompt` from `$HOME/.cursor-governance` whose HEAD equals `origin/main`. The first child action is the rendered prompt's first action, including `/coding-agent` ACTIVE, never edits before that. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test. Meta Planner with no eligible consumer is `CTO-STATUS: BLOCKED_NO_CONSUMER`. Coding Agent confidentiality while the worker can read `.github/strategy/` is `CTO-STATUS: BLOCKED_PRIVACY`. Both are complete for those roles.

**Publication:** From the Cursor-Governance checkout run `PR_REMEDIATE=0 PR_BASE="origin/main" make -C "$HOME/.cursor-governance" pr WS="<this checkout>"`. Leave `PR_STACK` empty. Then write `CTO-STATUS: stood-down`. Do not remediate, watch CI, or merge. The CTO remediates a red check inside this write set, runs integration tests, and merges this PR with the other in-scope PRs after those tests pass. A `make pr` rewrite outside this write set is named in `CTO-STATUS` and left uncommitted. No raw `git push` and no `gh pr create`.
