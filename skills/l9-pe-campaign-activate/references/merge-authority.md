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

# Campaign vs remediations merge

Campaigns publish with `make pr` and MUST end **green + merge-ready**.
They do not merge.

Invoking **`/l9-pr-remediation`** is the operator act that authorizes merge
of **all open PRs** in the target repo.

## Mechanical gate

`ops/autonomy/merge_gate.py` allows ordinary `gh pr merge` when:

- `L9_MERGE_AUTHORIZED` is a nonempty reason, or
- `ops/autonomy/authorize_merge.py` wrote a future receipt for this repo
  (`pr: "*"` or the exact PR)

```bash
python3 ops/autonomy/authorize_merge.py --repo Quantum-L9/Cursor-Governance --all-open \
  --reason "l9-pr-remediation invoked"
gh pr merge 123 --repo Quantum-L9/Cursor-Governance --squash --delete-branch
```

Never waived: `--admin`, force-push, hard-reset.

The wrapper
`skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py`
calls the same ops script.
