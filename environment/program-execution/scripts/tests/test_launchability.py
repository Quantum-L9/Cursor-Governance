"""Launchability, validation inference, and one execution environment.

Together these cover the conditions that used to survive every preparation
stage and only surface long after bootstrap had frozen the blueprint.
"""

from __future__ import annotations

import hashlib
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
        # Canonical per task-cards.schema.json:
        # program_control | repo_local | external_adapter | read_only.
        # This fixture said "repo_change", which the schema does not accept, so
        # every test built on it asserted a vocabulary nothing else speaks.
        "execution_kind": "repo_local",
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
                ["python3 -m pytest tests/test_rule_loader.py --tb=short -q --no-cov"],
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
                    "tests/ops/scripts/test_multi_agent_main_bound.py --tb=short -q --no-cov"
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
                ["python3 -m pytest pkg/tests/test_widget.py --tb=short -q --no-cov"],
            )

    def test_declared_validation_overrides_inference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            task = _task(validation=[{"method": "command", "command_or_inspection": "make check"}])
            report = launchability.check_tasks([task], Path(raw), infer=True)
            self.assertTrue(report["launchable"])
            self.assertNotIn("TASK-001", report["synthesized_validations"])

    def test_inspection_kinds_do_not_require_executable_validation(self) -> None:
        """`read_only` is the canonical inspection kind; "analysis" is not one."""
        with tempfile.TemporaryDirectory() as raw:
            report = launchability.check_tasks(
                [_task(execution_kind="read_only", outputs=[])], Path(raw), infer=False
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
                blueprint, {"TASK-001": ["test -s 'docs/result.md'"]}, validate=False
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

            launchability.apply_synthesized_validations(
                blueprint, {"TASK-001": ["make check"]}, validate=False
            )

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
                blueprint, {"TASK-001": ["python3 -m pytest -q"]}, validate=False
            )

            self.assertEqual(changed, [])
            self.assertEqual(self._written(blueprint), [declared])

    def test_nothing_is_written_when_nothing_was_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = self._cards(Path(raw), [_task()])
            before = (blueprint / "TASK_CARDS.yaml").read_bytes()

            self.assertEqual(
                launchability.apply_synthesized_validations(blueprint, {}, validate=False), []
            )
            self.assertEqual((blueprint / "TASK_CARDS.yaml").read_bytes(), before)


