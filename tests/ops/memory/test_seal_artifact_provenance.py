"""Seal reads installer provenance; it does not invent a digest."""

from __future__ import annotations

from pathlib import Path

import pytest

from ops.memory import seal_artifact_provenance as seal
from ops.memory.runtime_binding import BindingManifest

ROOT = Path(__file__).resolve().parents[3]


def test_lock_wheel_digest_matches_the_audited_artifact() -> None:
    manifest = BindingManifest.load(ROOT / "ops" / "config" / "memory-binding.json")
    url, digest = seal._lock_wheel(ROOT / "uv.lock", manifest.distribution)
    assert digest == manifest.artifact_sha256
    assert url.endswith("l9_graphite_memory-2.3.1-py3-none-any.whl")


def test_hash_from_direct_url_reads_pip_archive_hashes() -> None:
    digest = "b" * 64
    assert (
        seal._hash_from_direct_url(
            {"archive_info": {"hashes": {"sha256": digest}}, "url": "https://example/x.whl"}
        )
        == digest
    )
    assert (
        seal._hash_from_direct_url(
            {"archive_info": {"hash": f"sha256={digest}"}, "url": "https://example/x.whl"}
        )
        == digest
    )
    assert seal._hash_from_direct_url({"url": "https://example/x.whl", "archive_info": {}}) is None


def test_site_packages_uses_sys_prefix_not_resolved_symlink(tmp_path: Path) -> None:
    """A uv venv python is a symlink into the shared CPython; do not follow it."""
    venv = tmp_path / "venv"
    site = venv / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    python = venv / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)

    def fake_prefix(_interpreter: Path) -> Path:
        return venv

    monkey_prefix = seal._prefix
    seal._prefix = fake_prefix  # type: ignore[method-assign]
    try:
        assert seal._site_packages(python) == site
    finally:
        seal._prefix = monkey_prefix  # type: ignore[method-assign]


def test_already_sealed_false_when_direct_url_missing(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    site = venv / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    python = venv / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    original = seal._prefix
    seal._prefix = lambda _i: venv  # type: ignore[method-assign]
    try:
        assert seal.already_sealed(python, "a" * 64, "2.3.1") is False
    finally:
        seal._prefix = original  # type: ignore[method-assign]


def test_check_only_matches_already_sealed() -> None:
    interpreter = ROOT / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        pytest.skip("worktree venv not materialized")
    manifest = BindingManifest.load(ROOT / "ops" / "config" / "memory-binding.json")
    sealed = seal.already_sealed(
        interpreter, manifest.artifact_sha256, manifest.expected_package_version
    )
    rc = seal.seal(root=ROOT, interpreter=interpreter, check_only=True)
    assert rc == (0 if sealed else 1)
