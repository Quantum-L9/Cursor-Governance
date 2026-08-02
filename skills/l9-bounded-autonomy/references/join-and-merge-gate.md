# Protocol C — Join and merge gate

Mirrors `environment/claude-code/autonomy/profiles/pr-convergence.json` `merge_gate` and join barrier. Cursor reports eligibility; humans merge.

## Join barrier

Join only when all of the following hold:

- Every launched `work` Task returned `status: done|blocked|failed` with evidence.
- Every `poll` Task returned terminal (`merge_eligible` | `escalated` | `failed`) with evidence.
- No unresolved lock conflicts.
- Campaign authorization packet still matches declared PRs/branches (no silent scope expansion).

Do not claim campaign “merge-ready” or progress past join until the barrier passes.

## Merge gate checklist (report-only)

Copy from profile — all required for “merge_eligible”:

- [ ] Exact PR head SHA recorded and matches remote HEAD
- [ ] All required checks success
- [ ] Local validation run if mutation occurred (repo’s PR/local gate)
- [ ] No merge conflicts
- [ ] No blocking review threads
- [ ] Dependencies merged (if any declared)
- [ ] Branch protection satisfied
- [ ] Proof bundle / evidence note attached (what changed, cycles used, remaining risks)

## Human merge only

- `autonomous_merge: false` always in this SOP.
- Never run `gh pr merge` (or MCP merge) unless the user explicitly approved merge in this conversation.
- After checklist: stop and ask the human to merge (or decline).

## Forbidden at join/merge

- Force-push, admin merge override, disable required checks, weaken tests for green, commit secrets, rewrite published history.
