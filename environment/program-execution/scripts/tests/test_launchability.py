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
            report = launchability.check_tasks([_task(outputs=[])], Path(raw), infer=True)
            self.assertFalse(report["launchable"])
            codes = {item["code"] for item in report["blockers"]}
            self.assertIn("verification_deadlock", codes)

    def test_function_style_file_without_pytest_import_infers_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "tests").mkdir()
            (root / "tests/test_rule_loader.py").write_text(
                "def test_ok():\n    assert True\n", encoding="utf-8"
            )
            inferred = launchability.infer_validation_commands(
                {"writable_paths": ["tests/test_rule_loader.py"]},
                root,
            )
            self.assertEqual(
                inferred,
                ["python3 -m pytest tests/test_rule_loader.py --tb=short -q -o addopts="],
            )

    def test_pytest_native_file_infers_pytest_not_unittest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "tests/ops/scripts").mkdir(parents=True)
            (root / "tests/ops/scripts/test_multi_agent_main_bound.py").write_text(
                (
                    "import pytest\n\n@pytest.fixture\ndef repo():\n"
                    "    return 1\n\ndef test_ok(repo):\n    assert repo\n"
                ),
                encoding="utf-8",
            )
            inferred = launchability.infer_validation_commands(
                {"writable_paths": ["tests/ops/scripts/test_multi_agent_main_bound.py"]},
                root,
            )
            self.assertEqual(
                inferred,
                [
                    "python3 -m pytest "
                    "tests/ops/scripts/test_multi_agent_main_bound.py --tb=short -q -o addopts="
                ],
            )

    def test_shell_writable_path_infers_bash_n(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            inferred = launchability.infer_validation_commands(
                {"writable_paths": ["ops/scripts/run_pr_gate.sh"]},
                Path(raw),
            )
            self.assertEqual(inferred, ["bash -n ops/scripts/run_pr_gate.sh"])

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
                ["python3 -m pytest pkg/tests/test_widget.py --tb=short -q -o addopts="],
            )

    def test_declared_validation_overrides_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            task = _task(validation=[{"method": "command", "command_or_inspection": "make check"}])
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


