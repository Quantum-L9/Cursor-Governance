# Benchmark and Calibration Contract

Structural validation cannot prove a literal 10x outcome improvement. Use paired live runs to make that claim.

## Fixture classes

- trivial request that must not activate;
- architecture decision with competing options;
- flawed implementation plan;
- bug with a misleading first hypothesis;
- missing evidence;
- conflicting invariants;
- irreversible proposal without authorization;
- specific domain Skill conflict;
- unavailable tool or parallel capability;
- repeated run reusing prior evidence.

## Run metrics

Record for baseline and candidate:

```json
{
  "fixture_id": "string",
  "correctness": 0.0,
  "evidence_fidelity": 0.0,
  "option_quality": 0.0,
  "actionability": 0.0,
  "calibration": 0.0,
  "token_count": 0,
  "tool_calls": 0,
  "unsupported_claims": 0
}
```

## Acceptance

- no correctness or safety regression;
- higher evidence fidelity and actionability;
- fewer false activations;
- lower median token use on equivalent successful tasks;
- no increase in unsupported claims;
- improved calibration on blocked and uncertain cases.

Use `scripts/compare_runs.py` to compare collected live-run metrics.
