from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TargetFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def test_schema_requires_rollback(self) -> None:
        schema = json.loads(
            (self.root / "target-adapter-spec.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["rollback_required"]["const"], True)

    def test_generator_produces_complete_non_routable_adapter(self) -> None:
        spec = {
            "schema": "program-execution-target-adapter.spec.v1",
            "adapter_id": "fixture-target",
            "target_kind": "fixture_environment",
            "adapter_version": "1.0.0",
            "commands": {
                phase: [["python3", "-c", "print('ok')"]]
                for phase in (
                    "preflight",
                    "deploy",
                    "observe",
                    "rollback",
                    "collect",
                    "cleanup",
                )
            },
            "required_environment": [],
            "rollback_required": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            spec_path = temporary / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(self.root / "generate_target_adapter.py"),
                    str(spec_path),
                    str(temporary / "output"),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                env=environment,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            target = temporary / "output/fixture-target"
            required = {
                "ADAPTER.yaml",
                "TARGET_CONTRACT.json",
                "preflight.py",
                "deploy.py",
                "observe.py",
                "rollback.py",
                "collect.py",
                "cleanup.py",
                "tests/test_positive.py",
                "tests/test_negative.py",
                "tests/test_hostile.py",
                "MANIFEST.json",
                "COMPATIBILITY.json",
            }
            actual = {
                path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
            }
            self.assertLessEqual(required, actual)
            self.assertFalse(list(target.rglob("__pycache__")))
            generated_tests = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    str(target / "tests"),
                ],
                cwd=target,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(
                generated_tests.returncode,
                0,
                generated_tests.stdout + generated_tests.stderr,
            )


if __name__ == "__main__":
    unittest.main()
