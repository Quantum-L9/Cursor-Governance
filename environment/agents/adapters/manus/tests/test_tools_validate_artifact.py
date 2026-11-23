"""governance_validate_artifact: scoped findings, honest unsupported prefixes."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import RuntimeContext, ToolInputError

from tools import validate_artifact


def _repo(tmp_path: Path) -> Path:
    validator = tmp_path / "environment/agents/tools/validate_agents.py"
    validator.parent.mkdir(parents=True)
    validator.write_text("# stub validator\n", encoding="utf-8")
    artifact = tmp_path / "environment/agents/agents/demo.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("name: demo\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/note.md").write_text("# note\n", encoding="utf-8")
    return tmp_path


def test_scoped_validation_passes(tmp_path: Path, make_context) -> None:
    context = make_context(
        {"validate_agents.py": {"exit_code": 0, "stderr": "PASS — agent registry valid\n"}}
    )
    _repo(tmp_path)
    result = validate_artifact.handle(context, {"path": "environment/agents/agents/demo.yaml"})
    assert result["status"] == "passed"
    assert result["validator"].endswith("validate_agents.py")
    assert result["matched_findings"] == []


def test_findings_are_filtered_to_the_artifact(tmp_path: Path, make_context) -> None:
    stderr = "FAIL — demo.yaml: missing owner\nFAIL — other.yaml: missing owner\n"
    context = make_context({"validate_agents.py": {"exit_code": 1, "stderr": stderr}})
    _repo(tmp_path)
    result = validate_artifact.handle(context, {"path": "environment/agents/agents/demo.yaml"})
    assert result["status"] == "failed"
    assert any("demo.yaml" in line for line in result["matched_findings"])
    assert not any("other.yaml" in line for line in result["matched_findings"])


def test_unsupported_prefix_is_declared_not_invented(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    result = validate_artifact.handle(context, {"path": "docs/note.md"})
    assert result["status"] == "unsupported"
    assert "supported prefixes" in result["reason"]


def test_path_escape_is_refused(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    with pytest.raises(ToolInputError, match="escapes the governance root"):
        validate_artifact.handle(context, {"path": "../../etc/passwd"})
