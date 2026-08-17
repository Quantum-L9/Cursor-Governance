from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "replay_campaign.py"


def _load() -> object:
    spec = importlib.util.spec_from_file_location("replay_campaign_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def _commit(path: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", message], check=True, capture_output=True
    )
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class ReplayCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()

    def test_function_span_and_hold_back(self) -> None:
        base = "def keep():\n    return 1\n\ndef later():\n    return 0\n"
        ported = "def keep():\n    return 1\n\ndef later():\n    return 9\n"
        held = self.mod.hold_back_functions(ported, base, ("later",))
        self.assertIn("return 0", held)
        self.assertNotIn("return 9", held)

    def test_materialize_copies_declared_paths_and_holds_later_functions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.mkdir()
            _git_init(target)
            (target / "shared.py").write_text(
                "def early():\n    return 1\n\ndef late():\n    return 0\n"
            )
            (target / "only.py").write_text("only\n")
            _commit(target, "base")
            (target / "shared.py").write_text(
                "def early():\n    return 2\n\ndef late():\n    return 9\n"
            )
            (target / "only.py").write_text("only-new\n")
            ref = _commit(target, "tip")

            workspace = root / "workspace"
            worktree = workspace / "worktrees" / "TASK-001"
            worktree.mkdir(parents=True)
            _git_init(worktree)
            (worktree / "shared.py").write_text(
                "def early():\n    return 1\n\ndef late():\n    return 0\n"
            )
            (worktree / "only.py").write_text("only\n")
            _commit(worktree, "task-base")
            contract = workspace / "contracts" / "rendered" / "TASK-001.json"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                json.dumps({"writable_paths": ["shared.py", "only.py"]}) + "\n",
                encoding="utf-8",
            )

            result = self.mod.materialize_task(
                workspace=workspace,
                task_id="TASK-001",
                target=target,
                ref=ref,
                hold_back={"TASK-001": {"shared.py": ("late",)}},
            )
            self.assertEqual(sorted(result["ported"]), ["only.py", "shared.py"])
            self.assertEqual(result["missing"], [])
            self.assertEqual(result["held_back"], ["late"])
            shared = (worktree / "shared.py").read_text(encoding="utf-8")
            self.assertIn("return 2", shared)
            self.assertIn("return 0", shared)
            self.assertNotIn("return 9", shared)
            self.assertEqual((worktree / "only.py").read_text(encoding="utf-8"), "only-new\n")

    def test_regenerate_manifest_rewrites_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            manifest = root / "MANIFEST.json"
            manifest.write_text(
                json.dumps({"files": [{"path": "a.txt", "sha256": "deadbeef"}]}, indent=1) + "\n",
                encoding="utf-8",
            )
            self.mod.regenerate_manifest(manifest)
            document = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertNotEqual(document["files"][0]["sha256"], "deadbeef")
            self.assertEqual(len(document["files"][0]["sha256"]), 64)

    def test_first_incomplete_task_skips_completed(self) -> None:
        original = self.mod.pec_status_tasks
        self.mod.pec_status_tasks = lambda _workspace: [
            {"id": "TASK-001", "runtime_state": "COMPLETED"},
            {"id": "TASK-002", "runtime_state": "LEASED"},
        ]
        try:
            self.assertEqual(self.mod.first_incomplete_task(Path("/tmp")), "TASK-002")
        finally:
            self.mod.pec_status_tasks = original

    def test_reset_retires_runtime_and_rewinds_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            l9 = root / "l9"
            live = l9 / "programs" / "demo"
            live.mkdir(parents=True)
            (live / "runtime").mkdir()
            (live / "runtime" / "LAUNCH.json").write_text("{}\n", encoding="utf-8")
            target = root / "target"
            target.mkdir()
            _git_init(target)
            (target / "a.txt").write_text("old\n", encoding="utf-8")
            base = _commit(target, "base")
            (target / "a.txt").write_text("new\n", encoding="utf-8")
            _commit(target, "tip")
            subprocess.run(
                ["git", "-C", str(target), "branch", "pec/w0/task-001"],
                check=True,
                capture_output=True,
            )
            isolate = root / "isolate"
            isolate.mkdir()
            intent = root / "intent.yaml"
            intent.write_text("campaign_id: demo\n", encoding="utf-8")

            armed: list[str] = []

            def fake_until(
                _intent: Path, until: str, *, isolate: Path
            ) -> subprocess.CompletedProcess[str]:
                armed.append(until)
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="arm\n", stderr="")

            self.mod.run_campaign_until = fake_until
            result = self.mod.reset_campaign(
                campaign_id="demo",
                isolate=isolate,
                target=target,
                base=base,
                intent=intent,
                l9_root=l9,
            )
            self.assertEqual(armed, ["arm"])
            self.assertFalse(live.exists())
            self.assertTrue(Path(result["retired"]).is_dir())
            head = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(head, base)
            branches = subprocess.run(
                ["git", "-C", str(target), "branch", "--format=%(refname:short)"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn("pec/w0/task-001\n", branches + "\n")
            self.assertTrue(
                any(name.startswith("retired/pec-w0-task-001-") for name in branches.splitlines())
            )


if __name__ == "__main__":
    unittest.main()
