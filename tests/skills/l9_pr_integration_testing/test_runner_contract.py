"""l9-pr-integration-testing: the runner and quick-path contracts that need no Docker.

Each case pins a defect found running the pack against Quantum-L9/l9-ci-core#220
in a hosted session, or a rule the quick path must never relax.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
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
        + "Problem with the SSL CA cert (path? access rights?)",
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


def test_quick_procedures_have_unique_ids() -> None:
    procedures = quick.procedures_from_contract(CONTRACT, ["test", "check"], 600)
    assert [p["id"] for p in procedures] == ["make-test", "make-check"]


def _plan_with(procedures: list[dict]) -> dict:
    return {
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
        "image": "sha256:" + "c" * 64,
        "test_procedures": procedures,
        "execution_authority": {"scope": "DISPOSABLE_DOCKER_ONLY", "source": "operator"},
    }


@pytest.mark.parametrize("ids", [[None], ["", "x"], ["make-test", "make-test"]])
def test_runner_refuses_procedures_without_unique_ids(ids: list[str | None]) -> None:
    template = quick.procedures_from_contract(CONTRACT, ["test"], 600)[0]
    procedures = []
    for index, identifier in enumerate(ids):
        procedure = {**template, "argv": ["make", f"t{index}"]}
        procedure.pop("id")
        if identifier is not None:
            procedure["id"] = identifier
        procedures.append(procedure)
    with pytest.raises(integrate.SafetyError, match="unique nonempty id"):
        integrate.validate_plan(_plan_with(procedures))


def test_adapter_census_covers_paths_a_pr_adds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    repo.mkdir()
    git("init", "--quiet")
    (repo / "app.py").write_text("print(1)\n")
    git("add", "app.py")
    git("commit", "--quiet", "-m", "base")
    base = git("rev-parse", "HEAD")
    (repo / "addon").mkdir()
    (repo / "addon" / "__manifest__.py").write_text("{'name': 'x', 'depends': ['base']}\n")
    git("add", "addon/__manifest__.py")
    git("commit", "--quiet", "-m", "pr adds an Odoo addon")
    head = git("rev-parse", "HEAD")
    plan = {"repository": {"base_sha": base}, "prs": [{"number": 1, "head_sha": head}]}
    store = repo / ".git"
    assert "ODOO" not in integrate.detect_adapters(integrate.list_tree(store, base))
    assert "ODOO" in integrate.adapter_census(store, plan)


def test_quick_refuses_a_pr_that_changes_dependency_inputs() -> None:
    quick.refuse_dependency_changes({"12": ["src/app.py", "README.md"]})
    with pytest.raises(quick.QuickError, match="dependency inputs"):
        quick.refuse_dependency_changes({"12": ["src/app.py"], "13": ["uv.lock"]})
    with pytest.raises(quick.QuickError, match="Repo.mk"):
        quick.refuse_dependency_changes({"12": ["Repo.mk"]})


# --- Offline PEP 517 builds: the dependency layer carries a wheelhouse -------


def test_build_requirements_follow_pyproject_then_pip_fallback() -> None:
    declared = '[build-system]\nrequires = ["hatchling>=1.25"]\nbuild-backend = "hatchling.build"\n'
    assert quick.build_requirements(declared, False) == ["hatchling>=1.25"]
    assert quick.build_requirements('[project]\nname = "x"\n', False) == [quick.SETUPTOOLS_FALLBACK]
    assert quick.build_requirements(None, True) == [quick.SETUPTOOLS_FALLBACK]
    assert quick.build_requirements(None, False) == []


@pytest.mark.parametrize(
    "pyproject",
    ['[build-system\nrequires = ["x"]', '[build-system]\nrequires = "setuptools"\n'],
)
def test_build_requirements_refuse_an_unreadable_declaration(pyproject: str) -> None:
    with pytest.raises(quick.QuickError):
        quick.build_requirements(pyproject, False)


def test_dependency_layer_prepares_an_offline_wheelhouse_after_setup() -> None:
    text = quick.render_dependency_dockerfile(
        "l9-ci-toolchain:core-x", "o/r", "a" * 40, ["setuptools>=68"], with_ca=True
    )
    setup, download, env = (
        text.index("make setup"),
        text.index("pip download"),
        text.index("ENV PIP_FIND_LINKS"),
    )
    assert setup < download < env, "setup keeps the network; only the test run is offline"
    assert f"--dest {quick.WHEELHOUSE}" in text
    assert f"ENV PIP_FIND_LINKS={quick.WHEELHOUSE} PIP_NO_INDEX=1" in text
    assert f'org.l9.layer-recipe="{quick.LAYER_RECIPE}"' in text
    assert "COPY" not in text
    bare = quick.render_dependency_dockerfile("img", "o/r", "a" * 40, [], with_ca=False)
    assert "pip download" not in bare and "secret" not in bare


def _result(procedure: str, status: str, ids: list[str] | None = None) -> dict:
    return {"procedure": procedure, "status": status, "failure_ids": ids}


def test_probe_is_killed_when_a_passing_procedure_fails() -> None:
    status, basis = integrate.judge_probe([_result("t", "PASS", [])], [_result("t", "FAIL", [])])
    assert status == "KILLED" and "passed unmutated" in basis[0]


def test_probe_survives_when_nothing_new_fails() -> None:
    reference = [_result("t", "PASS", []), _result("u", "FAIL", ["a"])]
    mutated = [_result("t", "PASS", []), _result("u", "FAIL", ["a"])]
    assert integrate.judge_probe(reference, mutated)[0] == "SURVIVED"


def test_a_pre_existing_failure_is_not_counted_as_a_caught_probe() -> None:
    """The defect: any FAIL on a red candidate used to count as KILLED."""
    status, basis = integrate.judge_probe(
        [_result("t", "FAIL", None)], [_result("t", "FAIL", None)]
    )
    assert status == "INCONCLUSIVE"
    assert "no failure parser" in basis[0]


def test_new_failure_identities_on_a_red_candidate_kill_the_probe() -> None:
    status, basis = integrate.judge_probe(
        [_result("t", "FAIL", ["tests/a.py::x"])],
        [_result("t", "FAIL", ["tests/a.py::x", "tests/b.py::y"])],
    )
    assert status == "KILLED" and "tests/b.py::y" in basis[0]


@pytest.mark.parametrize(
    ("reference", "mutated", "reason"),
    [
        ([_result("t", "PASS", [])], [_result("t", "TIMEOUT", [])], "timed out under"),
        ([_result("t", "TIMEOUT", [])], [_result("t", "FAIL", [])], "timed out on the unmutated"),
        ([_result("t", "FAIL", ["a"])], [_result("t", "FAIL", [])], "named no test identities"),
        ([], [_result("t", "FAIL", [])], "no unmutated result"),
    ],
)
def test_probe_that_cannot_be_judged_is_inconclusive(
    reference: list[dict], mutated: list[dict], reason: str
) -> None:
    status, basis = integrate.judge_probe(reference, mutated)
    assert status == "INCONCLUSIVE" and reason in basis[0]


def test_one_caught_procedure_outweighs_an_unjudgeable_one() -> None:
    reference = [_result("t", "PASS", []), _result("u", "FAIL", None)]
    mutated = [_result("t", "FAIL", []), _result("u", "FAIL", None)]
    assert integrate.judge_probe(reference, mutated)[0] == "KILLED"


def test_quick_procedures_carry_the_declared_failure_parser() -> None:
    procedures = quick.procedures_from_contract(CONTRACT, ["test"], 600, "pytest")
    assert procedures[0]["failure_parser"] == "pytest"
    assert "failure_parser" not in quick.procedures_from_contract(CONTRACT, ["test"], 600)[0]
    with pytest.raises(quick.QuickError):
        quick.procedures_from_contract(CONTRACT, ["test"], 600, "jest")
