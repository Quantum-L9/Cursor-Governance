<!-- L9_META
l9_schema: 1
artifact_id: program-execution-autonomy-consumer
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-11-12
owner: platform
layer: program-execution
tags: [l9, autonomy, program-execution, consumer_binding, first_class]
/L9_META -->

# Program Execution autonomy consumer — metadata

**SSOT path:** `environment/program-execution/integrations/autonomy-control-plane/`
**Stage:** `manual` (`ops/autonomy/surface_profile.yaml` → `campaign_execution`)
**Law:** `CANONICAL_LAW.md` `PROGRAM_EXECUTION_MANUAL_STAGE_V1`

## Purpose

How Program Execution consumes root autonomy. It reads its standing authority
from the surface profile, takes one subordinate root lease per task, authorizes
every worker effect through the root gateway from a hook it registers in its
own worker windows, and stays inside the lanes the autonomy execution profile
grants.

## Direction

One way. Program Execution depends on root `autonomy/`. Root autonomy, L4 and
publication never require, import or resolve through Program Execution.

## Not for

- a campaign no operator explicitly asked for;
- a root make target before the `registered` stage;
- making root autonomy depend on Program Execution.
