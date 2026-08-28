# MANIFEST — l9-pipeline-orchestrator v1.0.0

Execution half of the L9 pipeline. Extracted from `l9-claude-coding-contract-compiler` v2.4.0–v2.6.1
(the `orchestrate/` module) into a standalone sibling pack so the compiler stays pure and the
orchestrator versions independently. Repo-agnostic; nothing hardcodes a repo.

## Files (11)
| File | Role |
|---|---|
| `SKILL.md` | control plane — the 3-stage flow, components, merge policy, safety invariants |
| `README.md` | full flow + Routine wiring + auto-merge policy + branch-protection setup + migration record |
| `MANIFEST.md` | this file |
| `advance.py` | deterministic chain driver: `next` / `seed` / `set` / `gate` |
| `make_state.py` | build `state.yaml` from an emitted `out/PR-*/` set |
| `automerge_gate.py` | no-HITL merge predicate (ci_green + review_flags_resolved + review_comments_resolved) |
| `apply_branch_protection.py` | repo-agnostic branch-protection apply (auto-discovers; never blocks) |
| `verify_branch_protection.py` | fail-closed check that live protection matches config |
| `branch_protection.example.yaml` | desired protection (all fields optional overrides) |
| `CODEOWNERS.example` | optional: make the review agent the required approver (0 human approvals) |
| `state.example.yaml` | illustrative chain state |

## Consumes
`out/PR-*/` emitted by `l9-claude-coding-contract-compiler` (`compile_contract.py --emit-artifacts`).

## Validation evidence
- `advance.py` reaches `__DONE__` in both `green` and `merged` gate modes; `gate` promotes only on ELIGIBLE.
- `automerge_gate.py` tested on 6 fixtures (1 eligible + 5 fail-closed).
- `apply_branch_protection.py` runs repo-agnostically (zero args), auto-discovers, never blocks;
  `verify_branch_protection.py` passes on a compliant fixture and fail-closed lists gaps on a weak one.

## Boundaries
- Owns: chain execution, merge policy/gate, branch-protection apply/verify.
- Does not own: emitting/validating contracts (that is `l9-claude-coding-contract-compiler`); building
  code inside a contract (the per-contract build session, which cannot push/merge).
