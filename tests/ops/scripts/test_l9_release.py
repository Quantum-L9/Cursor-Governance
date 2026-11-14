"""``make release`` — unit tests per stage, integration releases, refusal paths.

Integration tests release a throwaway repository to a local bare origin, with
``gh`` stubbed at the transport boundary (``release_fixtures.FAKE_GH``). The
builds are real: ``uv build`` (setuptools sdist + wheel) and ``npm pack``.
"""

from __future__ import annotations

import gzip
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l9_release  # noqa: E402
import release_declaration as decl  # noqa: E402
import release_reproducible as repro  # noqa: E402
from release_fixtures import python_project, release_env_fixture  # noqa: E402,F401

EXAMPLES = ROOT / "docs" / "examples" / "release"


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.release.json")))
def test_shipped_examples_conform_to_the_schema(example: Path) -> None:
    assert decl.schema_errors(json.loads(example.read_text())) == []


def test_examples_cover_topology_and_meta_injector() -> None:
    names = {path.name for path in EXAMPLES.glob("*.release.json")}
    assert names == {
        "l9-constellation-topology.release.json",
        "l9-meta-injector.release.json",
    }
    topology = json.loads((EXAMPLES / "l9-constellation-topology.release.json").read_text())
    injector = json.loads((EXAMPLES / "l9-meta-injector.release.json").read_text())
    assert topology["major_tag"] == "none"
    assert topology["ecosystems"][0]["kind"] == "python-uv"
    assert injector["major_tag"] == "advance"
    assert injector["ecosystems"][0]["kind"] == "node-npm"


def test_schema_rejects_unknown_fields_and_shell_strings() -> None:
    bad = {
        "schema": "l9.release/v1",
        "repository": "a/b",
        "ecosystems": [{"kind": "python-uv", "version_authority": "pyproject.toml"}],
        "artifacts": ["x.whl"],
        "major_tag": "none",
        "notes": {"changelog": "CHANGELOG.md"},
        "pre_release": {"argv": "make all"},
        "publish_to_pypi": True,
    }
    errors = decl.schema_errors(bad)
    assert any("publish_to_pypi" in error for error in errors)
    assert any(error.startswith("pre_release/argv") for error in errors)


def test_absent_declaration_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(decl.DeclarationError, match=r"\.l9/release\.json"):
        decl.load(tmp_path)


def test_declaration_paths_cannot_escape_the_repository(tmp_path: Path) -> None:
    (tmp_path / ".l9").mkdir()
    document = {
        "schema": "l9.release/v1",
        "repository": "a/b",
        "ecosystems": [{"kind": "node-npm", "version_authority": "../package.json"}],
        "artifacts": ["a.tgz"],
        "major_tag": "none",
        "notes": {"changelog": "CHANGELOG.md"},
    }
    (tmp_path / ".l9" / "release.json").write_text(json.dumps(document))
    with pytest.raises(decl.DeclarationError, match="escapes"):
        decl.load(tmp_path)


def test_version_authorities() -> None:
    assert decl.read_version("python-uv", '[project]\nversion = "3.0.0"\n') == "3.0.0"
    assert decl.read_version("node-npm", '{"version": "4.4.0"}') == "4.4.0"
    with pytest.raises(decl.DeclarationError, match="dynamic"):
        decl.read_version("python-uv", '[project]\ndynamic = ["version"]\n')
    with pytest.raises(decl.DeclarationError, match="MAJOR.MINOR.PATCH"):
        decl.read_version("node-npm", '{"version": "4.4"}')


def test_version_authorities_must_agree() -> None:
    declaration = decl.Declaration(
        repository="a/b",
        default_branch="main",
        ecosystems=(
            decl.Ecosystem("python-uv", "pyproject.toml"),
            decl.Ecosystem("node-npm", "package.json"),
        ),
        artifacts=("x",),
        major_tag="none",
        changelog="CHANGELOG.md",
    )
    files = {
        "pyproject.toml": '[project]\nversion = "1.0.0"\n',
        "package.json": '{"version":"1.0.1"}',
    }
    with pytest.raises(decl.DeclarationError, match="disagree"):
        decl.declared_version(declaration, files.__getitem__)


