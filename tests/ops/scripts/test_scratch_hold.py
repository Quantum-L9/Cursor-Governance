"""scratch_hold park/restore roundtrip inside the workspace vault."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def test_cli_park_outside_workspace_fails(tmp_path_factory: pytest.TempPathFactory) -> None:
    workspace = tmp_path_factory.mktemp("ws")
    outside = tmp_path_factory.mktemp("elsewhere") / "outside.txt"
    outside.write_text("x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        sh.main(["--workspace", str(workspace), "park", str(outside)])
    assert "outside workspace" in str(raised.value)
    assert outside.is_file()
    assert not (workspace / ".l9" / "scratch-hold").exists()
