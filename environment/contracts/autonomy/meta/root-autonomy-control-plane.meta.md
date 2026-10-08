<!-- L9_META
l9_schema: 1
artifact_id: root-autonomy-control-plane
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-08-12
owner: platform
layer: control_plane
tags: [l9, autonomy, first_class, control_plane]
/L9_META -->

# Root autonomy control plane — metadata

**SSOT path:** `autonomy/`  
**owns_program_state:** `false`

## Purpose

Campaign compiler, leases, capability gateway, receipts, and provider-neutral
bounded-concurrency runtime. Provider adapters remain thin consumers.

## Not for

- Owning program state or outliving a Program lease
- Free-form mutation without a Program lease / campaign packet
