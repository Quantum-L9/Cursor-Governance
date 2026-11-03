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
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

# CI inherits these; the gate then reads the live PR body and the missing-source
# test would pass. Isolate every case so local and Actions agree.
_CI_BODY_LEAKS = ("GITHUB_ACTIONS", "GITHUB_EVENT_PATH", "L9_PR_BODY")

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
    def setUp(self) -> None:
        self._saved_ci_env = {
            key: os.environ.pop(key) for key in _CI_BODY_LEAKS if key in os.environ
        }

    def tearDown(self) -> None:
        os.environ.update(self._saved_ci_env)

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

    def test_list_touched_additive_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nMORE\n", encoding="utf-8")
            commit(repo, "append AAA")
            self.assertEqual(
                rp.additive_only_touched(repo, CONFIG, base, "HEAD"),
                ["AAA.md"],
            )
            self.assertEqual(
                rp.main(["--base", base, "--repo", str(repo), "--list-touched-additive-only"]),
                0,
            )

    def test_template_stamp_required_when_body_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nMORE\n", encoding="utf-8")
            commit(repo, "append AAA")
            body = Path(tmp) / "body.md"
            body.write_text("## Summary\nno stamp\n", encoding="utf-8")
            self.assertEqual(
                rp.main(["--base", base, "--repo", str(repo), "--pr-body-file", str(body)]),
                1,
            )
            body.write_text(
                f"{rp.PROTECTED_ROOT_PR_STAMP}\n## Protected-root PR\n",
                encoding="utf-8",
            )
            self.assertEqual(
                rp.main(["--base", base, "--repo", str(repo), "--pr-body-file", str(body)]),
                0,
            )

    def test_template_not_required_without_additive_only_touch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "MMM.md").write_text("keep\nedit\nCHANGED\n", encoding="utf-8")
            commit(repo, "managed only")
            body = Path(tmp) / "body.md"
            body.write_text("ordinary PR body\n", encoding="utf-8")
            self.assertEqual(
                rp.main(["--base", base, "--repo", str(repo), "--pr-body-file", str(body)]),
                0,
            )

    def test_require_pr_body_fails_when_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_repo(Path(tmp))
            (repo / "AAA.md").write_text("alpha\nbeta\ngamma\nMORE\n", encoding="utf-8")
            commit(repo, "append AAA")
            self.assertEqual(
                rp.main(["--base", base, "--repo", str(repo), "--require-pr-body"]),
                1,
            )


# --- version-pin bumps (pin_bump) ---------------------------------------------

PIN_CONFIG = {
    "schema_version": "1.0.0",
    "protected_files": [
        {"path": "pyproject.toml", "tier": "canonical", "rule": "additive_only"},
        {"path": "OTHER.md", "tier": "canonical", "rule": "additive_only"},
        {"path": "uv.lock", "tier": "regenerable", "rule": "regenerable"},
    ],
    "pin_bump": {"files": ["pyproject.toml"], "lock": "uv.lock"},
}

PYPROJECT = """[project]
dependencies = [
    "langgraph>=0.2",
]

[project.optional-dependencies]
ui = [
    "playwright==1.64.0",
    "boto3>=1.34,<2",
]
# keep this comment
"""


def _lock(**versions: str) -> str:
    return "".join(f'[[package]]\nname = "{n}"\nversion = "{v}"\n\n' for n, v in versions.items())


