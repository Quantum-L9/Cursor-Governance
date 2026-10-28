# L9 Coding Agent Runbook

## Start

1. Activate the skill for a mutating coding request.
2. Read `runtime/BOOTSTRAP.yaml` only.
3. Load the intake group, bind the exact target/revision, resolve authority, and bind or derive one execution contract.
4. Bind canonical invariants from **externally supplied** inputs. `.github` owns the law and profile, a producer emits the projection, and the consumer repository commits it as a bundle cut by a pinned producer revision and attested by trusted replay (`Quantum-L9/.github` ADR-021). This skill only consumes it: never run the Semantic Compiler, a producer, or the bundle driver to create the projection you are about to bind, and do not assume either is operational.
   - Inputs: the committed bundle directory (`bundle.lock.json` plus one producer-emitted artifact and receipt per declared source class), or a handed artifact and receipt pair; the authority revision pin; and an exact `Quantum-L9/.github` checkout of that revision fetched from the canonical owner. The pin must come from an independent record of the published revision, never from the bundle, artifact, receipt, or checkout being checked.
   - Open the run on the host: write `<workspace>/.l9/coding-agent/run.json` (`{"schema": "l9.coding-agent-run/v1", "started_at": "<UTC>", "binding_record": "binding.json", "authority_root": "<the exact .github checkout below>"}`; contract in `integrations/L9_RUNTIME_BINDING.yaml` `run_state_files`).
   - Run `"$HOME/.cursor-governance/.venv/bin/python" scripts/verify_canonical_binding.py --authority-root <checkout> --bundle <bundle dir> --expect-revision <pin> --require-invariant <id> ... > <workspace>/.l9/coding-agent/binding.json` (a handed pair uses `--artifact <projection> --receipt <receipt>` in place of `--bundle`; the host gate re-verifies only bundle-bound records) and record the printed binding in run state. The record is the verifier's output, never authored or edited by hand.
   - Exit 1/3/4 (`REJECTED`/`BLOCKED`/`STALE`) blocks mutation. No supplied projection means `BLOCKED_UPSTREAM_PROJECTION_PRODUCER`, and a missing pin means `AUTHORITY_REVISION_PIN_ABSENT`; both stay `Unknown`, never produced locally. Only an explicit current user instruction may let the run proceed with that `Unknown`: the operator sets `L9_CODING_BINDING_REAUTHORIZED="<the user's words verbatim>"` in the hook environment (a file the run can write is not a grant), and the receipt carries the same text.
   - On Claude Code under `Quantum-L9/Cursor-Governance` this is enforced: while `run.json` exists, the PreToolUse gate `ops/autonomy/coding_agent_binding_gate.py` denies `Edit`/`Write`/`MultiEdit`/`NotebookEdit` unless the verifier, re-run by the gate on `binding.json`, the bundle and `authority_root`, answers `CURRENT`, or the operator reauthorization is set. A `BOUND` label in a writable file releases nothing. Elsewhere the same law is instructional; say which applied.
5. Establish the semantic envelope before mutation.

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

1. Load `contracts/CONVERGENCE.yaml`. Re-check a bound canonical binding with `--prior-binding <binding.json> --expect-revision <pin>`; `STALE` invalidates the binding and the evidence derived from it.
2. Evaluate terminal state against observed evidence.
3. Emit the execution receipt.
4. Perform external delivery only when capability and authority are both observed.
5. Close the run on the host: delete `<workspace>/.l9/coding-agent/run.json` from the shell (keep `binding.json` as evidence) so later, unrelated work is not gated by this run. While the run is active the gate refuses file-tool writes under `.l9/coding-agent/`.

## Escalate

Escalate only when correct execution requires a public semantic change, owner/invariant revision, provider/substrate choice, required scope expansion, unresolved authority conflict, unavailable required validation, or unavailable authorized delivery path. Return the smallest architecture question needed to resume.

## Skill maintenance

For promotion or package work, use the package-quality route in `runtime/BOOTSTRAP.yaml`, then run the current L9 Skill Compiler validators plus the runtime alignment and lazy-bootstrap validators. Do not load package intelligence during ordinary code execution.

## Full-readiness guard

When whole-target readiness is requested, inventory the complete authorized target before mutation claims can become whole-target claims. Keep inspection and modification scope separate. Record `Unknown` for inaccessible coverage. Before delivery, verify the handoff resolves to the exact state that passed final validation.
