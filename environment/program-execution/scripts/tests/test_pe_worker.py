"""Worker handoff: unmodified trees fail closed; already-modified trees do not."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/pe_worker.py"


def _load():
    spec = importlib.util.spec_from_file_location("pe_worker_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PeWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()

    def _repo(self, root: Path) -> Path:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        )
        return head.stdout.strip()

    def test_unmodified_tree_without_worker_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": ["ops/scripts/resolve_stack_tip.py"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertFalse(outcome.changed)
            self.assertEqual(outcome.reason, "no_worker_configured")

    def test_worker_binding_defaults_to_cursor_foreground(self) -> None:
        env = {key: value for key, value in os.environ.items() if key != "L9_PE_WORKER_CMD"}
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            binding = self.mod.worker_binding()
        self.assertEqual(binding["adapter"], "cursor-foreground")
        self.assertEqual(binding["mode"], "peer_session")
        self.assertIsNone(binding["command"])

    def test_unexecuted_peer_message_does_not_require_setting_worker_cmd(self) -> None:
        outcome = self.mod.WorkerOutcome(
            invoked=False,
            changed=False,
            reason="no_worker_configured",
            detail="brief written",
        )
        env = {key: value for key, value in os.environ.items() if key != "L9_PE_WORKER_CMD"}
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            message = self.mod.unexecuted_task_message(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                outcome,
                Path("/tmp/task-001"),
            )
        self.assertIn("cursor-foreground", message)
        self.assertIn("error, not a warning", message)
        self.assertIn("rerun `make campaign`", message)
        self.assertIn("Do not set L9_PE_WORKER_CMD unless", message)

    def test_workspace_wiring_links_are_not_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            (worktree / ".cursor-commands").symlink_to(Path.home() / ".cursor-governance")
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": ["app/engines/handlers.py"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertFalse(outcome.changed)
            self.assertEqual(outcome.reason, "no_worker_configured")

    def test_tracked_cursor_rules_count_as_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            rules = worktree / ".cursor" / "rules"
            rules.mkdir(parents=True)
            (rules / "local.mdc").write_text("# consumer rule\n", encoding="utf-8")
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": [".cursor/rules/local.mdc"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertTrue(outcome.changed)
            self.assertEqual(outcome.reason, "worktree_already_modified")

    def test_already_modified_tree_counts_as_work(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            workspace = Path(raw) / "ws"
            worktree.mkdir()
            base = self._repo(worktree)
            (worktree / "ops" / "scripts").mkdir(parents=True)
            (worktree / "ops" / "scripts" / "resolve_stack_tip.py").write_text(
                "print('tip')\n", encoding="utf-8"
            )
            outcome = self.mod.invoke_worker(
                {"id": "TASK-001", "execution_kind": "repo_local"},
                {"base_sha": base, "writable_paths": ["ops/scripts/resolve_stack_tip.py"]},
                worktree,
                workspace=workspace,
                command="",
            )
            self.assertTrue(outcome.changed)
            self.assertEqual(outcome.reason, "worktree_already_modified")


if __name__ == "__main__":
    raise SystemExit(unittest.main())


class ChangedPathSemanticsTest(unittest.TestCase):
    """Worker and controller must judge a changed path by the same rule.

    The controller suppressed `.cursor/rules/`, `.cursor/governance/`,
    `.claude/` and `.vscode/` wholesale because PE drops generated links
    nearby. A task whose whole deliverable was a tracked `.cursor/rules/*` file
    therefore reported an unmodified worktree, and scope verification never saw
    the change it exists to judge.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()
        cls.wiring = cls.mod.workspace_wiring()
        scripts = PE_ROOT / "core/program-execution-controller-template/scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from pec import controller as pec_controller  # noqa: PLC0415 - path set above

        cls.controller = pec_controller

    def test_generated_cursor_wiring_is_ignored(self) -> None:
        for path in (
            ".cursor-commands",
            ".cursor-commands/commands/plan.md",
            ".cursor/plans",
            ".cursor/plans/draft.md",
            ".cursor/governance/CANONICAL_LAW.md",
        ):
            self.assertTrue(
                self.wiring.is_generated_workspace_wiring(path, Path(".")),
                msg=f"{path} is generated by ensure_workspace_wired",
            )

    def test_tracked_cursor_rule_is_counted(self) -> None:
        self.assertFalse(
            self.wiring.is_generated_workspace_wiring(".cursor/rules/security.mdc", Path("."))
        )

    def test_tracked_claude_file_is_counted(self) -> None:
        self.assertFalse(
            self.wiring.is_generated_workspace_wiring(".claude/project-settings", Path("."))
        )

    def test_tracked_vscode_file_is_counted(self) -> None:
        self.assertFalse(
            self.wiring.is_generated_workspace_wiring(".vscode/settings.json", Path("."))
        )

    def test_a_non_generated_cursor_governance_file_is_counted(self) -> None:
        """Only the CANONICAL_LAW symlink is generated in that directory."""
        self.assertFalse(
            self.wiring.is_generated_workspace_wiring(".cursor/governance/notes.md", Path("."))
        )

    def test_controller_and_worker_share_one_definition(self) -> None:
        """Not "the same rule" by inspection -- literally the same predicate."""
        self.assertEqual(
            self.controller.product_paths.__globals__["GENERATED_LINK_ROOTS"],
            self.wiring.GENERATED_LINK_ROOTS,
        )
        source = (
            PE_ROOT / "core/program-execution-controller-template/scripts/pec/controller.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("WIRING_PREFIXES", source)
        self.assertNotIn('".vscode/"', source)

    def test_out_of_scope_tracked_rule_fails_scope(self) -> None:
        self.assertEqual(
            self.wiring.relevant_changed_paths(
                [".cursor/rules/security.mdc"], ["docs/program-execution"], Path(".")
            ),
            [],
        )

    def test_declared_writable_rule_passes_scope(self) -> None:
        self.assertEqual(
            self.wiring.relevant_changed_paths(
                [".cursor/rules/security.mdc"], [".cursor/rules"], Path(".")
            ),
            [".cursor/rules/security.mdc"],
        )

    def test_an_exactly_declared_file_passes_scope(self) -> None:
        self.assertEqual(
            self.wiring.relevant_changed_paths(["docs/a.md"], ["docs/a.md"], Path(".")),
            ["docs/a.md"],
        )


class ImplementationDetectionTest(unittest.TestCase):
    """`HEAD != base_sha` is not evidence that *this* task was implemented."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()

    def _repo(self, root: Path) -> str:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def _commit(self, root: Path, rel: str, body: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        subprocess.run(["git", "add", "--", rel], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"add {rel}"], cwd=root, check=True, capture_output=True
        )

    def test_unrelated_preexisting_commit_does_not_count_as_task_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            worktree.mkdir()
            base = self._repo(worktree)
            # Someone else's commit already moved HEAD past the contract base.
            self._commit(worktree, "unrelated/other.md", "not this task\n")
            contract = {"base_sha": base, "writable_paths": ["docs/program-execution/TASK-001.md"]}

            self.assertFalse(self.mod.worktree_already_implements(worktree, contract))

    def test_committed_writable_change_counts_as_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            worktree.mkdir()
            base = self._repo(worktree)
            self._commit(worktree, "docs/program-execution/TASK-001.md", "real work\n")
            contract = {"base_sha": base, "writable_paths": ["docs/program-execution/TASK-001.md"]}

            self.assertTrue(self.mod.worktree_already_implements(worktree, contract))

    def test_dirty_writable_change_counts_as_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            worktree.mkdir()
            base = self._repo(worktree)
            target = worktree / "docs/program-execution/TASK-001.md"
            target.parent.mkdir(parents=True)
            target.write_text("uncommitted work\n", encoding="utf-8")
            contract = {"base_sha": base, "writable_paths": ["docs/program-execution"]}

            self.assertTrue(self.mod.worktree_already_implements(worktree, contract))

    def test_generated_wiring_does_not_count_as_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "wt"
            worktree.mkdir()
            base = self._repo(worktree)
            plans = worktree / ".cursor/plans"
            plans.mkdir(parents=True)
            (plans / "draft.md").write_text("generated\n", encoding="utf-8")
            contract = {"base_sha": base, "writable_paths": ["docs/program-execution"]}

            self.assertFalse(self.mod.worktree_already_implements(worktree, contract))
