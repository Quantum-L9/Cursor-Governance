"""Workflow commands run as argument lists and never through a shell.

A ``${var}`` value is one argument, so shell syntax inside it is inert; a
string command is refused rather than handed to a shell; a python step names an
importable function and never executes inline code; and the /wire executor
only ever treats its component as a module name.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load("l9_workflow_runner_no_shell", "workflows/runner.py")
wire = _load("l9_wire_executor_no_shell", "workflows/wire_executor.py")


def _executor(tmp_path: Path, **variables: str):
    return runner.StepExecutor(tmp_path, dict(variables))


def test_a_variable_holding_shell_syntax_stays_one_argument(tmp_path: Path) -> None:
    hostile = "x; touch pwned && echo $(id)"
    result = _executor(tmp_path, value=hostile)._execute_shell(
        {"commands": [["printf", "%s", "${value}"]]}
    )
    assert result.success, result.error
    assert result.output.endswith(hostile)
    assert not (tmp_path / "pwned").exists()


def test_a_string_command_is_refused_not_run(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="argument list"):
        _executor(tmp_path)._execute_shell({"commands": ["touch must-not-exist"]})
    assert not (tmp_path / "must-not-exist").exists()


def test_allow_failure_tolerates_one_command(tmp_path: Path) -> None:
    ok = _executor(tmp_path)._execute_shell(
        {"commands": [{"argv": ["false"], "allow_failure": True}, ["true"]]}
    )
    assert ok.success
    failed = _executor(tmp_path)._execute_shell({"commands": [["false"]]})
    assert not failed.success


def test_python_step_refuses_inline_code(tmp_path: Path) -> None:
    result = _executor(tmp_path)._execute_python({"code": "open('pwned', 'w').write('x')"})
    assert not result.success
    assert not (tmp_path / "pwned").exists()


def test_python_step_calls_a_named_function(tmp_path: Path, monkeypatch) -> None:
    module = types.ModuleType("l9_runner_step_fixture")

    def process(variables, working_dir):
        return {"output": f"ran in {working_dir}", "artifacts": {"n": len(variables)}}

    module.process = process  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "l9_runner_step_fixture", module)
    result = _executor(tmp_path, a="1")._execute_python(
        {"callable": "l9_runner_step_fixture:process"}
    )
    assert result.success, result.error
    assert result.artifacts == {"n": 1}
    bad = _executor(tmp_path)._execute_python({"callable": "os; import x:y"})
    assert not bad.success


def test_inject_and_replace_edit_files_without_sed(tmp_path: Path) -> None:
    (tmp_path / "dst.txt").write_text("a\nb\nc\n", encoding="utf-8")
    (tmp_path / "src.txt").write_text("X\n", encoding="utf-8")
    ex = _executor(tmp_path)
    assert ex._execute_inject(
        {"mappings": [{"from": "src.txt", "to": "dst.txt", "after_line": 1}]}
    ).success
    assert (tmp_path / "dst.txt").read_text() == "a\nX\nb\nc\n"
    assert ex._execute_inject(
        {"mappings": [{"from": "src.txt", "to": "dst.txt", "after_pattern": "^c"}]}
    ).success
    assert (tmp_path / "dst.txt").read_text() == "a\nX\nb\nc\nX\n"
    assert ex._execute_replace(
        {"mappings": [{"from": "src.txt", "to": "dst.txt", "start_line": 2, "end_line": 3}]}
    ).success
    assert (tmp_path / "dst.txt").read_text() == "a\nX\nc\nX\n"


def test_extract_strips_fences(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("intro\n```\nprint(1)\n```\n", encoding="utf-8")
    result = _executor(tmp_path)._execute_extract(
        {
            "source": "doc.md",
            "target_dir": "out",
            "patterns": [{"start_line": 2, "end_line": 4, "output": "a.py"}],
        }
    )
    assert result.success, result.error
    assert (tmp_path / "out" / "a.py").read_text() == "print(1)\n"


@pytest.mark.parametrize(
    "name", ["os; import shutil", 'x"; rm -rf /', "a b", ".relative", "1abc", ""]
)
def test_wire_component_must_be_a_module_path(name: str) -> None:
    with pytest.raises(ValueError):
        wire._module_name(name)


def test_wire_import_check_passes_the_name_as_data() -> None:
    argv = wire._import_check_argv("json.decoder")
    assert argv[-1] == "json.decoder"
    assert "json.decoder" not in argv[2]
