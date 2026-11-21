# Merge-queue proof (X8)

Evidence for the merge-queue mode of `/l9-pr-remediation` (`stack_safe_merge.py`,
PR #1109) on `Quantum-L9/Cursor-Governance`, 2026-11-21. All reads below were made
over REST from the REST-only gateway the operator's `/l9-pr-remediation` runs on.

## Settings verified

| Item | Value | Source |
|---|---|---|
| `merge_queue` rule on `main` (ruleset 20855699) | `merge_method SQUASH`, `grouping_strategy ALLGREEN`, `max_entries_to_build 5`, `min_entries_to_merge 1`, `max_entries_to_merge 5`, `min_entries_to_merge_wait_minutes 5`, `check_response_timeout_minutes 60` | `GET repos/Quantum-L9/Cursor-Governance/rules/branches/main` |
| Repository "Allow auto-merge" | `true` (turned on by the operator after F1) | `GET repos/Quantum-L9/Cursor-Governance` → `allow_auto_merge` |

## Results

| Check | Result | Evidence |
|---|---|---|
| Queue merge end to end | PROVEN | #1130 (head `a446e55c`): `added_to_merge_queue` 17:51:27Z, `merged` and `removed_from_merge_queue` (`github-merge-queue[bot]`) 18:12:49Z, merge commit `c5fd35ca`. 21 minutes. The `stack_safe_merge.py` watcher reported MERGED. |
| (iii) REST observes queue membership | PROVEN | The issue timeline (`GET issues/{n}/timeline`) carries `added_to_merge_queue` / `removed_from_merge_queue`, the signal `queue_state()` reads on the REST path. Also visible: the `gh-readonly-queue/main/pr-<n>-<base>` branch (`GET git/matching-refs/heads/gh-readonly-queue`) and `GET actions/runs?event=merge_group`. `pulls/{n}.auto_merge` stays `null` while a PR is queued, so it is not a membership signal. |
| Eject detection | PROVEN | #1113 was closed while queued at 18:17:11Z; `removed_from_merge_queue` followed at 18:17:12Z; the watcher reported EJECTED ("removed from the queue without merging"). Nothing reached `main`. |
| (i) a push to a queued PR dequeues it | DISPROVEN, stronger | GitHub refuses the push. Pushing to #1113's branch while queued (18:13:49Z) returned `GH006: Protected branch update failed … A pull request for this branch has been added to a merge queue. Branches that are queued for merging cannot be updated. To modify this branch, dequeue the associated pull request.` A queued entry's head cannot move, so it stays bound to the granted head; the watcher's moved-head path is a second safeguard. |
| (ii) REST `DELETE pulls/{n}/ccr/auto_merge` dequeues | NOT YET PROVEN | Blocked by the guardrail defect below. To be run on a fresh throwaway PR once #1132 is on `main`. |

### Merge-group runs

#1130, merge-group branch `gh-readonly-queue/main/pr-1130-ba82b296…` (commit `c5fd35ca`):

| Run id | Workflow | Conclusion |
|---|---|---|
| 44932341239 | L9 Root-File Protection | success |
| 44932341221 | repo-hygiene | success |
| 44932341246 | governance-self-check | success |
| 44932341237 | L9 Lint and Test | success |
| 44932341459 | Organization CI (Core) | success |

#1113, merge-group branch `gh-readonly-queue/main/pr-1113-c5fd35ca…` (commit `f24211f1`), dequeued by the close: 44934366371 (L9 Root-File Protection, success), 44934366313 (repo-hygiene, success), 44934366328 (governance-self-check, success), 44934366331 (L9 Lint and Test) and 44934366642 (Organization CI (Core)) still running when the queue branch was removed.

## Findings

### F1 — the REST enqueue needs "Allow auto-merge"

On the REST-only gateway `stack_safe_merge.py` enqueues with `PUT pulls/{n}/ccr/auto_merge`.
With the repository setting off, GitHub answered **HTTP 422 "Auto merge is not allowed for
this repository"** (#1130, head `a446e55c`). The executor reported MERGE_PENDING and queued
nothing. GitHub's docs say the setting does not apply on a merge-queue branch; that covers
the web UI's **Merge when ready**, not this route. Precondition for the queue click-path:
Settings → General → Pull Requests → **Allow auto-merge** ON.

### F2 — the guardrail denied the dequeue DELETE

`ops/autonomy/git_guardrails.py` denied every authenticated `gh api` DELETE as "an
irreversible remote deletion with no local recovery", including
`DELETE pulls/{n}/ccr/auto_merge`, for the coding agent and the CTO session alike. That
route deletes no ref, commit or branch, and re-enqueueing the same head restores it. The
`stack_safe_merge.py` withdraw path (the UNBOUND_QUEUE_ENTRY fail-closed) depends on it.
#1113 was kept off `main` by closing the PR instead. Fix: **#1132** classifies exactly that
route as GUARD_THEN_ALLOW (deterministic regeneration) and keeps every other authenticated
DELETE denied.

## Operator readiness

`/l9-pr-remediation Quantum-L9/Cursor-Governance` can hand a green, authorized stack to the
queue from this surface: membership is observable over REST, a queued head cannot move, and
a queue merge completed end to end. Until (ii) is proven, withdraw a queued PR (cancellation
or timeout) with the web UI's **Remove from queue** or by closing it.
