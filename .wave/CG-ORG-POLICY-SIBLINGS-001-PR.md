# Summary

Adds the normative sibling artifacts for the canonical organization policy
introduced by PR 53.

This pull request does not modify or duplicate `ORG_INVARIANTS.yaml`.

## Relationship to PR 53

This branch is based on a commit containing PR 53's organization-policy file.

PR 53 owns the canonical policy payload.

This pull request adds:

- assertion semantics;
- policy grammar;
- policy model;
- trust model;
- change process;
- immutable release-record contract;
- operator documentation;
- repository-local validation;
- positive and negative-path tests.

## Authority boundary

This repository owns policy meaning and normative governance artifacts.

This pull request intentionally excludes:

- GitHub organization rulesets;
- organization repository inventories;
- platform exemption records;
- organization deployment bindings;
- generalized CI execution;
- assurance reduction;
- consumer repository installation.

## Validation

```bash
python3 ops/scripts/validate_org_policy.py
python3 -m unittest discover -s tests/org_policy -p 'test_*.py'
```

## Negative-path coverage

Tests reject:

- duplicate invariant IDs;
- unknown assertion types;
- unsupported assertion versions;
- invalid lifecycle states;
- invalid enforcement states;
- incomplete critical invariants;
- unsupported blocking claims;
- duplicate YAML keys;
- mutable release-commit contracts.

## Enforcement honesty

This pull request validates normative repository artifacts.

It does not claim that organization-wide blocking enforcement is deployed.

## Installation notes

Applied against the live repository, this install differs from the literal wave
script in two evidence-backed, in-scope ways (no redesign, no edit to
`ORG_INVARIANTS.yaml`):

- **`docs/governance/ORG_INVARIANTS.md` already existed.** Per operator
  direction, the wave's operator-doc content was **appended** under a clear
  divider rather than overwriting the existing single-source-of-truth doc.
- **Schema compatibility with the live `l9_schema: 2` policy.** The policy's
  `metadata.policy_id` is `quantum-l9.org-invariants` and several invariants use
  `required_repository_state`, `forbidden_actors`, and `allowed_reference_types`.
  `schemas/org-invariants.schema.json` was authored to accept these so it
  faithfully describes the canonical policy. The repo-local validator itself is
  structural and passes against the unmodified policy.

## Out of scope

`ORG_INVARIANTS.yaml` remains owned by PR 53.

Platform bindings and rollout remain in their owning repositories.

## Merge order

Merge after PR 53, or retain the current stacked dependency until PR 53 merges.

## Merge readiness

Ready when:

- repository validation passes;
- required CI passes;
- review findings are resolved;
- the branch remains free of unrelated changes.
