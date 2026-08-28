<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: canonicalspec
version: 2.7.0
updated: 2026-08-27
-->

# Canonical Spec — target-aware, same-branch contract chains

The model/operator authors one canonical `campaign-spec.yaml`; `scripts/compile_contract.py`
deterministically emits the contract instances and Claude artifacts. Generated contracts are never
hand-edited. Schema: `schemas/campaign-spec.schema.json`.

## 1. One allowed file = one deliverable
Each `items[].allowed_files[]` entry becomes one `scope_lock.in_scope` row. A file not listed may
not be created or modified. Keep each item within the session thresholds.

## 2. Split forbidden paths from forbidden capabilities
- `forbidden_paths[]` are concrete files that must not change and become `preserved_files`.
- `forbidden_capabilities[]` are behaviors/features that must not be implemented and become
  `hard_out_of_scope` + `must_not_add`.

## 3. Target validation is explicit campaign authority
`campaign.validation` is mandatory:

```yaml
campaign:
  validation:
    cold_resume:
      commands:
        - "python -m unittest discover -s tests -v"
    commit_gate:
      commands:
        - "make pr-check"
```

Rules:
- `cold_resume.commands` prove repository state is safe for a fresh session.
- `commit_gate.commands` are repository-native gates that must pass before the current contract's
  one local commit.
- Commands are projected verbatim, in order.
- Commands must be non-empty, unique, and single-line.
- Dependency/bootstrap commands (`npm ci`, `uv sync`, etc.) are not validation and are never injected.
- The compiler MUST NOT infer language, package manager, test framework, or validation command from
  filenames, installed tools, repository names, or model judgment.
- If target validation cannot be established from repository evidence, compilation is BLOCKED.

## 4. `verify_proof` proves THIS item completed correctly
`items[].verify_proof` is a runnable, single-line completion proof for the current item. It is not a
precondition for that same item.

The compiler uses it twice:
1. append it to this contract's `commit_gate.required_before_commit`; and
2. re-run it in contract N+1's preflight as the predecessor completion proof.

This prevents the old defect where a contract was required to prove its own future output before it
had executed.

## 5. Exactly one local commit per contract
`items[].sizing.commits` is fixed to `1`. Multi-commit work must be decomposed into ordered items.
The compiler derives one local commit ordinal and exact commit subject per contract.

Every emitted contract uses:

```text
commit subject = contract_id
commit command = git commit -m "<contract_id>"
```

All contracts in the campaign use the same `target_branch`. No contract pushes between items.

## 6. Internal handoff means committed and validated, not merged
For contract N -> N+1 the compiler derives:

```text
N handoff:     <N-id> committed_and_validated
N+1 assumes:   <N-id> committed_and_validated
N+1 prereq:    {id: <N-id>, required_state: committed_and_validated}
```

Contract N+1 preflight proves that state by checking:
- current branch equals the campaign `target_branch`;
- HEAD commit subject exactly equals contract N's compiler-owned subject;
- campaign cold-resume validation passes; and
- contract N's exact `completion_proof` passes.

External `base_prerequisite` may still use `merged_and_green`, `merged`, `present`, or
`committed_and_validated`; internal seams always use `committed_and_validated`.

## 7. Remote delivery occurs once, at the terminal contract
Every nonterminal contract has:

```yaml
terminal_delivery: {authorized: false, command: null}
```

The terminal contract alone has:

```yaml
terminal_delivery: {authorized: true, command: "make pr"}
```

Direct `git push` and direct PR-creation commands stay in `denied_tools` for every contract,
where they are denied by the generated permission list rather than by a governance gate. The terminal
`make pr` wrapper is the sole authorized push/PR-opening path for the chain. Run it once, only after
the terminal contract has created its one validated local commit.

## 8. Size honestly; decomposition is explicit
Session sizing remains fail-closed. `plan_decomposition.py` uses max 20 new files, max 1 commit,
max 25 matrix cases, and max 10 deliverables. Oversized work returns `DECOMPOSE_REQUIRED`; split it
into ordered items rather than compressing scope.

## 9. Never hand-author deterministic fields
The compiler derives contract IDs, internal prerequisite seams, handoff tokens, commit ordinals,
commit subjects/commands, terminal-delivery authority, and `chain_digest` from item order.

## 10. DPK remains enforced
DPK ownership, rollback, readiness, and `in_scope subset-of owns` rules are unchanged. DPK does not
own runtime validation commands; `campaign.validation` does.

## Compile

```bash
python scripts/compile_contract.py \
  --spec campaign-spec.yaml \
  --out DIR \
  --validate \
  --emit-artifacts
```

`--validate` runs every instance through `validate_contract.py` and the entire ordered set through
`validate_chain.py`. `--emit-artifacts` writes `.claude/settings.json`, `CLAUDE.md`, and
`preflight.sh` per contract.
