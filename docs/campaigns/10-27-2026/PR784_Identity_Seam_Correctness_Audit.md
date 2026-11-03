# PR #784: Identity-Seam Correctness Audit

**Repository:** `Quantum-L9/Cursor-Governance`  
**PR:** https://github.com/Quantum-L9/Cursor-Governance/pull/784  
**Head audited:** `4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107`  
**Base:** `e31ea23149ae2669bcaca82da65252e56cf2ace5`  
**Scope:** ActorIdentity, SurfaceIdentity, assertion issuance and evidence validation, closely coupled identity consumers and tests. This is not a full audit of all 57 changed files.

## Decision

**IDENTITY-SEAM BLOCKED** pending repair and regression proof for finding I784-01. A second newly introduced evidence inconsistency (I784-02) should be repaired in the same bounded slice. Product/release result semantics remain an explicitly identified authority interpretation (I784-U01), not a proven PR-introduced regression. This is a read-only source audit: no repository changes or tests were executed locally.

## What is correct

- Cursor and Claude runtime actor IDs derive from host evidence. Claude desktop, CLI, web and mobile are one `claude-code` actor, not separate authors.
- Unknown Claude entrypoints preserve `actor_identity=claude-code` and `surface_identity=unknown`; no guessed mobile/desktop surface.
- Surface refs are accepted only when assigned in the operating-plane binding, and a caller's differing agent claim cannot replace the derived author.
- A public OAuth client ID alone does not create an actor. Historical actor aliases are rejected on new writes.
- CI at this exact head reports success for L9 Canonical Identity Projection, L9 Lint and Test, Memory Cross-Repo Proof, Organization CI Core, and CodeQL. Three review threads are resolved/outdated. Green CI is not evidence against the counterexamples below.

## Findings

### I784-01 | HIGH | OPEN | Pre-existing gap, material to the PR's identity boundary

**Projection receipt hash is not verified at assertion issuance.**

The downstream identity binding expressly requires `output_digest_mismatch: reject` and `stale_projection: reject`. The runtime `build_runtime_identity_assertion` checks only `projection.source_revision == receipt.projection.source_revision`; it then copies the receipt's `output.digest` into a sealed, HMAC-signed assertion without comparing it to the projection file's actual SHA-256. A locally modified projection with an unchanged source revision is therefore treated as verified identity evidence. A separate authoritative project checker already implements the correct `sha256(PROJECTION_PATH.read_bytes())` validation.

**Falsification test:** In a temporary copy of the fixture, change a canonical projection actor's `description` or `status` but leave the receipt unchanged and its source revision equal. Invoke `build_runtime_identity_assertion({'CURSOR_AGENT':'1'}, root=tmp)`. Expect an identity-resolution refusal before signing. Based on the inspected code, the present function would accept this case. The PR's new stale-receipt test instead changes only the receipt source revision, so it does not test this condition.

**Smallest sufficient remediation:** Reuse one pure projection/receipt verification owner across the runtime issuer and the existing governance checker. Before minting an assertion, verify exact output bytes against `receipt.output.digest`, receipt/projection source coordinates, expected binding/profile coordinates, and authoritative actor/surface status. Fail closed. Do not duplicate the entire projection compiler.

**Evidence:**
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/ops/memory/print_agent_assertion_env.py#L205-L274
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/governance/authority-bindings/canonical-agent-identity.yaml#L113-L130
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/tools/assurance/check_canonical_identity_projection.py#L118-L146
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/tests/ops/memory/test_agent_assertion.py#L595-L629

### I784-02 | MEDIUM | OPEN | Introduced in this PR

**OAuth client value changes actor resolution but is omitted from normalized runtime evidence.**

`resolve_agent_id` compares `L9_MEMORY_AGENT_ID` to the first public OAuth client ID. `normalized_runtime_evidence` does not record the client match, even as a boolean, so distinct resolution outcomes can have the same evidence digest.

**Concrete counterexample:**

