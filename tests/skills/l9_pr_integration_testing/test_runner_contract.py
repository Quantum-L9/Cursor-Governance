"""l9-pr-integration-testing: the runner and quick-path contracts that need no Docker.

Each case pins a defect found running the pack against Quantum-L9/l9-ci-core#220
in a hosted session, or a rule the quick path must never relax.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/l9-pr-integration-testing/scripts"
sys.path.insert(0, str(SCRIPTS))

import integrate  # noqa: E402
import quick  # noqa: E402

CONTRACT = (
    b'{\n  "schema": "l9.repo-execution/v2",\n  "facade": "make-v1",\n'
    b'  "required_phases": ["setup", "validate", "check", "test"]\n}\n'
)


def docker_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, isolate_git: bool) -> list[str]:
    seen: list[list[str]] = []

    class Done:
        returncode, stdout, stderr = 0, "", ""

    def fake_run(args, **_kwargs):
        seen.append(args)
        return Done()

    monkeypatch.setattr(integrate.subprocess, "run", fake_run)
    sandbox = integrate.DockerSandbox("sha256:" + "a" * 64, "run", uid=1000, gid=1000)
    sandbox.command(tmp_path, ["make", "test"], isolate_git=isolate_git)
    return seen[0]


def test_workspace_bind_carries_no_bare_rw(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = docker_args(monkeypatch, tmp_path, isolate_git=False)
    mount = args[args.index("--mount") + 1]
    assert mount == f"type=bind,src={tmp_path.resolve()},dst=/workspace"


def test_tmp_allows_exec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = docker_args(monkeypatch, tmp_path, isolate_git=False)
    options = args[args.index("--tmpfs") + 1].split(":", 1)[1].split(",")
    assert "exec" in options and "noexec" not in options
    assert "nosuid" in options and "nodev" in options


def test_test_procedures_keep_their_own_git_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    joined = " ".join(docker_args(monkeypatch, tmp_path, isolate_git=False))
    assert "GIT_CONFIG_GLOBAL" not in joined and "GIT_COMMITTER_DATE" not in joined


def test_runner_git_steps_stay_isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    joined = " ".join(docker_args(monkeypatch, tmp_path, isolate_git=True))
    assert "GIT_CONFIG_GLOBAL=/dev/null" in joined and "GIT_CONFIG_NOSYSTEM=1" in joined


def test_profile_hardening_is_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = docker_args(monkeypatch, tmp_path, isolate_git=False)
    for flag, value in (
        ("--network", "none"),
        ("--cap-drop", "ALL"),
        ("--security-opt", "no-new-privileges"),
        ("--user", "1000:1000"),
    ):
        assert args[args.index(flag) + 1] == value
    assert "--read-only" in args and "--privileged" not in args


@pytest.mark.parametrize(
    "reason",
    [
        "Git failed (128): fatal: unable to access 'https://github.com/o/r.git/': "
        "Problem with the SSL CA cert (path? access rights?)",
        "Git failed (128): fatal: unable to access 'x': Could not resolve host: github.com",
        "DOCKER_UNAVAILABLE: Docker daemon or pinned local image unavailable",
    ],
)
def test_transport_and_runtime_failures_are_environment(reason: str) -> None:
    assert integrate.blocker_kind(reason) == "ENVIRONMENT"


def test_authority_failures_stay_authority() -> None:
    assert (
        integrate.blocker_kind("explicit verified disposable execution authority source required")
        == "AUTHORITY"
    )


def test_quick_procedures_come_only_from_declared_phases() -> None:
    procedures = quick.procedures_from_contract(CONTRACT, ["test", "check"], 600)
    assert [p["argv"] for p in procedures] == [["make", "test"], ["make", "check"]]
    for procedure in procedures:
        source = procedure["source"]
        assert source["path"] == ".l9/repo-workflow.json"
        assert source["sha256"] == hashlib.sha256(CONTRACT).hexdigest()
        assert source["anchor"].encode() in CONTRACT


def test_quick_procedures_satisfy_the_runner_contract() -> None:
    manifest = {
        "repository": {
            "full_name": "o/r",
            "base_ref": "main",
            "base_sha": "a" * 40,
            "url": "https://github.com/o/r.git",
        },
        "prs": [
            {
                "number": 1,
                "head_sha": "b" * 40,
                "base_ref": "main",
                "fetch_url": "https://github.com/o/r.git",
                "fetch_ref": "refs/pull/1/head",
            }
        ],
        "integration_order": [1],
        "network": "none",
        "image": "sha256:" + "c" * 64,
        "test_procedures": quick.procedures_from_contract(CONTRACT, ["test"], 600),
        "execution_authority": {"scope": "DISPOSABLE_DOCKER_ONLY", "source": "operator"},
    }
    assert integrate.validate_plan(manifest) is True


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"not json", "is not JSON"),
        (b'{"schema_version": 1, "commands": {}}', "must declare schema"),
        (
            b'{"schema": "l9.repo-execution/v2", "facade": "make-v2", "required_phases": []}',
            "must declare schema",
        ),
    ],
)
def test_quick_refuses_repositories_without_a_v2_contract(raw: bytes, message: str) -> None:
    with pytest.raises(quick.QuickError, match=message):
        quick.procedures_from_contract(raw, ["test"], 600)


def test_quick_refuses_an_undeclared_phase() -> None:
    raw = json.dumps(
        {
            "schema": "l9.repo-execution/v2",
            "facade": "make-v1",
            "required_phases": ["setup", "test"],
        }
    ).encode()
    with pytest.raises(quick.QuickError, match="does not declare phase"):
        quick.procedures_from_contract(raw, ["check"], 600)


def test_quick_reports_dependency_manifests_a_base_layer_cannot_reflect() -> None:
    changed = {
        "12": ["src/app.py", "requirements-ci.txt"],
        "13": ["sub/pyproject.toml", "README.md"],
    }
    assert quick.dependency_changes(changed) == ["requirements-ci.txt", "sub/pyproject.toml"]
