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
