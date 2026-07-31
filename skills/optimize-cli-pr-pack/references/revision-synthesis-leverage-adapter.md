# CLI Revision Synthesis and Leverage Adapter

## Activation

Load after performance, reachability, documentation-code, resource, validation, deployment, and external-limit findings have been collected. Apply before choosing the CLI revision strategy or editing the final change map.

## Core law

Choose the revision that improves future revisions, strengthens existing repository assets, produces reusable capability, solves multiple bottlenecks where safe, and avoids recurring maintenance drag. Do not confuse a larger patch or faster benchmark with leverage.

## Synthesis order

1. Normalize every material observation into a `CLI-FND-NNN` finding.
2. Map every finding to at least one `CLI-TGT-NNN` revision target, including out-of-scope downstream targets.
3. Generate one or more `CLI-OPT-NNN` options for each target.
4. Score each option using the dimensions and weights below.
5. Apply thresholds and select only options whose evidence, scope, and risk support implementation.
6. Freeze the selected option IDs before generating `OPTIMIZATION_PLAN.json`.
7. Preserve rejected, deferred, and out-of-scope options in the synthesis report so future agents do not repeat discovery.

## Weighted dimensions

Use a 0-5 scale. Interpret the universal kernel for CLI engineering as follows:

| Dimension | Weight | CLI interpretation |
|---|---:|---|
| `future_action_acceleration` | 0.22 | makes future CLI changes, tests, diagnosis, or releases easier |
| `existing_asset_amplification` | 0.20 | activates or strengthens code, tests, configs, tooling, or docs already present |
| `reusable_system_value` | 0.18 | creates a reusable primitive instead of one-off tuning |
| `multi_domain_benefit` | 0.14 | improves multiple CLI commands, surfaces, or lifecycle stages |
| `optionality_gain` | 0.10 | keeps safe future strategies open and reduces lock-in |
| `energy_load_inverse` | 0.08 | lowers maintenance, operator, and cognitive load |
| `social_or_network_gain` | 0.08 | improves team handoff, ecosystem integration, or shared ownership |

The weighted score is the sum of dimension value multiplied by weight, rounded to two decimals.

## Decisions

- `< 2.5`: `reject_or_reframe`;
- `2.5 <= score < 3.5`: `defer`;
- `3.5 <= score < 4.0`: `approve`;
- `score >= 4.0`: `prioritize`.

A selected implementation option must be `approve` or `prioritize`. `PR_READY` requires at least one selected in-scope option, no selected-option unknowns, and a score consistent with its dimensions.

## Mandatory machine-readable output

Always emit `evidence/CLI_REVISION_SYNTHESIS.json` containing all findings, targets, options, selected option IDs, unresolved divergence IDs, unknowns, and the selection rationale. Emit `evidence/CLI_REVISION_PLAN.md` as a human-readable projection.

The report is cohesive only when every finding maps to a target and every target maps to an option. Out-of-scope findings remain part of the report rather than disappearing from the plan.
