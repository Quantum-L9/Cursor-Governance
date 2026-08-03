#!/usr/bin/env python3
"""Tests for the repo-root append-only protection gate.

Offline; builds throwaway git repositories under a temp dir and never touches the
real tree or the network. Runnable directly (`python ops/scripts/test_root_file_protection.py`)
and collectable by root pytest. The module under test is loaded by file path so it
imports whether run standalone or from the repository root.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        msg = f"cannot load module: {name}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rp = _load("validate_root_file_protection")

CONFIG = {
    "schema_version": "1.0.0",
    "protected_files": [
        {"path": "AAA.md", "tier": "canonical", "rule": "additive_only"},
        {"path": "BBB.md", "tier": "canonical", "rule": "additive_only"},
        {"path": "gen.lock", "tier": "regenerable", "rule": "regenerable"},
    ],
}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def init_repo(tmp: Path) -> tuple[Path, str]:
    repo = tmp
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "ops" / "config").mkdir(parents=True)
    (repo / "ops" / "config" / "root-file-protection.json").write_text(
        json.dumps(CONFIG), encoding="utf-8"
    )
    (repo / "AAA.md").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (repo / "BBB.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (repo / "gen.lock").write_text("locked = 1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo, git(repo, "rev-parse", "HEAD")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


class RootProtectionTests(unittest.TestCase):
    def _findings(self, repo: Path, base: str) -> dict[str, str]:
        findings = rp.check(repo, CONFIG, base, "HEAD")
        return {f["path"]: f["verdict"] for f in findings}

    def test_pure_addition_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nDELTA\n", encoding="utf-8")
            commit(repo, "append to AAA")
            self.assertEqual(self._findings(repo, base).get("AAA.md"), "ok")

    def test_overwrite_without_justification_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nCHANGED\ngamma\n", encoding="utf-8")
            commit(repo, "rewrite line in AAA")
            self.assertEqual(self._findings(repo, base).get("AAA.md"), "violation")

    def test_deletion_without_justification_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "BBB.md").write_text("one\nthree\n", encoding="utf-8")
            commit(repo, "drop a line from BBB")
            self.assertEqual(self._findings(repo, base).get("BBB.md"), "violation")

    def test_overwrite_with_justification_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "BBB.md").write_text("one\nTWO\nthree\n", encoding="utf-8")
            commit(
                repo, "fix BBB\n\nALLOW-ROOT-DELETION: BBB.md - corrects a typo, proof in issue 9"
            )
            self.assertEqual(self._findings(repo, base).get("BBB.md"), "justified")

    def test_regenerable_wholesale_rewrite_is_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "gen.lock").write_text("locked = 2\nregenerated = true\n", encoding="utf-8")
            commit(repo, "regenerate lock")
            self.assertEqual(self._findings(repo, base).get("gen.lock"), "exempt")

    def test_justification_for_wrong_path_does_not_excuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "BBB.md").write_text("one\nthree\n", encoding="utf-8")
            commit(repo, "drop BBB line\n\nALLOW-ROOT-DELETION: AAA.md - unrelated marker")
            self.assertEqual(self._findings(repo, base).get("BBB.md"), "violation")

    def test_marker_without_reason_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "BBB.md").write_text("one\nthree\n", encoding="utf-8")
            commit(repo, "drop BBB line\n\nALLOW-ROOT-DELETION: BBB.md")
            self.assertEqual(self._findings(repo, base).get("BBB.md"), "violation")

    def test_unchanged_files_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nMORE\n", encoding="utf-8")
            commit(repo, "touch AAA only")
            findings = self._findings(repo, base)
            self.assertNotIn("BBB.md", findings)
            self.assertNotIn("gen.lock", findings)

    def test_new_root_file_is_advisory_not_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "NEWFILE.md").write_text("brand new\n", encoding="utf-8")
            commit(repo, "add a new root file")
            advisories = rp.added_root_files_outside_policy(repo, base, "HEAD", CONFIG)
            self.assertIn("NEWFILE.md", advisories)
            self.assertEqual(self._findings(repo, base), {})

    def test_main_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nX\n", encoding="utf-8")
            commit(repo, "additive")
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 0)
            (repo / "AAA.md").write_text("alpha\nZ\ngamma\nX\n", encoding="utf-8")
            commit(repo, "overwrite without justification")
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 1)


if __name__ == "__main__":
    unittest.main()
