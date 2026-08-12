<!-- L9_META
l9_schema: 1
artifact_id: l4-local-autonomy
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-08-12
owner: platform
layer: ops
tags: [l9, autonomy, first_class, l4]
/L9_META -->

# L4 local autonomy — metadata

**CLI:** `ops/autonomy/l4_local.py`  
**Gate:** `ops/autonomy/local_execution_gate.py`  
**Merge gate:** `ops/autonomy/merge_gate.py`  
**Profile fragment:** `l4_local_autonomy` in `ops/autonomy/surface_profile.yaml`

## Purpose

Mechanical no-mid-execution-push doctrine for all surfaces; release receipt
unlocks scoped push/PR.

## Not for

- Mid-execution `git push` / `gh pr create` / `make pr` before `release_authorized`
