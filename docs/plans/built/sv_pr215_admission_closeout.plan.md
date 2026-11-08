---
name: SV PR215 admission closeout (candidate-side)
overview: >-
  Close the agent-executable part of the Strategic Value admission closeout on the PR #215
  candidate pack. Prove that compiler 0.9.3's always-on composition checks enforce exactly what
  the four profile-local required_provenance tokens declare (independent verifier plus negative
  controls). Scaffold the owner-decision record as PENDING with both SV-001 wording options and
  both provenance routes. Re-resolve the admission target against the moved origin/main. No owner
  decision, admission, canonical edit, release or merge is performed or claimed.
todos:
  - id: T1
    content: Independent composition-provenance verifier (no compiler imports) over a composed run directory
    file: docs/candidates/SV/tests/verify_composition_provenance.py
    action: CREATE
    status: completed
  - id: T2
    content: Positive and negative-control tests for the verifier (digest corruption, ref swap, profile digest change, duplicate, missing source, payload drift, receipt drift)
    file: docs/candidates/SV/tests/test_composition_provenance_equivalence.py
    action: CREATE
    status: completed
  - id: T3
    content: Committed verifier result over evidence/reduction-v1/projection-run1.tar and projection-run2.tar
    file: docs/candidates/SV/evidence/admission/composition-provenance-equivalence.json
    action: CREATE
    status: completed
  - id: T4
    content: Owner-decision record scaffold, decision_status PENDING, all authority refs null, both SV-001 options and both provenance routes
    file: docs/candidates/SV/evidence/admission/owner-decision.yaml
    action: CREATE
    status: completed
  - id: T5
    content: Admission closeout record with the re-resolved target (main 9488d8f, v3.28.0 admitted, v3.29.0 candidate), 12-item checklist and blockers
    file: docs/candidates/SV/evidence/admission/ADMISSION_CLOSEOUT.md
    action: CREATE
    status: completed
  - id: T6
    content: Update the readiness ledger with the composition-equivalence evidence and the re-resolved target; status unchanged (not admission ready)
    file: docs/candidates/SV/evidence/reduction-v1/admission-readiness.json
    action: REPLACE
    status: completed
  - id: T7
    content: Regenerate pack checksums covering the new files
    file: docs/candidates/SV/SHA256SUMS.txt
    action: REPLACE
    status: completed
  - id: T8
    content: Register new files in the pack manifest
    file: docs/candidates/SV/MANIFEST.json
    action: REPLACE
    status: completed
  - id: T9
    content: Point the pack README at the admission closeout record
    file: docs/candidates/SV/README.md
    action: REPLACE
    status: completed
isProject: false
---

# SV PR215 admission closeout (candidate-side)

## Tests

- `python3 -m unittest discover -s tests` from `docs/candidates/SV` (82 baseline + new verifier tests).
- `python3 tests/verify_composition_provenance.py` over both committed rehearsal archives.

## Non-goals

- No owner decision, no SV-001 text change, no removal of `required_provenance`.
- No edit under `semantics/` or `docs/semantic-foundation/`; no successor release; no admission PR; no merge.

## Outcome (2026-11-08)

The owner first approved D1–D5. A later owner instruction superseded the plan's "no admission" scope and admitted Semantic Foundation v3.32.0 / ADR-029, which merged at Quantum-L9/.github `64d8b85` (#222). The campaign record is in Quantum-L9/.github `docs/evidence/sv-campaign-closeout/` (#224). The candidate-side todos above landed through #220 → #215 → #212.
