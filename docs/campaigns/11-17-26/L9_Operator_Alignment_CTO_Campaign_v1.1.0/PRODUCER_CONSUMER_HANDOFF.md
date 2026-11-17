# Operator-source projection interface handoff | do not invent a new global law

## Observed owner interface (2026-11-17 snapshot, must recheck)

- `Quantum-L9/.github`: global semantic registry/profile source owner, and separately operator-owned Doctrine/Intent candidate under `docs/candidates/.../repo-overlay/strategy/`. Global semantics require the `.claude/skills/l9-projection-admission` pipeline; this operator instance does not qualify automatically.
- `Quantum-L9/l9-semantic-compiler-engine`: `src/l9_semantic_compiler/engine/registry.py#CanonicalAuthority.resolve_source` accepts only a projectable registered canonical source declared in the global catalog. `src/l9_semantic_compiler/cli.py` exposes project/compose and coordinate/verify commands; those names **do not prove an operator-instance input works**.
- `Quantum-L9/Cursor-Governance`: `tools/authority/produce_projection_bundle.py` invokes the producer for admitted global profiles, writes derived bundle locks; `ops/autonomy/projection_mode.py` verifies required global bundles. It must not become an independent projection compiler or source truth owner.

## CTO interface freeze BEFORE producer/consumer code is merged

The CTO requests a **producer-owned** evidence decision with these required facts. These are acceptance facts, **not a new schema**:

1. Exact operator subject: `Quantum-L9/.github` commit on `main`, operator-scoped admission decision, five approved source byte digests and stable subject digest (canonical JSON over `OPERATOR_RELEASE_MANIFEST.json` without its `subject_digest`, then SHA-256); independent comparison with source bytes required; Doctrine and Intent exact versions.
2. Input authority: explicit operator owner, source scope and permission to project each selected leaf. No global class spoofing or unapproved values.
3. Projection contract: source identifiers/selectors, profile version, producer revision, output and receipt schema, byte/digest conventions, unresolved/unknown behavior, and result status. Reuse actually admitted contracts before adding any type.
4. Output evidence: compiler creates the view and receipt from pinned source bytes, independent verifier recomputes source selection, source and projection digest, schema, and receipt output identity; bad digest, source swap, stale revision, unapproved value are rejected.
5. Consumer boundary: Cursor commits/stores only derived bytes and locks; its verifier never runs source selection and its runtime loads only the verified material in the privilege of the actual actor. Mode changes no permissions.
6. Compatibility: no mutation to the eight admitted domain profiles, canonical global registry, or existing `coding-agent-execution@1` behavior. New provider contracts need applicable authority and versioning rather than clever fallback.

If (1)-(6) cannot be bound to a current source-owned API, Lane B emits `CTO-BLOCKER: OPERATOR_SOURCE_CONTRACT_UNKNOWN` and describes the earliest owner and exact missing contract. Lane D does not guess a JSON format, write another projector, or call its local preview live. The CTO can continue merging authorized PRs and source adoption while this join is unresolved.

## Integration handshake

- **B → CTO:** contract shape & exact producer artifact/receipt coordinates, evidence of independent verification and negative controls, or earliest blocker.
- **CTO → D:** accepted source-owned contract and exact producer revision/bundle coordinates as *read-only* task dependency. A changed material interface reopens only D's affected work, not prior admitted source text.
- **D → CTO:** consumer verifier proof and per-mode integration branch. CTO alone executes cross-repo integration and mode behavior verification.

**No parallel B/D guesses:** D can build tests for source freshness and role isolation independently, but its producer-dependent implementation waits for B's verified interface decision.