class DefinitionStatusNormalizationTest(unittest.TestCase):
    """Ordering intent must not become a state the controller cannot leave."""

    def test_blocked_with_dependency_edges_compiles_as_ready(self) -> None:
        src = {
            "tasks": [
                {"id": "TASK-001", "definition_status": "ready"},
                {"id": "TASK-002", "definition_status": "blocked"},
            ],
            "dependency_edges": [{"from": "TASK-001", "to": "TASK-002"}],
        }
        notes = compile_source.normalize_definition_status(src)
        self.assertEqual(src["tasks"][1]["definition_status"], "ready")
        self.assertTrue(any("compiled as 'ready'" in note for note in notes))

    def test_a_task_local_dependency_alias_carries_no_ordering(self) -> None:
        """The alias never made a task ready; only `dependency_edges` does.

        A source declaring one is refused outright by `_semantic_precheck`
        before reaching here. This proves the alias is also inert at the
        ordering decision itself, so neither layer can be the one that lets a
        second DAG representation drive readiness.
        """
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
        with self.assertRaises(compile_source.CompileError) as ctx:
            compile_source.normalize_definition_status(src)
        self.assertIn("unclaimable", str(ctx.exception))

        with self.assertRaises(compile_source.CompileError) as alias_ctx:
            compile_source._semantic_precheck(
                {
                    "targets": [{"id": "TARGET-001", "repository_id": "org/repo"}],
                    "tasks": [
                        {
                            "id": "TASK-002",
                            "definition_status": "ready",
                            "dependency_ids": ["TASK-001"],
                        }
                    ],
                }
            )
        self.assertIn("dependency_ids", str(alias_ctx.exception))

    def test_blocked_without_dependencies_refuses_compilation(self) -> None:
        # ADR-0023: a blocked task with nothing to wait on is a runtime
        # dead-end; the compiler fails instead of emitting it.
        src = {"tasks": [{"id": "TASK-001", "definition_status": "blocked"}]}
        with self.assertRaises(compile_source.CompileError) as ctx:
            compile_source.normalize_definition_status(src)
        self.assertIn("unclaimable", str(ctx.exception))


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

    def _identity_files(self, root: Path) -> None:
        for rel in self.exec_env._GOVERNANCE_IDENTITY:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("identity\n", encoding="utf-8")

    def test_governance_identity_uses_donor_and_never_calls_uv(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "gov"
            self._identity_files(root)
            (root / "pyproject.toml").write_text("[tool.uv]\npackage = false\n", encoding="utf-8")
            donor = Path(raw) / "donor"
            (donor / ".venv" / "bin").mkdir(parents=True)
            (donor / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
            donor_py = donor / ".venv" / "bin" / "python3"
            donor_py.write_text("#!/bin/sh\n", encoding="utf-8")
            donor_py.chmod(0o755)
            env = {"GOV_TOOLCHAIN_ROOT": str(donor), "L9_PE_PYTHON": "", "VIRTUAL_ENV": ""}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "is_consumer_task_worktree", return_value=True
                ):
                    with unittest.mock.patch.object(
                        self.exec_env.subprocess, "run", side_effect=AssertionError("uv")
                    ):
                        resolved = self.exec_env.resolve_exec_env(root)
            self.assertEqual(resolved.python, (donor / ".venv").resolve() / "bin" / "python3")

    def test_governance_identity_without_a_donor_names_the_override(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "gov"
            self._identity_files(root)
            env = {"L9_PE_PYTHON": "", "GOV_TOOLCHAIN_ROOT": "", "VIRTUAL_ENV": ""}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "_donor_toolchain_python", return_value=None
                ):
                    with self.assertRaises(self.exec_env.ExecEnvError) as caught:
                        self.exec_env.resolve_exec_env(root)
            self.assertIn("L9_PE_PYTHON", str(caught.exception))

    def test_package_false_does_not_provision_with_uv(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "pyproject.toml").write_text("[tool.uv]\npackage = false\n", encoding="utf-8")
            env = {"L9_PE_PYTHON": "", "VIRTUAL_ENV": ""}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(
                    self.exec_env, "is_consumer_task_worktree", return_value=True
                ):
                    with unittest.mock.patch.object(
                        self.exec_env.subprocess, "run", side_effect=AssertionError("uv")
                    ):
                        resolved = self.exec_env._discover_python(root)
            self.assertEqual(resolved, self.exec_env._keep_venv_shim(Path(sys.executable)))

    def test_package_false_syncs_dependencies_without_installing_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            project.mkdir()
            (project / "pyproject.toml").write_text(
                "[tool.uv]\npackage = false\n", encoding="utf-8"
            )
            runtime = Path(raw) / "runtime"
            seen: list[list[str]] = []

            def fake_run(cmd, **kwargs):
                seen.append(list(cmd))
                python = runtime / ".venv" / "bin" / "python3"
                python.parent.mkdir(parents=True, exist_ok=True)
                python.write_text("#!/bin/sh\n", encoding="utf-8")
                self.assertEqual(kwargs["env"]["UV_PROJECT_ENVIRONMENT"], str(runtime / ".venv"))
                return subprocess.CompletedProcess(cmd, 0, "", "")

            with unittest.mock.patch.object(self.exec_env, "exec_env_root", return_value=runtime):
                with unittest.mock.patch.object(self.exec_env.shutil, "which", return_value="uv"):
                    with unittest.mock.patch.object(
                        self.exec_env.subprocess, "run", side_effect=fake_run
                    ):
                        resolved = self.exec_env._consumer_project_python(project)
            self.assertEqual(seen[0][1:3], ["sync", "--no-install-project"])
            self.assertEqual(resolved, (runtime / ".venv" / "bin" / "python3").resolve())

    def test_failed_editable_install_is_not_the_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            project.mkdir()
            (project / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            runtime = Path(raw) / "runtime"

            def fake_run(cmd, **kwargs):
                if cmd[1] == "venv":
                    python = runtime / ".venv" / "bin" / "python3"
                    python.parent.mkdir(parents=True, exist_ok=True)
                    python.write_text("#!/bin/sh\n", encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, "", "")
                return subprocess.CompletedProcess(cmd, 1, "", "install failed")

            with unittest.mock.patch.object(self.exec_env, "exec_env_root", return_value=runtime):
                with unittest.mock.patch.object(self.exec_env.shutil, "which", return_value="uv"):
                    with unittest.mock.patch.object(
                        self.exec_env.subprocess, "run", side_effect=fake_run
                    ):
                        with self.assertRaises(self.exec_env.ExecEnvError) as caught:
                            self.exec_env._consumer_project_python(project)
            self.assertIn("not adopted", str(caught.exception))


class RenderedPlanCampaignTest(unittest.TestCase):
    """A rendered .plan.md validates once and does not re-enter the judgment stages."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.run_campaign = _load(
            "run_campaign_rendered_plan_test", PE_ROOT / "scripts/run_campaign.py"
        )

    def _plan(self, root: Path, *, rendered_by: str | None = None) -> Path:
        source = root / "CAMPAIGN_SOURCE.yaml"
        blueprint = root / "blueprint"
        blueprint.mkdir()
        (blueprint / "PROGRAM.yaml").write_text(
            "program:\n  id: rendered-proof\n  definition_status: draft\n",
            encoding="utf-8",
        )
        producer = rendered_by or "skills/l9-plan/scripts/render_campaign_source.py"
        source.write_text(
            "schema: l9.program-execution.campaign-source.v2\n"
            "metadata:\n"
            "  campaign_id: rendered-proof\n"
            f"  rendered_by: {producer}\n"
            "program:\n"
            "  id: rendered-proof\n"
            "targets:\n"
            "  - repository_id: Quantum-L9/Cursor-Governance\n"
            "tasks: []\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        (blueprint / "MANIFEST.yaml").write_text(
            f"source_sha256: {digest}\nfiles: []\n",
            encoding="utf-8",
        )
        plan = root / "demo.plan.md"
        plan.write_text(
            "---\n"
            "name: demo\n"
            f"campaign_source: {source}\n"
            f"campaign_source_sha256: {digest}\n"
            f"campaign_blueprint: {blueprint}\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        return plan

    def test_rendered_plan_validates_then_starts_without_the_judgment_stages(self) -> None:
        runner = self.run_campaign
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = self._plan(root)
            called = {"runtime": 0}

            def runtime(run):
                called["runtime"] += 1
                self.assertEqual(run.blueprint, root / "blueprint")
                self.assertIn("validate_blueprint", run.report.stages_completed)
                self.assertNotIn("stack_proof", run.report.stages_completed)
                program = (root / "blueprint" / "PROGRAM.yaml").read_text(encoding="utf-8")
                self.assertIn("accepted", program)
                return run.report

            def refused(*_args, **_kwargs):
                raise AssertionError("judgment stage ran")

            env = {"L9_PE_OPERATOR_INVOCATION": f"make campaign {plan}"}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(runner, "_stage_runtime", side_effect=runtime):
                    with unittest.mock.patch.object(runner, "check_launchability", refused):
                        with unittest.mock.patch.object(runner, "default_plan_window", refused):
                            with unittest.mock.patch.object(
                                runner, "default_compile_activation", refused
                            ):
                                with unittest.mock.patch.object(runner, "default_admit", refused):
                                    with unittest.mock.patch.object(
                                        runner, "default_context7_stack", refused
                                    ):
                                        report = runner._run_campaign_stages(
                                            plan,
                                            until="execute",
                                            repo_root=root,
                                            l9_root=root / "l9",
                                            hooks=runner.Hooks(
                                                validate_blueprint=lambda _blueprint: []
                                            ),
                                        )
            self.assertEqual(called["runtime"], 1)
            self.assertEqual(report.mode, "rendered-plan")
            self.assertEqual(report.stages_completed[:2], ["validate_blueprint", "accept"])

    def test_a_plan_without_recorded_paths_names_l9_plan(self) -> None:
        runner = self.run_campaign
        with tempfile.TemporaryDirectory() as raw:
            plan = Path(raw) / "bare.plan.md"
            plan.write_text("---\nname: bare\n---\n\n", encoding="utf-8")
            env = {"L9_PE_OPERATOR_INVOCATION": f"make campaign {plan}"}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with self.assertRaises(runner.CampaignError) as caught:
                    runner._run_campaign_stages(plan, until="execute", l9_root=Path(raw) / "l9")
            self.assertIn("/l9-plan", str(caught.exception))

    def test_validation_errors_do_not_stamp_or_start(self) -> None:
        runner = self.run_campaign
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = self._plan(root)

            def runtime(_run):
                raise AssertionError("runtime started")

            env = {"L9_PE_OPERATOR_INVOCATION": f"make campaign {plan}"}
            with unittest.mock.patch.dict("os.environ", env, clear=False):
                with unittest.mock.patch.object(runner, "_stage_runtime", side_effect=runtime):
                    with self.assertRaises(runner.CampaignError) as caught:
                        runner._run_campaign_stages(
                            plan,
                            until="execute",
                            l9_root=root / "l9",
                            hooks=runner.Hooks(validate_blueprint=lambda _blueprint: ["broken"]),
                        )
            self.assertIn("template validate failed", str(caught.exception))
            program = (root / "blueprint" / "PROGRAM.yaml").read_text(encoding="utf-8")
            self.assertIn("draft", program)
            self.assertNotIn("accepted", program)


if __name__ == "__main__":
    unittest.main()
