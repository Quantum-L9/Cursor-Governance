# VALIDATION — l9-claude-coding-contract-compiler v2.7.0

## Current validation contract

A release is valid only when all of the following pass:

```text
schema parse
Python syntax compile
Node explicit-validation compile
Python neutrality compile
Go neutrality compile
per-contract validator on all emitted fixtures
chain validator on all emitted chains
target-validation regression suite
wrong-branch real Git preflight rejection
valid predecessor real Git preflight acceptance
deterministic recompilation
single terminal make-pr authorization
Cursor-Governance remediation compatibility compile
skill exemplary gate
skill package validation
```

## v2.7.0 repair evidence

Targeted regression command:

```bash
python scripts/test_target_validation.py
```

Required tests:
- explicit Node/npm validation is preserved;
- Python output contains zero implicit npm validation;
- Go output contains zero implicit npm/Python fallback;
- missing `campaign.validation` fails closed;
- empty validation fails closed;
- multiline command fails closed;
- `sizing.commits != 1` fails closed;
- an item proof identical to the repository commit gate deduplicates without becoming schema-invalid;
- generated preflight runs successfully before contract 1 output exists;
- contract 2 preflight accepts exact contract 1 commit + contract 1 dedicated completion proof without replaying its repository-wide commit gate;
- wrong branch fails closed;
- unchanged spec recompiles deterministically;
- exactly the final contract carries `make pr` delivery authority.

## Semantic deltas from v2.6.2

- Removed hardcoded `npm ci && npm run validate` cold-resume assumption.
- Removed hardcoded `npm run validate` commit gate.
- Added mandatory explicit target validation to campaign schema.
- Fixed branch verification from comment-only expectation to executable equality.
- Stopped stripping inline `#` content from generated preflight commands.
- Reinterpreted `items[].verify_proof` correctly as current-item completion proof.
- Changed internal seam state from `merged_and_green` to `committed_and_validated`.
- Locked every contract to one local commit on the same branch.
- Added exact compiler-owned commit command/subject.
- Added one terminal `make pr` delivery and forbade intermediate pushes.

## Non-regression boundaries

Unchanged in authority/purpose:
- DPK manifest/readiness scoring and red lines;
- `in_scope subset-of owns` enforcement;
- scope/preservation semantics;
- 30-section manifest;
- contract-ID derivation;
- chain-digest algorithm;
- `promotion_ready: false`;
- agent self-approval prohibition.
