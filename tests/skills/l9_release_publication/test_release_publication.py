"""Regression tests for skills/l9-release-publication scripts.

Local tag identity runs against real git repositories built in tmp_path; host
responses are replaced at the single `gh_api` seam, so no test touches GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "l9-release-publication" / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


detect = _load("detect_release_model")
tags = _load("verify_release_tag")
releases = _load("verify_github_release")

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_T = "c" * 40


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "--", "README.md")
    _git(root, "commit", "-q", "-m", "c1")
    _git(root, "remote", "add", "origin", "https://github.com/Org/repo.git")
    return root


def _run_main(module: ModuleType, argv: list[str], capsys) -> tuple[int, dict]:
    old = sys.argv
    sys.argv = [module.__name__, *argv]
    try:
        code = module.main()
    finally:
        sys.argv = old
    return code, json.loads(capsys.readouterr().out)


def _workflows(root: Path, files: dict[str, str]) -> Path:
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    for name, text in files.items():
        (wf / name).write_text(text, encoding="utf-8")
    return root


# ---- detect_release_model -------------------------------------------------------

TAG_PUBLISH = "on:\n  push:\n    tags: ['v*']\njobs:\n  p:\n    steps:\n      - run: echo publish\n"
BRANCH_TAGGER = (
    "on:\n  push:\n    branches: [main]\n    paths: [package.json]\n"
    'jobs:\n  r:\n    steps:\n      - run: git tag "v$V" "$GITHUB_SHA"\n'
    '      - run: gh release create "v$V" --verify-tag\n'
)
TAG_READER = (
    "on:\n  push:\n    branches: [main]\njobs:\n  x:\n    steps:\n"
    "      - run: git ls-remote --tags origin refs/tags/v1\n"
    "      - run: git tag --list 'v*'\n"
)


@pytest.mark.parametrize(
    ("files", "model", "tag_creator", "release_creator"),
    [
        ({"publish.yml": TAG_PUBLISH}, "TAG_TRIGGERED", "operator_admitted_tag", "agent"),
        ({"release.yml": BRANCH_TAGGER}, "MAIN_TAGGER", "workflow", "workflow"),
        ({"ci.yml": TAG_READER}, "NO_AUTOMATION", "agent", "agent"),
        ({}, "NO_AUTOMATION", "agent", "agent"),
    ],
)
def test_detect_models(tmp_path, capsys, files, model, tag_creator, release_creator):
    root = _workflows(tmp_path, files) if files else tmp_path
    code, out = _run_main(detect, ["--repo-dir", str(root)], capsys)
    assert code == 0
    assert (out["model"], out["tag_creator"], out["release_creator"]) == (
        model,
        tag_creator,
        release_creator,
    )


UNFILTERED_TAGGER_STEPS = 'jobs:\n  r:\n    steps:\n      - run: git tag "v$V" "$GITHUB_SHA"\n'


@pytest.mark.parametrize(
    "trigger",
    ["on: push\n", "on: [push]\n", "on:\n  push:\n", "on:\n  push:\n    paths: [package.json]\n"],
)
def test_detect_unfiltered_push_tagger_is_main_tagger(tmp_path, capsys, trigger):
    root = _workflows(tmp_path, {"release.yml": trigger + UNFILTERED_TAGGER_STEPS})
    code, out = _run_main(detect, ["--repo-dir", str(root)], capsys)
    assert code == 0
    assert (out["model"], out["tag_creator"]) == ("MAIN_TAGGER", "workflow")


def test_detect_tags_ignore_only_is_not_a_branch_tagger(tmp_path, capsys):
    text = "on:\n  push:\n    tags-ignore: ['nightly']\n" + UNFILTERED_TAGGER_STEPS
    root = _workflows(tmp_path, {"r.yml": text})
    code, out = _run_main(detect, ["--repo-dir", str(root)], capsys)
    assert code == 0 and out["model"] == "NO_AUTOMATION"


def test_detect_tag_push_job_that_creates_the_release(tmp_path, capsys):
    text = TAG_PUBLISH + '      - run: gh release create "$GITHUB_REF_NAME"\n'
    code, out = _run_main(
        detect, ["--repo-dir", str(_workflows(tmp_path, {"r.yml": text}))], capsys
    )
    assert code == 0 and out["release_creator"] == "workflow"


def test_detect_ambiguous_stops(tmp_path, capsys):
    root = _workflows(tmp_path, {"publish.yml": TAG_PUBLISH, "release.yml": BRANCH_TAGGER})
    code, out = _run_main(detect, ["--repo-dir", str(root)], capsys)
    assert code == 1 and out["model"] == "AMBIGUOUS"


def test_detect_unreadable_workflow_is_unknown(tmp_path, capsys):
    root = _workflows(tmp_path, {"bad.yml": "on: [push\n"})
    code, out = _run_main(detect, ["--repo-dir", str(root)], capsys)
    assert code == 1 and out["model"] == "UNKNOWN"


def test_detect_reads_version_authority(tmp_path, capsys):
    (tmp_path / "package.json").write_text('{"version": "4.3.0"}', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "2.0.0"\n', encoding="utf-8")
    _code, out = _run_main(detect, ["--repo-dir", str(tmp_path)], capsys)
    assert {"file": "package.json", "version": "4.3.0"} in out["version_authority"]
    assert {"file": "pyproject.toml", "version": "2.0.0"} in out["version_authority"]


# ---- verify_release_tag: local --------------------------------------------------


def test_local_annotated_match(repo, capsys):
    _git(repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    obj, commit = _git(repo, "rev-parse", "v1.0.0"), _git(repo, "rev-parse", "HEAD")
    argv = [
        "--repo-dir",
        str(repo),
        "--tag",
        "v1.0.0",
        "--tag-object",
        obj,
        "--peeled-commit",
        commit,
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 0 and out["status"] == "MATCH" and out["local_kind"] == "tag"


def test_local_lightweight_rejected_as_annotated(repo, capsys):
    _git(repo, "tag", "v1.0.0")
    commit = _git(repo, "rev-parse", "HEAD")
    argv = [
        "--repo-dir",
        str(repo),
        "--tag",
        "v1.0.0",
        "--tag-object",
        commit,
        "--peeled-commit",
        commit,
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 1 and out["status"] == "MISMATCH"


def test_local_lightweight_accepted_with_kind(repo, capsys):
    _git(repo, "tag", "v1.0.0")
    commit = _git(repo, "rev-parse", "HEAD")
    argv = [
        "--repo-dir",
        str(repo),
        "--tag",
        "v1.0.0",
        "--kind",
        "lightweight",
        "--peeled-commit",
        commit,
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 0 and out["status"] == "MATCH"


def test_local_tag_at_older_commit_is_mismatch(repo, capsys):
    _git(repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    obj = _git(repo, "rev-parse", "v1.0.0")
    (repo / "README.md").write_text("y\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "c2")
    head = _git(repo, "rev-parse", "HEAD")
    argv = [
        "--repo-dir",
        str(repo),
        "--tag",
        "v1.0.0",
        "--tag-object",
        obj,
        "--peeled-commit",
        head,
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 1 and out["status"] == "MISMATCH"


def test_bind_origin_rejects_other_repository(repo, capsys, monkeypatch):
    _git(repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    obj, commit = _git(repo, "rev-parse", "v1.0.0"), _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(tags, "gh_api", lambda path: pytest.fail("host must not be queried"))
    argv = [
        "--repo-dir",
        str(repo),
        "--tag",
        "v1.0.0",
        "--tag-object",
        obj,
        "--peeled-commit",
        commit,
        "--remote",
        "Org/other",
        "--bind-origin",
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 1 and out["detail"] == "origin is not the verified owner/name"


# ---- verify_release_tag: remote -------------------------------------------------


def _host(responses: dict[str, tuple[int, str, str]]):
    def fake(path: str) -> tuple[int, str, str]:
        return responses.get(path, (1, "", "gh: Not Found (HTTP 404)"))

    return fake


def _ref(kind: str, sha: str) -> tuple[int, str, str]:
    return 0, json.dumps({"object": {"type": kind, "sha": sha}}), ""


def test_remote_lightweight_match(monkeypatch, capsys):
    monkeypatch.setattr(
        tags, "gh_api", _host({"repos/Org/repo/git/ref/tags/v4.3.0": _ref("commit", SHA_A)})
    )
    argv = [
        "--remote",
        "Org/repo",
        "--tag",
        "v4.3.0",
        "--kind",
        "any",
        "--peeled-commit",
        SHA_A,
        "--require-remote",
    ]
    code, out = _run_main(tags, argv, capsys)
    assert code == 0 and out["remote_kind"] == "commit"


def test_remote_annotated_match_and_wrong_peel(monkeypatch, capsys):
    host = {
        "repos/Org/repo/git/ref/tags/v1.0.0": _ref("tag", SHA_T),
        f"repos/Org/repo/git/tags/{SHA_T}": (
            0,
            json.dumps({"object": {"type": "commit", "sha": SHA_A}}),
            "",
        ),
    }
    monkeypatch.setattr(tags, "gh_api", _host(host))
    base = ["--remote", "Org/repo", "--tag", "v1.0.0", "--tag-object", SHA_T, "--require-remote"]
    code, out = _run_main(tags, [*base, "--peeled-commit", SHA_A], capsys)
    assert code == 0 and out["status"] == "MATCH"
    code, out = _run_main(tags, [*base, "--peeled-commit", SHA_B], capsys)
    assert code == 1 and out["status"] == "MISMATCH"


def test_remote_absent_and_required(monkeypatch, capsys):
    monkeypatch.setattr(tags, "gh_api", _host({}))
    base = ["--remote", "Org/repo", "--tag", "v9.9.9", "--kind", "any", "--peeled-commit", SHA_A]
    code, out = _run_main(tags, base, capsys)
    assert code == 2 and out["status"] == "REMOTE_ABSENT"
    code, out = _run_main(tags, [*base, "--require-remote"], capsys)
    assert code == 1 and out["status"] == "MISMATCH"


def test_remote_forbidden_is_transport_blocked(monkeypatch, capsys):
    monkeypatch.setattr(tags, "gh_api", lambda path: (1, "", "gh: access not enabled (HTTP 403)"))
    argv = ["--remote", "Org/repo", "--tag", "v1.0.0", "--kind", "any", "--peeled-commit", SHA_A]
    code, out = _run_main(tags, argv, capsys)
    assert code == 3 and out["status"] == "TRANSPORT_BLOCKED"


def test_input_allowlist(capsys):
    code, out = _run_main(
        tags,
        ["--remote", "Org/repo", "--tag", "v1;rm", "--kind", "any", "--peeled-commit", SHA_A],
        capsys,
    )
    assert code == 1 and "allowlisted" in out["detail"]
    code, out = _run_main(
        tags, ["--remote", "Org/repo", "--tag", "v1", "--peeled-commit", SHA_A], capsys
    )
    assert code == 1 and "--tag-object" in out["detail"]


# ---- verify_github_release ------------------------------------------------------


def _release(**overrides) -> tuple[int, str, str]:
    record = {
        "tag_name": "v4.3.0",
        "draft": False,
        "prerelease": False,
        "html_url": "https://github.com/Org/repo/releases/tag/v4.3.0",
        "assets": [{"name": "pkg.tgz"}],
    }
    record.update(overrides)
    return 0, json.dumps(record), ""


def _release_host(release: tuple[int, str, str], major_sha: str = SHA_A):
    return _host(
        {
            "repos/Org/repo/git/ref/tags/v4.3.0": _ref("commit", SHA_A),
            "repos/Org/repo/git/ref/tags/v4": _ref("commit", major_sha),
            "repos/Org/repo/releases/tags/v4.3.0": release,
        }
    )


RELEASE_ARGV = ["--remote", "Org/repo", "--tag", "v4.3.0", "--peeled-commit", SHA_A]


def test_release_verified(monkeypatch, capsys):
    monkeypatch.setattr(tags, "gh_api", _release_host(_release()))
    code, out = _run_main(
        releases, [*RELEASE_ARGV, "--major-tag", "v4", "--require-asset", "pkg.tgz"], capsys
    )
    assert code == 0 and out["status"] == "RELEASE_VERIFIED"


@pytest.mark.parametrize(
    ("release", "extra", "fragment"),
    [
        (_release(draft=True), [], "draft"),
        (_release(prerelease=True), [], "prerelease"),
        (_release(assets=[]), ["--require-asset", "pkg.tgz"], "missing assets"),
        (_release(tag_name="v4.2.0"), [], "tag_name"),
    ],
)
def test_release_mismatches(monkeypatch, capsys, release, extra, fragment):
    monkeypatch.setattr(tags, "gh_api", _release_host(release))
    code, out = _run_main(releases, [*RELEASE_ARGV, *extra], capsys)
    assert code == 1 and fragment in out["detail"]


def test_major_tag_left_behind_is_mismatch(monkeypatch, capsys):
    monkeypatch.setattr(tags, "gh_api", _release_host(_release(), major_sha=SHA_B))
    code, out = _run_main(releases, [*RELEASE_ARGV, "--major-tag", "v4"], capsys)
    assert code == 1 and "v4 does not point" in out["detail"]


def test_release_absent(monkeypatch, capsys):
    monkeypatch.setattr(
        tags,
        "gh_api",
        _host({"repos/Org/repo/git/ref/tags/v4.3.0": _ref("commit", SHA_A)}),
    )
    code, out = _run_main(releases, RELEASE_ARGV, capsys)
    assert code == 2 and out["status"] == "RELEASE_ABSENT"


@pytest.mark.parametrize("assets", [["pkg.tgz", None], {"name": "pkg.tgz"}, "pkg.tgz"])
def test_malformed_release_assets_are_a_mismatch_not_a_crash(monkeypatch, capsys, assets):
    monkeypatch.setattr(tags, "gh_api", _release_host(_release(assets=assets)))
    code, out = _run_main(releases, [*RELEASE_ARGV, "--require-asset", "pkg.tgz"], capsys)
    assert code == 1 and "missing assets" in out["detail"]
    assert out["release"]["assets"] == []


def test_executable_outside_absolute_path_is_never_run_by_bare_name(monkeypatch, tmp_path):
    rogue = tmp_path / "git"
    rogue.write_text("#!/bin/sh\necho hijacked\n", encoding="utf-8")
    rogue.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", ".")
    assert tags._absolute("git") is None
    result = tags._run(["git", "--version"])
    assert result.returncode == 127 and "hijacked" not in result.stdout
