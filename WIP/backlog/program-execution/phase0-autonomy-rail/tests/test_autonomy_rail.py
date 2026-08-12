from __future__ import annotations

import copy
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BP = ROOT / "program-execution-blueprint-template"


class AutonomyRailHostileTests(unittest.TestCase):
    def test_phase0_artifact_and_gate_zero_exist(self) -> None:
        phase0 = yaml.safe_load((BP / "PHASE0_USER_CONFIG.yaml").read_text(encoding="utf-8"))
        self.assertEqual(phase0["phase"], 0)
        self.assertIs(phase0["autonomy"]["autonomous_merge"], False)
        self.assertIs(phase0["alignment"]["make_pr_gate_required"], True)
        gates = yaml.safe_load((BP / "CONVERGENCE_GATES.yaml").read_text(encoding="utf-8"))["gates"]
        self.assertIn("GATE-000", {g["id"] for g in gates})

    def test_stop_taxonomy_and_error_codes(self) -> None:
        stops = yaml.safe_load(
            (ROOT / "program-execution-controller-template/policy/stop-conditions.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("stop_taxonomy", stops)
        self.assertIn("phase0_incomplete", stops["stop_when"])
        self.assertIn("local_pr_gate_skipped", stops["stop_when"])
        self.assertIn("lock_or_pin_misalignment", stops["stop_when"])
        codes = {
            e["code"]
            for e in yaml.safe_load(
                (ROOT / "shared/ERROR_TAXONOMY.yaml").read_text(encoding="utf-8")
            )["errors"]
        }
        for code in (
            "PHASE0_INCOMPLETE",
            "LOCAL_PR_GATE_SKIPPED",
            "UV_LOCK_DRIFT",
            "ADVISORY_CI_NOISE",
            "NON_BUSINESS_STOP_UNCLEARED",
            "ADAPTER_ABSENT_FOR_REMOTE",
        ):
            self.assertIn(code, codes)

    def test_deploy_profile_exists_and_default_stays_bounded(self) -> None:
        autonomy = yaml.safe_load(
            (ROOT / "program-execution-controller-template/policy/autonomy.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(autonomy["profile"], "bounded_local_execution")
        self.assertIn("program_deploy_max_autonomy", autonomy["profiles"])
        self.assertIs(
            autonomy["profiles"]["program_deploy_max_autonomy"]["autonomous_merge"], False
        )
        parallelism = yaml.safe_load(
            (ROOT / "program-execution-controller-template/policy/parallelism.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(parallelism["limits"]["global_max_workers"], 1)
        self.assertEqual(parallelism["deploy_profile_limits"]["global_max_workers"], 4)
        self.assertEqual(parallelism["deploy_profile_limits"]["max_writers_per_repository"], 1)

    def test_template_mode_passes_with_phase0_rail(self) -> None:
        import shutil
        import subprocess
        import sys

        for junk in BP.rglob("__pycache__"):
            shutil.rmtree(junk, ignore_errors=True)
        phase0 = yaml.safe_load((BP / "PHASE0_USER_CONFIG.yaml").read_text(encoding="utf-8"))
        hostile = copy.deepcopy(phase0)
        hostile["program_deploying"] = True
        hostile["completeness"]["phase0_complete"] = False
        self.assertTrue(hostile["program_deploying"])
        self.assertFalse(hostile["completeness"]["phase0_complete"])
        result = subprocess.run(
            [
            sys.executable,
            str(BP / "scripts" / "validate_blueprint.py"),
            str(BP),
            "--mode",
            "template",
        ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        for junk in BP.rglob("__pycache__"):
            shutil.rmtree(junk, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
