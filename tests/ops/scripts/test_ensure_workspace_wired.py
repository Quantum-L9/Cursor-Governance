"""SP-02 / SP-03: workspace wire helper is idempotent and creates consumer links."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "ops/scripts/ensure_workspace_wired.sh"
GATE = ROOT / "ops/scripts/run_pr_gate.sh"


@pytest.mark.skipif(not HELPER.is_file(), reason="helper missing")
def test_ensure_workspace_wired_creates_links_and_is_idempotent(tmp_path: Path) -> None:
    # Isolate HOME so a leaked os.environ["HOME"] from another test cannot
    # make resolve_governance_paths no-op (exit 0, no links).
    home = tmp_path / "home"
    ssot = home / ".cursor-governance"
    (ssot / "skills").mkdir(parents=True)
    (ssot / "CANONICAL_LAW.md").write_text("canonical law\n", encoding="utf-8")
    ws = tmp_path / "consumer"
    ws.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["L9_WIRE_LINKS_ONLY"] = "1"
    first = subprocess.run(
        ["bash", str(HELPER), str(ws)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert (ws / ".cursor-commands").is_symlink(), first.stdout + first.stderr
    assert (ws / ".cursor/plans").is_symlink()
    assert (ws / ".cursor/governance/CANONICAL_LAW.md").is_symlink()
    gc = Path(os.path.realpath(ssot))
    assert Path(os.path.realpath(ws / ".cursor-commands")) == gc
    second = subprocess.run(
        ["bash", str(HELPER), str(ws)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert "already wired" in second.stdout
    assert "WIRE:" in first.stdout or "LINKED:" in first.stdout or "OK:" in first.stdout


def test_run_pr_gate_heals_before_wiring_check() -> None:
    text = GATE.read_text(encoding="utf-8")
    marker = "# Heal missing gitignored .cursor links"
    heal_at = text.find(marker)
    invoke_at = text.find('bash "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh"')
    check_at = text.find('if ! bash "$SCRIPT_DIR/check_governance_wiring.sh" "$WS"')
    assert heal_at != -1
    assert invoke_at != -1
    assert check_at != -1
    assert heal_at < invoke_at < check_at
    lock_at = text.find('L9_REPO_WRITE_LOCK_LABEL="make-pr-gate"')
    assert lock_at != -1
    assert lock_at < heal_at
    assert "wiring check will fail-closed" in text
    assert 'L9_WIRE_LINKS_ONLY=1 bash "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh"' in text
