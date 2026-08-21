"""One execution environment for worker-side and controller-side validation.

Both sides used to shell out through ``bash -lc``. A login shell re-runs the
user's profile, so PATH — and therefore ``python3`` — was whatever the profile
happened to export, not the interpreter the campaign was launched with. A
worker could pass a pytest command that the controller then failed, purely
because the two resolved different interpreters.

This module resolves the environment once and hands the same resolution to both
sides. Commands run under ``bash -c`` (no ``-l``), with the resolved
interpreter's directory prepended to PATH, so ``python3`` in a validation
command means the campaign's interpreter.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_VALIDATION_TIMEOUT_S = 300
_ENV_OVERRIDE = "L9_PE_PYTHON"
_EVIDENCE_TAIL = 2000
_STREAM_TAIL = 8000


def _venv_root(python: Path) -> Path | None:
    """Return the virtualenv root owning ``python``, or None outside a venv."""
    parent = python.parent
    if parent.name != "bin" and parent.name.lower() != "scripts":
        return None
    root = parent.parent
    return root if (root / "pyvenv.cfg").is_file() else None


def _keep_venv_shim(candidate: Path) -> Path:
    """Keep the venv entrypoint. ``Path.resolve()`` follows it to Homebrew.

    Invoking the Cellar interpreter drops ``pyvenv.cfg``, so ``import yaml``
    and other locked extras disappear even though the donor venv has them.
    """
    absolute = candidate.absolute()
    root = _venv_root(absolute)
    if root is not None:
        return root.resolve() / absolute.parent.name / absolute.name
    return absolute.resolve()


def is_l9_isolate_workspace(path: Path) -> bool:
    """Match ops/scripts/resolve_governance_paths.sh is_l9_isolate_workspace."""
    workspace = path.resolve()
    l9 = (Path.home() / ".l9").resolve()
    try:
        parts = workspace.relative_to(l9).parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] in {"gov-worktrees", "programs"}


def _donor_toolchain_python() -> Path | None:
    roots: list[Path] = []
    override = os.environ.get("GOV_TOOLCHAIN_ROOT", "").strip()
    if override:
        roots.append(Path(override))
    roots.append(Path.home() / ".cursor-governance")
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        for exe in (".venv/bin/python3", ".venv/bin/python", ".venv/Scripts/python.exe"):
            candidate = resolved / exe
            if candidate.is_file():
                return _keep_venv_shim(candidate)
    return None


def _discover_python(cwd: Path | None) -> Path:
    """Resolve the interpreter validation commands must see as ``python3``."""
    override = os.environ.get(_ENV_OVERRIDE, "").strip()
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return _keep_venv_shim(candidate)
        located = shutil.which(override)
        if located:
            return _keep_venv_shim(Path(located))
    # Isolates are not uv projects. Their local .venv, if any, is pytest-less.
    # Validation must use the donor toolchain that owns the locked extras.
    if cwd is not None and is_l9_isolate_workspace(cwd):
        donor = _donor_toolchain_python()
        if donor is not None:
            return donor
    # An active venv wins over sys.executable so a controller launched from the
    # system interpreter still validates against the project's dependencies.
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    if virtual_env:
        for name in ("bin/python3", "bin/python", "Scripts/python.exe"):
            candidate = Path(virtual_env) / name
            if candidate.is_file():
                return _keep_venv_shim(candidate)
    if cwd is not None:
        for name in (".venv", "venv"):
            for exe in ("bin/python3", "bin/python", "Scripts/python.exe"):
                candidate = cwd / name / exe
                if candidate.is_file():
                    return _keep_venv_shim(candidate)
    return _keep_venv_shim(Path(sys.executable))


@dataclass(frozen=True)
class ExecEnv:
    """A resolved, reproducible environment for running validation commands."""

    python: Path
    env: dict[str, str] = field(default_factory=dict)

    @property
    def bin_dir(self) -> Path:
        return self.python.parent

    def describe(self) -> dict[str, Any]:
        """Resolution detail worth returning with a failure, not just a code."""
        return {
            "python": str(self.python),
            "python_version": self.python_version(),
            "bin_dir": str(self.bin_dir),
            "virtual_env": self.env.get("VIRTUAL_ENV") or None,
            "path_head": self.env.get("PATH", "").split(os.pathsep)[0],
        }

    def python_version(self) -> str:
        completed = subprocess.run(
            [str(self.python), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        return completed.stdout.strip() or "unknown"


def resolve_exec_env(cwd: Path | None = None) -> ExecEnv:
    """Resolve the single environment both validation sides must use."""
    python = _discover_python(cwd)
    env = dict(os.environ)
    bin_dir = str(python.parent)
    path = env.get("PATH", os.defpath)
    if path.split(os.pathsep)[0] != bin_dir:
        env["PATH"] = os.pathsep.join([bin_dir, *[p for p in path.split(os.pathsep) if p]])
    venv = _venv_root(python)
    if venv is not None:
        env["VIRTUAL_ENV"] = str(venv)
    else:
        env.pop("VIRTUAL_ENV", None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    # A user site-packages directory is not part of the resolved environment and
    # would let the two sides diverge again.
    env["PYTHONNOUSERSITE"] = "1"
    env["L9_PE_PYTHON"] = str(python)
    return ExecEnv(python=python, env=env)


def run_validation_command(
    command: str,
    cwd: Path,
    *,
    exec_env: ExecEnv | None = None,
    timeout: int = DEFAULT_VALIDATION_TIMEOUT_S,
) -> dict[str, Any]:
    """Run one contract-declared validation command and report what happened."""
    resolved = exec_env or resolve_exec_env(cwd)
    try:
        completed = subprocess.run(  # noqa: S603 - contract-declared command, no login shell
            ["bash", "-c", command],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=resolved.env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        return {
            "command": command,
            "status": "FAIL",
            "exit_code": 124,
            "stdout": stdout[-_STREAM_TAIL:],
            "stderr": f"validation command timed out after {timeout}s",
            "exec_env": resolved.describe(),
        }
    result: dict[str, Any] = {
        "command": command,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-_STREAM_TAIL:],
        "stderr": (completed.stderr or "")[-_STREAM_TAIL:],
    }
    if completed.returncode != 0:
        result["exec_env"] = resolved.describe()
    return result


def to_attempt_result(result: dict[str, Any]) -> dict[str, Any]:
    """Shrink a validation result to the attempt-receipt shape."""
    evidence = ((result.get("stdout") or "") + (result.get("stderr") or "")).strip()
    entry: dict[str, Any] = {
        "command": result["command"],
        "status": result["status"],
        "exit_code": result["exit_code"],
        "evidence": evidence[-_EVIDENCE_TAIL:] or None,
    }
    return entry
