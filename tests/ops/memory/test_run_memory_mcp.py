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

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "ops" / "memory" / "run_memory_mcp.sh"
BINDER = REPO_ROOT / "ops" / "scripts" / "lib" / "bind_memory_interpreter.sh"
EXPORTER = REPO_ROOT / "ops" / "memory" / "export_agent_assertion_env.sh"
#: The launcher starts the server only with the signed agent door (every memory
#: names its author); these stand in for a minted door (presence is checked,
#: values never read here).
#: Identity comes from the host marker (Claude Code Desktop), never a pasted id.
DESKTOP = {"CLAUDECODE": "1"}
DOOR = {
    **DESKTOP,
    "L9_MEMORY_AGENTS_DOOR_SECRET": "stub-door",
    "L9_MEMORY_AGENT_ASSERTION": "stub-assertion",
    "L9_MEMORY_AGENT_SIGNING_KEYS_JSON": "{}",
    "L9_MEMORY_AGENT_GRANTS_JSON": "{}",
    "L9_MEMORY_IDENTITY_ASSERTION_JSON": "{}",
    "L9_MEMORY_IDENTITY_ASSERTION_HMAC": "stub-hmac",
}
DOOR_NAMES = tuple(name for name in DOOR if name not in DESKTOP)

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
    shutil.copy(EXPORTER, memory / "export_agent_assertion_env.sh")
    shutil.copy(REPO_ROOT / "ops" / "memory" / "agent_identity.py", memory / "agent_identity.py")
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
        "TMPDIR": str(gov.parent),
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
        {"STUB_FALLBACK": str(launched), **DOOR},
        args=["-m", "l9_graphite_memory.server", "--transport", "stdio"],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ("LAUNCH -m l9_graphite_memory.server --transport stdio")


def test_a_proven_interpreter_without_a_door_is_not_launched(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    launched = _executable(tmp_path / "proven-python")
    env = {"STUB_FALLBACK": str(launched), **DESKTOP}
    result = _run(gov, env, args=["-m", "x"])
    assert result.returncode == 1
    assert "LAUNCH" not in result.stdout
    assert "a memory must name the agent that wrote it" in result.stderr


def test_a_pasted_derived_identity_without_host_markers_is_not_launched(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    launched = _executable(tmp_path / "proven-python")
    door = {k: v for k, v in DOOR.items() if k not in DESKTOP}
    env = {"STUB_FALLBACK": str(launched), **door, "L9_MEMORY_AGENT_ID": "claude-code"}
    result = _run(gov, env, args=["-m", "x"])
    assert result.returncode == 1
    assert "LAUNCH" not in result.stdout
    assert "derived from host markers, never configured" in result.stderr


#: An interpreter that also stands in for print_agent_assertion_env.py: given
#: that helper it either refuses (exit 2) or writes a six-value env file and
#: prints its path, as the real helper does. As the server it reports, by name
#: only, which door values it was exec'd with.
_DOOR_LIST = " ".join(DOOR_NAMES)
_MINTING_PYTHON = f"""#!/bin/sh
case "$1" in
  *print_agent_assertion_env.py)
    if [ "${{STUB_MINT:-}}" = "refuse" ]; then echo "stub helper refused" >&2; exit 2; fi
    f="$(mktemp)"
    for n in {_DOOR_LIST}; do printf "export %s='minted-%s'\\n" "$n" "$n" >> "$f"; done
    echo "$f"
    exit 0 ;;
esac
present=""
for n in {_DOOR_LIST}; do
  eval "v=\\${{$n:-}}"
  [ -n "$v" ] && present="$present $n"
done
printf 'LAUNCH%s\\n' "$present"
"""


def _with_local_maps(gov: Path) -> None:
    """The exporter mints only when both local maps exist (contents are the stub's)."""
    local = gov.parent / ".config" / "l9-memory"
    local.mkdir(parents=True)
    (local / "agent_tokens.local.json").write_text("{}", encoding="utf-8")
    (local / "agent_grants.json").write_text("{}", encoding="utf-8")


@pytest.mark.parametrize("missing", DOOR_NAMES)
def test_each_of_the_six_door_values_is_required_before_exec(tmp_path: Path, missing: str) -> None:
    gov = _stub_gov(tmp_path)
    launched = _executable(tmp_path / "proven-python")
    env = {"STUB_FALLBACK": str(launched), **{k: v for k, v in DOOR.items() if k != missing}}
    result = _run(gov, env, args=["-m", "x"])
    assert result.returncode == 1
    assert "LAUNCH" not in result.stdout
    assert f"(missing {missing})" in result.stderr
    assert "refuse to launch" in result.stderr
    for value in ("stub-door", "stub-assertion", "stub-hmac"):
        assert value not in result.stdout + result.stderr, "values are never printed"


def test_the_exporter_mints_all_six_into_the_execd_process(tmp_path: Path) -> None:
    gov = _stub_gov(tmp_path)
    _with_local_maps(gov)
    launched = _executable(tmp_path / "proven-python", _MINTING_PYTHON)
    result = _run(gov, {"STUB_FALLBACK": str(launched), **DESKTOP}, args=["-m", "x"])
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["LAUNCH", *DOOR_NAMES]
    assert "minted-" not in result.stdout + result.stderr


def test_a_refused_mint_discards_an_inherited_complete_door(tmp_path: Path) -> None:
    """Stale parent values that merely look complete never launch after a failed mint."""
    gov = _stub_gov(tmp_path)
    _with_local_maps(gov)
    launched = _executable(tmp_path / "proven-python", _MINTING_PYTHON)
    env = {"STUB_FALLBACK": str(launched), "STUB_MINT": "refuse", **DOOR}
    result = _run(gov, env, args=["-m", "x"])
    assert result.returncode == 1
    assert "LAUNCH" not in result.stdout
    assert "assertion env NOT minted" in result.stderr
    assert "inherited door values discarded" in result.stderr
    assert "stub-door" not in result.stderr


def test_without_local_maps_an_inherited_complete_door_still_launches(tmp_path: Path) -> None:
    """The pre-launch handoff stays valid: a mint that never ran discards nothing."""
    gov = _stub_gov(tmp_path)
    launched = _executable(tmp_path / "proven-python", _MINTING_PYTHON)
    result = _run(gov, {"STUB_FALLBACK": str(launched), **DOOR}, args=["-m", "x"])
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["LAUNCH", *DOOR_NAMES]
