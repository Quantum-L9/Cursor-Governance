<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: build-execution-contract
version: 3.7.0
status: active
-->

# Build Execution Contract

## Entry conditions

A build starts only after source inventory, mode selection, activated directives, and Gate A. Ask one focused question only when a missing core input prevents correct execution; otherwise proceed with explicit assumptions.

## File scope

Before the first write, Gate C must list every file in scope. New files require a Gate C update. Do not generate decorative reports or adapters that change no behavior.

## Execution

1. Build the canonical core.
2. Add intelligence artifacts for exemplary mode.
3. Add deterministic scripts only when they can be run.
4. Add platform or domain adapters only when activated.
5. Validate files and references.
6. Run included scripts and tests.
7. Compare against the prior baseline when rebuilding.
8. Package and inspect the archive.

## Evidence

For each check record target, method, expected result, actual result, status, and evidence location. `not run`, `blocked`, and `Unknown` are valid statuses; invented `pass` is not.

## Delivery

Return the actual artifact, concise validation status, material changes, known limitations, and the highest-leverage next action only when useful.
