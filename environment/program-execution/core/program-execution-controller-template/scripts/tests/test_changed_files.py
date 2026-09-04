from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli


class ChangedFilesTest(unittest.TestCase):
    def test_declared_changed_files_must_equal_observed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace, declared_changed=["docs/not-result.txt"])
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            self.assertEqual(verification["gates"]["changed_files_exact"], "FAIL")
            run_cli(
                "release-lease",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "test cleanup",
                "--actor",
                "test",
            )
            cleanup_worktree(repo, workspace)


class RenameEntryTests(unittest.TestCase):
    """`git status --porcelain=v1 -z` lists a rename as `R  <new>\0<old>\0`."""

    def test_rename_reports_both_the_new_and_the_old_path(self) -> None:
        import subprocess
        import sys
        from tempfile import TemporaryDirectory

        from helpers import SCRIPTS

        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        from pec.controller import _changed_paths

        with TemporaryDirectory() as raw:
            repo = Path(raw)
            identity = ["-c", "user.email=t@example.com", "-c", "user.name=t"]
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "allowed").mkdir()
            (repo / "allowed" / "f.py").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "allowed"], check=True)
            subprocess.run(["git", *identity, "-C", str(repo), "commit", "-qm", "seed"], check=True)
            (repo / "forbidden").mkdir()
            subprocess.run(
                ["git", "-C", str(repo), "mv", "allowed/f.py", "forbidden/evil.py"], check=True
            )
            self.assertEqual(_changed_paths(repo), ["allowed/f.py", "forbidden/evil.py"])


if __name__ == "__main__":
    unittest.main()
