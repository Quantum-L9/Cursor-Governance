<!-- L9_META
l9_schema: 1
artifact_id: peer-execution-bounded-autonomy-runtime
first_class_artifact: true
schema_family: l9_autonomy_architecture
version: 1.0.0
status: active
updated: 2026-08-12
owner: platform
layer: peer-execution
tags: [l9, autonomy, peer-execution, first_class]
/L9_META -->

# Peer Execution bounded-autonomy runtime metadata

**SSOT path:** `environment/program-execution/peer_execution/autonomy/`

This runtime owns shared admitted-dispatch concurrency mechanics only. Program
Execution owns Program state and admission. Root `autonomy/` owns authorization.
No provider adapter receives an autonomy or scheduler exemption.
