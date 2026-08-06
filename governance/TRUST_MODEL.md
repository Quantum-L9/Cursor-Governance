# Organization Governance Trust Model

## Core rule

Coding agents are untrusted change producers.

They may inspect, propose, implement, test, and report. They are not the final
authority for approving or bypassing the controls governing their own changes.

This applies to:

- Cursor;
- Claude Code;
- Codex;
- other coding agents;
- IDE extensions;
- local scripts;
- local hooks;
- pull-request automation.

## Change producers and enforcement boundaries

A change producer creates or modifies candidate state.

An enforcement boundary independently decides whether that candidate state may
proceed.

Examples of enforcement boundaries include:

- an organization ruleset;
- a repository ruleset;
- a required status check;
- an approved repository provisioner;
- an approved policy-release process.

An instruction file, prompt, convention, local hook, or agent self-report is not
an independent enforcement boundary.

## Human identity

A human contributor or repository administrator is also a change producer when
authoring a change.

Administrative access does not automatically establish independent approval.

For governance-sensitive changes:

- the author must not approve their own work;
- agent approval is not human approval;
- the approver must belong to the authorized owner group;
- platform-verifiable approval evidence is required.

## Authority separation

The canonical authority is:

1. CANONICAL_LAW.md;
2. ORG_INVARIANTS.yaml;
3. registered assertion semantics;
4. approved release metadata.

Consumer repositories, platform bindings, and adapters may not declare
competing canonical authority.

## Mutable and immutable references

A branch such as `main` identifies a moving source location.

It does not identify an immutable policy release.

Blocking consumers should bind to:

- an immutable commit;
- or an approved signed release resolving to an immutable commit.

## Digests and authenticity

A digest can establish that two payloads are identical under a declared
canonicalization process.

A digest does not establish:

- who approved the payload;
- who published it;
- whether the source was authorized;
- whether the surrounding release process was trusted.

Authenticity requires independent identity evidence such as an approved
signature, attestation, or platform-verified release process.

## Failure and uncertainty

For critical governance decisions:

- unsupported semantics block;
- conflicting identity produces unknown;
- incomplete evidence prevents verified or blocking claims;
- incomplete inventory prevents full-coverage claims;
- stale evidence does not support current enforcement claims.

The system must distinguish:

```text
pass
fail
unknown
indeterminate
blocked
```

## Self-approval and self-bypass

An agent must not:

- approve its own policy change;
- mark its own work verified without executed evidence;
- grant itself a bypass;
- alter the rules governing its own bypass;
- resolve review findings without applying and validating the correction.

Break-glass access must be:

- human-authorized;
- time-limited;
- incident-linked;
- auditable;
- retrospectively reviewed.

## Repository boundaries

### Cursor-Governance

Owns policy meaning and normative governance artifacts.

### Quantum-L9/.github

May own GitHub-specific organization bindings, distribution, rulesets, and
posture observation.

### Assurance systems

May own evidence schemas, admission, and deterministic verdict reduction.

### CI execution systems

May own reusable executable validators and evidence production.

### Consumer repositories

Should contain only the minimum local binding and workflow caller required to
consume the approved policy.

No downstream repository may silently redefine upstream authority.
