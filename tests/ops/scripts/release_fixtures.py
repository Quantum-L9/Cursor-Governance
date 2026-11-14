"""Shared fixtures for the ``make release`` tests.

A throwaway repository is published to a local bare ``origin``. Its origin URL
is a real GitHub URL rewritten to the bare path by ``url.<bare>.insteadOf`` in
an isolated global git config, so the release command sees a GitHub slug while
every git transport stays local. ``gh`` is replaced at the transport boundary by
:data:`FAKE_GH`, which keeps Releases in a state directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

SLUG = "acme/widget"
URL = f"https://github.com/{SLUG}"

FAKE_GH = textwrap.dedent(
    """\
    #!{python}
    import json, os, shutil, subprocess, sys
    from pathlib import Path

    state = Path(os.environ["FAKE_GH_STATE"])
    args = sys.argv[1:]
    (state / "calls.log").open("a").write(json.dumps(args) + "\\n")

    def opt(name):
        return args[args.index(name) + 1]

    if args[:3] == ["api", "--method", "GET"] and args[3].endswith("/pulls"):
        prs = state / "open_prs"
        print(prs.read_text() if prs.exists() else "", end="")
        sys.exit(0)
    if args[:3] == ["api", "--method", "GET"] and "/releases/tags/" in args[3]:
        tag = args[3].rsplit("/", 1)[1]
        record = state / "releases" / f"{{tag}}.json"
        if not record.exists():
            print("gh: Not Found (HTTP 404)", file=sys.stderr)
            sys.exit(1)
        print(record.read_text())
        sys.exit(0)
    if args[:2] == ["release", "create"]:
        if os.environ.get("FAKE_GH_DENY_RELEASE"):
            print("HTTP 403: not permitted for this session type", file=sys.stderr)
            sys.exit(1)
        tag = args[2]
        assert "--verify-tag" in args
        refs = subprocess.run(
            ["git", "ls-remote", os.environ["FAKE_GH_ORIGIN"], f"refs/tags/{{tag}}"],
            capture_output=True, text=True, check=True,
        ).stdout
        if not refs.strip():
            print(f"tag {{tag}} doesn't exist in the repo", file=sys.stderr)
            sys.exit(1)
        notes = Path(opt("--notes-file")).read_text()
        flags_with_value = {{"--repo", "--title", "--notes-file"}}
        assets, skip = [], False
        for item in args[3:]:
            if skip:
                skip = False
                continue
            if item in flags_with_value:
                skip = True
                continue
            if item.startswith("--"):
                continue
            assets.append(Path(item))
        store = state / "releases" / tag
        store.mkdir(parents=True)
        for asset in assets:
            shutil.copy2(asset, store / asset.name)
        (state / "releases" / f"{{tag}}.json").write_text(json.dumps({{
            "tag_name": tag, "draft": False, "body": notes,
            "html_url": f"https://github.com/{{opt('--repo')}}/releases/tag/{{tag}}",
            "assets": [{{"name": a.name}} for a in assets],
        }}))
        sys.exit(0)
    if args[:2] == ["release", "download"]:
        store = state / "releases" / args[2]
        dest = Path(opt("--dir"))
        for item in store.iterdir():
            shutil.copy2(item, dest / item.name)
        sys.exit(0)
    print(f"fake gh: unsupported {{args}}", file=sys.stderr)
    sys.exit(2)
    """
)

MAKEFILE = "setup validate check test:\n\t@echo phase $@\n"

CHANGELOG = "# Changelog\n\n## {version} - 2026-11-14\n\n- Release {version}.\n"


@dataclass
class Repo:
    workspace: Path
    origin: Path
    state: Path

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.workspace, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit_all(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")
        return self.git("rev-parse", "HEAD")

    def remote_peeled(self, tag: str) -> str | None:
        out = subprocess.run(
            ["git", "ls-remote", str(self.origin), f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\n")
        rows = dict(line.split("\t")[::-1] for line in out if line)
        return rows.get(f"refs/tags/{tag}^{{}}") or rows.get(f"refs/tags/{tag}")

    def authorize(self, tag: str, commit: str) -> None:
        now = datetime.now(UTC).replace(microsecond=0)
        receipt = {
            "schema": "l9.publish-path-breakglass.v1",
            "scope": "publish_path",
            "issuer": "ops",
            "reason": f"make release {tag} {commit}",
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        Path(os.environ["L9_PUBLISH_PATH_RECEIPT"]).write_text(json.dumps(receipt))


def python_project(root: Path, version: str) -> None:
    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [build-system]
            requires = ["setuptools>=75"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "acme-widget"
            version = "{version}"
            requires-python = ">=3.9"
            """
        )
    )
    package = root / "src" / "acme_widget"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(f'__version__ = "{version}"\n')


def node_project(root: Path, version: str) -> None:
    (root / "package.json").write_text(
        json.dumps({"name": "acme-widget", "version": version, "files": ["index.js"]}, indent=2)
    )
    (root / "index.js").write_text("module.exports = 1;\n")


def declaration(kind: str, major: str = "none", pre_release: list[str] | None = None) -> dict:
    if kind == "python-uv":
        ecosystems = [{"kind": "python-uv", "version_authority": "pyproject.toml"}]
        artifacts = ["acme_widget-{version}-py3-none-any.whl", "acme_widget-{version}.tar.gz"]
    else:
        ecosystems = [{"kind": "node-npm", "version_authority": "package.json"}]
        artifacts = ["acme-widget-{version}.tgz"]
    document = {
        "schema": "l9.release/v1",
        "repository": SLUG,
        "ecosystems": ecosystems,
        "artifacts": artifacts,
        "major_tag": major,
        "notes": {"changelog": "CHANGELOG.md"},
    }
    if pre_release:
        document["pre_release"] = {"argv": pre_release}
    return document


@pytest.fixture(name="release_env")
def release_env_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Return a factory ``make(kind, version, major) -> Repo``."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(
        f"[user]\n\tname = Release Test\n\temail = release@example.invalid\n"
        f'[url "{origin}"]\n\tinsteadOf = {URL}\n'
        "[init]\n\tdefaultBranch = main\n[tag]\n\tgpgSign = false\n[commit]\n\tgpgSign = false\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    state = tmp_path / "gh-state"
    state.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "gh"
    fake.write_text(FAKE_GH.format(python=sys.executable))
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    monkeypatch.setenv("FAKE_GH_ORIGIN", str(origin))
    monkeypatch.setenv("L9_PUBLISH_PATH_RECEIPT", str(tmp_path / "breakglass.json"))
    monkeypatch.delenv("L9_PUBLISH_PATH_OVERRIDE", raising=False)

    def make(kind: str, version: str = "1.0.0", major: str = "none", **extra) -> Repo:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=workspace, check=True)
        subprocess.run(["git", "remote", "add", "origin", URL], cwd=workspace, check=True)
        (workspace / ".gitignore").write_text(".l9/release/\n")
        (workspace / "Makefile").write_text(MAKEFILE)
        (workspace / "CHANGELOG.md").write_text(CHANGELOG.format(version=version))
        (workspace / ".l9").mkdir()
        (workspace / ".l9" / "release.json").write_text(
            json.dumps(declaration(kind, major, extra.get("pre_release")), indent=2)
        )
        if kind == "python-uv":
            python_project(workspace, version)
        else:
            node_project(workspace, version)
        repo = Repo(workspace=workspace, origin=origin, state=state)
        repo.commit_all("initial")
        return repo

    return make
