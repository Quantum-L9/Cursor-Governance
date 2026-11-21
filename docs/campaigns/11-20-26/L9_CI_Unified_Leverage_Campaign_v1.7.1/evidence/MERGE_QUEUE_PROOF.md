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
| (i) a push to a queued PR dequeues it | DISPROVEN, stronger | GitHub refuses the push. Pushing to #1113's branch while queued (18:13:49Z) returned `GH006: Protected branch update failed … A pull request for this branch has been added to a merge queue. Branches that are queued for merging cannot be updated. To modify this branch, dequeue the associated pull request.` The same push to #1135 while queued was refused with the same GH006. A queued entry's head cannot move, so it stays bound to the granted head; the watcher's moved-head path is a second safeguard. |
| (ii) REST `DELETE pulls/{n}/ccr/auto_merge` dequeues | NOT YET PROVEN | The first attempt (#1135) was denied by a stale guardrail copy and the PR merged (F3). To be run on a PR the CTO enqueues and that should be merged anyway. |

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

### F3 — a do-not-merge throwaway merged through the queue (#1135)

#1135 added only `evidence/X8_THROWAWAY.md` and was enqueued for checks (i) and (ii).
Timeline (`GET issues/1135/timeline`): `added_to_merge_queue` 19:31:28Z;
`removed_from_merge_queue` (`github-merge-queue[bot]`) 19:58:07Z; `merged` 19:58:08Z as
`bec7cff4`. Merge group `gh-readonly-queue/main/pr-1135-5b9c2a3c…`:

| Run id | Workflow | Finished |
|---|---|---|
| 44941409703 | L9 Root-File Protection | 19:31:59Z |
| 44941409714 | repo-hygiene | 19:31:56Z |
| 44941409726 | governance-self-check | 19:32:59Z |
| 44941409640 | L9 Lint and Test | 19:40:41Z |
| 44941409986 | Organization CI (Core) | 19:57:34Z |

All five succeeded. Nothing dequeued the PR during those 26 minutes. The coding agent's
`DELETE pulls/1135/ccr/auto_merge` was denied with the pre-#1132 message. #1132 was on
`main`, but the PreToolUse hook loads `git_guardrails.py` from the session's primary checkout
(`CLAUDE_PROJECT_DIR`), and that checkout was still at `a3f07327`. Repair: `/ff` moved it to
`bec7cff4`, and `command_requires_human` now returns no denial for that DELETE from that
checkout. The file is removed by #1142.

Lesson: a dequeue that a hook may deny cannot be the only way a throwaway leaves the queue.
Prove (ii) on a PR whose merge is harmless.

### F4 — a docs-only PR still waits for the full merge-group CI

None of the four repository workflows that run on `merge_group` (`governance-self-check.yml`,
`l9-lint-test.yml`, `repo-hygiene.yml`, `root-file-protection.yml`) filters by path; each takes
`merge_group: {types: [checks_requested]}`. Organization CI (Core) is required on `main` by
ruleset 21895545 (`workflows` rule on the org `org-ci.yml`; required check
`Analyze (central Core)`). It ran on #1135's docs-only merge group and took 25 minutes. Ruleset
20855699 requires `Lint and Type Check`, `Test Suite`, `Root-file append-only gate`,
`governance-self-check` and `repo-hygiene`. So a docs-only PR is not merged near-instantly. It
waits about 21–26 minutes (#1130: 21; #1135: 26), and Organization CI (Core) is the critical path.

### F5 — a PR that only deletes files cannot pass `Analyze (central Core)`

#1142 deletes one file and nothing else. Its `Analyze (central Core)` run (44945680555) failed in
repository verification: `make test` exited 2 with
`PR_SCOPE_UNKNOWN: no changed path remains on HEAD; full suite refused`.
`ops/scripts/lib/ci_pr_scope.sh` keeps only changed paths that exist on HEAD, and
`ops/scripts/run_pytest_suites.sh` refuses an empty list on `pull_request`. Every PR that only
deletes files is blocked from `main` the same way, since that check is required.

## Operator readiness

`/l9-pr-remediation Quantum-L9/Cursor-Governance` can hand a green, authorized stack to the
queue from this surface: membership is observable over REST, a queued head cannot move, and
a queue merge completed end to end. Until (ii) is proven, withdraw a queued PR (cancellation
or timeout) with the web UI's **Remove from queue** or by closing it.
