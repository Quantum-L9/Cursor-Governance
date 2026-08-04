<!-- L9_META
layer: reference
role: findings_taxonomy
tags: [audit, evidence, drift, severity]
status: active
-->
# Findings Taxonomy

A finding requires observable evidence, an operational consequence, and a bounded remediation decision.

## Classes

| Class | Evidence | Renovation decision |
|---|---|---|
| dependency_authority_drift | manifest, lock, CI install, import | collapse declarations and install paths into one authority |
| package_boundary_ambiguity | build metadata, workspace layout, bootstrap | name actual package boundaries and install semantics |
| test_topology_gap | ignored suite, shadowed import, orphaned validator | register, isolate, and execute intentionally |
| local_ci_divergence | duplicated commands or different dependencies | make CI consume repository-owned entrypoints |
| dead_wiring | executable or capability with no reachable caller | wire and test, or classify dormant-by-design |
| registry_drift | disk inventory differs from canonical registry | regenerate or reconcile through one owner |
| documentation_code_drift | prose materially misstates active behavior | update prose after executable contract is fixed |
| security_or_permission_drift | excessive token, write scope, unsafe path | reduce privilege and add negative validation |
| release_consumer_drift | package/tag/template consumers misaligned | preserve or migrate with explicit compatibility proof |
| validation_theater | advisory or bypassed gate presented as strict | scope, ratchet, and report honestly |

## Severity

- `critical`: permits unsafe mutation, secret exposure, corrupt release, or silent data loss.
- `high`: active behavior is untested, dependency resolution is non-reproducible, or CI can falsely pass.
- `medium`: duplicated authority or stale contract creates likely future drift.
- `low`: misleading or inefficient but does not currently alter correctness.

## Proof burden

Do not call code dead because text search found no caller until registries, dynamic loading, plugin discovery, hooks, generated wiring, and external consumers are checked. Do not call a suite active because test files exist until a canonical command executes it.
