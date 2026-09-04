<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: adapters
tags: [ideaos, foundry, website-bot, program-execution]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Adapter contracts

## Table of contents

1. Common adapter protocol
2. l9-idea-foundry
3. Website-Bot
4. l9-plan-simple
5. Program Execution
6. Adapter failure behavior

## 1. Common adapter protocol

For every execution unit:

1. discover the current owner contract;
2. capture the relevant contract revision/path or other evidence;
3. verify the requested topology is supported;
4. compile only the owner's native public input;
5. validate through owner-native validation where available;
6. invoke only the owner's canonical front door;
7. stop at the owner's terminal boundary;
8. reference the owner's canonical receipt/state.

Adapters translate. They do not absorb downstream business logic.

## 2. l9-idea-foundry

Use when:

- a new standalone product/system repository is required;
- no specialized factory already owns that artifact.

Do not use for:

- Website-Bot-generated sites;
- modifications to an existing repository;
- generic code changes merely because code is required.

Load and obey the current `l9-idea-foundry` skill. Let it own architecture compilation, planning composition, realization, exact-state validation, freeze, and repo-template birth.

## 3. Website-Bot

Owner: `Quantum-L9/Website-Bot`.

Before use, inspect the current authoring contract, especially:

- `README.md` authoring flow;
- `src/pipeline/BuildContext.ts` `DomainSpec` type;
- `scripts/normalize-spec.ts`;
- current examples and validation;
- provisioning contract when remote/provisioning work is requested.

Compile **rich authoring input**, not the generated flat DomainSpec.

Expected ownership chain on the current baseline:

```text
IdeaOS truth
  -> domain_spec.source.yaml
  -> Website-Bot normalize-spec
  -> domain_spec.normalized.yaml
  -> Website-Bot pipeline
```

Preserve missing facts as missing/unknown. Never invent phone numbers, credentials, proof, case studies, legal claims, geographic facts, or deployment identifiers merely to satisfy a schema.

Let Website-Bot own its internal SEO intelligence, design stages, images, schema generation, site assembly, provisioning, publication, deployment, and SEO-Bot handoff.

## 4. l9-plan-simple

Use only for bounded existing-repository work when current execution artifacts are insufficient.

Before invoking:

- inspect the current live `l9-plan-simple` contract;
- verify its planning/execution handoff mode;
- reuse a valid existing plan rather than replacing it.

If the source is already execution-ready and the selected executor accepts it, skip planning.

## 5. Program Execution

Use for campaign-shaped coordinated modifications to existing systems.

Program Execution remains under development. Read [program-execution-adapter.md](program-execution-adapter.md) for the required live discovery procedure and current baseline.

The adapter must never call inner PE components to bypass the public front door.

## 6. Adapter failure behavior

Distinguish:

- `ADAPTER_CONTRACT_UNAVAILABLE`: cannot determine current public intake;
- `EXECUTOR_CAPABILITY_GAP`: correct executor, unsupported requested topology;
- `OWNER_NATIVE_INPUT_INVALID`: adapter compilation produced an input rejected by owner validation;
- `DOWNSTREAM_EXECUTION_FAILED`: canonical front door ran and failed;
- `DOWNSTREAM_RECEIPT_INVALID`: reported completion does not satisfy expected owner evidence.

Do not reroute to a weaker generic executor automatically after one of these failures.
