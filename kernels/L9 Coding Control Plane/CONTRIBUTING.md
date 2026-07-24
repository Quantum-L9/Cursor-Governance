# Contributing to L9 Assurance

## 1. Contribution model

`l9-assurance` is a trust-plane repository.

Changes must preserve strict boundaries between:

* execution;
* orchestration;
* repair;
* intelligence;
* editor integration;
* assurance.

Before proposing implementation changes, confirm that the responsibility belongs in assurance.

## 2. Scope test

A change belongs in this repository when it primarily answers one of these questions:

* Is this evidence structurally valid?
* Is the producer authorized?
* Does the evidence apply to the exact subject?
* Is the evidence fresh and intact?
* Which control does the evidence satisfy?
* Does a waiver apply?
* What remains unknown?
* What verdict follows?
* Can the decision be verified?

A change likely belongs elsewhere when it primarily:

* runs a scanner;
* executes tests;
* enumerates files;
* creates a patch;
* approves a mutation;
* publishes a GitHub check;
* mines recurring failures;
* generates prevention rules;
* serves editor diagnostics.

## 3. Repository boundaries

| Capability | Repository |
|---|---|
| Hosted CI orchestration | `l9-ci-core` |
| Scanner and check execution | `l9-ci-sdk` |
| CI failure diagnosis | `l9-ci-debt-resolver` |
| Governed mutation | `PR_Repair` |
| Historical debt analysis | `l9-ci-debt-intelligence` |
| Editor diagnostics | `l9-ci-debt-lsp` |
| Evidence, controls, decisions | `l9-assurance` |

## 4. Change categories

### Protocol changes

Examples:

* schema additions;
* schema compatibility changes;
* new evidence fields;
* new decision fields;
* new reason codes.

Protocol changes require:

* versioning analysis;
* fixtures;
* compatibility tests;
* migration notes;
* changelog entry.

### Control changes

Examples:

* new control;
* evidence requirement change;
* severity change;
* waiver rule change.

Control changes require:

* rationale;
* evidence semantics;
* profile impact;
* failure behavior;
* unknown behavior;
* migration analysis.

### Policy changes

Policy changes require explicit review when they:

* weaken a mandatory control;
* expand waiver eligibility;
* extend freshness windows;
* reduce signer requirements;
* convert indeterminate to pass;
* alter hard-gate semantics.

### Security changes

Changes involving:

* signatures;
* hashes;
* canonicalization;
* archive extraction;
* trust registries;
* waiver authorization;
* redaction

require security review.

## 5. Design principles

All contributions should preserve:

* exact subject binding;
* immutable decisions;
* admission before evaluation;
* deterministic evaluation;
* protocol-based integration;
* explicit unknowns;
* hard-gate precedence;
* minimal implementation coupling.

## 6. Development workflow

A typical contribution should:

1. define the problem;
2. identify the architectural owner;
3. update or add protocol fixtures;
4. implement the smallest coherent change;
5. add unit tests;
6. add contract tests;
7. add adversarial tests where relevant;
8. document compatibility effects;
9. update the changelog.

## 7. Determinism requirements

Contributions to evaluation logic must not depend on:

* wall-clock time without injection;
* locale;
* filesystem iteration order;
* random values;
* network access;
* mutable global state;
* nondeterministic map ordering.

Equivalent normalized input must produce equivalent canonical output.

## 8. Schema contribution rules

Schema changes must:

* use semantic versioning;
* document unknown-field behavior;
* define size and cardinality constraints;
* avoid ambiguous unions;
* avoid unbounded nested structures;
* include valid fixtures;
* include invalid fixtures;
* include compatibility fixtures.

Security-sensitive top-level objects should reject unknown fields by default.

## 9. Reason codes

Machine-readable reason codes must:

* be stable;
* be documented;
* be specific;
* avoid embedding dynamic data;
* remain suitable for automation.

Human-readable explanations may contain dynamic context.

## 10. Testing expectations

Changes should include the applicable test layers:

* unit;
* contract;
* conformance;
* integration;
* replay;
* adversarial;
* performance.

Important properties include:

* evidence order does not change the verdict;
* duplicate evidence does not improve a verdict;
* wrong-revision evidence is rejected;
* expired waivers do not improve a verdict;
* missing mandatory evidence does not become pass;
* failed mandatory controls prevent pass;
* replayed evidence is detected.

## 11. Commit guidance

Commits should be narrow and intentional.

Prefer:

```text
feat(contracts): add evidence admission reason codes
fix(evaluator): preserve indeterminate mandatory controls
docs(architecture): clarify repair boundary
security(evidence): reject unsupported signature algorithms
```

Avoid combining:

* protocol changes;
* policy changes;
* package moves;
* unrelated formatting;
* generated output

in one commit.

## 12. Pull-request expectations

A pull request should explain:

* problem;
* architectural ownership;
* proposed change;
* alternatives considered;
* compatibility impact;
* security impact;
* testing performed;
* migration impact;
* rollback strategy.

## 13. Package movement

When moving responsibility out of assurance, document:

* current package;
* target repository;
* replacement interface;
* compatibility period;
* deprecation version;
* removal version;
* migration owner.

Use one of:

```text
KEEP
MOVE
MERGE
DEPRECATE
ARCHIVE
```

## 14. Generated files

Generated files must be reproducible.

Do not commit:

* local cache files;
* build timestamps;
* machine-specific paths;
* test secrets;
* private keys;
* transient execution artifacts.

Generated protocol bindings may be committed only when:

* generation is deterministic;
* source schemas are authoritative;
* regeneration is documented;
* CI verifies no drift.

## 15. Documentation changes

Documentation must distinguish:

* implemented behavior;
* target behavior;
* draft behavior;
* deprecated behavior.

Do not describe a planned command or package as implemented unless it exists and is tested.

## 16. Security disclosures

Do not report security vulnerabilities in public pull requests or issues.

Follow `SECURITY.md`.

## 17. Review checklist

Before requesting review, verify:

* the change belongs in assurance;
* subject binding remains exact;
* decisions remain immutable;
* evaluation remains deterministic;
* unknowns remain explicit;
* hard-gate precedence remains intact;
* schemas are versioned;
* compatibility is documented;
* tests cover failure and adversarial paths;
* the changelog is updated.
