"""governance_binding: parses the host binding report, never invents a status."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import RuntimeContext, ToolInputError

from tools import binding


def _root(tmp_path: Path) -> Path:
    script = tmp_path / "ops/autonomy/host_binding.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# stub\n", encoding="utf-8")
    return tmp_path


def test_parses_bound_report(tmp_path: Path, binding_json: str, make_context) -> None:
    _root(tmp_path)
    context = make_context({"host_binding.py": {"stdout": binding_json}})
    result = binding.handle(context, {})
    assert result["status"] == "BOUND"
    assert result["host"] == "manus"
    assert result["default_projection"]["status"] == "BOUND"


def test_line_format_is_human_readable(tmp_path: Path, binding_json: str, make_context) -> None:
    _root(tmp_path)
    context = make_context({"host_binding.py": {"stdout": binding_json}})
    result = binding.handle(context, {"format": "line"})
    assert "BOUND" in result["line"]
    assert result["report"]["status"] == "BOUND"


def test_missing_control_is_an_input_error(tmp_path: Path) -> None:
    context = RuntimeContext(tmp_path)
    with pytest.raises(ToolInputError, match="binding control absent"):
        binding.collect_binding(context)


def test_non_json_output_degrades_to_unknown(tmp_path: Path, make_context) -> None:
    _root(tmp_path)
    context = make_context({"host_binding.py": {"stdout": "not json at all"}})
    result = binding.collect_binding(context)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "binding report was not JSON"


def test_rejects_unknown_format(tmp_path: Path, binding_json: str, make_context) -> None:
    _root(tmp_path)
    context = make_context({"host_binding.py": {"stdout": binding_json}})
    with pytest.raises(ToolInputError, match="format must be json or line"):
        binding.handle(context, {"format": "yaml"})
