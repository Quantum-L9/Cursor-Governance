"""The trusted replay's data-only bundle extraction fails closed on every non-regular entry."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO / "tools/authority/extract_bundle_data.py"
TRUSTED = REPO / ".github/workflows/l9-architecture-intelligence-trusted-replay.yml"
ROOT = "generated/governance/architecture_intelligence"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@invalid", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class Subject:
    """An untrusted repository whose commit carries a bundle directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir()
        _git(root, "init", "-q")
        self.bundle = root / ROOT
        (self.bundle / "projections").mkdir(parents=True)
        (self.bundle / "bundle.lock.json").write_text('{"schema": "x"}\n')
        (self.bundle / "projections/a.projection.json").write_text('{"a": 1}\n')

    def commit(self) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "subject")
        return _git(self.root, "rev-parse", "HEAD")


def _extract(subject: Subject, commit: str, dest: Path, path: str = ROOT) -> tuple[int, dict]:
    completed = subprocess.run(
        [
            sys.executable,
            str(EXTRACTOR),
            "--git-dir",
            str(subject.root),
            "--commit",
            commit,
            "--path",
            path,
            "--dest",
            str(dest),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return completed.returncode, json.loads(completed.stdout)


def _refused(result: tuple[int, dict], reason: str, dest: Path) -> dict:
    code, report = result
    assert (code, report["status"], report["reason"]) == (1, "REFUSED", reason), report
    assert not dest.exists(), "a refused extraction must write nothing"
    return report


@pytest.fixture
def subject(tmp_path: Path) -> Subject:
    return Subject(tmp_path / "subject")


def test_regular_bundle_is_extracted_byte_for_byte(subject: Subject, tmp_path: Path) -> None:
    commit = subject.commit()
    dest = tmp_path / "out"
    code, report = _extract(subject, commit, dest)
    assert (code, report["status"], report["files"]) == (0, "EXTRACTED", 2), report
    for rel in ("bundle.lock.json", "projections/a.projection.json"):
        assert (dest / rel).read_bytes() == (subject.bundle / rel).read_bytes()
        assert stat.S_IMODE((dest / rel).stat().st_mode) == 0o644
        assert not (dest / rel).is_symlink()


@pytest.mark.parametrize("target", ["../../../../etc/passwd", "bundle.lock.json", "/etc/passwd"])
def test_symlink_is_refused(subject: Subject, tmp_path: Path, target: str) -> None:
    (subject.bundle / "projections/link.projection.json").symlink_to(target)
    report = _refused(
        _extract(subject, subject.commit(), tmp_path / "out"), "NON_REGULAR_ENTRY", tmp_path / "out"
    )
    assert report["detail"]["entries"][0]["mode"] == "120000"


def test_gitlink_is_refused(subject: Subject, tmp_path: Path) -> None:
    subject.commit()
    foreign = _git(subject.root, "rev-parse", "HEAD")
    _git(subject.root, "update-index", "--add", "--cacheinfo", f"160000,{foreign},{ROOT}/vendored")
    _git(subject.root, "commit", "-q", "-m", "gitlink")
    commit = _git(subject.root, "rev-parse", "HEAD")
    report = _refused(
        _extract(subject, commit, tmp_path / "out"), "NON_REGULAR_ENTRY", tmp_path / "out"
    )
    assert report["detail"]["entries"][0] == {
        "path": f"{ROOT}/vendored",
        "mode": "160000",
        "type": "commit",
    }


def test_executable_file_is_refused(subject: Subject, tmp_path: Path) -> None:
    script = subject.bundle / "projections/run.sh"
    script.write_text("#!/bin/sh\necho pwned\n")
    script.chmod(0o755)
    report = _refused(
        _extract(subject, subject.commit(), tmp_path / "out"), "NON_REGULAR_ENTRY", tmp_path / "out"
    )
    assert report["detail"]["entries"][0]["mode"] == "100755"


def test_bundle_root_that_is_a_symlink_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "subject"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "real").mkdir()
    (root / "real/bundle.lock.json").write_text("{}\n")
    (root / "generated/governance").mkdir(parents=True)
    (root / ROOT).symlink_to("../../real")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "symlinked root")
    subject = Subject.__new__(Subject)
    subject.root = root
    _refused(
        _extract(subject, _git(root, "rev-parse", "HEAD"), tmp_path / "out"),
        "NON_REGULAR_ENTRY",
        tmp_path / "out",
    )


def test_bundle_below_a_symlinked_ancestor_is_refused_as_absent(tmp_path: Path) -> None:
    root = tmp_path / "subject"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "elsewhere/governance/architecture_intelligence").mkdir(parents=True)
    (root / "elsewhere/governance/architecture_intelligence/bundle.lock.json").write_text("{}\n")
    (root / "generated").symlink_to("elsewhere")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "symlinked ancestor")
    subject = Subject.__new__(Subject)
    subject.root = root
    _refused(
        _extract(subject, _git(root, "rev-parse", "HEAD"), tmp_path / "out"),
        "BUNDLE_ABSENT",
        tmp_path / "out",
    )


def test_absent_bundle_is_refused(subject: Subject, tmp_path: Path) -> None:
    commit = subject.commit()
    _refused(
        _extract(subject, commit, tmp_path / "out", path="generated/nothing"),
        "BUNDLE_ABSENT",
        tmp_path / "out",
    )


@pytest.mark.parametrize("path", ["../outside", "/etc", "generated/../etc", "a//b", ""])
def test_unsafe_path_argument_is_refused(subject: Subject, tmp_path: Path, path: str) -> None:
    _refused(
        _extract(subject, subject.commit(), tmp_path / "out", path=path),
        "UNSAFE_PATH",
        tmp_path / "out",
    )


@pytest.mark.parametrize(
    ("commit", "reason"),
    [("not-a-sha", "COMMIT_MALFORMED"), ("0" * 40, "GIT_OBJECT_UNRESOLVED")],
)
def test_bad_commit_is_refused(subject: Subject, tmp_path: Path, commit: str, reason: str) -> None:
    subject.commit()
    _refused(_extract(subject, commit, tmp_path / "out"), reason, tmp_path / "out")


def test_existing_destination_is_refused(subject: Subject, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir()
    code, report = _extract(subject, subject.commit(), dest)
    assert (code, report["reason"]) == (1, "DESTINATION_EXISTS")
    assert list(dest.iterdir()) == []


def test_trusted_workflow_reads_pull_requests_only_as_data() -> None:
    workflow = yaml.safe_load(TRUSTED.read_text())
    triggers = workflow[True] if True in workflow else workflow["on"]
    assert "pull_request" not in triggers, "a pull_request trigger would run PR-controlled code"
    text = TRUSTED.read_text()
    assert "tar -x" not in text and "git archive" not in text
    assert "tools/authority/extract_bundle_data.py" in text
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            with_ = step.get("with") or {}
            if "secrets.GH_TOKEN" in json.dumps(step):
                # The credential appears only on the private compiler checkout, never persisted.
                assert step["uses"].startswith("actions/checkout@")
                assert with_["repository"] == "Quantum-L9/l9-semantic-compiler-engine"
                assert with_["persist-credentials"] is False
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                ref = str(with_.get("ref", ""))
                assert "pull_request.head" not in ref, "the pull request head is never checked out"
            if str(step.get("uses", "")).startswith("actions/upload-artifact@"):
                assert str(with_["path"]).endswith("attestation.json"), (
                    "only the attestation uploads"
                )
