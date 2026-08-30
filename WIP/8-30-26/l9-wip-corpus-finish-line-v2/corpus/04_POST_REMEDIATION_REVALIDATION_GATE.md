# Post-Remediation Revalidation Gate

## Purpose
The user reports the seam-audit findings remediated. Before production use, prove the repaired chain at current checked-out revisions. Do not rely on the historical audit receipt or on the remediation claim alone.

## Required proof
1. Bind exact SHAs for meta-injector, topology, and graphiti-memory.
2. Generate a real Corpus Intelligence Packet from l9-meta-injector.
3. Consume that packet through topology without the legacy generation-directory adapter being required.
4. Exercise every policy-eligible corpus edge type, including DUPLICATE_OF, BLOCKED_BY, REFERENCES.
5. Verify structured edge direction/properties survive lowering and canonical memory.
6. Verify forged publication payloads fail closed even if file hashes/manifests are repaired.
7. Verify structured source locators round-trip across producer/consumer contracts.
8. Verify source removal/retraction terminates current truth and withdraws/invalidates the Graphiti projection without deleting history.
9. Replay unchanged publication and require duplicate/no-op semantics.
10. Rebuild Graphiti from canonical memory and require identity/relationship equivalence.

## Gate
Production corpus execution is allowed only when all ten proofs are PASS and the cross-repo fixture is pinned with provenance.
