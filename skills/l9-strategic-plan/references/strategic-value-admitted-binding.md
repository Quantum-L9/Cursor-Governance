# Admitted Strategic Value: Planner consumer contract

## Release authority and exact identities

The *admitted* Strategic Value contract is from `Quantum-L9/.github` semantic-foundation **v3.32.0**, effective at commit `64d8b8598300f94c3201f26866f73be6895dab60` (ADR-029). The current main commit checked while this pack was prepared was `c9bbfaf61bd0f7444b1a617876a031c2fba75406`; the admission record explicitly states that the admitted semantics tree has not changed. Re-resolve source authority for later use; do not silently promote a moving branch to a source lock.

- Model: `l9.strategic.value@1` (`l9.source/strategic-value-model@1`).
- Global new invariants: **only** `L9-SV-001` and `L9-SV-002`. Other proposed SV IDs were reduced/merged; their applicable semantics survive in the model and assessment contract, not as global invariants.
- Assessment contract: `l9.contract/strategic-value-assessment@1`; applies **only** to assessments asserting applicable objective-relative quantitative Strategic Value.
- Source projection profile: `l9.projection/strategic-planner-value@1` with output payload `l9.projection.strategic-planner-value/v1`.
- Composition profile: `l9.compose/strategic-planner-value@1` with output payload `l9.composed-projection.strategic-planner-value/v1`.
- Five source classes: `strategic_value_model`, `vocabulary`, `invariants`, `contracts`, `authority_model`. Each is a separate canonical-source projection; composition preserves each under its own namespace without interpreting or numerically combining them.
- Composition requires four independently checked provenance coordinates: `source_projection_refs`, `source_projection_digests`, `composition_profile_ref`, and `composition_profile_digest`.

## Activation and verification

1. Resolve the exact admitted `.github` revision and the actual `l9-semantic-compiler-engine` compatible with the admitted source (post-merge replay records `33e4c5832bf73c7d9b0b70854af011e9582f1ab2` and cross-checks the later byte-equivalent main build). Do not substitute arbitrary local JSON projections.
2. Obtain all **five** genuine compiled projection artifacts **and receipts**, plus the composed artifact and its receipt. Retain their original bytes and provenance. Do not generate stand-in PASS receipts.
3. Run `scripts/verify_sv_binding.py --authority-root <pinned-git-checkout> --manifest <real-file-manifest>`. The verifier invokes the *actual canonical compiler's* `CanonicalAuthority`, `verify_projection_artifact`, `verify_projection_receipt`, `verify_composed_projection` and `verify_composed_receipt`; it checks full source coverage, distinct classes, exact projection digests, admitted profile identities, complete receipt criteria, and the release digest lock. The tool refuses to claim `BOUND` if the compiler library, source checkout, or artifacts are missing.
4. The portable file manifest format is in `references/strategic-value-binding-manifest.template.json`. The fixed admission digests are in `references/strategic-value-admission-lock.json`. The template is deliberately **not** a receipt and cannot itself activate binding.
5. A successful authenticated and current replay allows `CANONICAL_BINDING_VERIFIED` for that exact source and artifact set, not runtime auto-installation or permission to mutate the Strategic Plan. An absent or incomplete bundle must be reported `CANONICAL_BINDING_BLOCKED`.

## Assessing Strategic Value

Only activate this domain-specific assessment contract **when the user is actually asserting a quantified Strategic Value claim**. Ordinary strategic exploration, portfolio maps, or work-priority advice remain governed by their regular sources without coercing SV calculations. If a Strategic Value claim is made:

- Identify the decision objective and beneficiary, compatible utility units, counterfactual baseline, bounded time horizon, evidence/model coordinates, material uncertainty, and formal feasibility constraints.
- Apply the **five-bucket mutually exclusive and exhaustive accounting partition**: `SV = IEV + SFV - DC - ERL - OC`. Each material causal effect has one accounted home. In a net-flow model, any DC/ERL/OC already embedded in IEV/SFV is **excluded** from separate subtraction. A gross-flow model may subtract the same cost separately, but not both. Unreconciled effects remain Unknown rather than zero.
- Use question-appropriate Numerical Reasoning methods: discounted counterfactual trajectories, bounded scenario analysis, robust optimization, optional bounded Q/V belief-state lookahead, or another owner-admitted method. **Q/V is not universally mandatory.** Probability-mass checks apply only to methods using probabilities; actor/belief-state coordinates apply only when material to the chosen method.
- Respect causation and welfare scope, stable effect identity, actor responses, nonanticipative policies, shared resource/portfolio effects, uncertainty-sensitive decision boundaries, and evidence provenance when material.
- `scripts/check_sv_assessment.py` checks *declared* partition and claim obligations, without predicting benefits, validating external evidence, calibrating probabilities, or executing an owner numerical solver. A passing local claim check is `DECLARED_INPUT_CONSISTENT_NOT_NUMERICALLY_ATTESTED`. For multiple comparable alternatives, use `scripts/compare_sv_claims.py` to obtain a declared-only ranking or tied frontier. Known infeasible actions are excluded; an unresolved feasible alternative prevents a unique overall winner. It is not a forecast-calibration or policy optimizer.
- Forecasts, projected value, and recommendations are non-authoritative derived evidence; only Plan Keeper/Strategic Authority may admit new Strategic Commitments. SV never grants publication or execution authority.

## Evidence status

The public closeout `docs/evidence/sv-campaign-closeout/final-receipt.yaml` records `SV_CANONICALLY_ADMITTED_AND_VERIFIED`, and post-merge replay reports five passing projections and composition with provenance verification. This is **producer** evidence. It explicitly excludes independent consumer binding. In this skill's preparation environment there is no pinned `.github` Git checkout or available `l9_semantic_compiler` package, nor the original six producer artifact/receipt pairs. Therefore actual consumer replay has not been performed here. No synthetic test may claim otherwise.
