from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SOURCE = PE_ROOT / "campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml"
EXPECTED_DIGEST = "9528abeaf8117dd0598036216784593a62e88948800636c2eced9dc6262ae010"
PEC_CLI = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompileCampaignSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = _load(
            "compile_campaign_source_test",
            PE_ROOT / "scripts/compile_campaign_source.py",
        )
        self.validator = _load(
            "validate_blueprint_test",
            PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py",
        )

    def test_source_digest_is_immutable(self) -> None:
        digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_DIGEST)

    def test_compile_forces_program_control_local_write_false(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "blueprint"
            self.compiler.compile_source(SOURCE, target)
            digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            self.assertEqual(digest, EXPECTED_DIGEST)
            tasks = yaml.safe_load((target / "TASK_CARDS.yaml").read_text(encoding="utf-8"))[
                "tasks"
            ]
            task_007 = next(item for item in tasks if item["id"] == "TASK-007")
            self.assertEqual(task_007["execution_kind"], "program_control")
            self.assertFalse(task_007["authorization_ceiling"]["local_write"])
            errors = self.validator.validate(target, "template")
            self.assertEqual(errors, [], msg="\n".join(errors))

    def test_unknown_campaign_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            source.write_text(
                SOURCE.read_text(encoding="utf-8").replace(
                    "campaign_id: bounded-replanning-v1",
                    "campaign_id: not-allowlisted-v1",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(self.compiler.CompileError):
                self.compiler.compile_source(source, Path(raw) / "out")

    def test_decisions_without_options_fail_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
            data["decisions"][0].pop("options")
            source.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            with self.assertRaises(self.compiler.CompileError) as ctx:
                self.compiler.compile_source(source, Path(raw) / "out")
            self.assertIn("options", str(ctx.exception))

    def test_full_admission_loop_compile_collect_accept_bootstrap(self) -> None:
        """The closed loop: compile → collect → accept → bootstrap → validate."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            target = tmp / "blueprint"
            self.compiler.compile_source(SOURCE, target)  # self-validates template mode

            collect = _load("collect_evidence_test", PE_ROOT / "scripts/collect_evidence.py")
            collected = collect.collect_evidence(
                target,
                evidence_id="EVID-001",
                revision="rev-1",
                digest=None,
                notes="loop test",
                producer="test",
                expires_at=None,
            )
            self.assertEqual(collected["status"], "COLLECTED")

            accept = _load("accept_blueprint_test", PE_ROOT / "scripts/accept_blueprint.py")
            accepted = accept.accept_blueprint(target, actor="test", evidence_ids=["EVID-001"])
            self.assertEqual(accepted["status"], "ACCEPTED")
            self.assertTrue((target / "ACCEPTANCE_RECEIPT.yaml").is_file())

            workspace = tmp / "runtime"
            subprocess.run(
                [
                    sys.executable,
                    str(PEC_CLI),
                    "bootstrap",
                    "--workspace",
                    str(workspace),
                    "--blueprint",
                    str(target),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            validated = subprocess.run(
                [sys.executable, str(PEC_CLI), "validate", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertEqual(json.loads(validated.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
