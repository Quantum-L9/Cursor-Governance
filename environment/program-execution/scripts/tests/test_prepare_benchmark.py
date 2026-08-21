"""The benchmark fixture, asserted rather than only reported.

`pe_prepare_bench.py` measures preparation and prints the numbers, which is what
a human wants when tuning. It cannot fail, which is what a regression needs. This
module drives the same harness at the contract's stated scale and asserts the two
properties the contract states as outcomes:

- a large campaign reaches its first executable task quickly (SP-07), and
- preparing it again is materially cheaper than preparing it the first time
  (SP-06), which is only true if the second run resumes.

The bounds are deliberately far looser than the measured numbers
(`PREPARE_BASELINE.md`): this asserts that the mechanism still works, not that
this machine is as fast as the one the baseline was taken on.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import pe_prepare_bench as bench  # type: ignore[import-not-found]  # noqa: E402

# The contract names 30-40 tasks. 35 sits in the middle and, with the harness's
# linear dependency chain, leaves exactly one task runnable -- the shape that
# made arming every locked task expensive in the first place.
TASKS = 35

# SP-07 allows ten minutes. Anything near that is a failure of a different kind,
# so the assertion is one minute: still ~15x the measured cold time, but tight
# enough that losing the frontier optimisation fails here rather than passing
# slowly.
COLD_BUDGET_S = 60.0

# SP-06 wants the repeat to be materially cheaper. 1.5x is well under the ~2.8x
# measured, and cannot be met at all by a run that quarantines and rebuilds.
MIN_WARM_SPEEDUP = 1.5


class PrepareBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = bench.bench(TASKS, repeat=3)
        cls.runs = [run for run in cls.result["runs"] if "failed" not in run]

    def test_every_run_completed(self) -> None:
        failures = [run for run in self.result["runs"] if "failed" in run]
        self.assertEqual(failures, [], f"a prepare run failed: {failures}")
        self.assertEqual(len(self.runs), 3)

    def test_a_large_campaign_prepares_within_the_budget(self) -> None:
        cold = self.runs[0]["seconds"]
        self.assertLess(cold, COLD_BUDGET_S, f"{TASKS} tasks took {cold:.1f}s to prepare")

    def test_preparing_it_again_is_materially_cheaper(self) -> None:
        cold, steady = self.runs[0]["seconds"], self.runs[-1]["seconds"]
        speedup = cold / steady if steady else float("inf")
        self.assertGreaterEqual(
            speedup,
            MIN_WARM_SPEEDUP,
            f"repeat prepare was only {speedup:.2f}x cheaper ({cold:.2f}s → {steady:.2f}s); "
            "a repeat this expensive means the runtime was rebuilt rather than resumed",
        )

    def test_the_expensive_stages_are_reused_on_a_repeat(self) -> None:
        reused = set(self.runs[-1]["cached_stages"])
        for stage in ("compile", "accept", "bootstrap", "validate_blueprint"):
            self.assertIn(stage, reused, f"{stage} recomputed on an unchanged repeat")

    def test_every_recompute_on_a_repeat_states_a_reason(self) -> None:
        steady = self.runs[-1]
        recomputed = set(steady["stage_seconds"]) - set(steady["cached_stages"])
        reasons = steady.get("recompute_reasons") or {}
        self.assertTrue(recomputed, "nothing recomputed; the assertion would be vacuous")
        for stage in recomputed:
            self.assertTrue(reasons.get(stage), f"{stage} recomputed without a recorded reason")


if __name__ == "__main__":
    unittest.main()
