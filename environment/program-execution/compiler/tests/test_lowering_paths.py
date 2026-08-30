"""W6 — no fabricated docs/program-execution/<TASK>.md write target."""

from __future__ import annotations

from pathlib import Path


def test_architecture_to_campaign_has_no_docs_task_fallback() -> None:
    path = Path(__file__).resolve().parents[1] / "architecture_to_campaign.py"
    text = path.read_text(encoding="utf-8")
    assert "docs/program-execution/{task_id}.md" not in text
    assert "unknown_seam" in text
    assert "inspection_only" in text
