"""LaunchAgent path-law scan: Dropbox/CloudStorage fail; missing dir warns; _retired skipped."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from scan_launchagents import classify_string, main, scan_dir  # noqa: E402


def _write_plist(path: Path, *, label: str, args: list[str], stdout: str | None = None) -> None:
    data: dict = {
        "Label": label,
        "ProgramArguments": args,
    }
    if stdout:
        data["StandardOutPath"] = stdout
    path.write_bytes(plistlib.dumps(data))


def test_missing_dir_is_warning(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-agents"
    fails, warns = scan_dir(missing, tmp_path / "ssot")
    assert fails == []
    assert any("missing" in w for w in warns)
    rc = main(["--dir", str(missing), "--ssot", str(tmp_path / "ssot")])
    assert rc == 0


def test_dropbox_plist_fails(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        agents / "com.cursor.governance-monitor.plist",
        label="com.cursor.governance-monitor",
        args=[
            "/bin/bash",
            "/Users/x/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/"
            "governance-monitor-wrapper.sh",
        ],
        stdout="/Users/x/Dropbox/Cursor Governance/GlobalCommands/ops/logs/out",
    )
    fails, warns = scan_dir(agents, ssot)
    assert warns == []
    assert any("Dropbox" in f for f in fails)
    rc = main(["--dir", str(agents), "--ssot", str(ssot)])
    assert rc == 1


def test_unloaded_dropbox_plist_still_fails(tmp_path: Path) -> None:
    """Presence is enough; launchctl loaded-state is not consulted."""
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        agents / "com.cursor.stale.plist",
        label="com.cursor.stale",
        args=["/bin/true"],
        stdout="/Users/x/Library/CloudStorage/Dropbox/out.log",
    )
    fails, _warns = scan_dir(agents, ssot)
    assert any("CloudStorage" in f or "Dropbox" in f for f in fails)


def test_dropbox_vendor_updater_is_ignored(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        agents / "com.dropbox.DropboxUpdater.wake.plist",
        label="com.dropbox.DropboxUpdater.wake",
        args=["/Users/x/Library/Application Support/Dropbox/DropboxUpdater/Current/app"],
    )
    fails, warns = scan_dir(agents, ssot)
    assert fails == []
    assert warns == []


def test_ssot_venv_python_passes(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        agents / "com.l9.agent_ui_control.plist",
        label="com.l9.agent_ui_control",
        args=[str(ssot / ".venv" / "bin" / "python")],
    )
    fails, _warns = scan_dir(agents, ssot)
    assert fails == []


def test_ssot_only_path_passes(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    (ssot / "ops" / "scripts").mkdir(parents=True)
    wrapper = ssot / "ops" / "scripts" / "ok.sh"
    wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
    _write_plist(
        agents / "com.l9.ok.plist",
        label="com.l9.ok",
        args=["/bin/bash", str(wrapper)],
        stdout=str(ssot / "ops" / "logs" / "out"),
    )
    fails, warns = scan_dir(agents, ssot.resolve())
    assert fails == []
    assert warns == []
    rc = main(["--dir", str(agents), "--ssot", str(ssot)])
    assert rc == 0


def test_retired_subdir_is_not_scanned(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    retired = agents / "_retired"
    retired.mkdir(parents=True)
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        retired / "com.cursor.governance-monitor.plist",
        label="com.cursor.governance-monitor",
        args=["/bin/bash", "/Users/x/Dropbox/wrapper.sh"],
    )
    fails, warns = scan_dir(agents, ssot)
    assert fails == []
    assert warns == []


def test_classify_ssot_path_ok(tmp_path: Path) -> None:
    ssot = (tmp_path / ".cursor-governance").resolve()
    ssot.mkdir()
    assert classify_string(str(ssot / "ops" / "hooks" / "x.sh"), ssot) is None


def test_tmp_label_filename_is_not_a_governance_root(tmp_path: Path) -> None:
    """Label-derived /tmp logs contain '.cursor-governance' as a filename, not a dir."""
    ssot = (tmp_path / ".cursor-governance").resolve()
    ssot.mkdir()
    assert classify_string("/tmp/com.tenx.cursor-governance.out", ssot) is None
    assert classify_string("/tmp/com.tenx.cursor-governance.err", ssot) is None


def test_tmp_tenx_label_plist_passes(tmp_path: Path) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    _write_plist(
        agents / "com.tenx.cursor-governance.plist",
        label="com.tenx.cursor-governance",
        args=["/bin/bash", "/Users/x/bin/tenx-cursor-governance.sh"],
        stdout="/tmp/com.tenx.cursor-governance.out",
    )
    fails, warns = scan_dir(agents, ssot.resolve())
    assert fails == []
    assert warns == []
    rc = main(["--dir", str(agents), "--ssot", str(ssot)])
    assert rc == 0


def test_non_ssot_cursor_governance_dir_still_fails(tmp_path: Path) -> None:
    ssot = (tmp_path / ".cursor-governance").resolve()
    ssot.mkdir()
    other = tmp_path / "alt" / ".cursor-governance" / "ops" / "x.sh"
    reason = classify_string(str(other), ssot)
    assert reason == "governance root other than $HOME/.cursor-governance"


def test_suffixed_governance_root_still_fails(tmp_path: Path) -> None:
    ssot = (tmp_path / ".cursor-governance").resolve()
    ssot.mkdir()
    assert classify_string("/Users/x/.cursor-governance-backup/ops/x.sh", ssot) == (
        "governance root other than $HOME/.cursor-governance"
    )
    assert classify_string("/Users/x/GlobalCommands.old/ops/x.sh", ssot) == (
        "governance root other than $HOME/.cursor-governance"
    )


def test_script_does_not_call_launchctl() -> None:
    text = Path(SCRIPTS / "scan_launchagents.py").read_text(encoding="utf-8")
    assert "launchctl" not in text
    wiring = Path(SCRIPTS / "check_governance_wiring.sh").read_text(encoding="utf-8")
    # Wiring may mention LaunchAgents; it must not mutate them.
    assert "launchctl unload" not in wiring
    assert "launchctl bootout" not in wiring
    assert "scan_launchagents.py" in wiring


@pytest.mark.parametrize(
    "fragment", ["launchctl unload", "launchctl bootout", "os.remove", "unlink"]
)
def test_scan_never_mutates(fragment: str) -> None:
    text = Path(SCRIPTS / "scan_launchagents.py").read_text(encoding="utf-8")
    assert fragment not in text


def test_subprocess_missing_dir_exit_0(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "scan_launchagents.py"),
            "--dir",
            str(tmp_path / "absent"),
            "--ssot",
            str(tmp_path / "ssot"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "WARN:" in proc.stdout
