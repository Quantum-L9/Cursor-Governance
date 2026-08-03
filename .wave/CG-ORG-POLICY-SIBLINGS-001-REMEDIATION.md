# Remediation Contract

## Objective

Keep the pull request subscribed and remediate concrete checks and review
findings until green.

## Allowed remediation

The installer agent may:

- correct syntax errors;
- correct schema-policy compatibility errors;
- correct unresolved assertion references;
- correct validator defects;
- correct test defects;
- correct workflow defects;
- clarify documentation when required by a valid review finding.

## Forbidden remediation

The installer agent must not:

- edit `ORG_INVARIANTS.yaml`;
- redesign the authority split;
- move files to another repository;
- add organization deployment machinery;
- add generalized CI execution;
- weaken fail-closed semantics;
- remove negative-path tests to make CI pass;
- loosen the schema solely to hide invalid policy;
- fabricate evidence;
- merge without separate authorization.

## Review handling

For each finding:

1. inspect the complete thread;
2. identify the affected supplied file;
3. determine the root cause;
4. apply the smallest complete correction;
5. run focused validation;
6. run the full wave validation;
7. push;
8. reply with the exact evidence;
9. resolve only after the correction is present remotely.

## Compatibility exception

If the live PR 53 policy differs structurally from the wave assumptions:

1. do not edit the policy;
2. report the exact incompatible field and path;
3. patch only the schema, registry, validator, tests, or documentation;
4. preserve policy meaning;
5. include the compatibility patch in the PR summary.

## Completion

The wave is converged only when:

- all required checks pass;
- all actionable review findings are resolved;
- no merge conflict remains;
- `ORG_INVARIANTS.yaml` is unchanged by this branch;
- no unrelated files are changed;
- repeated validation produces the same result.
