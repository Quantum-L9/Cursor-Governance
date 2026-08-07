<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, stress-test]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# Plan Stress Test (mandatory)

Every PLAN_DOCUMENT must include `stress_test` with:

- `disconfirming_questions` — questions that would falsify the plan if answered badly (min 1; deep ≥ 3)
- `assumed_false_ifs` — assumptions that must remain true
- `blast_radius` — what breaks if the plan is wrong
- `rollback` — how to reverse; required non-empty when any todo risk is high/irreversible

Also ensure `critical_path` is an ordered dependency-respecting sequence of todo ids.
