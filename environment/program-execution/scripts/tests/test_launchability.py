"""Launchability, validation inference, and one execution environment.

Together these cover the conditions that used to survive every preparation
stage and only surface long after bootstrap had frozen the blueprint.
"""

from __future__ import annotations

import importlib.util
import json
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


def _cards(root: Path, tasks: list[dict], *, name: str = "TASK_CARDS.yaml") -> Path:
    import yaml

    blueprint = root / "blueprint"
    blueprint.mkdir(parents=True, exist_ok=True)
    (blueprint / name).write_text(
        yaml.safe_dump({"tasks": tasks}, sort_keys=False), encoding="utf-8"
    )
    return blueprint


class CanonicalTaskLoadingTest(unittest.TestCase):
    """TASK_CARDS.yaml is what the compiler emits, so it is what launchability reads.

    Reading `tasks.json` instead let a 39-task campaign report `task_count=0`,
    `launchable=true`, `no_task_cards` -- a pass earned by not looking.
    """

    def test_launchability_reads_canonical_task_cards_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = _cards(Path(raw), [_task(), _task(id="TASK-002")])

            loaded = launchability.load_blueprint_tasks(blueprint)

            self.assertEqual([task["id"] for task in loaded], ["TASK-001", "TASK-002"])
            self.assertEqual(
                launchability.blueprint_task_source(blueprint),
                launchability.SOURCE_TASK_CARDS,
            )

    def test_compiled_campaign_task_count_matches_launchability_task_count(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            authored = [_task(id=f"TASK-{index:03d}") for index in range(1, 6)]
            blueprint = _cards(Path(raw), authored)

            report = launchability.check_tasks(
                launchability.load_blueprint_tasks(blueprint), Path(raw), defer_inference=True
            )

            self.assertEqual(report["task_count"], len(authored))

    def test_missing_validation_in_task_cards_is_seen_by_launchability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            # No validation and nothing to derive one from: a real deadlock the
            # reader has to actually load the card to notice.
            blueprint = _cards(Path(raw), [_task(outputs=[], validation=[])])

            report = launchability.check_tasks(
                launchability.load_blueprint_tasks(blueprint), Path(raw), defer_inference=True
            )

            self.assertEqual(report["task_count"], 1)
            self.assertFalse(report["launchable"])
            self.assertIn(
                "verification_deadlock", {item["code"] for item in report["blockers"]}
            )

    def test_invalid_task_cards_yaml_fails_launchability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()
            (blueprint / "TASK_CARDS.yaml").write_text("tasks: [: not: yaml\n", encoding="utf-8")

            with self.assertRaises(launchability.LaunchabilityError):
                launchability.load_blueprint_tasks(blueprint)

    def test_task_cards_without_a_tasks_key_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()
            (blueprint / "TASK_CARDS.yaml").write_text("schema: v1\n", encoding="utf-8")

            with self.assertRaises(launchability.LaunchabilityError):
                launchability.load_blueprint_tasks(blueprint)

    def test_an_explicitly_taskless_campaign_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = _cards(Path(raw), [])

            self.assertEqual(launchability.load_blueprint_tasks(blueprint), [])

    def test_legacy_task_loader_is_fallback_only(self) -> None:
        import json as _json

        with tempfile.TemporaryDirectory() as raw:
            blueprint = _cards(Path(raw), [_task(id="FROM-CARDS")])
            (blueprint / "tasks.json").write_text(
                _json.dumps({"tasks": [{"id": "FROM-LEGACY"}]}), encoding="utf-8"
            )

            # Both representations present: the canonical one answers.
            self.assertEqual(
                [task["id"] for task in launchability.load_blueprint_tasks(blueprint)],
                ["FROM-CARDS"],
            )

            (blueprint / "TASK_CARDS.yaml").unlink()
            self.assertEqual(
                [task["id"] for task in launchability.load_blueprint_tasks(blueprint)],
                ["FROM-LEGACY"],
            )
            self.assertEqual(
                launchability.blueprint_task_source(blueprint),
                launchability.SOURCE_LEGACY_JSON,
            )

    def test_a_blueprint_with_no_task_representation_reports_none(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()

            self.assertEqual(
                launchability.blueprint_task_source(blueprint), launchability.SOURCE_NONE
            )
            self.assertEqual(launchability.load_blueprint_tasks(blueprint), [])


class GlobalLaunchabilityIsReadOnlyTest(unittest.TestCase):
    """Preparation-time launchability inspects; it does not rewrite the campaign."""

    def test_global_launchability_does_not_mutate_task_cards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = _cards(Path(raw), [_task(outputs=[{"location": "docs/result.md"}])])
            before = (blueprint / "TASK_CARDS.yaml").read_bytes()

            report = launchability.check_tasks(
                launchability.load_blueprint_tasks(blueprint), Path(raw), defer_inference=True
            )

            self.assertTrue(report["launchable"])
            self.assertEqual((blueprint / "TASK_CARDS.yaml").read_bytes(), before)
            self.assertEqual(report["synthesized_validations"], {})

    def test_no_global_task_card_mutator_remains(self) -> None:
        source = (PE_ROOT / "scripts/launchability.py").read_text(encoding="utf-8")
        self.assertNotIn("apply_synthesized_validations", source)

    def test_future_task_validation_not_inferred_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            # A test file exists in *this* (governance) checkout at the path the
            # task will write in its own repository. Global inference would bind
            # to it; deferred inference must not even look.
            (root / "pkg/tests").mkdir(parents=True)
            (root / "pkg/widget.py").write_text("x = 1\n", encoding="utf-8")
            (root / "pkg/tests/test_widget.py").write_text("def test_x(): pass\n", encoding="utf-8")
            task = _task(outputs=[{"location": "pkg/widget.py"}])

            report = launchability.check_tasks([task], root, defer_inference=True)

            self.assertTrue(report["launchable"])
            self.assertEqual(report["synthesized_validations"], {})
            self.assertIn("validation_deferred", {item["code"] for item in report["findings"]})

    def test_explicit_validation_wins_over_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            task = _task(validation=[{"method": "command", "command_or_inspection": "make check"}])

            report = launchability.check_tasks([task], Path(raw), defer_inference=True)

            self.assertTrue(report["launchable"])
            self.assertEqual(report["findings"], [])

    def test_a_task_with_nowhere_to_write_is_still_a_deadlock(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(outputs=[], validation=[])], Path(raw), defer_inference=True
            )

            self.assertFalse(report["launchable"])


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


class ExecEnvProvisioningTest(unittest.TestCase):
    """Resolution reads; only `ensure_exec_env` builds.

    Resolution used to run `uv sync` / `uv venv` / `uv pip install`, so every
    validation command and every controller verification reprovisioned the same
    unchanged project: the campaign paid for its environment once per command
    instead of once per environment.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if str(PEC_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(PEC_SCRIPTS))
        from pec import exec_env  # noqa: PLC0415 - path is set above

        cls.exec_env = exec_env

    def _project(self, root: Path) -> Path:
        """A consumer project that declares an environment but has none built."""
        (root / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8"
        )
        (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        return root

    def _fake_venv(self, root: Path) -> Path:
        (root / ".venv/bin").mkdir(parents=True, exist_ok=True)
        python = root / ".venv/bin/python3"
        python.write_text("#!/bin/sh\n", encoding="utf-8")
        python.chmod(0o755)
        (root / ".venv/pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
        return python

    def test_resolve_exec_env_has_no_provisioning_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = self._project(Path(raw))
            with unittest.mock.patch.object(
                self.exec_env, "is_consumer_task_worktree", return_value=True
            ):
                with unittest.mock.patch.object(self.exec_env.subprocess, "run") as ran:
                    self.exec_env.resolve_exec_env(project)
            for call in ran.call_args_list:
                argv = call.args[0] if call.args else []
                self.assertNotIn(
                    "uv", [Path(str(argv[0])).name] if argv else [], msg=f"resolution ran {argv}"
                )
            self.assertFalse((project / ".venv").exists(), "resolution created an environment")

    def test_resolution_source_declares_no_installer(self) -> None:
        """The resolution path spawns no subprocess at all, so it cannot install."""
        source = (PEC_SCRIPTS / "pec/exec_env.py").read_text(encoding="utf-8")
        resolve = source[source.index("def _discover_python(") : source.index("def _existing_venv")]
        self.assertNotIn("subprocess.run", resolve, "resolution spawns a process")
        self.assertNotIn("_provision_consumer_project", resolve, "resolution provisions")
        # `uv` may only be reached from the one function allowed to build.
        provision = source[source.index("def _provision_consumer_project(") :]
        self.assertIn("shutil.which(\"uv\")", provision)
        before_provision = source[: source.index("def _provision_consumer_project(")]
        self.assertNotIn("shutil.which(\"uv\")", before_provision)

    def test_exec_env_provisions_once_per_environment_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = self._project(Path(raw))
            calls: list[int] = []

            def fake_provision(cwd: Path):
                calls.append(1)
                return self._fake_venv(cwd)

            with unittest.mock.patch.object(
                self.exec_env, "is_consumer_task_worktree", return_value=True
            ):
                with unittest.mock.patch.object(
                    self.exec_env, "_provision_consumer_project", fake_provision
                ):
                    # prepare, then validation x5, then controller verification x2
                    for _ in range(8):
                        self.exec_env.ensure_exec_env(project)

            self.assertEqual(len(calls), 1, "environment was rebuilt for unchanged declarations")

    def test_multiple_validations_reuse_provisioned_environment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = self._project(Path(raw))
            python = self._fake_venv(project)
            self.exec_env._provision_receipt(project).write_text(
                json.dumps(
                    {
                        "schema": self.exec_env.ENV_RECEIPT_SCHEMA,
                        "fingerprint": self.exec_env.environment_fingerprint(project),
                    }
                ),
                encoding="utf-8",
            )
            with unittest.mock.patch.object(
                self.exec_env, "is_consumer_task_worktree", return_value=True
            ):
                with unittest.mock.patch.object(
                    self.exec_env, "_provision_consumer_project"
                ) as provision:
                    for _ in range(5):
                        resolved = self.exec_env.ensure_exec_env(project)

            provision.assert_not_called()
            self.assertEqual(resolved.python, python.resolve())

    def test_controller_verification_reuses_worker_environment(self) -> None:
        """Both sides resolve the same interpreter without either rebuilding it."""
        with tempfile.TemporaryDirectory() as raw:
            project = self._project(Path(raw))
            python = self._fake_venv(project)
            with unittest.mock.patch.object(
                self.exec_env, "is_consumer_task_worktree", return_value=True
            ):
                with unittest.mock.patch.object(
                    self.exec_env, "_provision_consumer_project"
                ) as provision:
                    worker_side = self.exec_env.resolve_exec_env(project)
                    controller_side = self.exec_env.resolve_exec_env(project)

            provision.assert_not_called()
            self.assertEqual(worker_side.python, controller_side.python)
            self.assertEqual(controller_side.python, python.resolve())

    def test_lockfile_change_reprovisions_environment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = self._project(Path(raw))
            calls: list[str] = []

            def fake_provision(cwd: Path):
                calls.append(self.exec_env.environment_fingerprint(cwd))
                return self._fake_venv(cwd)

            with unittest.mock.patch.object(
                self.exec_env, "is_consumer_task_worktree", return_value=True
            ):
                with unittest.mock.patch.object(
                    self.exec_env, "_provision_consumer_project", fake_provision
                ):
                    self.exec_env.ensure_exec_env(project)
                    self.exec_env.ensure_exec_env(project)
                    (project / "uv.lock").write_text("version = 2\n", encoding="utf-8")
                    self.exec_env.ensure_exec_env(project)

            self.assertEqual(len(calls), 2, "a changed lockfile must rebuild the environment")
            self.assertNotEqual(calls[0], calls[1])

    def test_no_machine_specific_interpreter_rewrite(self) -> None:
        """Commands stay repository-portable; the environment resolves python3."""
        for path in (
            PEC_SCRIPTS / "pec/exec_env.py",
            PE_ROOT / "scripts/run_campaign.py",
            PE_ROOT / "scripts/launchability.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn('"python3.12"', source, msg=f"{path} pins a machine interpreter")
            self.assertNotIn("python3 -> python3.1", source)
