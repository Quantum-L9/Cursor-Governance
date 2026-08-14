#!/usr/bin/env python3
"""Regression suite for the make pr gate's dirtiness classification and writer
attribution.

The bug this guards against: pre-commit reports "files were modified by this
hook" for any tree change inside a hook's wall-clock window, the gate died on
that exit code before it could classify anything, and an agent then spent a
cycle auditing a read-only validator. Each test below pins one link in that
chain.

Fixtures are throwaway git repos under pytest's tmp_path; nothing writes into
the real workspace.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "ops" / "scripts"
CLASSIFY = SCRIPTS / "classify_generated_dirtiness.sh"
ATTRIBUTE = SCRIPTS / "attribute_tree_writers.sh"
LOG_LIB = SCRIPTS / "lib" / "precommit_log.sh"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, env=merged, capture_output=True, text=True)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A git repo that mirrors the governance layout the gate scripts expect."""
    repo = tmp_path / "ws"
    (repo / "rules").mkdir(parents=True)
    (repo / "ops" / "config").mkdir(parents=True)
    (repo / "ops" / "scripts").mkdir(parents=True)
    (repo / "WIP").mkdir()

    # The classifier resolves "generated" through the real implementation, so the
    # fixture only needs the files those helpers read.
    (repo / "rules" / "RULES-MANIFEST.yaml").write_text("rules: []\n", encoding="utf-8")
    (repo / "rules" / "authored.mdc").write_text("# authored\n", encoding="utf-8")
    (repo / "WIP" / "notes.md").write_text("scratch\n", encoding="utf-8")
    (repo / "ops" / "config" / "root-file-protection.json").write_text(
        json.dumps({"protected_files": [{"path": "AGENTS.md", "tier": "canonical"}]}),
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text("# agents\n", encoding="utf-8")

    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "test")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture")
    return repo


def snapshot(repo: Path, path: Path) -> Path:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    )
    path.write_text(result.stdout, encoding="utf-8")
    return path


def classify(repo: Path, before: Path) -> subprocess.CompletedProcess:
    after = before.parent / "after.txt"
    snapshot(repo, after)
    return run(["bash", str(CLASSIFY), str(repo), str(before), str(after)], cwd=repo)


class TestDirtinessClassification:
    def test_generated_only_dirt_is_tolerated(self, fixture_repo: Path, tmp_path: Path) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "rules" / "RULES-MANIFEST.yaml").write_text("rules: [a]\n", encoding="utf-8")

        result = classify(fixture_repo, before)

        assert result.returncode == 0, result.stdout
        assert "GENERATED_NEW_DIRTY" in result.stdout

    def test_scratch_dirt_is_tolerated(self, fixture_repo: Path, tmp_path: Path) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "WIP" / "new.md").write_text("scratch\n", encoding="utf-8")

        result = classify(fixture_repo, before)

        assert result.returncode == 0, result.stdout
        assert "SCRATCH_NEW_DIRTY" in result.stdout

    def test_authored_dirt_fails_and_names_the_path(
        self, fixture_repo: Path, tmp_path: Path
    ) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "rules" / "authored.mdc").write_text("# edited\n", encoding="utf-8")

        result = classify(fixture_repo, before)

        assert result.returncode == 1
        assert "rules/authored.mdc" in result.stdout

    def test_protected_root_file_is_not_generated(
        self, fixture_repo: Path, tmp_path: Path
    ) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "AGENTS.md").write_text("# agents\nmore\n", encoding="utf-8")

        result = classify(fixture_repo, before)

        assert result.returncode == 1
        assert "AGENTS.md" in result.stdout


