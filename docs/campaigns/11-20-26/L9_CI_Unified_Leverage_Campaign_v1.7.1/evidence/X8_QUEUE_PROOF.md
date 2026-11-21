# X8 merge-queue proof

Operator check from PR #1109 (lane X8-PROOF), run on the throwaway PR #1113.
Do not merge this PR by hand; it is closed after the proof.

## Preconditions

| Item | State | Evidence |
|---|---|---|
| `merge_queue` rule on `main` (ruleset 20855699) | ON | `GET repos/Quantum-L9/Cursor-Governance/rules/branches/main`, 2026-11-21T17:31Z: `merge_method SQUASH`, `grouping_strategy ALLGREEN`, `max_entries_to_build 5`, `min/max_entries_to_merge 1/5`, `min_entries_to_merge_wait_minutes 5`, `check_response_timeout_minutes 60` |
| Repository setting "Allow auto-merge" | OFF (finding F1) | see below |

## Findings

### F1 — the REST-only enqueue needs "Allow auto-merge" (precondition missing from the X8 click-path)

On 2026-11-21 the CTO session ran the sanctioned queue path for CG #1130 (head
`a446e55c`). On the REST-only gateway `stack_safe_merge.py` enqueues with
`PUT pulls/{n}/ccr/auto_merge`, and GitHub answered **HTTP 422 "Auto merge is
not allowed for this repository"**. The executor reported MERGE_PENDING and
nothing was queued, which is the fail-closed outcome.

GitHub's docs say the "Allow auto-merge" setting does not apply on a branch that
requires a merge queue (*Automatically merging a pull request*). That covers the
web UI's **Merge when ready**. It does not cover the REST `ccr/auto_merge` route,
which this result shows is refused while the setting is off. The GraphQL
`enqueuePullRequest` mutation, which the executor uses where GraphQL is
available, is a separate path; whether it needs the setting is not established
here.

Required before (iii), (i), (ii): Settings → General → Pull Requests → **Allow
auto-merge** ON. This is not a result for (iii), (i) or (ii).

## Results

| Check | Result | Evidence |
|---|---|---|
| (iii) REST queue membership observable | NOT RUN | waiting on F1 |
| (i) a push to a queued PR dequeues it | NOT RUN | waiting on (iii) |
| (ii) REST `DELETE ccr/auto_merge` dequeues | NOT RUN | waiting on (i) |

merge_group run ids and the required checks' conclusions on the merge_group
commit: not yet recorded.
