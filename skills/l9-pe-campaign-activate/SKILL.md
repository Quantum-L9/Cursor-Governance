---
name: l9-pe-campaign-activate
description: activate a program execution campaign through make pr to a green merge-ready campaign PR. merge is not this skill — invoke /l9-pr-remediation after the campaign if PRs are still open.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, program-execution, campaign, merge]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-08-16
---

# PE Campaign Activate — merge boundary

Campaigns publish with `PR_REMEDIATE=0 make pr` and MUST end **green +
merge-ready**. They do not merge.

Invoking **`/l9-pr-remediation`** authorizes merge of all open PRs in the
target repo. Receipt writer SSOT: `ops/autonomy/authorize_merge.py`.
Wrapper: [scripts/authorize_campaign_merge.py](scripts/authorize_campaign_merge.py).
Policy: [references/merge-authority.md](references/merge-authority.md).
