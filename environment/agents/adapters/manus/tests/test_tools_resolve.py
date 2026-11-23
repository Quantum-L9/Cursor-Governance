"""governance_resolve: deterministic ranking over the governance corpus."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import RuntimeContext, ToolInputError

from tools import resolve


def _corpus(tmp_path: Path) -> Path:
    (tmp_path / "kernels").mkdir()
    (tmp_path / "kernels/deployment-kernel.yaml").write_text(
        "name: deployment-kernel\ndescription: deployment authority and release gates\n",
        encoding="utf-8",
    )
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules/00-global.mdc").write_text(
        "# Global rules\ndeployment requires authority\n", encoding="utf-8"
    )
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols/unrelated.md").write_text(
        "# Something else\nnothing about the query here\n", encoding="utf-8"
    )
    return tmp_path


def test_matches_are_ranked_and_kind_tagged(tmp_path: Path) -> None:
    context = RuntimeContext(_corpus(tmp_path))
    result = resolve.handle(context, {"query": "deployment authority"})
    paths = [match["path"] for match in result["matches"]]
    assert "kernels/deployment-kernel.yaml" in paths
    assert "rules/00-global.mdc" in paths
    assert "protocols/unrelated.md" not in paths
    assert result["matches"][0]["score"] >= result["matches"][-1]["score"]
    assert {match["kind"] for match in result["matches"]} <= {"kernel", "rule"}


def test_kind_filter_is_respected(tmp_path: Path) -> None:
    context = RuntimeContext(_corpus(tmp_path))
    result = resolve.handle(context, {"query": "deployment authority", "kinds": ["rule"]})
    assert all(match["kind"] == "rule" for match in result["matches"])


def test_empty_query_is_rejected(tmp_path: Path) -> None:
    context = RuntimeContext(_corpus(tmp_path))
    with pytest.raises(ToolInputError, match="query must be a non-empty string"):
        resolve.handle(context, {"query": "   "})


def test_limit_bounds_are_enforced(tmp_path: Path) -> None:
    context = RuntimeContext(_corpus(tmp_path))
    with pytest.raises(ToolInputError, match="limit must be an integer"):
        resolve.handle(context, {"query": "deployment", "limit": 0})
