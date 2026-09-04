<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: issue_handoff
tags: [pr, issues, handoff, l9-issue-remediation, cursor-subagents, autonomy]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Above-paygrade issue handoff

The remediator does **not** stop to ask the human to unblock. After it has
done its own best-effort fix (codebase cycles, venv preflight, required-check
board), anything still above this pack's edit axis is a GitHub issue plus a
downstream `l9-issue-remediation` launch. Independent PRs stay on the train.

Authority for this edge:

- `environment/contracts/autonomy/MANIFEST.yaml` (surface doctrine + merge gate)
- `environment/agents/cursor-subagents/DELEGATION_CONTRACT.yaml`
  (`above_paygrade_handoff`)
- Specialized owner: `skills/l9-issue-remediation` (not a sixth Cursor role)

## When (after best-effort only)

| Class | Best-effort first | Then |
|-------|-------------------|------|
| `HUMAN` | Reply + resolve the thread; name the decision | `gh issue create`; `pr_board.py --human-decision`; continue |
| `CI_PIPELINE` required and unfixable | Do not edit workflows; attempt merge if the check is not required | `gh issue create`; `pr_board.py --unfixable-check`; continue |
| `ENVIRONMENT` still broken after one venv preflight | Export `UV_PYTHON`; do not unpin locks | `gh issue create`; continue other PRs |

Do not open an issue for a required check that is still **in progress**
(`board=wait`). Poll it. Do not open an issue for optional red checks.

## How

1. Open one issue per distinct root cause (not per comment):

```bash
gh issue create --repo {owner}/{repo} --title "{class}: {one-line root cause}" --body "$(cat <<'EOF'
## Handoff from l9-pr-remediation

- **class:** HUMAN | CI_PIPELINE | ENVIRONMENT
- **repo:** {owner}/{repo}
- **pr:** #{n}
- **head:** {sha}
- **best-effort:** {what this remediator already tried}
- **why above paygrade:** {named decision or unfixable required check}
- **downstream:** l9-issue-remediation

Do not bounce this back to the PR remediator until `open_issues=0`.
EOF
)"
```

2. Record the issue number on the thread reply (HUMAN Deferred) and in the
   cycle status.
3. Launch `l9-issue-remediation` Converge as one background Task
   (`DELEGATION_CONTRACT.above_paygrade_handoff`: `launch_as: generalPurpose`
   under the `pr_remediation` role rules — the specialised issue skill, not a
   sixth Cursor role and not a remediator lane). Bound it to the new issue and
   `{owner}/{repo}`. It returns a result document like any lane. Continue the
   PR train immediately. Do not idle for that subagent.
4. This skill still does **not** merge from the issue agent, and the issue
   agent still does **not** `gh pr merge`. Reverse gate stays
   `open_issues=0` before the issue pack may invoke this skill.

## Forbidden

- Asking the human to unblock, click GitHub UI, or answer before continuing
- Parking the whole train because one PR is `leftover`
- Opening an issue instead of a codebase cycle that still remains
- Editing `.github/workflows/**` to "finish" the handoff
