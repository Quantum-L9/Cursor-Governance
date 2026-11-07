"""The violation register stays inside the pack and matches its briefs."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_register import check  # noqa: E402


def test_live_register_passes():
    assert check(ROOT) == []


def test_orphan_brief_fails(tmp_path: Path):
    shutil.copytree(ROOT / "records", tmp_path / "records")
    orphan = tmp_path / "records" / "V-2026-11-07-999.md"
    orphan.write_text("# V-2026-11-07-999\n", encoding="utf-8")
    errors = check(tmp_path)
    assert any("V-2026-11-07-999" in error for error in errors)


def test_brief_outside_records_fails(tmp_path: Path):
    shutil.copytree(ROOT / "records", tmp_path / "records")
    register = tmp_path / "records" / "register.yaml"
    text = register.read_text(encoding="utf-8")
    register.write_text(
        text.replace("records/V-2026-11-07-001.md", "../V-2026-11-07-001.md"),
        encoding="utf-8",
    )
    errors = check(tmp_path)
    assert any("brief must be records/V-2026-11-07-001.md" in error for error in errors)
