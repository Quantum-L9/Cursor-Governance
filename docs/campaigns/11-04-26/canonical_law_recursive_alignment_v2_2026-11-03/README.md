# Canonical Law Recursive Alignment - revision 2.0.0

**Status:** static revision-map alignment, **not** source changes, admitted policy or runtime proof.

**Target:** `https://github.com/Quantum-L9/Cursor-Governance` pinned to `b6b33e8e3877348e305cce30f9e37a56537a7ad6`.
**Global reference:** `Quantum-L9/.github@bc6a4a1c1f61c20528abcb46c25173c41315bd41` (live projection replay not executed).
**Input:** `canonical_law_revision_runbook_2026-11-03.yaml` (`sha256:b6b2c11a806ada566786fefb65ddbda0cec31855fd1ce350213479109c35dc8a`).

## Corrections established by recursive alignment

1. **RA01:** Previous resolver-only correction was insufficient. The root `.pre-commit-config.yaml`, `.semgrepignore` and `.gitleaks.toml` independently exclude active workflows or deliberately published reports. Revised runbook now owns all selectors (D41-D44), plus existing D04-D05.
2. **RA02:** No reconstructible immutable **original** PR footprint producer was proven. Fail closed for a raw open-PR push with unknown provenance; do not pretend today's PR file list is historical evidence. This is an unresolved implementation design obligation, not a verified implementation.
3. **RA03:** Remediator **local write** allowances, including generated paths and new child-PR preparation, are separate from permission to advance the original remote PR branch. D03 now preserves local authoring while requiring a separate publication decision.
4. **RA04:** Duplicate D29/D33 test actions are merged, and old law clause L16 is correctly classified as superseded, not live.
5. **RA05:** `.pre-commit-config.yaml` and `.gitleaks.toml` are additive-only protected root files. Changing their old exclusion lines requires path-specific justification in commit messages, PR-body stamp and actual owner authorization. This pack grants none of those permissions.
6. **RA06:** The PR publisher's dirty-tree warning filters reports as scratch by prefix; D45 requires a focused witness before changing it.
7. **RA07:** Publication gate host interception and nested Python subprocess enforcement have not been exercised on the live host. Static source comparison does not establish that boundary.

## Legal amendment

`canonical_append.payload` in the YAML is the **only** proposed canonical-law change. The existing prefix through line 1848 must remain byte-identical. It introduces a bounded clarification at proposed sections 6.2.17, 6.2.18 and 6.2.19; it does not create new global semantic authority.

The root-file exception is important: this **append-only** law change has a different protection path from the **non-additive** `.pre-commit-config.yaml` and `.gitleaks.toml` changes.

## Implementation ordering

1. Re-pin exact current repo and inspect PR overlap, branch, owner and protected root.
2. Block unknown open-PR push, resolve truthful original PR footprint, secure direct helper push and preserve local worker grants.
3. Reconcile all path-selector owners; obtain separate actual protected-root authorization for non-additive config changes.
4. Clear the four actual CI failure areas, then reconcile PE/Memory/Infisical instruction drift and source-owned generated projections.
5. Prove local negative and positive witnesses; run full hosted CI at the actual published head. Do **not** merge on a pack validator result.

## Runbook navigation

- `canonical_law_line_dispositions` - original law line ranges and effective authority.
- `canonical_append` - machine-readable exact append guard, payload and projected line coordinates.
- `downstream_changes` - all existing owners, operation type, required changes, tests, and root-protection blockers.
- `validation_matrix` - negative and positive behavior proof requirements.
- `recursive_alignment` - adversarial passes, remaining unknowns, closure gates.
- `unknowns_and_stop_conditions` - material blockers that must not become implied approvals.

## Package verification

Run `python validate_runbook.py canonical_law_revision_runbook_v2.yaml` from this directory, with PyYAML installed. This validates the **artifact structure and amendment guards**, not live GitHub or runtime operation. `python validate_runbook.py --self-test` runs negative-fixture tests. The package SHA256 manifest checks delivered bytes.
