<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: change-discipline
version: 2.0.0
status: active
-->

# Change Discipline Audit

## Purpose

Close the gap between ordinary CI validation and architectural PR review. The audit must determine not only whether changed code works, but whether the PR implemented the authorized objective completely, stayed inside scope, reused the existing architecture, avoided unnecessary machinery, retired superseded paths, covered material failure behavior, and contains tests that actually discriminate the changed behavior.

The model does semantic adjudication. Deterministic code owns enumeration wherever possible. Never ask the model to remember to inspect a surface that code can enumerate. Record the resulting inspection universe explicitly so final verification rechecks the same evidence surface rather than wandering a different repository path.

## Donor boundary

This pack harvests read-only signal-census patterns from `l9-pr-remediation` and scope/expansion detectors from `l9-pr-digest`. It does not call either skill at runtime and does not inherit mutation, convergence, merge, or campaign behavior from them. `l9-pr-audit` is self-contained.

## Original PR prompt

When the prompt/task contract used to generate the original PR is available, capture it as intent evidence. It is especially valuable for:

- objective closure and acceptance criteria;
- explicit scope and non-goals;
- proportionality and "larger than necessary" analysis;
- expected failure behavior;
- expected tests or validation.

The original prompt is authoritative for historical requested intent, not for overriding current repository architecture, current user instructions, or stronger current contracts. If it is unavailable, continue with other evidence and record the provenance gap; absence alone does not block the audit.

## Deterministic census

Run `scripts/build_change_ledger.py` on a normalized read-only snapshot for every audited PR and bind its canonical digest. The output is a machine-owned census, not a verdict. It enumerates changed surfaces, changed symbols, CI failures, unresolved review threads, architectural-growth candidates, material failure-path candidates, test-discrimination obligations, claim seeds, and falsification seeds.

Machine rows remain immutable audit inputs. The audit may add semantic symbols, obligations, claims, or counterexample probes discovered by deeper inspection, but it may not omit or rewrite deterministic rows. See [adversarial-red-team.md](adversarial-red-team.md).

## Required domains

### Objective closure

Every active objective receives one disposition: `SATISFIED`, `UNPROVEN`, `NOT_IMPLEMENTED`, or `CONFLICTED`. Each objective binds intent provenance, implementation evidence, validation evidence, and findings when deficient.

### Scope fidelity

Every changed file receives exactly one disposition: `REQUIRED`, `DIRECTLY_COUPLED`, `VALIDATION_REQUIRED`, `GENERATED_CONSEQUENCE`, `SCOPE_EXTENSION`, or `UNKNOWN`. File count is not a scope judgment. Any `SCOPE_EXTENSION` or `UNKNOWN` that can affect correctness/readiness must become a finding or blocking Unknown.

### Complexity delta

Record structural growth rather than guessing from diff size: added/deleted/modified files, new architectural-object candidates, dependency/config/control-path growth when observable. Growth is evidence, never automatic failure.

### Architectural economy

For every detected new service/manager/factory/adapter/registry/protocol/interface/compatibility layer/feature-flag or equivalent architecture object, require a disposition of `JUSTIFIED`, `UNJUSTIFIED`, or `UNKNOWN`. `JUSTIFIED` requires an active objective or repository authority plus evidence that the existing owner/capability was considered. Do not equate "new abstraction" with a defect.

### Supersession closure

When the PR replaces an owner, path, entrypoint, dependency, configuration key, workflow, or subsystem, inspect for residual live references. Disposition each replacement `CLOSED`, `RESIDUAL`, `NOT_APPLICABLE`, or `UNKNOWN`. Residual duplicate authority/path must become a finding when material.

### Failure-path coverage

For material changed failure behavior, classify `TESTED`, `STRUCTURALLY_PROVEN`, `NOT_APPLICABLE`, or `UNKNOWN`. Focus on changed error/retry/timeout/auth/rollback/cleanup/external-call behavior rather than demanding generic failure tests everywhere.

### Test discrimination

For each materially changed production behavior, classify the validating test/check as `DISCRIMINATING`, `WEAK`, `ABSENT`, `NOT_APPLICABLE`, or `UNKNOWN`. A green test is not discriminating merely because it executes the code. Prefer evidence that the test would fail if the governed behavior were wrong; selective mutation testing is strong evidence when repository-safe and available.

## Audit obligation ledger

Every deterministic or semantically discovered obligation is closed as `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN`, with evidence IDs. Audit convergence requires complete disposition of the obligation ledger. `UNKNOWN` may remain only when represented in `residual_unknowns` with its effect on readiness/convergence.

At minimum the ledger covers:

- every changed surface;
- every machine changed symbol;
- every active objective;
- every architectural-growth candidate;
- every material supersession;
- every material failure path;
- every test-discrimination obligation;
- every in-scope CI failure;
- every unresolved review thread discovered at the audited head.

## Validation versus audit

CI/check execution is validation evidence. The audit decides which obligations and claims matter, whether evidence actually discriminates them, whether the change belongs, whether architecture is preserved, and whether scope/complexity is justified. Positive audit conclusions are adversarial: material `SUPPORTED` claims require a validation row and all applicable counterexample/falsification probes to survive. Do not collapse audit judgment into test status or reviewer confidence.

## Control adequacy

Audit underbuilding as deliberately as overbuilding. For each material required control, record `control_type`, governing requirement, current evidence, and one status: `ADEQUATE`, `UNDERBUILT`, `NOT_APPLICABLE`, or `UNKNOWN`. `UNDERBUILT` requires a finding and a `CONTROL_ADEQUACY` obligation. Never invent a control merely because more machinery could exist; the requirement must come from intent, repository law, a contract, or a materially necessary boundary.

## v2.0 closure cross-links

Machine failure-edge IDs must exactly equal `failure_path_coverage.failure_path_id` values. Machine architecture-growth IDs must exactly equal `architectural_economy.candidate_id` values and their semantic dispositions must agree with deterministic justification basis. Supersession `CLOSED`/`RESIDUAL` state must agree with per-reference liveness rows.
