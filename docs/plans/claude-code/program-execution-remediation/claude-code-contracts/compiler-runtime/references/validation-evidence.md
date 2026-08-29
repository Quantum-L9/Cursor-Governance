<!-- L9META
parent: claude-coding-contract-compiler
layer: reference
role: validationevidence
version: 2.7.0
updated: 2026-08-27
-->

# Validation Evidence

## Required validation classes
1. Structural: schemas parse, required files/resources exist.
2. Contract: every emitted instance is schema-valid and Claude-fit.
3. Target binding: emitted cold-resume and commit-gate commands equal canonical campaign input;
   no undeclared ecosystem fallback appears.
4. Execution: generated preflight actually fails a wrong branch and accepts a valid predecessor.
5. Chain: same repo/branch, one local commit ordinal per contract, exact predecessor HEAD proof plus
   only the predecessor dedicated completion proof, stable digest; no predecessor commit-gate replay.
6. Delivery: zero nonterminal remote delivery; exactly one terminal `make pr` authorization.
7. DPK: ownership/readiness/rollback rules remain green.
8. Regression: Node, Python, Go, negative-schema, determinism, and terminal-delivery matrix passes.

## Forbidden validation patterns
- fabricated pass results or hashes;
- empty or prose-only command fields;
- compiler-injected npm/pytest/go/etc. fallback;
- bootstrap/install treated as validation without explicit canonical authority;
- current item `verify_proof` used as its own cold-start precondition;
- internal seam represented as merged when the work only exists as local commits;
- more than one local commit per contract;
- push between contracts;
- terminal delivery through anything other than exact `make pr`;
- `make pr` authorization on more than one contract;
- `|| true` or warning-only handling of failed preconditions.

## Target-validation provenance
Record:
- canonical `campaign.validation.cold_resume.commands`;
- emitted `resume_from.verify_before_starting`;
- canonical `campaign.validation.commit_gate.commands`;
- emitted `commit_gate.required_before_commit`;
- each item `verify_proof`;
- N+1 proof that every command from N's `required_before_commit` gate was carried forward;
- static proof no undeclared ecosystem default exists in `compile_contract.py`.

## Definition of green
A chain is green only after all instances validate, the chain validator is green, the regression
suite is green, and generated preflights have been exercised for branch/predecessor behavior.
