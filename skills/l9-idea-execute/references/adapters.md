<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: adapters
tags: [ideaos, foundry, website-bot, plan-simple, program-execution, evidence]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-12
/L9_META -->

# Adapter contracts

## Table of contents

1. Common adapter protocol
2. Capability evidence states
3. l9-idea-foundry
4. Website-Bot
5. l9-plan-simple
6. Program Execution
7. Failure behavior

## 1. Common adapter protocol

For every execution unit:

1. discover the current owner contract;
2. capture authoritative source refs plus exact repository revision/path bindings;
3. compile a current `l9.idea-execute.adapter-capabilities/v2` snapshot bound to the exact Graph unit;
4. validate the snapshot;
5. reconcile any supplied/reused snapshot against the current snapshot before reuse;
6. verify requested topology with `check_adapter_capability.py` using current evidence;
7. compile only the owner's native public input;
8. validate through owner-native validation where available;
9. invoke only the canonical public front door;
10. stop at the owner's terminal boundary;
11. reference the owner's canonical receipt/state.

Adapters translate. They do not absorb downstream business logic.

A snapshot is not reusable merely because its schema validates. It must identify the Graph unit it evaluates and, when reused from an earlier run, its source bindings and contract fields must agree with freshly discovered current evidence.

## 2. Capability evidence states

A valid current snapshot may establish:

- `COMPATIBLE`: requested topology is explicitly supported;
- `EXECUTOR_CAPABILITY_GAP`: requested topology is explicitly unsupported;
- `ADAPTER_CAPABILITY_UNKNOWN`: snapshot is valid but support remains unresolved.

Evidence defects are separate:

- `ADAPTER_SNAPSHOT_INVALID`: snapshot shape/provenance is invalid;
- `ADAPTER_SNAPSHOT_STALE`: supplied snapshot source revision/path bindings differ from current evidence;
- `ADAPTER_CONTRACT_CONFLICT`: snapshot identity, Graph-unit binding, or same-source contract facts conflict;
- `UNRESOLVED`: supplied evidence has no fresh current snapshot available for a reuse decision.

Never convert missing, malformed, stale, conflicting, or unrefreshed evidence into `EXECUTOR_CAPABILITY_GAP`.

## 3. l9-idea-foundry

Use only when a new standalone product/system repository is required and no specialized factory already owns the artifact.

Do not use for Website-Bot-generated sites, existing-repository modifications, or generic code changes merely because code is required.

Load the current Foundry contract and let Foundry own its blueprint, code realization, traceability, exact-state validation, freeze, and repo-template seam.

## 4. Website-Bot

Owner: `Quantum-L9/Website-Bot`.

Before use, inspect the current authoring and provisioning contract. Compile rich `domain_spec.source.yaml`, not a hand-maintained generated DomainSpec.

Preserve missing facts as Unknown. Do not invent credentials, phone numbers, proof, case studies, legal claims, geographic facts, or deployment identifiers to satisfy a schema.

## 5. l9-plan-simple

Use for bounded existing-repository work when current execution artifacts are insufficient.

Before invoking:

- inspect the current `l9-plan-simple` contract;
- bind the current snapshot to the exact Graph unit plus revision/path inspected;
- reconcile any prior snapshot against that current evidence;
- determine the current planning/execution handoff mode;
- reuse a valid existing plan rather than replacing it.

The existence of embedded mode or another accepted handoff must be proven from the live contract. An old capability snapshot is not sufficient evidence.

## 6. Program Execution

Use for campaign-shaped coordinated modifications to existing systems.

Program Execution is an evolving adapter. Read `program-execution-adapter.md` as a discovery guide, then inspect the live front door before each mutating handoff.

Never call inner PE components to bypass public admission. Never decompose one atomic campaign merely because the current adapter cannot represent it.

## 7. Failure behavior

Distinguish exactly:

- `ADAPTER_CONTRACT_UNAVAILABLE`: cannot discover current public intake;
- `ADAPTER_SNAPSHOT_INVALID`: discovered evidence cannot satisfy the snapshot contract;
- `ADAPTER_SNAPSHOT_STALE`: supplied snapshot bindings no longer match current source bindings;
- `ADAPTER_CONTRACT_CONFLICT`: authoritative sources, adapter identity, or Graph-unit binding disagree materially;
- `ADAPTER_CAPABILITY_UNKNOWN`: valid current evidence does not resolve support;
- `EXECUTOR_CAPABILITY_GAP`: valid current evidence proves the requested topology unsupported;
- `OWNER_NATIVE_INPUT_INVALID`: compiled native input is rejected by owner validation;
- `DOWNSTREAM_EXECUTION_FAILED`: canonical front door ran and failed;
- `DOWNSTREAM_RECEIPT_INVALID`: claimed completion does not satisfy owner evidence.

Do not automatically reroute to a weaker executor after any of these failures.
