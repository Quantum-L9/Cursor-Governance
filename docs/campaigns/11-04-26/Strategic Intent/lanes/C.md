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

**Work:** Repair issues on the original branches only inside the frozen changed-file set, then publish. Do not merge. Do not squash the stacked parent or force-push the stack. `#1030` keeps base `skills/l9-strategic-plan` until the CTO merges `#1011`. After that merge the CTO retargets `#1030` and re-dispatches this slot if the child-only diff must be revalidated. The child that published has already stood down.

**Return:** both current heads and changed-file census, safe merge order, producer receipts validated or specific Unknown, then `CTO-STATUS: stood-down`. Merge waits for the integration-test train.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO renders `cto_mode.py child-prompt` from `$HOME/.cursor-governance` whose HEAD equals `origin/main`. The first child action is the rendered prompt's first action, including `/coding-agent` ACTIVE, never edits before that. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test.

**Publication:** From the Cursor-Governance checkout run `PR_REMEDIATE=0 PR_BASE="origin/<this PR's current base>" make -C "$HOME/.cursor-governance" pr WS="<this checkout>"`. `#1011` uses `origin/main`. `#1030` uses `origin/skills/l9-strategic-plan` until `#1011` has merged. Leave `PR_STACK` empty. Then write `CTO-STATUS: stood-down`. Do not remediate, watch CI, or merge. The CTO remediates a red check inside the frozen changed-file set, runs integration tests, and merges `#1011` then `#1030` with the other in-scope PRs after those tests pass. A `make pr` rewrite outside the frozen set is named in `CTO-STATUS` and left uncommitted. No raw `git push` and no `gh pr create`.
