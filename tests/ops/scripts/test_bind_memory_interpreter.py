"""bind_l9_memory_interpreter fails closed (PR #548 review, F-548-006).

Every call either exports an interpreter proven by THIS resolution or leaves
``L9_MEMORY_INTERPRETER`` unset. The first version only assigned inside
``if [ -n "$interp" ]``, so a cached shell exporting an obsolete path kept it
when resolution failed and the stale value went on to satisfy the projection's
``_requires_env``, render the memory server, and be persisted again.

The helper is exercised against a stub ``ops.memory.runtime_binding`` whose
verdict is scripted through the environment, so no real memory package, venv
or manifest is involved: the property under test is the shell helper's
handling of the verdict, not the resolver.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BINDER = REPO_ROOT / "ops" / "scripts" / "lib" / "bind_memory_interpreter.sh"

# Verdict script: an interpreter whose path is listed in STUB_GOOD_INTERPRETERS
# (colon-separated) resolves ``exact`` to itself; when L9_MEMORY_INTERPRETER is
# unset the stub stands in for the governance python and resolves to
# STUB_FALLBACK when that is set; everything else is unbound.
_STUB = """
import os

class _Binding:
    def __init__(self, status, interpreter):
        self.status = status
        self.interpreter = interpreter

def resolve_runtime_binding(**_kw):
    good = [p for p in os.environ.get("STUB_GOOD_INTERPRETERS", "").split(":") if p]
    configured = os.environ.get("L9_MEMORY_INTERPRETER", "").strip()
    if configured:
        if configured in good:
            return _Binding("exact", configured)
        return _Binding("unbound", None)
    fallback = os.environ.get("STUB_FALLBACK", "").strip()
    if fallback:
        return _Binding("exact", fallback)
    return _Binding("unbound", None)
"""


def _stub_gov(tmp_path: Path) -> Path:
    gov = tmp_path / "gov"
    memory = gov / "ops" / "memory"
    memory.mkdir(parents=True)
    (gov / "ops" / "__init__.py").write_text("", encoding="utf-8")
    (memory / "__init__.py").write_text("", encoding="utf-8")
    (memory / "runtime_binding.py").write_text(_STUB, encoding="utf-8")
    return gov


def _executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _bind(gov: Path, env: dict[str, str]) -> str:
    """Source the helper, bind, print the resulting variable (or <unset>)."""
    script = (
        f". {BINDER}\n"
        f"bind_l9_memory_interpreter {os.fspath(REPO_ROOT / '.venv' / 'bin' / 'python3')!r} "
        f"{os.fspath(gov)!r}\n"
        'printf "%s" "${L9_MEMORY_INTERPRETER-<unset>}"\n'
    )
    py = REPO_ROOT / ".venv" / "bin" / "python3"
    if not py.is_file():
        import sys

        script = script.replace(repr(os.fspath(py)), repr(sys.executable))
    full_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(gov.parent),
        **env,
    }
    # cwd is the stub tree, never the repository: `python -c` puts the working
    # directory ahead of PYTHONPATH, and the real ops.memory must not shadow the
    # scripted verdict.
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(gov),
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_stale_export_is_cleared_when_nothing_resolves(tmp_path: Path) -> None:
    """The closing property: a stale value cannot survive a failed rebinding."""
    gov = _stub_gov(tmp_path)
    out = _bind(gov, {"L9_MEMORY_INTERPRETER": str(tmp_path / "deleted-venv" / "bin" / "python")})
    assert out == "<unset>"


def test_stale_export_is_replaced_by_the_freshly_proven_interpreter(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    fresh = _executable(tmp_path / "fresh-python")
    out = _bind(
        gov,
        {
            "L9_MEMORY_INTERPRETER": str(tmp_path / "deleted-venv" / "bin" / "python"),
            "STUB_FALLBACK": str(fresh),
        },
    )
    assert out == str(fresh)


def test_a_pinned_interpreter_that_still_proves_is_kept(tmp_path: Path) -> None:
    """A deliberately pinned, valid interpreter is re-proven, not displaced."""
    gov = _stub_gov(tmp_path)
    pinned = _executable(tmp_path / "pinned-python")
    other = _executable(tmp_path / "gov-python")
    out = _bind(
        gov,
        {
            "L9_MEMORY_INTERPRETER": str(pinned),
            "STUB_GOOD_INTERPRETERS": str(pinned),
            "STUB_FALLBACK": str(other),
        },
    )
    assert out == str(pinned)


def test_a_proven_path_that_is_not_executable_is_not_exported(tmp_path: Path) -> None:
    """The export names something the MCP entry can launch, or nothing."""
    gov = _stub_gov(tmp_path)
    not_exec = tmp_path / "python-but-not-executable"
    not_exec.write_text("", encoding="utf-8")
    out = _bind(gov, {"STUB_FALLBACK": str(not_exec)})
    assert out == "<unset>"


def test_retired_provider_transport_is_stripped(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    script = (
        f". {BINDER}\n"
        f"bind_l9_memory_interpreter /nonexistent/python {os.fspath(gov)!r}\n"
        'printf "%s|%s" "${GRAPHITI_MCP_URL-<unset>}" "${GRAPHITI_MCP_TOKEN-<unset>}"\n'
    )
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "GRAPHITI_MCP_URL": "x",
            "GRAPHITI_MCP_TOKEN": "y",
        },
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "<unset>|<unset>"
