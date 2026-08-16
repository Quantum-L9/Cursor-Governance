<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: merge_authority
tags: [campaign, merge, remediation, autonomy]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-08-16
/L9_META -->

# Authorized merge after remediation

Do not use this file as a campaign front door. Start and finish the
campaign with `make campaign INTENT=`. These commands apply only to
STACK.json PRs the runner already opened.

Purpose: this skill's merge step. Standing campaign policy still says
`merge: false` for ordinary agents. Invoking **this skill** is the operator
act that authorizes merge of **one** PR.

Invoking **`/l9-pr-remediation`** from `make campaign` authorizes merge of
**stacked PRs opened by this run** (`STACK.json` `pr_number` values) after
they are green and mergeable. It does not authorize
`all_open_prs_in_target_repo`. Receipt SSOT: `ops/autonomy/authorize_merge.py`.

## When merge is allowed

All of the following must be true on the observed head SHA:

1. This skill is the active control plane for the run
2. The PR was opened by this run for `campaign/<id>`
3. `l9-pr-remediation` Converge reports required checks success
4. The PR is mergeable (no conflict; no unanswered codebase review threads)
5. Remaining blockers are empty or only recorded CI-pipeline items that
   cannot be fixed in codebase (then do **not** merge — stop)
6. `scripts/authorize_campaign_merge.py` wrote a matching one-shot entry

## Mechanical gate

`ops/autonomy/merge_gate.py` allows ordinary `gh pr merge` when:

- `L9_MERGE_AUTHORIZED` is a nonempty reason, or
- `ops/autonomy/authorize_merge.py` wrote a future receipt for this repo
  (`pr: "*"` or the exact PR)

This skill uses the file channel, scoped to one PR, 4-hour expiry:

```bash
python3 skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py \
  --repo Quantum-L9/Cursor-Governance --pr 123 \
  --reason "l9-pe-campaign-activate remediation complete"
gh pr merge 123 --squash --delete-branch
```

`/l9-pr-remediation` uses repo scope:

```bash
python3 ops/autonomy/authorize_merge.py --repo Quantum-L9/Cursor-Governance --all-open \
  --reason "l9-pr-remediation invoked"
gh pr merge 123 --repo Quantum-L9/Cursor-Governance --squash --delete-branch
```

An L4 release receipt does **not** authorize merge.

The wrapper
`skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py`
calls the same ops script.

## Still forbidden

- merge of any other PR from this skill (use `/l9-pr-remediation` for fleet merge)
- `--admin` / bypass rules
- force-push
- merge while checks are red or reviews request codebase changes
- exporting `L9_MERGE_AUTHORIZED` as a session-wide blanket

## After merge

Close the campaign ledger. Do not start the next `execute_order` campaign
from this skill unless the user named it in the same invocation.