def test_changelog_section_requires_a_dated_heading() -> None:
    text = "# C\n\n## 3.0.0 - 2026-11-14\n\nBody line.\n\n## 2.0.0 - 2026-11-01\n\nOld.\n"
    assert decl.changelog_section(text, "3.0.0") == ("2026-11-14", "Body line.")
    with pytest.raises(decl.DeclarationError, match="no dated section"):
        decl.changelog_section("## 3.0.0\n\nundated\n", "3.0.0")
    with pytest.raises(decl.DeclarationError, match="no dated section"):
        decl.changelog_section(text, "3.0.1")


def test_exact_tags_exclude_major_tags() -> None:
    assert decl.exact_tag_version("v4.4.0") == (4, 4, 0)
    assert decl.exact_tag_version("v4") is None
    assert decl.exact_tag_version("v4.4.0-rc1") is None


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def _tar_gz(path: Path, members: dict[str, bytes], mtime: int, uid: int, order: list[str]) -> None:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in order:
            info = tarfile.TarInfo(name)
            info.size = len(members[name])
            info.mtime = mtime
            info.uid = uid
            info.uname = f"user{uid}"
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(members[name]))
    with gzip.GzipFile(filename=path.name, mode="wb", fileobj=path.open("wb"), mtime=mtime) as gz:
        gz.write(raw.getvalue())


def test_normalise_sdist_converges_envelopes_and_keeps_contents(tmp_path: Path) -> None:
    members = {"pkg-1.0/PKG-INFO": b"Name: pkg\n", "pkg-1.0/a.py": b"x = 1\n"}
    first, second = tmp_path / "a" / "pkg-1.0.tar.gz", tmp_path / "b" / "pkg-1.0.tar.gz"
    first.parent.mkdir()
    second.parent.mkdir()
    _tar_gz(first, members, 1_700_000_000, 501, sorted(members))
    _tar_gz(second, members, 1_700_000_999, 1000, sorted(members, reverse=True))
    assert repro.sha256_file(first) != repro.sha256_file(second)
    before = repro.member_digests(first)
    assert repro.normalise_sdist(first, 42) == before
    assert repro.normalise_sdist(second, 42) == before
    assert repro.sha256_file(first) == repro.sha256_file(second)
    header = first.read_bytes()[:10]
    assert header[4:8] == b"\x00\x00\x00\x00", "gzip header mtime must be 0"
    assert header[3] & 0x08 == 0, "gzip header must carry no file name"
    with tarfile.open(first) as tar:
        infos = tar.getmembers()
    assert [i.name for i in infos] == sorted(members)
    assert {(i.mtime, i.uid, i.gid, i.uname, i.gname) for i in infos} == {(42, 0, 0, "", "")}


def test_member_digests_see_content_changes(tmp_path: Path) -> None:
    one, two = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
    _tar_gz(one, {"p/a": b"1"}, 1, 0, ["p/a"])
    _tar_gz(two, {"p/a": b"2"}, 1, 0, ["p/a"])
    assert repro.member_digests(one) != repro.member_digests(two)


def test_sha256sums_is_sha256sum_check_compatible(tmp_path: Path) -> None:
    (tmp_path / "b.whl").write_bytes(b"wheel")
    (tmp_path / "a.tar.gz").write_bytes(b"sdist")
    repro.write_sha256sums(tmp_path, ["b.whl", "a.tar.gz"])
    lines = (tmp_path / "SHA256SUMS").read_text().splitlines()
    assert [line.split("  ")[1] for line in lines] == ["a.tar.gz", "b.whl"]
    check = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=tmp_path, check=False)
    assert check.returncode == 0


