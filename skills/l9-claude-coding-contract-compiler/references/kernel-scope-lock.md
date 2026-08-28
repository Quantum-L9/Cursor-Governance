<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: scopelockkernel
version: 1.0.0
updated: 2026-08-27
sources: Pr-B-Contract.md (sections 3, 21, 25)
-->

# Scope-Lock Kernel  (BINDING — always active)

## Prime Directive
Vague scope is permission to build unbounded. Every contract MUST declare three explicit
lists. Anything not in `in_scope` may not be created.

## Three Mandatory Lists
1. `in_scope` — ordered, numbered deliverables. This is the allowlist.
2. `hard_out_of_scope` — explicit forbidden implementations, named file by file.
3. `preserved_files` — files whose commands/behavior must not change; comment-only edits.

## Scope Rules
- Files not on `in_scope` require re-entering the scope-lock gate before creation.
- `hard_out_of_scope` items become the `Non-Goals Verification` checklist (section 25).
- Preserved files must be diffable to prove behavior preservation.
- The `Required File Manifest` (section 21) MUST carry an explicit `MustNotAdd` list that
  mirrors `hard_out_of_scope`.

## Non-Goals Verification
The contract must require the agent to prove the diff does NOT add or change anything in
`hard_out_of_scope`. Proof, not assertion. Absence is verified by diff, not by claim.

## Violation
Any file created outside `in_scope`, any preserved file whose behavior changed, or any
`hard_out_of_scope` item present in the diff -> `scope_violation` -> contract result = failed.


## Claude Context-Window Addendum
For claude-code, `in_scope` is bounded by what fits ONE focused session (diff + tests +
evidence). If it does not fit, emit an ordered sub-contract chain and STOP. Never compress
scope to force a single fit. Each internal sub-contract prerequisite is the prior contract committed_and_validated on the same campaign branch.
