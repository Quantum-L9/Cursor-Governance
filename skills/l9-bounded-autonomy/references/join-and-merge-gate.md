# Protocol C — Join and merge gate

Mirrors `environment/program-execution/peer_execution/autonomy/profiles/pr-convergence.json` `merge_gate` and join barrier. After `/l9-pr-remediation` reaches green + mergeable + resolved threads, ordinary squash merge is authorized (`L9_AUTONOMY_AUTONOMOUS_MERGE=true`).

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

## Autonomous ordinary merge after remediation

- `autonomous_merge: true` in `pr-convergence.json`. `merge_gate.py` reads `L9_AUTONOMY_AUTONOMOUS_MERGE`.
- After this checklist: `gh pr merge --squash` oldest first. Never `--admin`, never force-push.
- Campaigns and `make pr` still stop at green + merge-ready. They do not merge.

## Forbidden at join/merge

- Force-push, admin merge override, disable required checks, weaken tests for green, commit secrets, rewrite published history.