```
A = {'L9_MEMORY_AGENT_ID':'manus', 'OAUTH_CLIENT_ID':'manus'}
B = {'L9_MEMORY_AGENT_ID':'manus', 'OAUTH_CLIENT_ID':'different'}
resolve_agent_id(A) == ''
resolve_agent_id(B) == 'manus'
normalized_runtime_evidence(A) == normalized_runtime_evidence(B)
```

The actor is spuriously denied under A even though `manus` is a registered adapter actor, and the normalized evidence does not explain why. This is an evidence-bound resolution correctness issue, not a proven access escalation.

**Smallest sufficient remediation:** Remove the equality test from actor classification, deriving admitted adapter actors only from the adapter marker as before; public OAuth IDs alone will still not select an actor. If OAuth collision must remain a denial condition, include the exact boolean comparison predicate in normalized evidence and test both branches. Avoid recording raw OAuth IDs.

**Evidence:**
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/ops/memory/agent_identity.py#L130-L162
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/ops/memory/agent_identity.py#L208-L237
- https://github.com/Quantum-L9/.github/blob/3dcdeaae355b6de08562993f705084d7a3714bfd/semantics/contracts.yaml#L925-L964

## Contract interpretation requiring an owner decision

### I784-U01 | UNRESOLVED | Pre-existing result flag, newly explicit applicable dimensions

The assertion explicitly declares the applicable dependency dimensions as `[product_identity, release_identity]` but still emits `release_identity='unknown'` and `result='resolved'`. The global `l9.contract/identity-resolution@1` describes `resolved` as resolving *required identity dimensions*. The `result='resolved'` behavior existed before this PR, but the applicable dimension list is newly declared and tests now assert the combination.

This must be reconciled with the upstream Memory 2.6.0 verifier, which accepts only `result='resolved'` for actor authentication. Simply changing the result to `unknown` in Cursor-Governance would disable valid signed-agent writes. Do not manufacture a ReleaseIdentity from a version, SHA or wheel digest. Ask the canonical identity owner to clarify whether the assertion result scopes only to the subject actor or all required product-kind dimensions; if all dimensions, coordinate a typed separation or upstream verifier change with the Memory owner.

**Evidence:**
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/ops/memory/print_agent_assertion_env.py#L239-L274
- https://github.com/Quantum-L9/Cursor-Governance/blob/4e5e5a0cf0f5dc82fbbf0f1b356b38430d9e6107/tests/ops/memory/test_agent_assertion.py#L533-L548
- https://github.com/Quantum-L9/.github/blob/3dcdeaae355b6de08562993f705084d7a3714bfd/semantics/contracts.yaml#L925-L1003
- https://github.com/Quantum-L9/l9-graphiti-memory/blob/846f283f7dade101b324b87008ab4f5901f97074/src/l9_graphite_memory/authz/signed_assertion.py

## Evidence and completion limitations

- GitHub PR head and workflow conclusions were rechecked after inspection. Exact head unchanged.
- The PR's body labels its scoped gate receipt `STALE` because it was produced at an earlier commit. This is release evidence status, not an additional identity code finding.
- No full clone, repository test execution, mutation test, or complete 57-file census was available in this read-only tool environment. CI workflows at the exact head were observed, not independently rerun. This is an identity-seam audit, not a whole-PR merge approval.

## Acceptance conditions for the next bounded repair

1. Same-revision, different-content projection and receipt must be rejected before an identity assertion is signed; unchanged canonical fixtures must still mint and verify against Memory 2.6.0.
2. OAuth collision tests must prove that client strings alone never select an actor and that every actor-affecting input is represented in provenance without leaking client IDs.
3. Keep the already-correct Claude actor/surface treatment and signed-agent door wire contract unchanged.
4. Get an explicit interpretation for I784-U01 before claiming complete global identity conformance; do not let a local runtime claim redefine global law.
5. Regenerate a head-bound scoped gate receipt and re-run identity integration tests after repair; keep publication via `make pr` only, with no merge without authorization.

**Decision authority:** The user authorizes the audit only. No mutation, comment posting, PR merge or publication was performed.
