"""The conformance runner shards; sharding must not change what ran.

`run_conformance.py` splits the suite across worker processes, one test class
per shard. That is a scheduling change and nothing else, so the property worth
holding is an equality: the parallel report and the serial report must agree,
test for test, on a root where the answer is known independently.

Built on a synthetic root rather than the real one so the assertions can be
exact (counts, statuses, which files were collected) and the test stays fast.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PE_ROOT = TESTS_DIR.parents[1]
RUNNER = PE_ROOT / "scripts/run_conformance.py"

PASSING = """
import unittest


class AlphaTests(unittest.TestCase):
    def test_one(self):
        self.assertTrue(True)

    def test_two(self):
        self.assertTrue(True)


class BetaTests(unittest.TestCase):
    def test_three(self):
        self.assertTrue(True)

    @unittest.skip("declared skip, counted as such")
    def test_skipped(self):
        raise AssertionError("must not run")
"""

# A sibling imported by bare name: the pattern that made shards order-dependent.
SIBLING = """
SHARED = "shared-value"


import unittest


class GammaTests(unittest.TestCase):
    def test_four(self):
        self.assertTrue(True)
"""

IMPORTER = """
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_sibling import SHARED  # noqa: E402


class DeltaTests(unittest.TestCase):
    def test_five(self):
        self.assertEqual(SHARED, "shared-value")
"""

FAILING = """
import unittest


class EpsilonTests(unittest.TestCase):
    def test_fails(self):
        self.assertEqual(1, 2)

    def test_errors(self):
        raise RuntimeError("boom")
"""


def _root(tmp: Path, *, include_failing: bool) -> Path:
    """A minimal tree shaped like the directories `_test_files` globs."""
    root = tmp / "pe"
    conformance = root / "conformance"
    conformance.mkdir(parents=True)
    (conformance / "test_alpha.py").write_text(PASSING, encoding="utf-8")

    scripts_tests = root / "scripts/tests"
    scripts_tests.mkdir(parents=True)
    (scripts_tests / "test_sibling.py").write_text(SIBLING, encoding="utf-8")
    (scripts_tests / "test_importer.py").write_text(IMPORTER, encoding="utf-8")
    if include_failing:
        (scripts_tests / "test_broken.py").write_text(FAILING, encoding="utf-8")
    return root


def _report(root: Path, *, jobs: int) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(RUNNER), str(root), "--jobs", str(jobs)],
        cwd=str(PE_ROOT),
        env={"PYTHONPATH": str(PE_ROOT), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout)
    payload["exit_code"] = completed.returncode
    return payload


class ShardingPreservesTheSuite(unittest.TestCase):
    def test_parallel_and_serial_reports_are_identical(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _root(Path(raw), include_failing=False)
            serial = _report(root, jobs=1)
            parallel = _report(root, jobs=4)

        self.assertEqual(serial, parallel, "sharding changed the report")

    def test_every_test_is_accounted_for_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _root(Path(raw), include_failing=False)
            report = _report(root, jobs=4)

        # 2 (AlphaTests) + 2 (BetaTests, one skipped) + 1 (GammaTests) + 1 (DeltaTests)
        self.assertEqual(report["tests_run"], 6)
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(
            report["test_files"],
            [
                "conformance/test_alpha.py",
                "scripts/tests/test_importer.py",
                "scripts/tests/test_sibling.py",
            ],
        )

    def test_a_sibling_imported_by_bare_name_resolves_in_its_own_shard(self) -> None:
        """The shard that needs `test_sibling` must not depend on load order."""
        with tempfile.TemporaryDirectory() as raw:
            root = _root(Path(raw), include_failing=False)
            report = _report(root, jobs=4)

        self.assertEqual(report["errors"], 0, "a shard failed to import its sibling")

    def test_a_failure_in_one_shard_fails_the_whole_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _root(Path(raw), include_failing=True)
            report = _report(root, jobs=4)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["errors"], 1)
        # The passing shards still ran and were still counted.
        self.assertEqual(report["tests_run"], 8)


if __name__ == "__main__":
    unittest.main()
