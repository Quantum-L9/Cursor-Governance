# Source Provenance: Dead-Wiring and Latent-Capability Audit

> Source evidence only. Do not execute this report-only contract as the Skill's terminal workflow. Use `references/latent-capability-activation.md` for the adapted implementation law.

<!-- L9 Audit Suite — audit 08 (Dead-Wiring & Latent Capability) -->
# Canonical Dead-Wiring & Latent-Capability Audit v1

## Operating Mode
Elite Repository Audit Unit: Reachability Analyst + Latent-Leverage Reviewer.
BINDING, REPORT-ONLY. Do NOT modify code. Object of audit is **reachability and
activation**, NOT correctness. Never invent facts — unproven reachability is
`UNKNOWN`, never "dead". Fail-closed.

## Classification
Internal **latent-capability / dead-wiring audit** — the inverse of the suite.
The others ask "is what exists correct/safe?"; this asks "what exists but isn't
connected, and what leverage is left on the table?"

## Parameters
- TARGET_REPO / BASE_REF
- ENTRYPOINTS: <real runtime entrypoints / mounted routes / CLI roots>
- REGISTRIES: <dispatch tables, plugin registries, handler maps>
- FEATURE_FLAGS: <flag source + current values + roadmap intent>
- SIGNAL_CONSUMERS: <who is expected to consume emitted signals>

## Finding Record Format (schema + leverage extension)
Conforms to finding_schema.py. Prefix `DWA-NNN`. Adds one field: `leverage`.
- id | severity | rule_broken | evidence | impact | correction | owner_layer | blocks_release | leverage | verdict(activate|remove)

## Defect classes
- inactive_component — defined, never imported/instantiated.
- miswired_file — wired to wrong consumer or registered under an unread key.
- dormant_capability — complete code behind a permanently-off flag / unmounted route / unsurfaced CLI / never-emitted enum.
- unused_signal — value/event/telemetry/return field produced, never consumed downstream.
- orphaned_config_schema — field/key/env var defined but read by no code, or read but never set.
- broken_partial_wiring — producer + consumer both exist, edge never connected.

## Phase 0 — Reachability Convergence (multi-pass, recurse until stable)
1. Build import/call graph from ENTRYPOINTS. 2. Mark reachable set.
3. Diff defined-vs-reachable. 4. Resolve dynamic dispatch (REGISTRIES) before
declaring dead. 5. Classify each unreachable item. 6. Assign verdict + leverage.
7. Converge + Minimum Safe Next Action.

## Exemplary bars (mandatory)
- **Bidirectional evidence** — every "unused" cites BOTH definition site AND proof of no consumer (import-graph/grep). No consumer proof => UNKNOWN.
- **Every finding: activate OR remove** — `activate` names the downstream capability unlocked; `remove` proves true orphanhood.
- **Dormant-by-design != dead** — check FEATURE_FLAGS/roadmap intent first; staged-rollout flags are not findings.

## Phases 1-3
Phase 1 ground-truth wiring map; Phase 2 producer→consumer edge table (connected?
y/n); Phase 3 adversarial (dynamic dispatch, reflection, entrypoint-only reach).

## Integration
Report-only. Findings → audit_to_contract.py (carries `leverage` into the task
block). Leverage gate applies. Unresolved → 05. Feeds audit 09 (edge contracts).
