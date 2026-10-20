# Protocol C — Join and merge gate

Owned by `ops/autonomy/merge_gate.py` and `ops/autonomy/stack_safe_merge.py`. After `/l9-pr-remediation` reaches green + mergeable + resolved threads, a PR merges only under human authorization bound to the repo, PR and exact head — the operator's typed `/l9-pr-remediation` (CANONICAL_LAW §6.2.15), their recorded chat instruction, or a GitHub record — transcribed by the parent agent with `authorize_merge.py --operator-instruction` and merged with `stack_safe_merge.py --run` (or a human `L9_MERGE_AUTHORIZED=<reason>`); `merge_gate.py` consults no environment boolean and `--all-open` is never issuable.

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

- `merge_gate.py` reads no environment boolean: it authorizes merge only from a per-PR, exact-head human authorization (or a human `L9_MERGE_AUTHORIZED=<reason>`).
- After this checklist: `stack_safe_merge.py --head-sha <sha> --run` oldest first (it chooses the method). Never `--admin`, never force-push.
- Campaigns and `make pr` still stop at green + merge-ready. They do not merge.

## Forbidden at join/merge

- Force-push, admin merge override, disable required checks, weaken tests for green, commit secrets, rewrite published history.
