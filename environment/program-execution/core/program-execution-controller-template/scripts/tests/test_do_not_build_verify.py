from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    cleanup_worktree,
    establish_runtime_readiness,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
)


class DoNotBuildVerifyTest(unittest.TestCase):
    def test_verify_fails_when_changed_path_is_prohibited(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            establish_runtime_readiness(temp)
            blueprint = temp / "blueprint"
            make_blueprint(blueprint)
            dnb_path = blueprint / "DO_NOT_BUILD.yaml"
            dnb = yaml.safe_load(dnb_path.read_text(encoding="utf-8"))
            dnb["prohibited_primary_paths"] = [
                {
                    "id": "DNB-001",
                    "path_or_pattern": "docs/result.txt",
                    "reason": "fixture prohibition",
                    "detection": "controller_verify",
                    "exception_authority": "NONE",
                }
            ]
            dnb_path.write_text(yaml.safe_dump(dnb, sort_keys=False), encoding="utf-8")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli(
                "bootstrap",
                "--workspace",
                str(workspace),
                "--blueprint",
                str(blueprint),
            )
            run_cli(
                "reconcile",
                "--workspace",
                str(workspace),
                "--repository",
                f"repo-a={repo}",
            )
            try:
                register_contract(temp, workspace)
                prepare_attempt(temp, workspace)
                verification = run_cli(
                    "verify",
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                )
                self.assertEqual(verification["gates"]["do_not_build"], "FAIL")
            finally:
                cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
