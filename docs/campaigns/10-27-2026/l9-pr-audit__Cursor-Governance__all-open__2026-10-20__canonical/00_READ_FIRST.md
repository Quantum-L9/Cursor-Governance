# Read First

This bundle is cold-startable, revision-bound audit evidence for downstream remediation.

Repository: `Quantum-L9/Cursor-Governance`
Audited default branch: `main` at `60aee3be82e97984099678df4a311cf23a0e462a`
Audit coverage: `PARTIAL`
Audit convergence: `PARTIAL`
Autoremediate: `0`

`autoremediate=0` means this audit bundle stops at handoff generation. It does not silently launch remediation.

## Audited PR source heads

- PR #737: source head `d0682d99b76e59df7e5a627bf326e3faffeedcb2` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #738: source head `37072903942ffc5ef4c19b470e85635031a1affd` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #739: source head `2a2d0d839cd2d029509f49aa5a09cd29fa44ed85` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #740: source head `d2d4d8fbd593e628260f4f7be3f0e7347dcddf5b` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #741: source head `7baa960df32a612448a4e88f572675a94c10285f` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #744: source head `b8ed6b2c503c569eea4922ddd477dc77477ae8b9` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #745: source head `ba20287ed8b4d44dcea86a8bd607e6706bdca939` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #746: source head `641a6098a481c1a7d6d63f7f9cac6b17af0b7054` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #747: source head `c435b881dc3b2fc49fa40f619a65081854bad917` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #748: source head `b9d97983ce3c98cd34a950c9a081faab27bf30b9` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #749: source head `1e1eccb2978844ec77e439373a4143493fb0ef35` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #750: source head `d22a531ba59296e70ab4a4912f2b09f9490b6e34` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #751: source head `8439dfa8062e3420b142fe3f6b27a7ab871932c4` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #752: source head `78e5722a4a440130940f3c1477945dd045575ddd` (base `2406510a18124026ac48d50d9891e93fd9772be7`)
- PR #755: source head `02e0b7ef9b4c7791e4bdb6503907724d17475a1b` (base `60aee3be82e97984099678df4a311cf23a0e462a`)

## Identity law

A PR source head is not automatically the revision that a test or CI job executed. Use each evidence entry's `tested_revision_sha`; never rewrite it as the source head by assumption.

## Start order

1. `00_READ_FIRST.md` for identity, freshness, and run control.
2. `remediation-handoff.json` for owner-classified work units and exact scope.
3. `PR_REMEDIATION_CONTRACT.md` for the downstream execution contract.
4. `audit.json` only for cited evidence IDs required by active work units.
5. `change-ledger.json` only to verify deterministic census provenance when needed.
6. `audit.md` only when extra human context is needed.
7. `MANIFEST.json` for bundle integrity when applicable.

Before editing any PR, independently verify its current source head still equals the audited SHA above. If it differs or cannot be proven, do not mutate from this audit.

Only work units marked `mutation_eligible: true` carry a write allowlist.
Publication, when remediation is explicitly invoked, must use `make pr` from the canonical SSOT Makefile surface. The target repository Makefile is not a publication authority. If the SSOT publication path cannot be proven, return `PUBLICATION_BLOCKED`.
