# Deterministic Closure Contract v2.0

This reference defines the machine-enumerated closure surfaces that finish the previously partial audit controls. The deterministic census enumerates candidates; bounded semantic judgment may disposition a candidate but may not delete, rename, or rewrite a machine seed.

## Corpus completeness

Repository-wide absence, uniqueness, bypass-safety, supersession-death, and configuration-precedence conclusions require `repository_files_complete: true` in the normalized census snapshot. A partial repository corpus may produce candidates but cannot prove repository-wide absence or uniqueness.

## Canonical closure ledger

Every machine `closure_seed` must appear exactly once in `deterministic_closure_ledger` with the same `closure_id`, PR, kind, subject, and `seed_hash`. Auditor-added rows may extend the ledger but cannot replace machine rows. Every row ends `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN` with evidence and any finding IDs.

The v2.0 closure kinds are:

- `PUBLIC_CONTRACT`: public function/class signature, API route, public constant, schema/config/workflow key delta. A material disposition requires preservation/migration linkage or a finding.
- `SSOT_UNIQUENESS`: per-candidate competing-definition search plus a repository-coverage seed. Complete-corpus coverage closes as `UNIQUE` or `CANDIDATES_ENUMERATED`; competing authority requires a finding.
- `BYPASS_PATH`: candidate path around a required architecture boundary plus a repository-coverage seed. Python comments and string literals do not count as boundary traversal evidence.
- `SUPERSESSION_LIVENESS`: every remaining old-path reference is classified `LIVE`, `DEAD`, `DOC_ONLY`, `TEST_ONLY`, `GENERATED`, or `UNKNOWN`. `CLOSED` supersession cannot retain `LIVE`/`UNKNOWN` references.
- `FAILURE_EDGE`: each changed failure edge is individually closed as `TESTED`, `STRUCTURALLY_PROVEN`, `NOT_APPLICABLE`, or `UNKNOWN`, and machine edge IDs exactly match `change_discipline.failure_path_coverage` IDs.
- `CONFIG_PRECEDENCE`: each changed configuration key records discovered sources and closes as `SINGLE_WINNER`, `CONFLICT`, `NONE`, or `UNKNOWN`. `SINGLE_WINNER` requires a complete corpus and known authority for the selected source.
- `DEPENDENCY_CAUSALITY`: each dependency delta is `JUSTIFIED`, `UNJUSTIFIED`, `TRANSITIVE`, `LOCK_ONLY`, or `UNKNOWN`, with objective/finding linkage when required.
- `DEPENDENCY_PAIRING`: manifest/lock movement is `CONSISTENT`, `MISMATCH`, `NOT_APPLICABLE`, or `UNKNOWN`; mismatch requires a finding.
- `DIFF_HUNK`: every diff hunk is explicitly dispositioned. Substantive required/coupled/validation hunks require objective linkage; a finding hunk requires finding linkage.
- `CI_CAUSALITY`: every current failed check is classified `PR_CAUSED`, `PRE_EXISTING`, `ENVIRONMENT`, `PIPELINE`, or `UNKNOWN`. `PRE_EXISTING` requires baseline evidence; a current required failed check cannot coexist with READY.
- `GENERATED_PROVENANCE`: changed generated output requires generator, authoritative source inputs, generation command, and regenerated-byte/hash proof. `MATCHED` requires equal audited/generated hashes; mismatch requires a finding.

- `PRODUCER_CONSUMER`: every machine-discovered consumer of a changed public contract is dispositioned `UNCHANGED_COMPATIBLE`, `UPDATED`, `MIGRATION_REQUIRED`, `NOT_APPLICABLE`, or `UNKNOWN`; a complete-corpus coverage seed proves the consumer census was exhaustive.
- `MUTATION_EXECUTION`: changed Python conditions/operators/literals emit exact source-bound mutation candidates. Execute them only through `scripts/execute_mutation_probe.py`, which copies the repository to a disposable filesystem tree and never edits the audited source. Default command execution is argv-based with no shell; shell syntax requires explicit `--allow-shell`. The runner is not a process sandbox. Probe output must validate against `schemas/mutation-probe-result.schema.json`. Exit `0` means `KILLED`, `1` means `SURVIVED`, `2` means baseline/execution failure, and `3` means audited-source integrity failure. `KILLED` requires baseline PASS + mutant FAIL; `SURVIVED` requires a finding; execution uncertainty remains `UNKNOWN`.
- `REVIEW_THREAD_SEMANTIC`: every current review thread receives exactly one semantic disposition: `FIXED_BY_FINDING`, `DISPROVEN_WITH_EVIDENCE`, `ACCEPTED_NONBLOCKER`, `DUPLICATE`, `OUT_OF_SCOPE`, or `UNKNOWN`. GitHub/UI resolved state alone is insufficient.
- `ORPHAN_ARTIFACT`: every newly added executable/config/schema/workflow/other non-test artifact must close as `REACHABLE`, `REGISTERED`, `CONTRACT_AUTHORIZED`, `ORPHAN`, or `UNKNOWN`. `ORPHAN` requires a finding.
- `ARCHITECTURE_ECONOMY`: a new architecture primitive may be `JUSTIFIED` only by one of three bases: `REQUIREMENT_NECESSITATES_BOUNDARY`, `VERIFIED_PATTERN_EXTENSION`, or `EXISTING_OWNER_CANNOT_ABSORB`. `UNJUSTIFIED` requires a finding.

## Post-judgment deterministic closure

`post_judgment_closure` is machine-checked after findings exist:

- `root_cause_dominance`: findings sharing the same semantic owner and implementation surface must be explicitly consolidated under one root cause or proven independent.
- `severity_consistency`: every finding receives deterministic floor/ceiling bounds. Merge-blocking findings default to at least High; Critical requires a confirmed, merge-blocking high-impact class. Out-of-bound severity requires authority-backed override evidence.
- `validation_run_coverage`: every TEST/CI/RUNTIME/MEASUREMENT evidence record must either close one or more canonical claims or be explicitly justified as non-closing evidence. Unaccounted validation is forbidden.

## Recursive verification

The final `VERIFICATION` pass must re-observe every deterministic closure ID in addition to findings, obligations, claims, and falsification probes. `CONVERGED` requires zero unresolved machine closure rows and zero new material information.
