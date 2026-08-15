# Blueprint Runbook

## 1. Instantiate

```bash
python scripts/instantiate.py --name "Program Name" --id program-id --version 0.1.0 --owner "Owner" --target ../program-id-blueprint
```

## 2. Phase 0 — dial the rail (before mutation / long autonomy)

Complete `PHASE0_USER_CONFIG.yaml` before Wave 0 mutation or long-running autonomy:

1. Set `program_deploying` and autonomy profile (`bounded_local_execution` or `program_deploy_max_autonomy`).
2. Inventory CI / stop reasons: classify `true_blocking` vs `advisory_or_disabled` (LL-001).
3. Issue scoped, expiring waivers for advisory CI (never secrets/org-invariant/human-merge).
4. Align `uv.lock` / toolchain pins per target (`make uv-lock-check`, AGENTS.md pin SSOT) (LL-004).
5. Require local `make pr` before any push/PR; remediation is exception-only (LL-003).
6. Bind campaign authorization **packet** fields (never “envelope”); set `adapter_status`.
7. Review stop-conditions taxonomy; clear environmental stops; leave only business DEC/UNK + hard safety.
8. Ack kill-switch path and resource hygiene (idle Docker / hung subagents).
9. Set `completeness.phase0_complete: true` only when the above are evidenced.

When deploying a program, default is **maximum autonomy within ceiling** with `autonomous_merge: false`.

## 3. Establish authority before decomposition

Complete `PROGRAM.yaml`, `EXECUTIVE_DECISION.md`, `EXECUTION_TARGETS.yaml`, `AUTHORITY_REGISTRY.yaml`, and current-state evidence first.

## 4. Resolve blockers

Do not mark a task ready while a required decision is pending or a named Unknown is open.

## 5. Build the execution map

Define workstreams, then Task Cards, then encode all task-to-task dependency edges in `DEPENDENCY_GRAPH.yaml`, then assign tasks to waves.

## 6. Define proof before mutation

Set acceptance, validation, negative cases, rollback, risk, authorization ceiling, and completion gates before importing the task into a Controller.

## 7. Validate and reseal

```bash
python scripts/validate_blueprint.py . --mode instantiated
```

Regenerate `MANIFEST.yaml` after every accepted change. A Controller runtime becomes stale when an imported source digest changes.
