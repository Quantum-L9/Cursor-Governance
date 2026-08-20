# Prepare-path baseline (PE-FAST-002)

Measured on `origin/main` @ `941ab77` — the state of the tree *before* any
PE-FAST-002 change, which makes these numbers the regression reference. PE-FAST-001
(PR #221, squash-merged as `d1325c45`) is included in that base.

Reproduce with:

```bash
.venv/bin/python environment/program-execution/scripts/tests/pe_prepare_bench.py --tasks 2 7 30
```

The harness drives the public `run_campaign` entry point to the end of
preparation (`until=arm`), then does it again against the same `l9_root`. The
second run is the subject: preparing an already-prepared campaign is what an
operator actually does dozens of times a day.

## Totals

| tasks | cold | warm | warm speedup | cache hits on warm run |
| ----: | ---: | ---: | -----------: | ---------------------- |
| 2 | 2.243s | 2.056s | 1.09x | `stack_proof` only |
| 7 | 3.822s | 3.641s | 1.05x | `stack_proof` only |
| 30 | 11.083s | 11.055s | 1.00x | `stack_proof` only |

## Cold stage breakdown (seconds)

| stage | 2 tasks | 7 tasks | 30 tasks |
| ----- | ------: | ------: | -------: |
| `arm` | 1.075 | 2.637 | 9.160 |
| `compile` | 0.356 | 0.345 | 0.540 |
| `bootstrap` | 0.299 | 0.278 | 0.463 |
| `accept` | 0.198 | 0.210 | 0.380 |
| `validate_blueprint` | 0.188 | 0.204 | 0.292 |
| `admission_evidence` | 0.084 | 0.096 | 0.094 |
| `emit` | 0.009 | 0.015 | 0.049 |
| `stack_proof` | 0.002 | 0.001 | 0.002 |
| `launchability` | 0.001 | 0.000 | 0.000 |
| `isolate` | 0.000 | 0.000 | 0.000 |

## What the numbers say

1. **Warm prepare costs the same as cold at every size.** The warm run logs
   `quarantine occupied <workspace> → programs/stale/<campaign>-<stamp>`: the
   prepared workspace is moved aside and rebuilt from nothing, so there is no
   resumption to measure. This is the single largest finding, and it is a
   correctness-shaped problem rather than a tuning problem.

2. **`stack_proof` is the only stage that ever reports a cache hit.** PE-FAST-001
   introduced `StageCache` but wired exactly one stage into it, so every other
   stage recomputes unconditionally on every invocation.

3. **`arm` dominates and scales with the *total* task count, not the runnable
   frontier.** It is 48% of cold prepare at 2 tasks and 83% at 30. The benchmark
   fixture uses a linear dependency chain, so at 30 tasks exactly one task is
   runnable and the other 29 are materialized for nothing.

4. **The remaining stages are a roughly constant ~1.9s floor** that is paid on
   every invocation regardless of whether anything changed.

Note that `stack_proof` reads ~0.000s here only because the benchmark supplies a
stubbed research hook. In a live campaign it is network-backed, so its real cost
is absent from this table by construction and must not be read as "already
cheap".
