# REGRESSION_GUARD — claude-coding-contract-compiler v2.7.0

## Protected behavior

The v2.7.0 repair may change compiler input/output semantics only where required to remove the
hardcoded npm/merged-chain defects. DPK ownership/readiness, scope locking, contract IDs, digest
algorithm, section count/order, and fail-closed doctrine remain preserved.

## Permanent invariants

1. `compile_contract.py` contains no implicit ecosystem validation fallback.
2. Node/npm remains valid when npm is explicitly declared in campaign input.
3. Python and Go fixtures emit no undeclared npm/Python fallback respectively.
4. `campaign.validation` is mandatory and non-empty.
5. Preflight command strings are single-line and are executed without inline-comment stripping.
6. Target branch is asserted by equality, not by a comment.
7. Current item `verify_proof` gates its one commit; it is not required before that item exists.
8. Contract N+1 preflight re-runs only contract N's exact completion proof and requires N's exact
   commit subject to be HEAD; it must not replay N's repository-wide commit gate.
9. Every contract has exactly one local commit ordinal and exact compiler-owned commit command.
10. All contracts use one repo and one shared branch.
11. Internal seam state is `<id> committed_and_validated`.
12. No nonterminal contract has remote-delivery authority.
13. Exactly one contract, the terminal contract, has `terminal_delivery.command: make pr`.
14. Direct `git push` and direct PR creation remain denied even on the terminal contract.
15. `chain_digest` remains SHA-256 of the compact ordered contract-ID JSON list.
16. Commit-gate stable deduplication must not reject a contract when the repository gate and completion proof are identical.
17. Unchanged canonical input recompiles deterministically.

## Required executable proof

```bash
python scripts/test_target_validation.py
```

The suite must pass all Node, Python, Go, missing validation, empty validation, multiline command,
multi-commit, real Git branch/predecessor preflight, deterministic recompile, and terminal-delivery
cases.

## Historical compatibility note

v2.6.2 internal seams used `merged_and_green` and injected npm validation into every contract. Those
behaviors are intentionally superseded. External `base_prerequisite` still accepts legacy states
(`merged_and_green`, `merged`, `present`) because an external prerequisite may genuinely already be
merged; only internal contract-to-contract seams are forced to `committed_and_validated`.
