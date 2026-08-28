<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: outputmodes
version: 1.0.0
updated: 2026-07-12
-->

# Output Modes

| Mode | When | Output |
|---|---|---|
| author | new contract from a change request | full 29-section contract + schemas + validation report template |
| revise | correct/extend an existing contract | patch: changed sections only + reason per change; unchanged sections listed |
| harden | multi-pass hardening | 5-pass audit + 6 final artifacts (see kernel-recursive-harden.md) |
| validate | completeness + safety check | 6-class validation report + pass/fail per section |
| package | distributable bundle | zip + MANIFEST + machine_summary |

## Author Mode
Resolve 8 anchors -> author the canonical campaign spec (`references/canonical-spec.md`) ->
run `scripts/compile_contract.py` to EMIT the instances (sections manifest, IDs, seams,
`chain_digest` are script-derived, not hand-typed) -> emit validation report with evidence
fields UNKNOWN until produced. The 29-section semantics remain authoritative; the spec is the input.

## Revise Mode (patch discipline)
Emit only changed sections with `appliesTo`, `addsOrChanges`, `nonChanges`. Never rewrite
unchanged canon. Never reopen locked scope unless the user explicitly asks.

## Validate Mode
Run the 6 validation classes. Return per-section PASS/FAIL/NOT_APPLICABLE + evidence.
Flag any forbidden validation pattern.

## Formatting
YAML for contract bodies and schemas. Tables for section/gate matrices. Label all UNKNOWN.
No prose padding. No pre-filled evidence.### harden
Input: an existing contract or pack + "harden/improve/upgrade/polish".
Default mode: DRY_RUN — produces recommendations only until operator says "apply" or "execute".

Runs minimum 5 ordered passes (see `kernel-recursive-harden.md`).
Stop conditions terminate passes early when convergence is reached.
Must-not-stop conditions prevent premature termination when blockers remain.

Output (9 required final artifacts):
`IMPROVEMENT_REPORT.md`, `improvement_log.jsonl`, `DELTA_REPORT.md`,
`CONVERGENCE_REPORT.yaml`, `ENTROPYREDUCTIONREPORT.md`, `REGRESSIONGUARD.md`,
`FINALCONTRACT.md`, `VALIDATION.md`, `MANIFEST.md`.

Validate artifacts against: `schemas/improvement-report.schema.yaml`,
`schemas/improvement-log.schema.yaml`, `schemas/delta-report.schema.yaml`,
`schemas/convergence-report.schema.yaml`.

Review output must include all 16 sections from `review_output_schema` in the kernel.
Status: IMPROVED_EXECUTION_READY | IMPROVED_WITH_FINDINGS | BLOCKED_ON_IMPROVEMENT |
REJECTED_CHANGE_SET | MINE_FOR_FUTURE.




## Claude-code specifics (all modes)
- Every emitted contract opens with a resume-from block (section 0).
- Authority is emitted as `denied_tools`, DRY_RUN maps to plan mode.
- Determinism-critical sections ship `scripts/`, not specifications.
- `validate` mode also runs the seventh Claude-Fit validation class.
