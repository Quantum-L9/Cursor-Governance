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
    assert "GIT_AUTHOR_DATE" not in joined


def test_runner_git_steps_stay_isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    joined = " ".join(docker_args(monkeypatch, tmp_path, isolate_git=True))
    assert "GIT_CONFIG_GLOBAL=/dev/null" in joined and "GIT_CONFIG_NOSYSTEM=1" in joined
    # Author and committer date both pinned: a merge of the same inputs is the same commit.
    assert "GIT_AUTHOR_DATE=2000-01-01T00:00:00+00:00" in joined
    assert "GIT_COMMITTER_DATE=2000-01-01T00:00:00+00:00" in joined


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


CI_WORKFLOW = b"""
env:
  SHARED: one
jobs:
  validate:
    runs-on: ubuntu-latest
    env:
      DSN: host=localhost port=5432 user=postgres dbname=t
      TOKEN: ${{ secrets.TOKEN }}
      DB_PASSWORD: l9-ci-${{ github.run_id }}
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_HOST_AUTH_METHOD: trust
          POSTGRES_PASSWORD: l9-ci-${{ github.run_id }}
        ports: ["5432:5432"]
        options: --health-cmd "pg_isready -U postgres" --health-interval 10s --health-retries 5
      redis_cache:
        image: redis:7
        ports: ["6379:6379"]
        options: --health-cmd="redis-cli ping" --health-timeout 5s
"""


def test_ci_job_yields_services_and_literal_test_env() -> None:
    derived = quick.services_from_workflow(CI_WORKFLOW, "ci.yml", "validate")
    postgres, redis = derived["services"]
    assert postgres["image"] == "postgres:16" and postgres["ports"] == [5432]
    assert postgres["health"] == {"cmd": "pg_isready -U postgres", "interval": "10s", "retries": 5}
    assert postgres["env"]["POSTGRES_PASSWORD"] == f"l9-ci-{quick.LOCAL_RUN_VALUE}"
    assert redis["name"] == "redis-cache" and redis["health"]["cmd"] == "redis-cli ping"
    assert derived["test_env"] == {
        "SHARED": "one",
        "DSN": "host=localhost port=5432 user=postgres dbname=t",
        "DB_PASSWORD": f"l9-ci-{quick.LOCAL_RUN_VALUE}",
    }
    assert derived["test_env_omitted"] == ["TOKEN"], "a secret is named, never filled in"
    assert derived["service_warnings"] == []


def test_a_startup_plugin_download_is_named_as_not_reproduced() -> None:
    workflow = CI_WORKFLOW.replace(
        b"POSTGRES_HOST_AUTH_METHOD: trust",
        b"POSTGRES_HOST_AUTH_METHOD: trust\n          NEO4J_PLUGINS: '[\"graph-data-science\"]'",
    )
    derived = quick.services_from_workflow(workflow, "ci.yml", "validate")
    assert derived["service_warnings"] == [
        "postgres: NEO4J_PLUGINS downloads at startup; with no network it is not loaded"
    ]


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (b'pg_isready -U postgres" --health', b'pg_isready -U postgres" --privileged --health'),
        (b'["5432:5432"]', b'["15432:5432"]'),
        (b"POSTGRES_HOST_AUTH_METHOD: trust", b"POSTGRES_HOST_AUTH_METHOD: ${{ secrets.X }}"),
        (b'["6379:6379"]', b'["5432:5432"]'),
        (b'--health-cmd="redis-cli ping" --health-timeout 5s', b"--health-timeout 5s"),
    ],
    ids=["non-health option", "port remap", "secret in service env", "port clash", "no health"],
)
def test_ci_job_refuses_what_cannot_be_reproduced_offline(patch: bytes, message: bytes) -> None:
    with pytest.raises(quick.QuickError):
        quick.services_from_workflow(CI_WORKFLOW.replace(patch, message), "ci.yml", "validate")


def test_ci_job_must_exist() -> None:
    with pytest.raises(quick.QuickError, match="no job"):
        quick.services_from_workflow(CI_WORKFLOW, "ci.yml", "missing")


def _service(**overrides: object) -> dict:
    service = {
        "name": "postgres",
        "image": "postgres@sha256:" + "a" * 64,
        "env": {"POSTGRES_HOST_AUTH_METHOD": "trust"},
        "ports": [5432],
        "health": {"cmd": "pg_isready", "interval": "1s", "retries": 5},
    }
    service.update(overrides)
    return service


def test_runner_accepts_a_pinned_health_checked_service() -> None:
    assert integrate.validate_services([_service()]) == [_service()]


@pytest.mark.parametrize(
    "service",
    [
        _service(image="postgres:16"),
        _service(health=None),
        _service(health={"cmd": "x", "interval": "soon"}),
        _service(env={"PASSWORD": "${{ secrets.X }}"}),
        _service(name="Bad Name"),
    ],
    ids=["unpinned", "no health", "bad duration", "expression env", "bad name"],
)
def test_runner_refuses_an_unsafe_service(service: dict) -> None:
    with pytest.raises(integrate.SafetyError):
        integrate.validate_services([service])


def test_runner_refuses_two_services_on_one_port() -> None:
    with pytest.raises(integrate.SafetyError, match="port 5432"):
        integrate.validate_services([_service(), _service(name="other")])


def test_tests_join_only_their_own_loopback_namespace(tmp_path: Path) -> None:
    sandbox = integrate.DockerSandbox("sha256:" + "a" * 64, "abc123", uid=1000, gid=1000)
    with pytest.raises(integrate.SafetyError, match="loopback namespace"):
        sandbox.command(tmp_path, ["true"], network="host")
    with pytest.raises(integrate.SafetyError, match="loopback namespace"):
        sandbox.command(tmp_path, ["true"], network="container:someone-elses-db")


