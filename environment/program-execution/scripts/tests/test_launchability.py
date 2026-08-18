"""Launchability, validation inference, and one execution environment.

Together these cover the conditions that used to survive every preparation
stage and only surface long after bootstrap had frozen the blueprint.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
PEC_SCRIPTS = PE_ROOT / "core/program-execution-controller-template/scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launchability = _load("launchability_under_test", PE_ROOT / "scripts/launchability.py")
compile_source = _load(
    "compile_campaign_source_under_test", PE_ROOT / "scripts/compile_campaign_source.py"
)


def _task(**overrides):
    task = {
        "id": "TASK-001",
        "title": "Implement change",
        "execution_kind": "repo_change",
        "definition_status": "ready",
        "outputs": [{"location": "docs/result.md"}],
        "validation": [],
    }
    task.update(overrides)
    return task


class LaunchabilityTest(unittest.TestCase):
    def test_controller_verified_task_with_no_validation_is_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(outputs=[])], Path(raw), infer=True
            )
            self.assertFalse(report["launchable"])
            codes = {item["code"] for item in report["blockers"]}
            self.assertIn("verification_deadlock", codes)

    def test_validation_is_inferred_from_the_nearest_existing_test(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "pkg/tests").mkdir(parents=True)
            (root / "pkg/widget.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pkg/tests/test_widget.py").write_text("def test_x(): pass\n", encoding="utf-8")
            task = _task(outputs=[{"location": "pkg/widget.py"}])

            report = launchability.check_tasks([task], root, infer=True)
            self.assertTrue(report["launchable"])
            self.assertEqual(
                report["synthesized_validations"]["TASK-001"],
                ["python3 -m pytest -q pkg/tests/test_widget.py"],
            )

    def test_declared_validation_overrides_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            task = _task(
                validation=[{"method": "command", "command_or_inspection": "make check"}]
            )
            report = launchability.check_tasks([task], Path(raw), infer=True)
            self.assertTrue(report["launchable"])
            self.assertNotIn("TASK-001", report["synthesized_validations"])

    def test_inspection_kinds_do_not_require_executable_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(execution_kind="analysis", outputs=[])], Path(raw), infer=False
            )
            self.assertTrue(report["launchable"])

    def test_blocked_definition_status_is_reported_as_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(definition_status="blocked")], Path(raw), infer=True
            )
            codes = {item["code"] for item in report["blockers"]}
            self.assertIn("unreachable_definition_state", codes)

    def test_dangling_dependency_is_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(dependencies=["TASK-999"])], Path(raw), infer=True
            )
            codes = {item["code"] for item in report["blockers"]}
            self.assertIn("dangling_dependency", codes)


class DefinitionStatusNormalizationTest(unittest.TestCase):
    """Ordering intent must not become a state the controller cannot leave."""

    def test_blocked_with_dependencies_compiles_as_ready(self) -> None:
        src = {
            "tasks": [
                {"id": "TASK-001", "definition_status": "ready"},
                {
                    "id": "TASK-002",
                    "definition_status": "blocked",
                    "dependency_ids": ["TASK-001"],
                },
            ]
        }
        notes = compile_source.normalize_definition_status(src)
        self.assertEqual(src["tasks"][1]["definition_status"], "ready")
        self.assertTrue(any("normalized to 'ready'" in note for note in notes))

    def test_blocked_without_dependencies_is_left_alone_and_reported(self) -> None:
        src = {"tasks": [{"id": "TASK-001", "definition_status": "blocked"}]}
        notes = compile_source.normalize_definition_status(src)
        self.assertEqual(src["tasks"][0]["definition_status"], "blocked")
        self.assertTrue(any("can never be claimed" in note for note in notes))


class ExecutionEnvironmentTest(unittest.TestCase):
    """Worker-side and controller-side validation must resolve one interpreter."""

    @classmethod
    def setUpClass(cls) -> None:
        if str(PEC_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(PEC_SCRIPTS))
        from pec import exec_env  # noqa: PLC0415 - path is set above

        cls.exec_env = exec_env
        cls.run_campaign = _load("run_campaign_env_test", PE_ROOT / "scripts/run_campaign.py")

    def test_worker_and_controller_resolve_the_same_python(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw)
            worker_side = self.run_campaign.load_pec_module("exec_env").resolve_exec_env(worktree)
            controller_side = self.exec_env.resolve_exec_env(worktree)
            self.assertEqual(worker_side.python, controller_side.python)

            reported = subprocess.run(
                ["bash", "-c", "command -v python3"],
                cwd=raw,
                text=True,
                capture_output=True,
                check=True,
                env=controller_side.env,
            ).stdout.strip()
            self.assertEqual(
                Path(reported).resolve().parent,
                controller_side.python.parent,
                "a validation command resolved a different python3 than the controller",
            )

    def test_an_active_venv_wins_over_the_launching_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            venv = Path(raw) / "venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            fake = venv / "bin/python3"
            fake.write_text("#!/bin/sh\nexec /usr/bin/true\n", encoding="utf-8")
            fake.chmod(0o755)

            with unittest.mock.patch.dict("os.environ", {"VIRTUAL_ENV": str(venv)}):
                resolved = self.exec_env.resolve_exec_env(Path(raw))
            self.assertEqual(resolved.python, fake.resolve())
            self.assertEqual(Path(resolved.env["VIRTUAL_ENV"]), venv.resolve())
            self.assertEqual(Path(resolved.env["PATH"].split(":")[0]), (venv / "bin").resolve())

    def test_validation_failure_reports_the_resolved_environment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = self.exec_env.run_validation_command("exit 3", Path(raw))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["exit_code"], 3)
            self.assertIn("python", result["exec_env"])
            self.assertIn("path_head", result["exec_env"])

    def test_validation_does_not_use_a_login_shell(self) -> None:
        """A login shell re-runs the profile and re-mutates PATH."""
        source = (PEC_SCRIPTS / "pec/exec_env.py").read_text(encoding="utf-8")
        self.assertNotIn('"-lc"', source)
        self.assertIn('["bash", "-c", command]', source)
        for path in (
            PE_ROOT / "scripts/run_campaign.py",
            PEC_SCRIPTS / "pec/controller.py",
        ):
            self.assertNotIn(
                'bash", "-lc"', path.read_text(encoding="utf-8"), msg=f"{path} still login-shells"
            )


if __name__ == "__main__":
    unittest.main()
