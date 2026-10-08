# Protocol C — Join and merge gate

Owned by `ops/autonomy/merge_gate.py` and the scoped, expiring receipt `/l9-pr-remediation` writes. After that skill reaches green + mergeable + resolved threads, ordinary squash merge is authorized by that receipt (or a human `L9_MERGE_AUTHORIZED=<reason>`); `merge_gate.py` consults no environment boolean.

## Join barrier

Join only when all of the following hold:

- Every launched `work` Task returned `status: done|blocked|failed` with evidence.
- Every `poll` Task returned terminal (`merge_eligible` | `escalated` | `failed`) with evidence.
- No unresolved lock conflicts.
- Campaign authorization packet still matches declared PRs/branches (no silent scope expansion).

Do not claim campaign “merge-ready” or progress past join until the barrier passes.

## Merge gate checklist (report-only)

All required before `merge_gate.py` can treat a PR as merge-eligible:

- [ ] Exact PR head SHA recorded and matches remote HEAD
- [ ] All required checks success
- [ ] Local validation run if mutation occurred (repo’s PR/local gate)
- [ ] No merge conflicts
- [ ] No blocking review threads
- [ ] Dependencies merged (if any declared)
- [ ] Branch protection satisfied
- [ ] Proof bundle / evidence note attached (what changed, cycles used, remaining risks)

## Autonomous ordinary merge after remediation

- `merge_gate.py` reads no environment boolean: it authorizes merge only from the scoped, expiring receipt `/l9-pr-remediation` writes (or a human `L9_MERGE_AUTHORIZED=<reason>`).
- After this checklist: `gh pr merge --squash` oldest first. Never `--admin`, never force-push.
- Campaigns and `make pr` still stop at green + merge-ready. They do not merge.

## Forbidden at join/merge

- Force-push, admin merge override, disable required checks, weaken tests for green, commit secrets, rewrite published history.
