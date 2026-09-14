"""Seal reads installer provenance; it does not invent a digest."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from ops.memory import seal_artifact_provenance as seal
from ops.memory.runtime_binding import BindingManifest

ROOT = Path(__file__).resolve().parents[3]


def test_lock_wheel_digest_matches_the_audited_artifact() -> None:
    manifest = BindingManifest.load(ROOT / "ops" / "config" / "memory-binding.json")
    url, digest = seal._lock_wheel(ROOT / "uv.lock", manifest.distribution)
    assert digest == manifest.artifact_sha256
    assert url.endswith(f"l9_graphite_memory-{manifest.expected_package_version}-py3-none-any.whl")


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


def _fake_venv(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A venv-shaped tree: (venv, site-packages, bin/python)."""
    venv = tmp_path / "venv"
    site = venv / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    python = venv / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    return venv, site, python


def test_site_packages_uses_sys_prefix_not_resolved_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A uv venv python is a symlink into the shared CPython; do not follow it."""
    venv, site, python = _fake_venv(tmp_path)
    monkeypatch.setattr(seal, "_prefix", lambda _interpreter: venv)
    assert seal._site_packages(python) == site


def test_already_sealed_false_when_direct_url_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv, _site, python = _fake_venv(tmp_path)
    monkeypatch.setattr(seal, "_prefix", lambda _interpreter: venv)
    assert seal.already_sealed(python, "a" * 64, "2.3.1") is False


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


# --- bounded, noninteractive subprocesses (SessionStart must never hang) ------


class _Recorder:
    """Stand-in for subprocess.run that records every call and answers rc 0."""

    def __init__(self, *, stdout: str = "") -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.stdout = stdout

    def __call__(self, cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(cmd), kwargs))
        return subprocess.CompletedProcess(cmd, 0, self.stdout, "")


def _assert_bounded(kwargs: dict[str, object]) -> None:
    assert isinstance(kwargs.get("timeout"), (int, float)) and kwargs["timeout"] > 0
    assert kwargs.get("stdin") is subprocess.DEVNULL
    env = kwargs.get("env")
    assert isinstance(env, dict)
    assert env["PIP_NO_INPUT"] == "1"
    assert env["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"


def test_prefix_probe_is_bounded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recorder = _Recorder(stdout=f"{tmp_path}\n")
    monkeypatch.setattr(seal.subprocess, "run", recorder)
    assert seal._prefix(tmp_path / "python") == tmp_path
    ((cmd, kwargs),) = recorder.calls
    assert cmd[1:] == ["-c", "import sys; print(sys.prefix)"]
    assert kwargs["timeout"] == seal.PROBE_TIMEOUT_S
    _assert_bounded(kwargs)


def test_ensure_pip_probe_then_bootstrap_are_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = tmp_path / "python"
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((list(cmd), kwargs))
        rc = 1 if cmd[1:] == ["-m", "pip", "--version"] else 0
        return subprocess.CompletedProcess(cmd, rc, "", "")

    monkeypatch.setattr(seal.subprocess, "run", run)
    assert seal._ensure_pip(python).returncode == 0
    (probe_cmd, probe_kwargs), (boot_cmd, boot_kwargs) = calls
    assert probe_cmd[1:] == ["-m", "pip", "--version"]
    assert probe_kwargs["timeout"] == seal.PROBE_TIMEOUT_S
    assert boot_cmd[1:] == ["-m", "ensurepip", "--upgrade"]
    assert boot_kwargs["timeout"] == seal.BOOTSTRAP_TIMEOUT_S
    _assert_bounded(probe_kwargs)
    _assert_bounded(boot_kwargs)


def test_timeout_maps_to_nonzero_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, float(kwargs["timeout"]))  # type: ignore[arg-type]

    monkeypatch.setattr(seal.subprocess, "run", run)
    completed = seal._run(["python", "-m", "pip", "--version"], timeout=7)
    assert completed.returncode == seal.TIMEOUT_RC
    assert "timed out after 7s" in completed.stderr
    assert seal._ensure_pip(Path("python")).returncode == seal.TIMEOUT_RC
    with pytest.raises(RuntimeError, match="timed out"):
        seal._prefix(Path("python"))


def test_launch_failure_maps_to_nonzero_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(seal.subprocess, "run", run)
    completed = seal._run(["/nowhere/python", "-m", "pip"], timeout=1)
    assert completed.returncode == seal.LAUNCH_FAILURE_RC
    assert "failed to start /nowhere/python" in completed.stderr
    with pytest.raises(RuntimeError, match="failed to start"):
        seal._prefix(Path("/nowhere/python"))


def _seal_with_fake_installer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    run: object,
    *,
    sealed_after_install: bool = True,
) -> tuple[int, str, list[list[str]]]:
    """Drive seal() past its real manifest/lock checks with a fake pip."""

    manifest = BindingManifest.load(ROOT / "ops" / "config" / "memory-binding.json")
    interpreter = ROOT / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        pytest.skip("worktree venv not materialized")
    answers = iter([False, sealed_after_install])
    monkeypatch.setattr(seal, "already_sealed", lambda *_a: next(answers))
    recorded: list[list[str]] = []

    def recording_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded.append(list(cmd))
        return run(cmd, **kwargs)  # type: ignore[operator]

    monkeypatch.setattr(seal.subprocess, "run", recording_run)
    rc = seal.seal(root=ROOT, interpreter=interpreter)
    err = capsys.readouterr().err
    assert manifest.artifact_sha256
    return rc, err, recorded


def test_install_is_noninteractive_and_bounded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[dict[str, object]] = []

    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "pip 25.0\n", "")

    rc, err, recorded = _seal_with_fake_installer(monkeypatch, capsys, run)
    assert rc == 0, err
    assert "seal: recorded PEP 610 hash" in err
    install = next(cmd for cmd in recorded if cmd[1:4] == ["-m", "pip", "install"])
    manifest = BindingManifest.load(ROOT / "ops" / "config" / "memory-binding.json")
    assert "--no-input" in install
    assert "--no-deps" in install and "--force-reinstall" in install
    assert install[-1].endswith(f"#sha256={manifest.artifact_sha256}")
    for kwargs in seen:
        _assert_bounded(kwargs)
    assert seen[-1]["timeout"] == seal.INSTALL_TIMEOUT_S


def test_install_timeout_is_an_actionable_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[1:4] == ["-m", "pip", "install"]:
            raise subprocess.TimeoutExpired(cmd, float(kwargs["timeout"]))  # type: ignore[arg-type]
        return subprocess.CompletedProcess(cmd, 0, "pip 25.0\n", "")

    rc, err, _recorded = _seal_with_fake_installer(monkeypatch, capsys, run)
    assert rc == 1
    assert "seal: pip install failed: timed out after" in err


def test_unprobeable_interpreter_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    interpreter = ROOT / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        pytest.skip("worktree venv not materialized")

    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, float(kwargs["timeout"]))  # type: ignore[arg-type]

    monkeypatch.setattr(seal.subprocess, "run", run)
    assert seal.seal(root=ROOT, interpreter=interpreter, check_only=True) == 1
    assert "seal: cannot inspect the locked interpreter" in capsys.readouterr().err


# --- ensure_uv_environment.sh seals with the interpreter its guard checks ----

ENSURE = ROOT / "ops" / "scripts" / "ensure_uv_environment.sh"


def _fake_governance_root(tmp_path: Path, *, shims: tuple[str, ...]) -> tuple[Path, Path, Path]:
    """A fixture root with a fake ``uv`` and a stub seal module.

    ``uv sync`` materializes only the requested ``.venv/bin`` shims; each shim
    stamps its own name into the environment so the stub seal module can report
    which interpreter actually ran it.
    """

    root = tmp_path / "governance"
    binary = tmp_path / "bin"
    marker = tmp_path / "seal-invocation.json"
    (root / "ops" / "memory").mkdir(parents=True)
    binary.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\n', encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "ops" / "__init__.py").write_text("", encoding="utf-8")
    (root / "ops" / "memory" / "__init__.py").write_text("", encoding="utf-8")
    (root / "ops" / "memory" / "seal_artifact_provenance.py").write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['SEAL_MARKER']).write_text(json.dumps({\n"
        "    'shim': os.environ.get('L9_TEST_SHIM'), 'argv': sys.argv[1:]}))\n"
        "raise SystemExit(int(os.environ.get('SEAL_EXIT', '0')))\n",
        encoding="utf-8",
    )
    shim_lines = "\n".join(
        f'mkdir -p "$UV_TEST_ROOT/.venv/bin"\n'
        f"printf '%s\\n' '#!/usr/bin/env bash' 'export L9_TEST_SHIM={name}' "
        f'\'exec python3 "$@"\' > "$UV_TEST_ROOT/.venv/bin/{name}"\n'
        f'chmod +x "$UV_TEST_ROOT/.venv/bin/{name}"'
        for name in shims
    )
    (binary / "uv").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'if [ "${1:-}" = "--version" ]; then echo "uv 9.9.9-fixture"; exit 0; fi\n'
        'if [ "${1:-}" = "sync" ]; then\n' + shim_lines + "\nexit 0\nfi\nexit 2\n",
        encoding="utf-8",
    )
    (binary / "uv").chmod(0o755)
    return root, binary, marker


def _run_ensure(root: Path, binary: Path, marker: Path, *args: str, **env: str) -> str:
    # cwd=root: `python -m ops.memory...` puts the cwd ahead of PYTHONPATH, and
    # this checkout's real ops package must not shadow the fixture's stub.
    completed = subprocess.run(
        ["bash", str(ENSURE), str(root), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ.get('PATH', '')}",
            "UV_TEST_ROOT": str(root),
            "SEAL_MARKER": str(marker),
            **env,
        },
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stderr


@pytest.mark.parametrize("shims", [("python3",), ("python3", "python")])
def test_ensure_uv_environment_seals_with_the_guarded_interpreter(
    tmp_path: Path, shims: tuple[str, ...]
) -> None:
    """One-shim and dual-shim venvs both seal through .venv/bin/python3."""

    root, binary, marker = _fake_governance_root(tmp_path, shims=shims)
    _run_ensure(root, binary, marker)  # sync path
    first = json.loads(marker.read_text(encoding="utf-8"))
    assert first["shim"] == "python3"
    assert first["argv"] == [
        "--root",
        str(root),
        "--interpreter",
        str(root / ".venv" / "bin" / "python3"),
    ]
    marker.unlink()
    _run_ensure(root, binary, marker)  # cached path: guard passed, seal ran again
    assert json.loads(marker.read_text(encoding="utf-8"))["shim"] == "python3"
    marker.unlink()
    _run_ensure(root, binary, marker, "check")  # check mode never installs
    assert not marker.exists()


def test_ensure_uv_environment_reports_a_failed_seal(tmp_path: Path) -> None:
    root, binary, marker = _fake_governance_root(tmp_path, shims=("python3",))
    stderr = _run_ensure(root, binary, marker, SEAL_EXIT="3")
    assert "UV: memory artifact seal did not complete (rc=3)" in stderr
    assert marker.exists()
