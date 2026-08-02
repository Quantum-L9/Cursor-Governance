# Instantiation Guide

Use an Execution Program when work spans multiple dependent systems, repositories, teams, authority boundaries, migrations, cutovers, releases, or evidence gates. Use an ordinary implementation plan for a small isolated feature.

## Required sequence

1. Name the objective, problem, target state, scope, owner, and contract versions.
2. Complete **Phase 0** in `PHASE0_USER_CONFIG.yaml` before mutating waves or long autonomy: dial autonomy, classify blocking vs advisory stops, align `uv.lock`/pins, require local `make pr`, bind campaign authorization packet fields (never “envelope”), and acknowledge kill-switch / resource hygiene.
3. Register every target with a stable target ID. Do not use human prose as repository identity.
4. Assign one owner per durable responsibility.
5. Catalog current evidence and its freshness.
6. Record decisions, Unknowns, risks, waivers, and prohibited paths.
7. Define workstreams and bounded Task Cards (include `autonomy_action_id` when bridging to Cursor/Claude autonomy).
8. Encode dependencies once in `DEPENDENCY_GRAPH.yaml`.
9. Assign tasks to waves and gates.
10. Define observability, cutover, rollback, and Definition of Done.
11. Validate in instantiated mode and import into the Controller.

Every placeholder must be resolved before the Blueprint is considered executable.

When `program_deploying: true`, Phase 0 defaults autonomy to **maximum within ceiling** (`program_deploy_max_autonomy` profile) with `autonomous_merge: false`. Remaining mid-flight stops must be business-logic DEC-* / UNK-* or hard safety only.

## Acceptance transition

The instantiated copy remains `draft` while domain placeholders, evidence, decisions, Unknowns, task cards, and gates are completed. Set `program.definition_status: accepted` only after `--mode instantiated` validation passes.