class TestPrecommitLogParsing:
    """pre-commit's two verdicts must never be conflated."""

    def parse(self, tmp_path: Path, log_text: str, function: str) -> str:
        log = tmp_path / "precommit.log"
        log.write_text(log_text, encoding="utf-8")
        result = run(
            ["bash", "-c", f'. "{LOG_LIB}"; {function} "{log}"'],
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    MODIFIED_ONLY = (
        "symlinks check.........................Failed\n"
        "- hook id: symlinks-check\n"
        "- duration: 12.5s\n"
        "- files were modified by this hook\n"
    )
    REAL_FAILURE = (
        "rules check............................Failed\n"
        "- hook id: rules-check\n"
        "- duration: 0.4s\n"
        "- exit code: 1\n"
    )

    def test_modified_files_is_not_reported_as_a_failure(self, tmp_path: Path) -> None:
        assert self.parse(tmp_path, self.MODIFIED_ONLY, "precommit_failed_hooks") == ""
        assert self.parse(tmp_path, self.MODIFIED_ONLY, "precommit_blamed_hooks") == "symlinks-check"

    def test_exit_code_is_reported_with_its_hook(self, tmp_path: Path) -> None:
        assert self.parse(tmp_path, self.REAL_FAILURE, "precommit_failed_hooks") == "rules-check 1"
        assert self.parse(tmp_path, self.REAL_FAILURE, "precommit_blamed_hooks") == ""

    def test_each_verdict_is_attributed_to_its_own_hook(self, tmp_path: Path) -> None:
        combined = self.MODIFIED_ONLY + self.REAL_FAILURE
        assert self.parse(tmp_path, combined, "precommit_failed_hooks") == "rules-check 1"
        assert self.parse(tmp_path, combined, "precommit_blamed_hooks") == "symlinks-check"


class TestWriterAttribution:
    def attribute(
        self, repo: Path, before: Path, log: Path, home: Path
    ) -> tuple[subprocess.CompletedProcess, dict]:
        result = run(
            ["bash", str(ATTRIBUTE), str(repo), str(before), str(log)],
            cwd=repo,
            env={"PR_ATTRIBUTE_REPLAY": "0", "HOME": str(home)},
        )
        receipt_path = repo / ".l9" / "pr" / "gate-dirtiness.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        return result, receipt

    def test_untracked_only_churn_is_not_a_hook_modification(
        self, fixture_repo: Path, tmp_path: Path
    ) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "WIP" / "appeared.md").write_text("new\n", encoding="utf-8")
        log = tmp_path / "precommit.log"
        log.write_text("- hook id: symlinks-check\n", encoding="utf-8")

        result, receipt = self.attribute(fixture_repo, before, log, tmp_path)

        assert result.returncode == 0, result.stderr
        assert receipt["untracked_only"] is True
        assert "cannot have produced" in result.stdout
        assert [entry["path"] for entry in receipt["changed"]] == ["WIP/appeared.md"]

    def test_tracked_change_is_reported_with_its_classification(
        self, fixture_repo: Path, tmp_path: Path
    ) -> None:
        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "rules" / "authored.mdc").write_text("# edited\n", encoding="utf-8")
        log = tmp_path / "precommit.log"
        log.write_text(
            "- hook id: symlinks-check\n- files were modified by this hook\n", encoding="utf-8"
        )

        result, receipt = self.attribute(fixture_repo, before, log, tmp_path)

        assert result.returncode == 0, result.stderr
        assert receipt["untracked_only"] is False
        assert receipt["blamed_hooks"] == ["symlinks-check"]
        entry = next(e for e in receipt["changed"] if e["path"] == "rules/authored.mdc")
        assert entry["tracked"] is True
        assert entry["classification"] == "source"

    def test_concurrent_writer_is_named_by_the_lock_ledger(
        self, fixture_repo: Path, tmp_path: Path
    ) -> None:
        """The scenario that caused the original misdiagnosis: another process
        held the repo-write lock and wrote while a read-only hook was running."""
        home = tmp_path / "home"
        (home / ".cursor").mkdir(parents=True)
        lock_lib = SCRIPTS / "lib" / "repo_write_lock.sh"
        holder = run(
            [
                "bash",
                "-c",
                f'. "{lock_lib}"; L9_REPO_WRITE_LOCK_LABEL=install_ide_profile '
                f'repo_write_lock_acquire "{fixture_repo}" 0; repo_write_lock_holder "{fixture_repo}"',
            ],
            cwd=fixture_repo,
            env={"HOME": str(home)},
        )
        assert "install_ide_profile" in holder.stdout

        before = snapshot(fixture_repo, tmp_path / "before.txt")
        (fixture_repo / "rules" / "authored.mdc").write_text("# concurrent\n", encoding="utf-8")
        log = tmp_path / "precommit.log"
        log.write_text(
            "- hook id: symlinks-check\n- files were modified by this hook\n", encoding="utf-8"
        )

        result, _ = self.attribute(fixture_repo, before, log, home)

        assert "install_ide_profile" in result.stdout
        assert "repo-write lock ledger" in result.stdout


def test_hook_contract_covers_every_configured_hook() -> None:
    result = run(
        [sys.executable, str(SCRIPTS / "validate_precommit_hook_contract.py")], cwd=REPO_ROOT
    )
    assert result.returncode == 0, result.stdout


def test_hook_contract_fails_closed_on_an_undeclared_hook(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "ops" / "config").mkdir(parents=True)
    (root / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n      - id: brand-new-hook\n", encoding="utf-8"
    )
    (root / "ops" / "config" / "precommit-hook-contract.json").write_text(
        json.dumps({"version": 1, "hooks": {}}), encoding="utf-8"
    )

    result = run(
        [sys.executable, str(SCRIPTS / "validate_precommit_hook_contract.py"), "--root", str(root)],
        cwd=REPO_ROOT,
    )

    assert result.returncode == 1
    assert "brand-new-hook" in result.stdout
