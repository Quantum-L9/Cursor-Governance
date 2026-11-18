# Strategic Value admission-to-Planner alignment receipt

Date: 2026-11-08. This receipt describes the **packaged Planner skill** and its
consumer-side validation, not a `.github` canonical-admission action.

## Source and exact version

- `.github` observed default branch: `c9bbfaf61bd0f7444b1a617876a031c2fba75406`.
- Admitted semantic-foundation: `v3.32.0`, effective at
  `64d8b8598300f94c3201f26866f73be6895dab60`, accepted in ADR-029.
- Admitted model: `l9.strategic.value@1`.
- Admitted invariant identities: **L9-SV-001, L9-SV-002 only**.
- Admitted assessment contract: `l9.contract/strategic-value-assessment@1`.
- Admitted projection: `l9.projection/strategic-planner-value@1`.
- Admitted composition: `l9.compose/strategic-planner-value@1`.
- Payload schemas: `l9.projection.strategic-planner-value/v1` and
  `l9.composed-projection.strategic-planner-value/v1`.
- Official post-merge producer evidence: five projections PASS, one composition
  PASS, four required provenance criteria PASS, and `DOWNSTREAM_USABLE`.
- Current evidence links:
  - https://github.com/Quantum-L9/.github/blob/c9bbfaf61bd0f7444b1a617876a031c2fba75406/docs/evidence/sv-campaign-closeout/final-receipt.yaml
  - https://github.com/Quantum-L9/.github/blob/c9bbfaf61bd0f7444b1a617876a031c2fba75406/docs/evidence/sv-campaign-closeout/post-merge-replay/producer-summary-33e4c58.json
  - https://github.com/Quantum-L9/.github/blob/c9bbfaf61bd0f7444b1a617876a031c2fba75406/docs/evidence/sv-campaign-closeout/post-merge-replay/provenance-verifier.json

## Consumer coverage and proof

- Script `verify_sv_binding.py` resolves the canonical source at the exact
  admitted Git commit using the real compiler. It independently replays all
  projection and receipt verification and composition + composition receipt.
  It also checks the published release artifact digest lock, exact source
  classes, namespaced composition and profile identity.
- Synthetic tests demonstrate the adapter's routing and negative controls.
  **Fake test engines cannot return a `CANONICAL_BINDING_VERIFIED` status.**
- Script `check_sv_assessment.py` checks compatible five-term accounting,
  distinct causal booking, embedded-cost reconciliation, the six falsifiers,
  and conditional Q/V controls against *declared* inputs only.
- Script `compare_sv_claims.py` compares compatible declarations, preserving
  ties, formally blocked alternatives and unknowns without inventing a winner.
- Published producer evidence is real, but **the six actual consumer artifact
  and receipt pairs, immutable .github Git checkout and canonical compiler
  library are unavailable in the local packaging environment**. The live
  consumer check returns `CANONICAL_BINDING_BLOCKED`, not BOUND.
- Model assurance, numerical forecasting, independent causal calibration and
  Plan Keeper authority are **not** established by the local checks.

## Outstanding activation gate

Provide the exact admission-revision `.github` checkout and five original
projection/receipt pairs plus composition/receipt, with compatible canonical
`l9-semantic-compiler-engine` installed. Fill
`references/strategic-value-binding-manifest.template.json` with the genuine
artifact paths, then call the verifier as described in SKILL.md. A valid
`CANONICAL_BINDING_VERIFIED` result permits consumer use of projected semantics
for that exact revision only. Installing this skill still requires explicit
user action; packaging does not update the installed instance.
