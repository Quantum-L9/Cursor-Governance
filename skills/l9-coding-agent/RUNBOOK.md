# L9 Coding Agent Runbook

## Start

1. Activate the skill for a mutating coding request.
2. Read `runtime/BOOTSTRAP.yaml` only.
3. Load the intake group, bind the exact target/revision, resolve authority, and bind or derive one execution contract.
4. Establish the semantic envelope before mutation.

## Execute

1. Load the implementation group.
2. Keep inspection scope and modification scope separate.
3. Build the dependency-aware target graph needed to understand entrypoints, consumers, contracts, generators, tests, configuration, and material docs.
4. Record baseline evidence or explicit `Unknown` where unavailable.
5. Classify evidence-backed findings, trace to root cause, and build the smallest coherent fix map.
6. Choose private implementation details autonomously when they remain semantically equivalent.
7. Apply coherent root-cause batches and keep collateral work causally bounded.
8. Use conditional routes only when their trigger becomes material.

## Validate

1. Load `contracts/VALIDATION_AND_EVIDENCE.yaml`.
2. Run the narrowest check capable of disproving the repair first.
3. Expand validation along affected dependency paths and all mandatory obligations.
4. Record `Passed`, `Failed`, `Skipped`, `NotApplicable`, or `Unknown` from observed evidence only.
5. Repair implementation defects without weakening gates.
6. Run regression and final hygiene checks against the exact final state.
7. Revalidate after material mutation, revision drift, or delivery-state change.

## Finish

1. Load `contracts/CONVERGENCE.yaml`.
2. Evaluate terminal state against observed evidence.
3. Emit the execution receipt.
4. Perform external delivery only when capability and authority are both observed.

## Escalate

Escalate only when correct execution requires a public semantic change, owner/invariant revision, provider/substrate choice, required scope expansion, unresolved authority conflict, unavailable required validation, or unavailable authorized delivery path. Return the smallest architecture question needed to resume.

## Skill maintenance

For promotion or package work, use the package-quality route in `runtime/BOOTSTRAP.yaml`, then run the current L9 Skill Compiler validators plus the runtime alignment and lazy-bootstrap validators. Do not load package intelligence during ordinary code execution.

## Full-readiness guard

When whole-target readiness is requested, inventory the complete authorized target before mutation claims can become whole-target claims. Keep inspection and modification scope separate. Record `Unknown` for inaccessible coverage. Before delivery, verify the handoff resolves to the exact state that passed final validation.
