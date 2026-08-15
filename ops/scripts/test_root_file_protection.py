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
        {"path": "MMM.md", "tier": "managed", "rule": "managed"},
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
    (repo / "MMM.md").write_text("keep\nedit\ndrop\n", encoding="utf-8")
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

    def test_managed_overwrite_and_deletion_are_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            # Rewrite one line and delete another — no marker — must NOT be a violation.
            (repo / "MMM.md").write_text("keep\nREWRITTEN\n", encoding="utf-8")
            commit(repo, "edit managed file freely")
            self.assertEqual(self._findings(repo, base).get("MMM.md"), "exempt")

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

    def test_unregistered_new_root_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "NEWFILE.md").write_text("brand new\n", encoding="utf-8")
            commit(repo, "add an unregistered new root file")
            self.assertIn(
                "NEWFILE.md", rp.added_root_files_outside_policy(repo, base, "HEAD", CONFIG)
            )
            # A new root file not registered in the policy must fail the gate.
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 1)

    def test_rename_into_root_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            (repo / "sub").mkdir()
            (repo / "sub" / "x.md").write_text("nested content here\n", encoding="utf-8")
            commit(repo, "add a nested file")
            base2 = git(repo, "rev-parse", "HEAD")
            git(repo, "mv", "sub/x.md", "MOVEDIN.md")
            commit(repo, "move a nested file into the repo root")
            self.assertIn(
                "MOVEDIN.md", rp.added_root_files_outside_policy(repo, base2, "HEAD", CONFIG)
            )

    def test_new_root_file_registered_in_config_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "NEWFILE.md").write_text("brand new\n", encoding="utf-8")
            updated = json.loads(json.dumps(CONFIG))
            updated["protected_files"].append(
                {"path": "NEWFILE.md", "tier": "managed", "rule": "managed"}
            )
            (repo / "ops" / "config" / "root-file-protection.json").write_text(
                json.dumps(updated), encoding="utf-8"
            )
            commit(repo, "add new root file and register it in the policy")
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 0)

    def test_main_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nX\n", encoding="utf-8")
            commit(repo, "additive")
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 0)
            (repo / "AAA.md").write_text("alpha\nZ\ngamma\nX\n", encoding="utf-8")
            commit(repo, "overwrite without justification")
            self.assertEqual(rp.main(["--base", base, "--repo", str(repo)]), 1)

    # --- Inventory-complete reconciliation (P2-11) ---

    def test_inventory_clean_repo_reconciles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            unreg, stale = rp.reconcile_root_inventory(repo, CONFIG)
            self.assertEqual((unreg, stale), ([], []))

    def test_inventory_flags_preexisting_unregistered_root_file(self) -> None:
        # A root file that predates any diff and was never registered must fail,
        # even when nothing in the current change touches it (base == head).
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            (repo / "SNEAKY.md").write_text("never classified\n", encoding="utf-8")
            commit(repo, "pre-existing unregistered root file")
            unreg, _ = rp.reconcile_root_inventory(repo, CONFIG)
            self.assertIn("SNEAKY.md", unreg)
            self.assertEqual(rp.main(["--base", "HEAD", "--repo", str(repo)]), 1)

    def test_inventory_flags_stale_registry_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            cfg = json.loads(json.dumps(CONFIG))
            cfg["protected_files"].append(
                {"path": "GHOST.json", "tier": "regenerable", "rule": "regenerable"}
            )
            (repo / "ops" / "config" / "root-file-protection.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )
            commit(repo, "register a path that is not a tracked root file")
            _, stale = rp.reconcile_root_inventory(repo, cfg)
            self.assertIn("GHOST.json", stale)
            self.assertEqual(rp.main(["--base", "HEAD", "--repo", str(repo)]), 1)

    def test_inventory_exempt_root_file_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            cfg = json.loads(json.dumps(CONFIG))
            cfg["exempt_root_files"] = ["scratch.txt"]
            (repo / "scratch.txt").write_text("exempt on purpose\n", encoding="utf-8")
            (repo / "ops" / "config" / "root-file-protection.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )
            commit(repo, "exempt root file")
            unreg, stale = rp.reconcile_root_inventory(repo, cfg)
            self.assertEqual((unreg, stale), ([], []))

    def test_inventory_case_sensitive(self) -> None:
        # Registry casing must match git exactly; a case drift is a mismatch.
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_repo(Path(tmp))
            cfg = json.loads(json.dumps(CONFIG))
            cfg["protected_files"].append(
                {"path": "Notes.md", "tier": "managed", "rule": "managed"}
            )
            (repo / "notes.md").write_text("lowercase on disk\n", encoding="utf-8")
            (repo / "ops" / "config" / "root-file-protection.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )
            commit(repo, "case-mismatched registration")
            unreg, stale = rp.reconcile_root_inventory(repo, cfg)
            self.assertIn("notes.md", unreg)  # tracked, lowercase, unregistered
            self.assertIn("Notes.md", stale)  # registered, mixed-case, not tracked


if __name__ == "__main__":
    unittest.main()