def test_setuptools_sdist_rebuilds_are_byte_identical_after_normalisation(
    tmp_path: Path,
) -> None:
    """The defect this command exists for: setuptools ignores SOURCE_DATE_EPOCH
    for sdist members, so two builds a second apart differ; normalisation of
    the envelope alone makes them identical without touching any member."""
    epoch = "1794678803"
    outs = []
    for label in ("a", "b"):
        src = tmp_path / f"src-{label}"
        src.mkdir()
        python_project(src, "1.0.0")
        out = tmp_path / f"out-{label}"
        subprocess.run(
            ["uv", "build", "--sdist", "--out-dir", str(out)],
            cwd=src,
            check=True,
            capture_output=True,
            env=l9_release.isolated_env({"SOURCE_DATE_EPOCH": epoch}),
        )
        outs.append(out / "acme_widget-1.0.0.tar.gz")
        time.sleep(1.1)
    first, second = outs
    assert repro.sha256_file(first) != repro.sha256_file(second), "envelope should differ"
    contents = repro.member_digests(first)
    assert repro.member_digests(second) == contents
    assert repro.normalise_sdist(first, int(epoch)) == contents
    assert repro.normalise_sdist(second, int(epoch)) == contents
    assert repro.sha256_file(first) == repro.sha256_file(second)


def test_isolated_env_drops_governance_make_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAKEFLAGS", "WS=/gov VERSION=1.0.0")
    monkeypatch.setenv("PYTHON", "/gov/.venv/bin/python")
    env = l9_release.isolated_env({"SOURCE_DATE_EPOCH": "1"})
    assert "MAKEFLAGS" not in env and "PYTHON" not in env
    assert env["SOURCE_DATE_EPOCH"] == "1"


@pytest.mark.parametrize(
    ("url", "slug"),
    [
        ("https://github.com/Quantum-L9/l9-meta-injector.git", "Quantum-L9/l9-meta-injector"),
        (
            "git@github.com:Quantum-L9/l9-constellation-topology.git",
            "Quantum-L9/l9-constellation-topology",
        ),
        ("https://github.com/acme/widget", "acme/widget"),
    ],
)
def test_github_origin_parsing(url: str, slug: str) -> None:
    match = l9_release._GITHUB_URL.match(url)
    assert match is not None and match.group("slug") == slug


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------
def _release(repo, *, version: str | None = None, dry_run: bool = False):
    return l9_release.execute(repo.workspace, requested=version, dry_run=dry_run)