@pytest.mark.parametrize(
    ("parser", "body", "count"),
    [
        ("pytest", "== 10 passed, 263 skipped in 3.2s ==", 263),
        ("unittest", "OK (skipped=4)", 4),
        ("pytest", "== 3 passed in 0.1s ==", 0),
        ("", "== 1 skipped ==", None),
    ],
)
def test_skipped_tests_are_counted_for_known_runners(
    parser: str, body: str, count: int | None
) -> None:
    assert integrate.parse_skipped(body, parser) == count


class FakeServiceDocker:
    """docker for services_up: every container starts; health is scripted."""

    def __init__(self, health: str) -> None:
        self.health = health
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        out = f"running {self.health}" if args[1] == "inspect" else "id"
        return subprocess.CompletedProcess(args, 0, out, "")

    def removed(self) -> list[str]:
        return [call[-1] for call in self.calls if call[:3] == ["docker", "rm", "-f"]]


def _service_sandbox() -> integrate.DockerSandbox:
    return integrate.DockerSandbox(
        "sha256:" + "a" * 64, "abc123", uid=1000, gid=1000, services=[_service()]
    )


def test_services_share_a_network_less_namespace_and_are_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = FakeServiceDocker("healthy")
    monkeypatch.setattr(integrate.subprocess, "run", fake)
    sandbox = _service_sandbox()
    with sandbox.services_up(integrate.EvidenceWriter(tmp_path), "combined") as network:
        assert network == "container:l9-pr-abc123-net-1"
    holder, service = (c for c in fake.calls if c[:3] == ["docker", "run", "-d"])
    assert holder[holder.index("--network") + 1] == "none"
    assert holder[holder.index("--hostname") + 1] == "localhost", "a JVM service resolves itself"
    assert service[service.index("--network") + 1] == network
    assert "--privileged" not in service and service.count("--cap-add") == 5
    assert fake.removed() == ["l9-pr-abc123-net-1-postgres", "l9-pr-abc123-net-1"]
    logged = [c[-1] for c in fake.calls if c[:2] == ["docker", "logs"]]
    assert logged == ["l9-pr-abc123-net-1-postgres"], "the service log becomes evidence"


def test_an_unhealthy_service_blocks_and_is_still_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = FakeServiceDocker("unhealthy")
    monkeypatch.setattr(integrate.subprocess, "run", fake)
    with pytest.raises(integrate.SafetyError, match="did not become healthy") as caught:
        with _service_sandbox().services_up(integrate.EvidenceWriter(tmp_path), "combined"):
            pytest.fail("tests must not run beside an unhealthy service")
    assert integrate.blocker_kind(str(caught.value)) == "ENVIRONMENT"
    assert fake.removed() == ["l9-pr-abc123-net-1-postgres", "l9-pr-abc123-net-1"]


def test_vendored_service_pins_cover_the_graphiti_memory_ci_images() -> None:
    """The pins are a snapshot read from this skill; no upstream fetch happens."""
    pins = quick.load_service_pins()
    assert set(pins) >= {"postgres:16", "redis:7", "neo4j:5.26.31"}
    document = json.loads(quick.SERVICE_PINS.read_text(encoding="utf-8"))
    assert document["source"]["repository"] == "Quantum-L9/l9-graphiti-memory"
    assert len(document["source"]["commit"]) == 40


@pytest.mark.parametrize(
    ("image", "tag"),
    [
        ("postgres:16", "postgres:16"),
        ("docker.io/library/postgres:16", "postgres:16"),
        ("library/redis:7", "redis:7"),
        ("ghcr.io/o/svc:1", "ghcr.io/o/svc:1"),
    ],
)
def test_service_images_are_looked_up_by_canonical_tag(image: str, tag: str) -> None:
    assert quick.canonical_tag(image) == tag


@pytest.mark.parametrize(
    "images",
    [
        {"postgres:16": {"digest": "sha256:short"}},
        {"postgres@sha256:" + "a" * 64: {"digest": "sha256:" + "a" * 64}},
        {"docker.io/library/postgres:16": {"digest": "sha256:" + "a" * 64}},
    ],
    ids=["bad digest", "digest key", "prefixed key"],
)
def test_a_malformed_pin_file_is_refused(tmp_path: Path, images: dict) -> None:
    path = tmp_path / "pins.json"
    path.write_text(json.dumps({"schema": quick.SERVICE_PINS_SCHEMA, "images": images}))
    with pytest.raises(quick.QuickError):
        quick.load_service_pins(path)


class FakePinner:
    class SandboxError(Exception):
        pass

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def pin_image(self, image: str, digest: str | None = None) -> str:
        self.calls.append((image, digest))
        return f"{image.split(':')[0]}@{digest or 'sha256:' + 'f' * 64}"


def test_ci_services_run_listed_images_at_their_pinned_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = CI_WORKFLOW.replace(b"image: redis:7", b"image: redis:8")
    monkeypatch.setattr(quick, "gh_raw", lambda repo, path, ref: workflow)
    pinner = FakePinner()
    derived = quick.ci_services("o/r", "a" * 40, "ci.yml:validate", pinner)
    pins = quick.load_service_pins()
    assert pinner.calls == [("postgres:16", pins["postgres:16"]["digest"]), ("redis:8", None)]
    postgres, redis = derived["services"]
    assert postgres["pinned"] is True and redis["pinned"] is False
    assert any("redis:8 is not in service-images.json" in w for w in derived["service_warnings"])