def init_pin_repo(tmp: Path, *, with_lock: bool = True) -> tuple[Path, str]:
    repo = tmp
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "ops" / "config").mkdir(parents=True)
    config = dict(PIN_CONFIG)
    if not with_lock:
        config = {**PIN_CONFIG, "protected_files": PIN_CONFIG["protected_files"][:2]}
    (repo / "ops" / "config" / "root-file-protection.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    (repo / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (repo / "OTHER.md").write_text("one\ntwo\n", encoding="utf-8")
    if with_lock:
        (repo / "uv.lock").write_text(
            _lock(langgraph="1.2.16", playwright="1.64.0", boto3="1.43.1"), encoding="utf-8"
        )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo, git(repo, "rev-parse", "HEAD")


def bump(repo: Path, old: str, new: str) -> None:
    path = repo / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def relock(repo: Path, **versions: str) -> None:
    (repo / "uv.lock").write_text(_lock(**versions), encoding="utf-8")


class PinBumpTests(unittest.TestCase):
    """A version-pin bump is judged on its content, never on who made it."""

    def setUp(self) -> None:
        self._saved_ci_env = {
            key: os.environ.pop(key) for key in _CI_BODY_LEAKS if key in os.environ
        }

    def tearDown(self) -> None:
        os.environ.update(self._saved_ci_env)

    def _verdict(self, repo: Path, base: str, config: dict | None = None) -> str | None:
        findings = rp.check(repo, config or PIN_CONFIG, base, "HEAD")
        return {f["path"]: f["verdict"] for f in findings}.get("pyproject.toml")

    def test_exact_pin_bump_matching_lock_is_pin_bump(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "chore(deps): bump playwright")
            self.assertEqual(self._verdict(repo, base), "pin_bump")

    def test_range_bump_with_package_in_lock_is_pin_bump(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"boto3>=1.34,<2"', '"boto3>=1.35,<2"')
            commit(repo, "chore(deps): raise boto3 floor")
            self.assertEqual(self._verdict(repo, base), "pin_bump")

    def test_exact_pin_the_lock_does_not_resolve_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')  # lock still 1.64.0
            commit(repo, "bump without relock")
            self.assertEqual(self._verdict(repo, base), "violation")

    def test_pin_bump_plus_any_other_rewrite_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            bump(repo, "# keep this comment", "# rewritten comment")
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "bump and sneak an edit")
            self.assertEqual(self._verdict(repo, base), "violation")

    def test_pin_bump_plus_pure_addition_is_not_a_pin_bump(self) -> None:
        """Codex on #809: an added hunk beside a bump must keep the PR-body review."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            bump(repo, "# keep this comment\n", "# keep this comment\n[tool.extra]\nx = 1\n")
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "bump and append unrelated config")
            self.assertEqual(self._verdict(repo, base), "violation")
            os.environ["L9_PR_BODY"] = "no stamp"
            try:
                argv = ["--base", base, "--repo", str(repo), "--require-pr-body"]
                self.assertEqual(rp.main(argv), 1)
            finally:
                os.environ.pop("L9_PR_BODY", None)

    def test_renamed_package_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwrite==1.64.1"')
            relock(repo, langgraph="1.2.16", playwrite="1.64.1", boto3="1.43.1")
            commit(repo, "swap package")
            self.assertEqual(self._verdict(repo, base), "violation")

    def test_changed_operator_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright>=1.64.1"')
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "loosen pin")
            self.assertEqual(self._verdict(repo, base), "violation")

    def test_removed_dependency_is_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '    "boto3>=1.34,<2",\n', "")
            commit(repo, "drop a dependency")
            self.assertEqual(self._verdict(repo, base), "violation")

    def test_missing_lock_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp), with_lock=False)
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            commit(repo, "bump with no lock in repo")
            config = {**PIN_CONFIG, "protected_files": PIN_CONFIG["protected_files"][:2]}
            self.assertEqual(self._verdict(repo, base, config), "violation")

    def test_without_pin_bump_policy_the_rule_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "bump")
            config = {k: v for k, v in PIN_CONFIG.items() if k != "pin_bump"}
            self.assertEqual(self._verdict(repo, base, config), "violation")

    def test_marker_still_justifies_a_real_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, "# keep this comment", "# rewritten comment")
            commit(repo, "edit\n\nALLOW-ROOT-DELETION: pyproject.toml - reword, see issue 9")
            self.assertEqual(self._verdict(repo, base), "justified")

    def test_pin_bump_needs_no_protected_root_pr_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            commit(repo, "chore(deps): bump playwright")
            os.environ["L9_PR_BODY"] = "Dependabot body without the stamp"
            try:
                argv = ["--base", base, "--repo", str(repo), "--require-pr-body"]
                self.assertEqual(rp.main(argv), 0)
            finally:
                os.environ.pop("L9_PR_BODY", None)

    def test_other_additive_file_in_the_same_pr_still_needs_the_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = init_pin_repo(Path(tmp))
            bump(repo, '"playwright==1.64.0"', '"playwright==1.64.1"')
            relock(repo, langgraph="1.2.16", playwright="1.64.1", boto3="1.43.1")
            (repo / "OTHER.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
            commit(repo, "bump and append elsewhere")
            os.environ["L9_PR_BODY"] = "no stamp"
            try:
                argv = ["--base", base, "--repo", str(repo), "--require-pr-body"]
                self.assertEqual(rp.main(argv), 1)
            finally:
                os.environ.pop("L9_PR_BODY", None)

    def test_pin_bump_file_must_be_additive_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = init_pin_repo(Path(tmp))
            bad = {**PIN_CONFIG, "pin_bump": {"files": ["uv.lock"], "lock": "uv.lock"}}
            (repo / "ops" / "config" / "root-file-protection.json").write_text(
                json.dumps(bad), encoding="utf-8"
            )
            with self.assertRaises(rp.ProtectionError):
                rp.load_config(repo)


if __name__ == "__main__":
    unittest.main()
