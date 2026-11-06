"""tools.yaml loader, CI-drift validator and installer contracts."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import install  # noqa: E402
import manifest  # noqa: E402
import validate_manifest  # noqa: E402


def test_repository_manifest_loads_and_pins_every_release_by_sha256() -> None:
    loaded = manifest.load()
    assert set(loaded.lanes) >= {
        "codeql",
        "semgrep-l9",
        "semgrep-pro",
        "shellcheck",
        "actionlint",
        "zizmor",
    }
    for tool in loaded.tools.values():
        if tool.method.startswith("release_"):
            assert tool.url.startswith("https://")
            assert len(tool.sha256) == 64
    for lane in loaded.lanes.values():
        assert lane.tool in loaded.tools


def test_repository_ci_pins_are_current() -> None:
    assert validate_manifest.check() == []


def test_drift_validator_fails_when_ci_moves_without_a_repin(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "codeql.yml").write_text("uses: org/repo/.github/workflows/x.yml@0000000\n")
    (tmp_path / "biome.json").write_text(
        '{"$schema": "https://biomejs.dev/schemas/2.5.8/schema.json"}\n'
    )
    (tmp_path / "requirements.txt").write_text("pip-audit==2.10.1\n")
    (tmp_path / "pyproject.toml").write_text('"ruff==0.16.1"\n')
    problems = validate_manifest.check(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("codeql:")


def test_lane_glob_matches_basename_and_path_patterns() -> None:
    lanes = manifest.load().lanes
    assert lanes["shellcheck"].matches("ops/scripts/x.sh")
    assert lanes["actionlint"].matches(".github/workflows/ci.yml")
    assert not lanes["actionlint"].matches("docs/ci.yml")
    assert lanes["osv-scanner"].matches("uv.lock")


def test_kill_switch() -> None:
    assert manifest.disabled({"L9_CI_PARITY": "0"})
    assert not manifest.disabled({})


def _fake_tool_manifest(tmp_path: Path, payload: bytes, sha: str) -> manifest.Manifest:
    tool = manifest.Tool(
        name="fake",
        version="1.0.0",
        method="release_binary",
        binary="fake",
        version_cmd=("--version",),
        expect="fake 1.0.0",
        url="https://example.invalid/fake",
        sha256=sha,
    )
    (tmp_path / "dl").mkdir()
    (tmp_path / "dl" / "fake").write_bytes(payload)
    return manifest.Manifest(
        install_root=tmp_path / "root",
        bin_dir=tmp_path / "bin",
        cache_root=tmp_path / "cache",
        tools={"fake": tool},
        lanes={},
    )


PAYLOAD = b"#!/bin/sh\necho 'fake 1.0.0'\n"


def test_install_verifies_sha_records_state_links_and_is_idempotent(tmp_path: Path) -> None:
    loaded = _fake_tool_manifest(tmp_path, PAYLOAD, hashlib.sha256(PAYLOAD).hexdigest())
    loaded.install_root.mkdir()
    assert install.install_tool(loaded, "fake", tmp_path / "dl") == "INSTALLED"
    state = json.loads(loaded.state_path.read_text())
    assert state["fake"]["version"] == "1.0.0"
    assert (loaded.bin_dir / "fake").resolve() == Path(state["fake"]["path"]).resolve()
    assert install.install_tool(loaded, "fake", tmp_path / "dl") == "OK"


def test_install_refuses_a_sha_mismatch_and_writes_nothing(tmp_path: Path) -> None:
    loaded = _fake_tool_manifest(tmp_path, PAYLOAD, "0" * 64)
    loaded.install_root.mkdir()
    with pytest.raises(install.InstallError, match="sha256 mismatch"):
        install.install_tool(loaded, "fake", tmp_path / "dl")
    assert not loaded.state_path.exists()
    assert not (loaded.bin_dir / "fake").exists()


def test_install_never_clobbers_a_foreign_file_on_path(tmp_path: Path) -> None:
    loaded = _fake_tool_manifest(tmp_path, PAYLOAD, hashlib.sha256(PAYLOAD).hexdigest())
    loaded.install_root.mkdir()
    loaded.bin_dir.mkdir()
    foreign = loaded.bin_dir / "fake"
    foreign.write_text("operator's own binary")
    assert install.install_tool(loaded, "fake", tmp_path / "dl") == "INSTALLED"
    assert foreign.read_text() == "operator's own binary"
    assert loaded.resolve("fake") is not None  # resolved from state, not PATH


def test_unpinned_scanners_are_advisory() -> None:
    lanes = manifest.load().lanes
    for name in ("shellcheck", "actionlint", "zizmor", "yamllint", "osv-scanner"):
        assert lanes[name].block == (), name
    assert lanes["codeql"].block


def test_core_blocking_checks_block_at_exact_core_pins() -> None:
    """Analyze (central Core) blocks on Biome and its SDK Semgrep gate, at exact pins."""
    loaded = manifest.load()
    for name in ("biome", "semgrep-l9"):
        lane = loaded.lanes[name]
        assert lane.block == ("error",), name
        contains = loaded.tools[lane.tool].ci_ref["contains"]
        assert contains and not validate_manifest._RANGE.search(contains), name
    sdk = loaded.lanes["semgrep-l9"]
    assert sdk.tool == "l9-ci" and sdk.extra["provider"] == "semgrep"
    assert sdk.extra["scope"] == "whole-tree"
    assert loaded.lanes["biome"].extra["scope"] == "changed-files"
    assert loaded.tools["l9-ci"].package.startswith("git+https://")
    assert len(loaded.tools["l9-ci"].version) == 40


def test_uv_tool_spec_pins_pypi_by_version_and_git_by_commit() -> None:
    loaded = manifest.load()
    assert install.uv_tool_spec(loaded.tools["semgrep"]) == "semgrep==1.171.0"
    sdk = loaded.tools["l9-ci"]
    assert install.uv_tool_spec(sdk) == f"{sdk.package}@{sdk.version}"


def _remote_manifest(tmp_path: Path) -> Path:
    yml = tmp_path / "tools.yaml"
    yml.write_text(
        "schema: l9.ci-parity.tools.v1\n"
        "tools:\n  sdk:\n    version: '1'\n    method: uv_tool\n    package: x\n"
        "    binary: x\n    version_cmd: [--help]\n    expect: x\n    ci_ref:\n"
        "      repo: Quantum-L9/l9-ci-core\n      ref: main\n      path: org-ci.yml\n"
        "      contains: \"'abc'\"\n"
        "lanes: {}\n"
    )
    return yml


def test_remote_ci_ref_is_skipped_offline(tmp_path: Path) -> None:
    assert validate_manifest.check(tmp_path, _remote_manifest(tmp_path)) == []


def test_remote_ci_ref_fails_when_core_moved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yml = _remote_manifest(tmp_path)
    monkeypatch.setattr(validate_manifest, "_remote_text", lambda ref: "sdk-revision: 'def'")
    problems = validate_manifest.check(tmp_path, yml, remote=True)
    assert len(problems) == 1 and "Quantum-L9/l9-ci-core@main:org-ci.yml" in problems[0]
    monkeypatch.setattr(validate_manifest, "_remote_text", lambda ref: "x || 'abc' }}")
    assert validate_manifest.check(tmp_path, yml, remote=True) == []


def test_unreadable_remote_ci_ref_is_a_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreachable(ref: dict[str, str]) -> str:
        raise OSError("git transport also failed")

    monkeypatch.setattr(validate_manifest, "_remote_text", unreachable)
    problems = validate_manifest.check(tmp_path, _remote_manifest(tmp_path), remote=True)
    assert len(problems) == 1 and "unreadable" in problems[0]


def test_blocking_lane_rejects_a_version_range(tmp_path: Path) -> None:
    tool = manifest.Tool(
        name="semgrep",
        version="1",
        method="uv_tool",
        binary="semgrep",
        version_cmd=("--version",),
        expect="1",
        ci_ref={"path": "x", "contains": "semgrep>=1.100.0,<2.0.0"},
    )
    lane = manifest.Lane(
        name="semgrep-l9",
        tool="semgrep",
        tier="heavy",
        globs=("*.py",),
        block=("error",),
        weight=1,
    )
    loaded = manifest.Manifest(
        install_root=tmp_path,
        bin_dir=tmp_path,
        cache_root=tmp_path,
        tools={"semgrep": tool},
        lanes={"semgrep-l9": lane},
    )
    problems = validate_manifest._blocking_identity(loaded)
    assert problems and "version range" in problems[0]
