<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: merge_authority
tags: [campaign, merge, remediation, autonomy]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-15
/L9_META -->

# Authorized merge after remediation

Purpose: this skill's merge step. Standing campaign policy still says
`merge: false` for ordinary agents. Invoking **this skill** is the operator
act that authorizes merge of **one** PR.

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

`ops/autonomy/merge_gate.py` denies `gh pr merge` unless:

- `L9_MERGE_AUTHORIZED` is a nonempty reason, or
- `~/.l9/autonomy/merge-authorization.json` has a future `expires_at`
  matching this `repo` and `pr`

This skill uses the file channel, scoped to one PR, 4-hour expiry:

```bash
python3 skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py \
  --repo Quantum-L9/Cursor-Governance --pr 123 \
  --reason "l9-pe-campaign-activate remediation complete"
gh pr merge 123 --squash --delete-branch
```

An L4 release receipt does **not** authorize merge.

## Still forbidden

- merge of any other PR
- `--admin` / bypass rules
- force-push
- merge while checks are red or reviews request codebase changes
- exporting `L9_MERGE_AUTHORIZED` as a session-wide blanket

## After merge

Close the campaign ledger. Do not start the next `execute_order` campaign
from this skill unless the user named it in the same invocation.
