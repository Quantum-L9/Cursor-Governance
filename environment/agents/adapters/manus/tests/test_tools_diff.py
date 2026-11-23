"""governance_diff: the delta, bounded and structured."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import ToolInputError

from tools import diff


def _runner(
    make_context, *, status_out: str, stat_out: str = "", log_out: str = "", patch_out: str = ""
):
    return make_context(
        {
            "status --porcelain": {"stdout": status_out},
            "diff --stat": {"stdout": stat_out},
            "log --oneline": {"stdout": log_out},
            "diff --unified": {"stdout": patch_out},
        }
    )


def test_clean_checkout_reports_clean(tmp_path: Path, make_context) -> None:
    context = _runner(make_context, status_out="## main...origin/main\n")
    result = diff.handle(context, {})
    assert result["clean"] is True
    assert result["dirty_count"] == 0
    assert result["patch"] == ""


def test_dirty_checkout_reports_changes_and_patch(tmp_path: Path, make_context) -> None:
    context = _runner(
        make_context,
        status_out="## main...origin/main\n M rules/00-global.mdc\n?? new.md\n",
        stat_out=" rules/00-global.mdc | 2 +-\n",
        patch_out="diff --git a/x b/x\n+added line\n",
    )
    result = diff.handle(context, {"max_lines": 5})
    assert result["clean"] is False
    assert result["dirty_count"] == 2
    assert "+added line" in result["patch"]
    assert result["patch_truncated"] is False

    truncated = diff.handle(context, {"max_lines": 1})
    assert truncated["patch"] == "diff --git a/x b/x"
    assert truncated["patch_truncated"] is True


def test_ahead_count_from_origin_main(tmp_path: Path, make_context) -> None:
    context = _runner(
        make_context,
        status_out="## main...origin/main\n",
        log_out="abc1234 feat: one\ndef5678 feat: two\n",
    )
    result = diff.handle(context, {})
    assert result["ahead_of_origin_main"] == 2


def test_bad_max_lines_is_rejected(tmp_path: Path, make_context) -> None:
    context = _runner(make_context, status_out="## main\n")
    with pytest.raises(ToolInputError, match="max_lines must be an integer"):
        diff.handle(context, {"max_lines": 9999})
