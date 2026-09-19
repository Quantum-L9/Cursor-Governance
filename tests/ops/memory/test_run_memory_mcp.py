"""run_memory_mcp.sh bind-then-execs a proven interpreter, or exits nonzero.

The wrapper is Claude Code's spawn command. It must not launch a guess when
runtime_binding is unbound, and when a binding proves it must exec that
interpreter with the forwarded argv (the package's managed server args).
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "ops" / "memory" / "run_memory_mcp.sh"
BINDER = REPO_ROOT / "ops" / "scripts" / "lib" / "bind_memory_interpreter.sh"

_STUB = """
import os

class _Binding:
    def __init__(self, status, interpreter):
        self.status = status
        self.interpreter = interpreter

def resolve_runtime_binding(**_kw):
    fallback = os.environ.get("STUB_FALLBACK", "").strip()
    if fallback:
        return _Binding("exact", fallback)
    return _Binding("unbound", None)
"""


def _stub_gov(tmp_path: Path) -> Path:
    gov = tmp_path / "gov"
    memory = gov / "ops" / "memory"
    lib = gov / "ops" / "scripts" / "lib"
    memory.mkdir(parents=True)
    lib.mkdir(parents=True)
    (gov / "CANONICAL_LAW.md").write_text("# stub\n", encoding="utf-8")
    (gov / "ops" / "__init__.py").write_text("", encoding="utf-8")
    (memory / "__init__.py").write_text("", encoding="utf-8")
    (memory / "runtime_binding.py").write_text(_STUB, encoding="utf-8")
    shutil.copy(BINDER, lib / "bind_memory_interpreter.sh")
    return gov


def _executable(path: Path, body: str = "#!/bin/sh\nprintf 'LAUNCH %s\\n' \"$*\"\n") -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _run(
    gov: Path, env: dict[str, str], args: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    full_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(gov.parent),
        "L9_GOVERNANCE_DIR": str(gov),
        **env,
    }
    return subprocess.run(
        ["bash", str(WRAPPER), *(args or [])],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(gov),
        check=False,
        timeout=60,
    )


def test_wrapper_file_is_executable() -> None:
    assert WRAPPER.is_file()
    assert os.access(WRAPPER, os.X_OK)


def test_unbound_interpreter_exits_nonzero(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    result = _run(gov, {})
    assert result.returncode != 0
    assert "unbound" in result.stderr


def test_proven_interpreter_is_execd_with_forwarded_argv(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    launched = _executable(tmp_path / "proven-python")
    result = _run(
        gov,
        {"STUB_FALLBACK": str(launched)},
        args=["-m", "l9_graphite_memory.server", "--transport", "stdio"],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ("LAUNCH -m l9_graphite_memory.server --transport stdio")
