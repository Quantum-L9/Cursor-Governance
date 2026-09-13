"""T8: 3-link SessionStart health — missing/dangling/wrong-target/kinds.

Cursor auto-wire must not write a Claude projection receipt.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HEALTH = ROOT / "ops/scripts/lib/workspace_link_health.sh"
ENSURE = ROOT / "ops/scripts/ensure_workspace_wired.sh"
BOOTSTRAP = ROOT / "ops/hooks/session_start_bootstrap.sh"
SETUP = ROOT / "ops/scripts/setup_workspace_symlinks.sh"


def _seed_ssot(home: Path) -> Path:
    ssot = home / ".cursor-governance"
    (ssot / "skills").mkdir(parents=True)
    (ssot / "CANONICAL_LAW.md").write_text("canonical law\n", encoding="utf-8")
    return ssot


def _seed_identity(root: Path) -> None:
    (root / "skills").mkdir(parents=True, exist_ok=True)
    (root / "rules").mkdir(parents=True, exist_ok=True)
    (root / "ops/scripts").mkdir(parents=True, exist_ok=True)
    (root / "CANONICAL_LAW.md").write_text("# law\n", encoding="utf-8")
    (root / "skills/AUTONOMY_MANIFEST.yaml").write_text("x\n", encoding="utf-8")
    (root / "rules/RULES-MANIFEST.yaml").write_text("x\n", encoding="utf-8")
    (root / "ops/scripts/check_governance_wiring.sh").write_text("#!/bin/sh\n", encoding="utf-8")


def _env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["GLOBAL_COMMANDS"] = str(home / ".cursor-governance")
    env.pop("GOV_ROOT", None)
    return env


def _healthy(home: Path, ws: Path) -> bool:
    script = f"""
set -euo pipefail
source "{HEALTH}"
workspace_links_healthy "{ws}"
"""
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=_env(home),
    )
    return proc.returncode == 0


def _link_plugin(home: Path, ssot: Path) -> None:
    plugin = home / ".cursor/plugins/local/l9-governance"
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.symlink_to(ssot)


def _link_plans(home: Path, ws: Path) -> None:
    store = home / ".cursor/plans"
    store.mkdir(parents=True, exist_ok=True)
    dest = ws / ".cursor/plans"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(store)


def _assert_no_claude_projection(home: Path) -> None:
    receipt = home / ".l9/claude/projection-receipt.json"
    assert not receipt.exists(), f"Cursor auto-wire wrote Claude projection: {receipt}"


@pytest.mark.skipif(not HEALTH.is_file(), reason="helper missing")
def test_consumer_missing_links_unhealthy(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _seed_ssot(home)
    ws = tmp_path / "consumer"
    ws.mkdir()
    assert not _healthy(home, ws)


@pytest.mark.skipif(not HEALTH.is_file(), reason="helper missing")
def test_consumer_dangling_and_wrong_target_unhealthy(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssot = _seed_ssot(home)
    ws = tmp_path / "consumer"
    ws.mkdir()
    (ws / ".cursor").mkdir()
    (ws / ".cursor-commands").symlink_to(tmp_path / "gone-ssot")
    (ws / ".cursor/plans").symlink_to(tmp_path / "gone-plans")
    plugin = home / ".cursor/plugins/local/l9-governance"
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.symlink_to(tmp_path / "wrong-plugin")
    assert not _healthy(home, ws)

    (ws / ".cursor-commands").unlink()
    (ws / ".cursor-commands").symlink_to(tmp_path / "other-gov")
    _link_plans(home, ws)
    plugin.unlink()
    _link_plugin(home, ssot)
    assert not _healthy(home, ws)


@pytest.mark.skipif(not HEALTH.is_file(), reason="helper missing")
def test_consumer_healthy_when_three_links_match(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssot = _seed_ssot(home)
    ws = tmp_path / "consumer"
    ws.mkdir()
    (ws / ".cursor-commands").symlink_to(ssot)
    _link_plans(home, ws)
    _link_plugin(home, ssot)
    assert _healthy(home, ws)


@pytest.mark.skipif(not HEALTH.is_file(), reason="helper missing")
def test_ssot_and_ssot_checkout_reject_cursor_commands(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssot = _seed_ssot(home)
    _seed_identity(ssot)
    _link_plugin(home, ssot)
    _link_plans(home, ssot)
    leftover = ssot / ".cursor-commands"
    leftover.symlink_to(ssot)
    assert not _healthy(home, ssot)

    leftover.unlink()
    assert _healthy(home, ssot)

    checkout = tmp_path / "ssot-checkout"
    _seed_identity(checkout)
    _link_plans(home, checkout)
    leftover_co = checkout / ".cursor-commands"
    leftover_co.symlink_to(ssot)
    assert not _healthy(home, checkout)
    leftover_co.unlink()
    assert _healthy(home, checkout)


@pytest.mark.skipif(not ENSURE.is_file(), reason="ensure missing")
def test_links_only_repairs_wrong_target_and_skips_claude_projection(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    ssot = _seed_ssot(home)
    ws = tmp_path / "consumer"
    ws.mkdir()
    (ws / ".cursor").mkdir()
    (ws / ".cursor-commands").symlink_to(tmp_path / "stale-gov")
    (ws / ".cursor/plans").symlink_to(tmp_path / "stale-plans")
    plugin = home / ".cursor/plugins/local/l9-governance"
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.symlink_to(tmp_path / "stale-plugin")

    env = _env(home)
    env["L9_WIRE_LINKS_ONLY"] = "1"
    first = subprocess.run(
        ["bash", str(ENSURE), str(ws)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert Path(os.path.realpath(ws / ".cursor-commands")) == Path(os.path.realpath(ssot)), (
        first.stdout + first.stderr
    )
    assert Path(os.path.realpath(ws / ".cursor/plans")) == Path(
        os.path.realpath(home / ".cursor/plans")
    )
    assert Path(os.path.realpath(plugin)) == Path(os.path.realpath(ssot))
    assert _healthy(home, ws)
    _assert_no_claude_projection(home)
    assert "claude_projection" not in first.stdout
    assert "claude_projection" not in first.stderr


def test_bootstrap_uses_helper_retry_and_skips_claude_projection() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "workspace_links_healthy" in text
    assert "L9_WIRE_LINKS_ONLY=1" in text
    assert "exhausted auto-repair" in text
    assert "/wire" in text
    assert "classify_workspace_kind" in text or "workspace_link_health.sh" in text
    assert "claude_projection.py" not in text.split("Do not call claude_projection.py here.")[-1]
    setup = SETUP.read_text(encoding="utf-8")
    assert "SKIP: Claude projection" in setup
    assert "CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1" in setup
