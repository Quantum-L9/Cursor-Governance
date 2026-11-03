"""Tests for ops/scripts/docker_sandbox: the Core-locked toolchain contract.

Everything here is pure: the Docker, GitHub and filesystem side is exercised by
running `docker_sandbox.py ensure` in a hosted session, not by unit tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pytest  # noqa: E402
from docker_sandbox import (  # noqa: E402
    SandboxError,
    image_tag,
    parse_lock,
    parse_requirements,
    receipt_path,
    render_dockerfile,
    session_ca,
    verify_versions,
)

CORE_LOCK = {
    "ruff": "0.16.1",
    "mypy": "2.3.0",
    "pytest": "9.1.1",
    "biome": "2.5.8",
    "semgrep": "1.171.0",
    "python": "3.12.14",
    "pre-commit": "4.4.0",
    "pip": "26.2.1",
}
CORE_SHA = "89c9bc4e5ceafab932c92a2fdca2d3739fccf95f"
BASE = "python@sha256:" + "a" * 64


def test_parse_lock_accepts_core_shape() -> None:
    assert parse_lock(json.dumps(CORE_LOCK)) == CORE_LOCK


@pytest.mark.parametrize("version", ["latest", "0", ">=0.16.1", "0.16.*", "v0.16.1", 16])
def test_parse_lock_refuses_non_exact_versions(version: object) -> None:
    with pytest.raises(SandboxError, match="not an exact version"):
        parse_lock(json.dumps({**CORE_LOCK, "ruff": version}))


def test_parse_lock_requires_every_provided_tool() -> None:
    lock = dict(CORE_LOCK)
    del lock["pre-commit"]
    with pytest.raises(SandboxError, match="lacks pre-commit"):
        parse_lock(json.dumps(lock))


def test_parse_requirements_returns_core_pins() -> None:
    text = "# Core-owned pins\nruff==0.16.1\nmypy==2.3.0  # type gate\n\npytest==9.1.1\n"
    assert parse_requirements(text, CORE_LOCK) == ["ruff==0.16.1", "mypy==2.3.0", "pytest==9.1.1"]


def test_parse_requirements_refuses_drift_from_the_lock() -> None:
    with pytest.raises(SandboxError, match="ruff==0.16.2 but the lock says 0.16.1"):
        parse_requirements("ruff==0.16.2\n", CORE_LOCK)


@pytest.mark.parametrize("line", ["ruff", "ruff>=0.16", "-r other.txt", "ruff==0.16.1 --hash=x"])
def test_parse_requirements_refuses_unpinned_lines(line: str) -> None:
    with pytest.raises(SandboxError, match="not an exact pin"):
        parse_requirements(line + "\n", CORE_LOCK)


def test_image_tag_binds_the_core_sha_and_variant() -> None:
    assert image_tag(CORE_SHA, False) == "l9-ci-toolchain:core-89c9bc4e5cea"
    assert image_tag(CORE_SHA, True) == "l9-ci-toolchain:core-89c9bc4e5cea-semgrep"
    with pytest.raises(SandboxError):
        image_tag("main", False)


def test_dockerfile_installs_from_core_pins_and_never_copies_the_ca() -> None:
    text = render_dockerfile(BASE, CORE_LOCK, with_semgrep=True, with_ca=True, core_sha=CORE_SHA)
    assert text.startswith(f"FROM {BASE}\n")
    assert "pip==26.2.1" in text and "pre-commit==4.4.0" in text
    assert "-r /tmp/l9/requirements.txt" in text
    assert "--require-hashes" in text and "--only-binary :all:" in text
    assert "--mount=type=secret,id=ca" in text and "PIP_CERT=/run/secrets/ca" in text
    assert "COPY" not in text
    assert f'org.l9.core-sha="{CORE_SHA}"' in text


def test_dockerfile_without_ca_or_semgrep() -> None:
    text = render_dockerfile(BASE, CORE_LOCK, with_semgrep=False, with_ca=False, core_sha=CORE_SHA)
    assert "secret" not in text and "PIP_CERT" not in text and "semgrep" not in text


def test_dockerfile_refuses_an_unpinned_base() -> None:
    with pytest.raises(SandboxError, match="pinned by digest"):
        render_dockerfile(
            "python:3.12.14-slim", CORE_LOCK, with_semgrep=False, with_ca=False, core_sha=CORE_SHA
        )


def test_verify_versions_passes_only_on_exact_match() -> None:
    observed = {key: CORE_LOCK[key] for key in ("python", "pip", "ruff", "mypy", "pytest")}
    observed["pre-commit"] = "4.4.0"
    assert verify_versions(observed, CORE_LOCK, with_semgrep=False) == []
    drifted = {**observed, "ruff": "0.16.2"}
    assert verify_versions(drifted, CORE_LOCK, with_semgrep=False) == [
        "ruff: image has '0.16.2', Core lock pins '0.16.1'"
    ]


def test_verify_versions_requires_semgrep_only_for_that_variant() -> None:
    observed = {key: CORE_LOCK[key] for key in ("python", "pip", "ruff", "mypy", "pytest")}
    observed |= {"pre-commit": "4.4.0", "semgrep": None}
    assert verify_versions(observed, CORE_LOCK, with_semgrep=False) == []
    assert verify_versions(observed, CORE_LOCK, with_semgrep=True) == [
        "semgrep: image has None, Core lock pins '1.171.0'"
    ]


def test_each_variant_has_its_own_receipt() -> None:
    assert receipt_path(False) != receipt_path(True)


def test_session_ca_follows_the_exported_trust_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "ca.crt"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n")
    for name in ("PIP_CERT", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        monkeypatch.delenv(name, raising=False)
    assert session_ca() is None
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "missing.crt"))
    assert session_ca() is None
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    assert session_ca() == bundle


# --- Registry fallback (Docker Hub rate limits shared hosted IPs) ------------

import subprocess  # noqa: E402

import docker_sandbox  # noqa: E402

DIGEST = "sha256:" + "f" * 64


def test_mirrors_default_to_mirror_gcr_and_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_DOCKER_SANDBOX_MIRRORS", raising=False)
    assert docker_sandbox.registry_mirrors() == ["mirror.gcr.io"]
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", " a.example , b.example ")
    assert docker_sandbox.registry_mirrors() == ["a.example", "b.example"]
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "")
    assert docker_sandbox.registry_mirrors() == []


def test_dockerd_is_started_with_each_mirror() -> None:
    assert docker_sandbox.dockerd_argv(["mirror.gcr.io"]) == [
        "dockerd",
        "--registry-mirror=https://mirror.gcr.io",
    ]
    assert docker_sandbox.dockerd_argv([]) == ["dockerd"]


def test_base_refs_try_docker_hub_first_then_mirrors() -> None:
    assert docker_sandbox.base_refs("3.12.14", ["mirror.gcr.io"]) == [
        "python:3.12.14-slim",
        "mirror.gcr.io/library/python:3.12.14-slim",
    ]


def test_digest_for_picks_the_pulled_repository() -> None:
    digests = [f"python@{DIGEST}", f"mirror.gcr.io/library/python@{DIGEST}"]
    assert (
        docker_sandbox.digest_for("mirror.gcr.io/library/python:3.12.14-slim", digests)
        == f"mirror.gcr.io/library/python@{DIGEST}"
    )
    assert docker_sandbox.digest_for("python:3.12.14-slim", digests) == f"python@{DIGEST}"
    assert docker_sandbox.digest_for("python:3.12.14-slim", []) is None


class FakeDocker:
    """docker as a script: Docker Hub answers 429, the mirror answers."""

    def __init__(self, hub_fails: bool = True, mirror_fails: bool = False) -> None:
        self.hub_fails, self.mirror_fails = hub_fails, mirror_fails
        self.pulled: set[str] = set()
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ["docker", "pull"]:
            ref = args[-1]
            failed = self.mirror_fails if ref.startswith("mirror.gcr.io/") else self.hub_fails
            if failed:
                return subprocess.CompletedProcess(args, 1, "", "toomanyrequests: 429")
            self.pulled.add(ref)
            return subprocess.CompletedProcess(args, 0, ref, "")
        ref = args[-1]
        if ref in self.pulled:
            repository = ref.rsplit(":", 1)[0]
            return subprocess.CompletedProcess(args, 0, json.dumps([f"{repository}@{DIGEST}"]), "")
        return subprocess.CompletedProcess(args, 1, "", "No such image")


def test_a_rate_limited_docker_hub_falls_back_to_the_mirror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "mirror.gcr.io")
    fake = FakeDocker()
    monkeypatch.setattr(docker_sandbox, "run", lambda args, **kw: fake(args, **kw))
    assert docker_sandbox.pinned_base("3.12.14") == f"mirror.gcr.io/library/python@{DIGEST}"
    pulls = [call[-1] for call in fake.calls if call[:2] == ["docker", "pull"]]
    assert pulls == ["python:3.12.14-slim", "mirror.gcr.io/library/python:3.12.14-slim"]


def test_every_registry_failing_reports_each_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "mirror.gcr.io")
    fake = FakeDocker(hub_fails=True, mirror_fails=True)
    monkeypatch.setattr(docker_sandbox, "run", lambda args, **kw: fake(args, **kw))
    with pytest.raises(
        SandboxError, match=r"python:3\.12\.14-slim: toomanyrequests.*mirror\.gcr\.io"
    ):
        docker_sandbox.pinned_base("3.12.14")


def test_a_local_copy_is_used_without_any_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDocker()
    fake.pulled.add("mirror.gcr.io/library/python:3.12.14-slim")
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "mirror.gcr.io")
    monkeypatch.setattr(docker_sandbox, "run", lambda args, **kw: fake(args, **kw))
    assert docker_sandbox.pinned_base("3.12.14") == f"mirror.gcr.io/library/python@{DIGEST}"
    assert not [call for call in fake.calls if call[:2] == ["docker", "pull"]]


@pytest.mark.parametrize(
    ("image", "refs"),
    [
        ("postgres:16", ["postgres:16", "mirror.gcr.io/library/postgres:16"]),
        ("bitnami/redis:7", ["bitnami/redis:7", "mirror.gcr.io/bitnami/redis:7"]),
        ("ghcr.io/o/svc:1", ["ghcr.io/o/svc:1"]),
        ("localhost:5000/svc:1", ["localhost:5000/svc:1"]),
    ],
)
def test_only_docker_hub_images_fall_through_to_a_mirror(image: str, refs: list[str]) -> None:
    assert docker_sandbox.image_refs(image, ["mirror.gcr.io"]) == refs


def test_a_service_image_is_pinned_through_the_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "mirror.gcr.io")
    fake = FakeDocker()
    monkeypatch.setattr(docker_sandbox, "run", lambda args, **kw: fake(args, **kw))
    assert docker_sandbox.pin_image("redis:7") == f"mirror.gcr.io/library/redis@{DIGEST}"


@pytest.mark.parametrize(
    ("ref", "repository"),
    [
        ("postgres:16", "postgres"),
        ("mirror.gcr.io/library/redis:7", "mirror.gcr.io/library/redis"),
        ("localhost:5000/svc:1", "localhost:5000/svc"),
        ("postgres@sha256:" + "a" * 64, "postgres"),
    ],
)
def test_repository_of_drops_only_the_tag(ref: str, repository: str) -> None:
    assert docker_sandbox.repository_of(ref) == repository


def test_a_pinned_digest_is_pulled_by_digest_never_by_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("L9_DOCKER_SANDBOX_MIRRORS", "mirror.gcr.io")
    fake = FakeDocker()
    monkeypatch.setattr(docker_sandbox, "run", lambda args, **kw: fake(args, **kw))
    digest = "sha256:" + "b" * 64
    assert (
        docker_sandbox.pin_image("redis:7", digest=digest)
        == f"mirror.gcr.io/library/redis@{digest}"
    )
    pulls = [call[-1] for call in fake.calls if call[:2] == ["docker", "pull"]]
    assert pulls == [f"redis@{digest}", f"mirror.gcr.io/library/redis@{digest}"]
    assert not any(":7" in ref for ref in pulls), "a floating tag must not be resolved"


def test_a_malformed_pinned_digest_is_refused() -> None:
    with pytest.raises(SandboxError, match="sha256"):
        docker_sandbox.pin_image("redis:7", digest="sha256:short")


# --- Core transport: REST, then git (gateways that 403 Core over REST) -------

REST_403 = SandboxError("gh api repos/Quantum-L9/l9-ci-core failed (1): HTTP 403")


def _rest_denied(path: str) -> dict:
    raise REST_403


def test_core_commit_prefers_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docker_sandbox, "gh_api", lambda path: {"sha": CORE_SHA})
    monkeypatch.setattr(docker_sandbox, "_git", lambda *a: pytest.fail("git used while REST works"))
    assert docker_sandbox.core_commit("main") == CORE_SHA


def test_core_commit_falls_back_to_ls_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    other = "b" * 40
    listing = f"{other}\trefs/heads/mainline\n{CORE_SHA}\trefs/heads/main\n"
    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", lambda *a: listing)
    assert docker_sandbox.core_commit("main") == CORE_SHA


def test_core_commit_refuses_an_unknown_ref_over_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", lambda *a: f"{CORE_SHA}\trefs/heads/main\n")
    with pytest.raises(SandboxError, match="not a ref"):
        docker_sandbox.core_commit("no-such-branch")


def test_core_commit_reports_both_transports_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    def git_down(*args: str) -> str:
        raise SandboxError("git ls-remote failed (128): could not resolve host")

    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", git_down)
    with pytest.raises(SandboxError, match="HTTP 403.*git transport also failed"):
        docker_sandbox.core_commit("main")


def test_core_file_reads_the_exact_commit_over_git(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def git(*args: str) -> str:
        calls.append(args)
        return "lock-bytes" if "show" in args else ""

    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", git)
    assert docker_sandbox.core_file(CORE_SHA, "a/lock.json") == "lock-bytes"
    fetch = next(c for c in calls if "fetch" in c)
    assert fetch[-2:] == (docker_sandbox.CORE_GIT_URL, CORE_SHA)
    assert calls[-1][-1] == f"{CORE_SHA}:a/lock.json"


def test_core_commit_peels_an_annotated_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """refs/tags/<t> is the tag object; the ^{} row is the commit REST returns."""
    tag_object = "c" * 40
    listing = f"{tag_object}\trefs/tags/v2.0.0\n{CORE_SHA}\trefs/tags/v2.0.0^{{}}\n"
    seen: list[tuple[str, ...]] = []

    def git(*args: str) -> str:
        seen.append(args)
        return listing

    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", git)
    assert docker_sandbox.core_commit("v2.0.0") == CORE_SHA
    assert "refs/tags/v2.0.0^{}" in seen[0], "ls-remote must ask for the peeled row by name"


def test_core_commit_keeps_a_lightweight_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docker_sandbox, "gh_api", _rest_denied)
    monkeypatch.setattr(docker_sandbox, "_git", lambda *a: f"{CORE_SHA}\trefs/tags/v1\n")
    assert docker_sandbox.core_commit("v1") == CORE_SHA


def test_core_file_falls_back_when_the_rest_body_is_not_base64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker_sandbox, "gh_api", lambda path: {"content": "%%%not-base64"})
    monkeypatch.setattr(docker_sandbox, "_git", lambda *a: "git-bytes" if "show" in a else "")
    assert docker_sandbox.core_file(CORE_SHA, "a/lock.json") == "git-bytes"


def test_a_hung_git_is_a_sandbox_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def hang(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git", timeout=120)

    monkeypatch.setattr(docker_sandbox.subprocess, "run", hang)
    with pytest.raises(SandboxError, match="git ls-remote failed"):
        docker_sandbox._git("ls-remote", docker_sandbox.CORE_GIT_URL)
