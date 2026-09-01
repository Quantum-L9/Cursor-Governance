from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    cleanup_worktree,
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

    def test_semantic_prohibition_is_not_matched_as_a_path(self) -> None:
        """W8/S1: an architecture law must not be globbed against filenames.

        Such a rule used to ship in ``path_or_pattern`` and reach this gate,
        where a ContractError fallback substring-matched the sentence against
        each changed path. It never matched, so the gate reported PASS having
        enforced nothing - and would have reported FAIL had a path ever
        happened to contain the words. A semantic prohibition now carries no
        ``path_or_pattern`` at all, so it cannot decide this gate either way.
        """
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = temp / "blueprint"
            make_blueprint(blueprint)
            dnb_path = blueprint / "DO_NOT_BUILD.yaml"
            dnb = yaml.safe_load(dnb_path.read_text(encoding="utf-8"))
            dnb["prohibited_primary_paths"] = [
                {
                    "id": "DNB-001",
                    "kind": "semantic",
                    "statement": "a second Program Execution runtime or Controller",
                    "reason": "the existing Controller is the sole runtime authority",
                    "detection": "review_and_conformance",
                    "exception_authority": "NONE",
                },
                {
                    # A real path prohibition alongside it, on a directory this
                    # attempt does not touch, so the only thing that could turn
                    # the gate red is the semantic entry above.
                    "id": "DNB-002",
                    "kind": "path",
                    "path_or_pattern": "vendor/**",
                    "reason": "fixture prohibition on an untouched directory",
                    "detection": "controller_verify",
                    "exception_authority": "NONE",
                },
            ]
            dnb_path.write_text(yaml.safe_dump(dnb, sort_keys=False), encoding="utf-8")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint))
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
                verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
                self.assertEqual(
                    verification["gates"]["do_not_build"],
                    "PASS",
                    "a semantic prohibition must not decide a path gate",
                )
            finally:
                cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