def _slow_second_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the second clean build into a later second, so setuptools' sdist
    member mtimes really differ and normalisation is exercised end to end."""
    original = l9_release.checkout

    def checkout(workspace: Path, commit: str, dest: Path) -> Path:
        if dest.name == "build-b":
            time.sleep(1.1)
        return original(workspace, commit, dest)

    monkeypatch.setattr(l9_release, "checkout", checkout)


def test_python_uv_release_end_to_end(release_env, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = release_env("python-uv", "1.0.0")
    commit = repo.git("rev-parse", "HEAD")
    repo.authorize("v1.0.0", commit)
    _slow_second_checkout(monkeypatch)

    code, receipt = _release(repo, version="1.0.0")

    assert code == l9_release.EXIT_OK, receipt["detail"]
    assert receipt["status"] == "RELEASED"
    assert repo.remote_peeled("v1.0.0") == commit
    build = receipt["stages"]["build"]
    assert build["normalised"] == ["acme_widget-1.0.0.tar.gz"]
    sdist = build["artifacts"]["acme_widget-1.0.0.tar.gz"]
    assert sdist["raw"][0] != sdist["raw"][1]
    assert sdist["normalised"][0] == sdist["normalised"][1] == sdist["sha256"]
    assert sdist["member_contents_unchanged"] is True
    wheel = build["artifacts"]["acme_widget-1.0.0-py3-none-any.whl"]
    assert wheel["raw"][0] == wheel["raw"][1] and "normalised" not in wheel
    assert receipt["stages"]["tag"]["signed"] is False
    assert "unsigned" in receipt["stages"]["tag"]["note"]
    assert receipt["stages"]["verify"]["status"] == "PASS"
    assert receipt["stages"]["major_tag"] == {"policy": "none"}
    hosted = json.loads((repo.state / "releases" / "v1.0.0.json").read_text())
    assert "Release 1.0.0." in hosted["body"] and commit in hosted["body"]
    assert sorted(a["name"] for a in hosted["assets"]) == [
        "SHA256SUMS",
        "acme_widget-1.0.0-py3-none-any.whl",
        "acme_widget-1.0.0.tar.gz",
    ]
    on_disk = json.loads((repo.workspace / ".l9/release/release-receipt.json").read_text())
    assert on_disk["status"] == "RELEASED" and on_disk["commit"] == commit
    calls = (repo.state / "calls.log").read_text()
    assert "--verify-tag" in calls


def test_node_npm_release_creates_absent_major_tag(release_env) -> None:
    repo = release_env("node-npm", "1.0.0", major="advance")
    commit = repo.git("rev-parse", "HEAD")
    repo.authorize("v1.0.0", commit)

    code, receipt = _release(repo)

    assert code == l9_release.EXIT_OK, receipt["detail"]
    assert receipt["stages"]["major_tag"]["outcome"] == "CREATED"
    assert repo.remote_peeled("v1") == commit
    assert repo.remote_peeled("v1.0.0") == commit
    assert receipt["stages"]["build"]["normalised"] == []


def test_existing_major_tag_is_handed_to_the_operator(release_env) -> None:
    repo = release_env("node-npm", "1.0.0", major="advance")
    first = repo.git("rev-parse", "HEAD")
    repo.authorize("v1.0.0", first)
    assert _release(repo)[0] == l9_release.EXIT_OK

    node = json.loads((repo.workspace / "package.json").read_text())
    node["version"] = "1.1.0"
    (repo.workspace / "package.json").write_text(json.dumps(node, indent=2))
    (repo.workspace / "CHANGELOG.md").write_text("# C\n\n## 1.1.0 - 2026-11-15\n\n- More.\n")
    second = repo.commit_all("1.1.0")
    repo.authorize("v1.1.0", second)

    code, receipt = _release(repo)

    assert code == l9_release.EXIT_COMPLETION_REQUIRED
    major = receipt["stages"]["major_tag"]
    assert major["outcome"] == "OPERATOR_REQUIRED"
    assert major["operator_command"] == (
        f"git push --force-with-lease=refs/tags/v1:{first} origin {second}:refs/tags/v1"
    )
    assert repo.remote_peeled("v1") == first, "make release must never move an existing tag"
    assert repo.remote_peeled("v1.1.0") == second
    assert receipt["stages"]["verify"]["status"] == "PASS"


def test_dry_run_stops_before_publication(release_env) -> None:
    repo = release_env("node-npm", "2.0.0")
    code, receipt = _release(repo, dry_run=True)
    assert code == l9_release.EXIT_OK, receipt["detail"]
    assert receipt["status"] == "DRY_RUN_PASS"
    assert set(receipt["stages"]) >= {"preflight", "gate", "build"}
    assert "authorization" not in receipt["stages"] and "tag" not in receipt["stages"]
    assert repo.remote_peeled("v2.0.0") is None
    assert (repo.workspace / ".l9/release/v2.0.0/SHA256SUMS").is_file()
    assert not (repo.state / "releases").exists()


# ---------------------------------------------------------------------------
# Refusal paths
# ---------------------------------------------------------------------------
def test_refuses_without_declaration(release_env) -> None:
    repo = release_env("node-npm")
    (repo.workspace / ".l9" / "release.json").unlink()
    repo.commit_all("drop declaration")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_DECLARATION
    assert ".l9/release.json" in receipt["detail"]


def test_refuses_dirty_tree(release_env) -> None:
    repo = release_env("node-npm")
    (repo.workspace / "stray.txt").write_text("x")
    code, receipt = _release(repo)
    assert (code, receipt["status"]) == (l9_release.EXIT_REFUSED, "REFUSED")
    assert "not clean" in receipt["detail"]


def test_refuses_head_behind_origin(release_env) -> None:
    repo = release_env("node-npm")
    (repo.workspace / "index.js").write_text("module.exports = 2;\n")
    repo.commit_all("ahead")
    repo.git("reset", "-q", "--hard", "HEAD~1")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "is not freshly fetched origin/main" in receipt["detail"]


def test_refuses_open_prs(release_env) -> None:
    repo = release_env("node-npm")
    (repo.state / "open_prs").write_text("12\n17\n")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "2 open PR(s)" in receipt["detail"]


def test_refuses_version_mismatch(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    code, receipt = _release(repo, version="1.0.1")
    assert code == l9_release.EXIT_REFUSED
    assert "VERSION=1.0.1" in receipt["detail"]


def test_refuses_version_not_greater_than_latest_tag(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    repo.git("tag", "v1.2.0")
    repo.git("push", "-q", "origin", "refs/tags/v1.2.0")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "not greater than the latest tag v1.2.0" in receipt["detail"]


def test_refuses_existing_exact_tag(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    repo.git("tag", "v1.0.0")
    repo.git("push", "-q", "origin", "refs/tags/v1.0.0")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "already exists remotely" in receipt["detail"]


def test_refuses_missing_changelog_section(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    (repo.workspace / "CHANGELOG.md").write_text("# C\n\n## Unreleased\n")
    repo.commit_all("no section")
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "no dated section" in receipt["detail"]


def test_refuses_when_the_gate_fails(release_env) -> None:
    repo = release_env("node-npm", "1.0.0", pre_release=["sh", "-c", "echo boom; exit 3"])
    code, receipt = _release(repo)
    assert code == l9_release.EXIT_REFUSED
    assert "failed" in receipt["detail"] and "boom" in receipt["detail"]
    assert receipt["stages"]["gate"]["status"] == "FAIL"
    assert "build" not in receipt["stages"]


def test_refuses_undeclared_artifacts(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    document = json.loads((repo.workspace / ".l9/release.json").read_text())
    document["artifacts"] = ["something-else-{version}.tgz"]
    (repo.workspace / ".l9/release.json").write_text(json.dumps(document))
    repo.commit_all("wrong artifacts")
    code, receipt = _release(repo, dry_run=True)
    assert code == l9_release.EXIT_REFUSED
    assert "declared" in receipt["detail"]


def test_refuses_publication_without_authority(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    code, receipt = _release(repo)
    assert (code, receipt["status"]) == (l9_release.EXIT_REFUSED, "UNAUTHORIZED")
    assert repo.remote_peeled("v1.0.0") is None


def test_refuses_authority_for_a_different_tag(release_env) -> None:
    repo = release_env("node-npm", "1.0.0")
    repo.authorize("v9.9.9", repo.git("rev-parse", "HEAD"))
    code, receipt = _release(repo)
    assert receipt["status"] == "UNAUTHORIZED"
    assert receipt["stages"]["build"]["status"] == "PASS"
    assert repo.remote_peeled("v1.0.0") is None


def test_release_transport_refusal_is_reported(release_env, monkeypatch) -> None:
    repo = release_env("node-npm", "1.0.0")
    repo.authorize("v1.0.0", repo.git("rev-parse", "HEAD"))
    monkeypatch.setenv("FAKE_GH_DENY_RELEASE", "1")
    code, receipt = _release(repo)
    assert (code, receipt["status"]) == (l9_release.EXIT_TRANSPORT, "TRANSPORT_BLOCKED")
    assert "403" in receipt["detail"]


def test_make_target_routes_to_the_command() -> None:
    dry = subprocess.run(
        ["make", "--no-print-directory", "-n", "release", "WS=/r", "VERSION=3.0.0", "DRY_RUN=1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "ops/scripts/l9_release.py" in dry
    assert '--version "3.0.0"' in dry and "--dry-run" in dry
    safe = subprocess.run(
        ["make", "--no-print-directory", "l9-consumer-safe-list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert "release" in safe
