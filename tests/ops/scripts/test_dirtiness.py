"""Tests for ops/scripts/lib/dirtiness.py porcelain parsing."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts" / "lib"))

import dirtiness  # noqa: E402


def test_porcelain_path_decodes_git_octal_em_dash() -> None:
    line = (
        '?? "WIP/8-29-26/Web SEO LLM Trio/L9 Website Improvement '
        r'\342\200\224 Independent Validation Contract Pack.md"'
    )
    decoded = dirtiness.porcelain_path(line)
    assert "\u2014" in decoded
    assert "\\342" not in decoded
    assert decoded.endswith("Independent Validation Contract Pack.md")


def test_porcelain_path_plain_ascii_unchanged() -> None:
    line = "?? WIP/plain-file.md"
    assert dirtiness.porcelain_path(line) == "WIP/plain-file.md"
