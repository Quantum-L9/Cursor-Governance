"""scratch_hold park/restore roundtrip inside the workspace vault."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))

import scratch_hold as sh  # noqa: E402


def test_park_restore_roundtrip(tmp_path: Path) -> None:
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


def test_park_missing_path_fails(tmp_path: Path) -> None:
    assert sh.cmd_park(tmp_path, ["reports/absent.txt"]) == 2
    assert not (tmp_path / ".l9" / "scratch-hold").exists()


def test_cli_park_outside_workspace_fails(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("x\n", encoding="utf-8")
    try:
        try:
            rc = sh.main(["--workspace", str(tmp_path), "park", str(outside)])
        except SystemExit as exc:
            rc = 2 if exc.code else 0
        assert rc == 2
        assert outside.is_file()
    finally:
        outside.unlink(missing_ok=True)
