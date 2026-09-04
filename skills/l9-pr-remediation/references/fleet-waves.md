<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: fleet_waves
tags: [pr, fleet, waves, subagents, concurrency, result-contract]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-04
/L9_META -->

# Fleet waves (parallel remediation without a campaign)

`ops/autonomy/pr_fleet.py` names the largest safe wave; the main agent launches
it natively. No Program Execution, no campaign, no admission token, no lease
store. Safety comes from three things that already exist:

1. **Conflict isolation** — a PR enters a mutation wave only when its write
   claims (`path:<file>` for every non-generated file, `branch:<head>`) conflict
   with no PR already in that wave, decided by the claim plane's own primitive
   (`autonomy.runtime.claims.claim_scopes_conflict`). Generated-only overlap
   never serializes; it heals after merge.
2. **Bounded scope** — every assignment carries `allowed_paths` (the PR's files
   plus generated companions) and `forbidden_paths` (CI surfaces, secrets).
3. **Fail-closed acceptance** — every lane ends with one
   `l9.cursor-subagent.result.v1` document judged by `pr_fleet.py accept`
   through `result_bridge.validate_result_against_assignment` and the results
   gateway. Wrong base SHA, wrong identity, a changed file outside the grant, a
   read-only role reporting changes, or a non-success host stop is `REJECTED`.

Caps are read from `ops/autonomy/execution_profile.py` (Cursor constrained,
Claude saturating). This pack never states a number.

## Wave shapes

| Lane | Kind | Role / managed Task | Mutates | When |
|---|---|---|---|---|
| remediate | `remediate` | `pr_remediation` / `l9-pr-remediation` | bounded | every PR in `waves.first_wave.remediate` |
| recon | `recon` | `recon` / `l9-recon` | no | PRs blocked by a claim conflict or the mutation cap: diagnose now, patch next wave |
| watch | `watch` | `recon` / `l9-recon` | no | `board=wait` PRs: observe required checks in the background |

## Launch (one message)

```bash
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/pr_fleet.py plan --repo {owner}/{repo} --board --json
# wave 1, all assignments in one call per kind; --record writes the lifecycle
# assignment the results gateway loads; --prompt renders the Task prompt
"$GOV_PY" ops/autonomy/pr_fleet.py assign --repo {owner}/{repo} --kind remediate --record --prompt --json
"$GOV_PY" ops/autonomy/pr_fleet.py assign --repo {owner}/{repo} --kind recon --record --prompt --json
"$GOV_PY" ops/autonomy/pr_fleet.py assign --repo {owner}/{repo} --kind watch --record --prompt --json
```

Then, in **one** assistant message, launch one background Task per assignment
using its `cursor.managed_task_type` and `prompt`. Serializing independent
ready lanes is a protocol violation. Main agent afterwards: take one remediation
lane only if the cap left a free mutation slot; otherwise run the merge-train
preflight (thread re-query, board refresh for green heads) or the next PR's
diagnosis. Never `AwaitShell` on a lane; never poll a PR a watcher owns.

Each lane works on its own worktree for its own branch (`git worktree list`
first; `worktree_add_wired.sh` only when none holds the branch). Two lanes
never share a branch — the `branch:<head>` claim guarantees the planner never
admits that.

## Return and accept

A lane's last act is writing its result document (schema:
`environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json`,
`result_kind` `PRRemediationReport` for remediation, `ReconReport` for recon and
watch). Identity fields are copied verbatim from the assignment. `files_changed`
is truthful. `validations` names `make precommit-repo` with `PASS` / `FAIL`.
`status` is `completed` only when the plan was executed, verified, published,
and every thread replied to; otherwise `partial`, `blocked` (head moved, lease
of the branch lost), or `failed`.

```bash
"$GOV_PY" ops/autonomy/pr_fleet.py accept --assignment {assignment_id} --result {doc.json} --json
```

| Outcome | Meaning | Main agent does |
|---|---|---|
| `ACCEPTED` | completed and correlated; durable acceptance receipt written | close the lane; PR enters the merge train on its board verdict |
| `ACCEPTED_INCOMPLETE` | `partial` / `blocked` / `failed`, correlated | keep the PR in the next wave with the unresolved items as input |
| `REJECTED` | identity, base SHA, role, scope, or host status failed | re-assign with the reason, or take the PR into the main lane; never trust the narrative |

## Next wave

`mutation_waves[k]` for `k ≥ 1` launches the same way once every lane whose
claims blocked it has returned. Before launching, `pr_fleet.py plan` again:
if the fingerprint is unchanged the receipt is reused; if a head moved the
plan is recomputed and stale assignments are discarded. Watchers persist
across waves until their PR reaches `CLEAN` or a red required check.

## Never

- a lane that merges, force-pushes, edits CI surfaces, or asks the human
- two mutation lanes on one branch or one non-generated path
- a lane closed on "done" without an accepted document
- a cap or lane count written into this pack
