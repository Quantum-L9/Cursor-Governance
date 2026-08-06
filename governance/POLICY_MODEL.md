# Organization-Invariant Policy Model

## Authority

`ORG_INVARIANTS.yaml` is the canonical machine-readable declaration of
Quantum-L9 organization requirements.

This document explains the model. It does not replace the policy.

The authority chain is:

```text
CANONICAL_LAW.md
    constitutional governance authority
        ↓
ORG_INVARIANTS.yaml
    mandatory organization outcomes
        ↓
governance/ASSERTION_TYPES.yaml
    deterministic meaning of policy assertions
        ↓
external implementation bindings
    mechanisms that attempt to enforce requirements
        ↓
assurance evidence
    proof of what is effective now
```

## Five distinct layers

### 1. Policy requirement

A policy requirement states what must be true.

Example:

> Governed repositories must belong to Quantum-L9.

Policy requirements remain authoritative even when implementation is incomplete.

### 2. Assertion semantics

An assertion defines how a requirement can be evaluated.

Example:

```yaml
assertion:
  type: repository_owner
  version: 1
  expected_owner: Quantum-L9
```

The type and version resolve through `ASSERTION_TYPES.yaml`.

An assertion name without registered semantics is not executable policy.

### 3. Control requirement

A control requirement describes the minimum type and strength of mechanism
needed to enforce or detect a violation.

Examples include:

- preventive control;
- detective control;
- maximum detection latency;
- fail-closed behavior;
- independent approval.

A control requirement is not proof that a control exists.

### 4. Implementation binding

An implementation binding connects an abstract control requirement to a
specific mechanism.

Examples include:

- a GitHub ruleset;
- a required status check;
- an approved repository provisioner;
- a scheduled organization audit.

Platform-specific bindings do not belong in the canonical policy unless their
identity is itself a normative requirement.

### 5. Assurance

Assurance determines what is demonstrably true now.

A control may be:

```text
absent
planned
implemented
verified
degraded
disabled
```

Its effective enforcement may independently be:

```text
unenforced
advisory
blocking
bypassed
indeterminate
```

The words implemented, verified, and blocking are evidence claims.

They must never be inferred merely from policy intent.

## Promotion rules

### Planned to implemented

Requires evidence that:

- the implementation exists;
- the documented entry point resolves;
- the implementation is reviewed;
- relevant tests exist;
- the tests were actually executed.

### Implemented to verified

Requires evidence that:

- implementation requirements are satisfied;
- positive tests pass;
- negative-path tests pass;
- execution is deterministic for equivalent inputs;
- the intended workflow invokes the implementation.

### Verified to blocking

Requires evidence that:

- the stable check or control is deployed;
- the relevant platform requires it;
- a failure prevents the governed operation;
- bypass actors and bypass behavior are known;
- the evidence is current.

A workflow file in a repository is not proof of blocking enforcement.

A successful workflow run is not proof that failed runs block merges.

## Fail-closed behavior

For critical and high-severity policy:

- unsupported assertion semantics block;
- contradictory authority blocks;
- missing identity produces unknown;
- missing enforcement evidence prevents a blocking claim;
- incomplete repository inventory must not produce a coverage pass.

Fail closed does not mean fabricating a failure result.

It means an unresolved critical decision cannot be treated as permission.

## Policy monotonicity

Downstream repositories and adapters may strengthen policy.

They may not:

- reduce severity;
- change blocking to advisory;
- change fail-closed to fail-open;
- change block to warn;
- remove an invariant;
- reinterpret an assertion without changing its version;
- broaden an exemption;
- replace independent enforcement with agent instructions.

## Unknowns

`unknown` and `indeterminate` are first-class outcomes.

They must not be silently converted to pass.

A report containing remaining unknowns can still be useful, but it cannot claim
full verification or convergence while material critical unknowns remain.

## Repository ownership boundaries

Cursor-Governance owns:

- canonical policy;
- policy grammar;
- assertion vocabulary;
- trust semantics;
- change process;
- release-record requirements.

Other repositories may own:

- GitHub organization bindings;
- evidence protocols and reduction;
- reusable CI execution;
- consumer installation.

Those systems consume this policy; they do not redefine it.
