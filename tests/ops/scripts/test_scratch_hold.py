"""scratch_hold park/restore — WIP unparkable; non-WIP roundtrip."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))

import scratch_hold as sh  # noqa: E402


def test_park_rejects_wip(tmp_path: Path) -> None:
    wip = tmp_path / "WIP" / "note.md"
    wip.parent.mkdir(parents=True)
    wip.write_text("sacred\n", encoding="utf-8")
    rc = sh.cmd_park(tmp_path, ["WIP/note.md"])
    assert rc == 2
    assert wip.is_file()
    assert not (tmp_path / ".l9" / "scratch-hold").exists()


def test_park_restore_roundtrip_non_wip(tmp_path: Path) -> None:
    target = tmp_path / "reports" / "probe.txt"
    target.parent.mkdir(parents=True)
    target.write_text("keep-me\n", encoding="utf-8")
    assert sh.cmd_park(tmp_path, ["reports/probe.txt"]) == 0
    assert not target.exists()
    holds = list((tmp_path / ".l9" / "scratch-hold").iterdir())
    assert len(holds) == 1
    assert sh.cmd_status(tmp_path) == 1
    assert sh.cmd_restore(tmp_path, None, import_legacy=False) == 0
    assert target.read_text(encoding="utf-8") == "keep-me\n"
    assert sh.cmd_status(tmp_path) == 0


def test_cli_park_wip_fails(tmp_path: Path) -> None:
    (tmp_path / "WIP").mkdir()
    (tmp_path / "WIP" / "x.md").write_text("x\n", encoding="utf-8")
    assert sh.main(["--workspace", str(tmp_path), "park", "WIP/x.md"]) == 2