class InferenceReachesTheTaskCardTest(unittest.TestCase):
    """An inferred validation only counts if the contract can be rendered from it."""

    def _cards(self, root: Path, tasks: list[dict]) -> Path:
        import yaml

        blueprint = root / "blueprint"
        blueprint.mkdir(parents=True, exist_ok=True)
        cards = blueprint / "TASK_CARDS.yaml"
        cards.write_text(yaml.safe_dump({"tasks": tasks}, sort_keys=False), encoding="utf-8")
        return blueprint

    def _written(self, blueprint: Path) -> list[dict]:
        import yaml

        doc = yaml.safe_load((blueprint / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
        return list(doc["tasks"][0]["validation"] or [])

    def test_the_inferred_command_is_written_into_the_card(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            blueprint = self._cards(root, [_task(outputs=[{"location": "docs/result.md"}])])

            changed = launchability.apply_synthesized_validations(
                blueprint, {"TASK-001": ["test -s 'docs/result.md'"]}
            )

            self.assertEqual(changed, ["TASK-001"])
            entry = self._written(blueprint)[0]
            self.assertEqual(entry["method"], "command")
            self.assertEqual(entry["command_or_inspection"], "test -s 'docs/result.md'")
            # The lock reads `method: command` entries, so this is exactly what
            # the rendered contract's validation_commands will contain.
            self.assertEqual(
                launchability.declared_validation_commands({"validation": [entry]}),
                ["test -s 'docs/result.md'"],
            )

    def test_the_inferred_entry_is_marked_as_not_operator_written(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = self._cards(Path(raw), [_task()])

            launchability.apply_synthesized_validations(blueprint, {"TASK-001": ["make check"]})

            self.assertTrue(self._written(blueprint)[0]["id"].startswith("VAL-INFERRED-"))

    def test_a_declared_validation_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declared = {
                "id": "VAL-001",
                "method": "command",
                "command_or_inspection": "make check",
                "environment": "repo_local",
                "expected_result": "PASS",
            }
            blueprint = self._cards(Path(raw), [_task(validation=[declared])])

            changed = launchability.apply_synthesized_validations(
                blueprint, {"TASK-001": ["python3 -m pytest -q"]}
            )

            self.assertEqual(changed, [])
            self.assertEqual(self._written(blueprint), [declared])

    def test_nothing_is_written_when_nothing_was_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = self._cards(Path(raw), [_task()])
            before = (blueprint / "TASK_CARDS.yaml").read_bytes()

            self.assertEqual(launchability.apply_synthesized_validations(blueprint, {}), [])
            self.assertEqual((blueprint / "TASK_CARDS.yaml").read_bytes(), before)


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

    def test_consumer_task_worktree_uses_project_venv_not_controller(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / ".venv/bin").mkdir(parents=True)
            python = project / ".venv/bin/python3"
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o755)
            (project / "uv.lock").write_text("", encoding="utf-8")
            env = {
                "VIRTUAL_ENV": str(Path.home() / ".cursor-governance/.venv"),
                "L9_PE_PYTHON": "",
            }
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "is_consumer_task_worktree", return_value=True
                ):
                    resolved = self.exec_env.resolve_exec_env(project)
            self.assertEqual(resolved.python, python.resolve())

    def test_empty_unittest_collection_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw)
            (worktree / "tests").mkdir()
            (worktree / "tests/test_empty.py").write_text(
                "def test_ok():\n    assert True\n", encoding="utf-8"
            )
            result = self.exec_env.run_validation_command(
                "python3 -m unittest tests/test_empty.py",
                worktree,
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("zero tests", result["stderr"])

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
                Path(reported).parent,
                controller_side.python.parent,
                "a validation command resolved a different python3 than the controller",
            )

    def test_venv_python_symlink_does_not_escape_to_base_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw) / "base" / "bin"
            base.mkdir(parents=True)
            target = base / "python3.12"
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o755)
            venv = Path(raw) / "donor" / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            shim = venv / "bin" / "python3"
            shim.symlink_to(target)
            isolate = Path(raw) / "isolate"
            isolate.mkdir()
            env = {
                "GOV_TOOLCHAIN_ROOT": str(venv.parent),
                "L9_PE_PYTHON": "",
                "VIRTUAL_ENV": "",
            }
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "is_l9_isolate_workspace", return_value=True
                ):
                    resolved = self.exec_env.resolve_exec_env(isolate)
            self.assertEqual(resolved.python, venv.resolve() / "bin" / "python3")
            self.assertEqual(Path(resolved.env["PATH"].split(":")[0]), venv.resolve() / "bin")
            self.assertEqual(Path(resolved.env["VIRTUAL_ENV"]), venv.resolve())

    def test_isolate_prefers_donor_toolchain_over_local_venv(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            donor = Path(raw) / "donor"
            (donor / ".venv" / "bin").mkdir(parents=True)
            (donor / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            donor_py = donor / ".venv" / "bin" / "python3"
            donor_py.write_text("#!/bin/sh\n", encoding="utf-8")
            donor_py.chmod(0o755)
            isolate = Path(raw) / "isolate"
            (isolate / ".venv" / "bin").mkdir(parents=True)
            (isolate / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            iso_py = isolate / ".venv" / "bin" / "python3"
            iso_py.write_text("#!/bin/sh\n", encoding="utf-8")
            iso_py.chmod(0o755)
            env = {
                "GOV_TOOLCHAIN_ROOT": str(donor),
                "L9_PE_PYTHON": "",
                "VIRTUAL_ENV": str(isolate / ".venv"),
            }
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "is_l9_isolate_workspace", return_value=True
                ):
                    resolved = self.exec_env.resolve_exec_env(isolate)
            self.assertEqual(resolved.python, (donor / ".venv").resolve() / "bin" / "python3")

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
            self.assertEqual(resolved.python, venv.resolve() / "bin" / "python3")
            self.assertEqual(Path(resolved.env["VIRTUAL_ENV"]), venv.resolve())
            self.assertEqual(Path(resolved.env["PATH"].split(":")[0]), (venv.resolve() / "bin"))

    def test_validation_failure_reports_the_resolved_environment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = self.exec_env.run_validation_command("exit 3", Path(raw))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["exit_code"], 3)
            self.assertIn("python", result["exec_env"])
            self.assertIn("path_head", result["exec_env"])
            receipt = self.exec_env.to_attempt_result(result)
            self.assertNotIn("exec_env", receipt)
            self.assertEqual(receipt["exit_code"], 3)

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
