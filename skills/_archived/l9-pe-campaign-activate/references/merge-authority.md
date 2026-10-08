<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: merge_authority
tags: [campaign, merge, remediation, autonomy]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-23
/L9_META -->

# Merge authority boundary

Program Execution owns **no** push, pull-request, or merge authority.

`make campaign INTENT=...` terminates after Controller verification and local
commits. `L9_PE_RELEASE_AUTHORIZED` is not an authority source and cannot reopen
remote actions. The compatibility script `authorize_campaign_merge.py` therefore
fails closed and never writes a merge grant.

After PE handoff:

1. Publish through the root L4 surface: `PR_REMEDIATE=0 make pr`.
2. Converge and merge only through `/l9-pr-remediation`, under the exact approval
   model owned by `core/shared/AUTHORIZATION_MODEL.yaml`.

Capability never implies authorization. A PE lease or campaign invocation cannot
manufacture a remote-action approval.
