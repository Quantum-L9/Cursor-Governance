<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: enforcementgates
version: 2.7.0
updated: 2026-08-27
-->

# Enforcement Gates

Rules without executable proof are suggestions. Advance only when the current gate is green.

## Gate A — Canonical spec parsed
Require target repo, shared target branch, ordered items, DPK block, and mandatory
`campaign.validation.cold_resume.commands` + `campaign.validation.commit_gate.commands`.
STOP on missing/empty/multiline validation or any item with `sizing.commits != 1`.

## Gate B — Scope and sizing
Validate against `campaign-spec.schema.json`, DPK ownership, and session limits.
STOP on `DECOMPOSE_REQUIRED`; split the work into ordered one-commit contracts.

## Gate C — Deterministic emission
`compile_contract.py` must derive IDs, `committed_and_validated` seams, exact commit subjects/commands,
one source-commit ordinal per contract, and terminal-delivery authority.
STOP if deterministic fields are hand-authored.

## Gate D — Per-instance validation
Every contract must pass `validate_contract.py`: schema + Claude-fit + DPK + git-workflow invariants.

## Gate E — Chain validation
`validate_chain.py` must prove:
- handoff/resume seam equality;
- digest stability;
- exactly one contiguous source-commit ordinal per contract;
- one repo + one shared branch;
- N+1 preflight contains N's exact HEAD-subject assertion and every command from N's
  `commit_gate.required_before_commit`;
- nonterminal delivery is unauthorized; and
- exactly the terminal contract is authorized for `make pr`.

## Gate F — Generated Claude artifacts
With `--emit-artifacts`, every contract gets `.claude/settings.json`, `CLAUDE.md`, and
`preflight.sh`. Generated preflight executes canonical commands exactly and fails on branch or
predecessor-proof mismatch.

## Gate G — Regression neutrality
Run `scripts/test_target_validation.py`. Required: Node explicit npm preserved, Python no implicit
npm, Go no implicit Node/Python fallback, missing/empty/multiline validation rejected, multi-commit
item rejected, real Git preflight behavior green/fail-closed, deterministic recompile, exactly one
terminal `make pr` authority.

## Gate H — Package
Validate the complete Skill, then package the whole Skill as `skill.zip`. No partial patch bundle.
