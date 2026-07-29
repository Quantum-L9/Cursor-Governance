# Latent Capability Unthrottling Adapter

## Purpose

Load this adapter when CLI throughput may already exist in code but is unreachable, miswired, disabled, or unconsumed. Use reachability analysis to select an implementation candidate. Do not let the source audit's report-only mode replace the Skill's terminal requirement: a validated code change and deployable PR commit pack.

## Activation Signals

Activate when repository evidence or supplied findings mention:

- inactive components or code defined but never instantiated;
- miswired registries, dispatch tables, plugin maps, or unread keys;
- complete capabilities behind permanently-off flags or unmounted CLI routes;
- produced values, events, telemetry, or return fields with no consumer;
- configuration fields or environment variables with no producer or reader;
- producer and consumer components that exist but have no connecting edge.

Do not activate for ordinary hot-path optimization when reachability is not material.

## Required Inputs

Resolve or mark `UNKNOWN`:

- real CLI entrypoints and mounted command roots;
- registries, dispatch tables, plugin maps, reflection, and dynamic imports;
- feature-flag sources, current values, and staged-rollout intent;
- expected consumers of produced signals, fields, events, or return values;
- repository ownership of the disconnected edge;
- the workload and metric that the dormant capability is expected to improve.

## Reachability Convergence

Run at most three focused passes and stop when the edge table stabilizes:

1. **Static graph:** build import and call reachability from real CLI entrypoints.
2. **Dynamic graph:** resolve registries, plugins, reflection, generated entrypoints, and configuration-driven dispatch before classifying anything as disconnected.
3. **Producer-consumer graph:** map each relevant producer to its intended consumer, feature flag, configuration source, and runtime edge.

Diff defined components against the reachable set only after dynamic dispatch is resolved. Preserve unresolved reachability as `UNKNOWN`; never label it dead merely because grep found no direct call.

## Finding Classes

Use IDs `DWA-NNN` and exactly one class:

- `inactive_component`: defined but never imported, instantiated, or reached;
- `miswired_file`: connected to the wrong consumer or registered under an unread key;
- `dormant_capability`: complete code behind a permanently-off flag, unmounted route, unsurfaced CLI command, or never-emitted enum;
- `unused_signal`: produced value, event, telemetry, or return field with no consumer;
- `orphaned_config_schema`: configuration is defined but unread, or read but never set;
- `broken_partial_wiring`: producer and consumer both exist but their edge is absent.

## Mandatory Evidence

Every material finding must include:

- definition-site evidence;
- consumer-edge evidence proving the expected consumer is absent or misconnected;
- confirmation that dynamic dispatch and registries were checked;
- feature-flag or roadmap intent when applicable;
- an explicit `dormant_by_design` decision;
- the downstream capability unlocked by activation;
- the owner layer and repository ownership;
- leverage and release impact;
- a verdict: `activate`, `remove`, or `unknown`.

No consumer proof means `unknown`. `dormant_by_design: true` is not a defect and cannot be selected for activation by this Skill. A `remove` verdict is not automatically an optimization change; route true orphan cleanup outside this Skill unless deletion is required for the selected activation and remains inside the locked change map.

## Implementation Selection

A reachability finding may enter the optimization PR only when:

1. the finding is repository-owned;
2. its verdict is `activate`;
3. the selected edge directly affects a CLI execution path;
4. activation reuses an existing capability rather than inventing a parallel subsystem;
5. correctness and resource bounds are explicit;
6. a comparable baseline and candidate measurement can prove the throughput effect.

Prefer the smallest wiring repair that unlocks the highest verified leverage. Do not activate dormant code merely because it exists.

## Pack Evidence

When this adapter is active, the generated pack must include:

- `evidence/WIRING_MAP.md` with entrypoints, registries, flags, consumers, convergence status, and producer-to-consumer edges;
- `evidence/LATENT_CAPABILITY_FINDINGS.json` with all findings and selected IDs;
- selected finding IDs and unresolved wiring unknowns in `MANIFEST.json`;
- the activated capability and evidence path in the PR body and agent handoff.

`PR_READY` requires converged reachability, at least one selected `activate` finding, complete bidirectional evidence, no selected unknowns, no unresolved material wiring unknowns, and positive measured performance improvement after activation.
