# Bounded LLM contract: ACTIVATION_EVAL and BEHAVIOR_EVAL judgment

## Scope
Semantic judgment only where a deterministic fixture cannot decide the outcome.

## Ordering rule
Deterministic fixtures run first via `scripts/evaluate_activation.py`. LLM
judgment is invoked only for fixtures the deterministic runner marks
non-deterministic, and only for behavior evals flagged `deterministic: false`
in `policies/behavior-evals.yaml`.

## Permitted
- Judge semantic instruction coverage for advisory Skills.
- Judge evidence grounding for diagnostic Skills.
- Judge hidden-ownership violations for adapter Skills.
- Judge sibling collision when two Skills have genuinely overlapping phrasing.

## Forbidden
- Overriding a deterministic fixture result.
- Declaring a family-required eval satisfied without an assertion and an observation.
- Reporting PASS when any deterministic fixture failed.

## Output contract
Return `{results: [{id, status, rationale, evidence}]}`. `status` is one of
`pass`, `fail`, `unknown`. A `fail` or `unknown` must never be aggregated into PASS.

## Minimum requirement
Every built Skill needs at least one positive, one negative, and one
sibling_collision fixture appropriate to its family.
