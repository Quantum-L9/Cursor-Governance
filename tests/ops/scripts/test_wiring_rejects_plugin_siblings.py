"""A sibling of ~/.cursor/plugins/local/l9-governance is a fault, not a backup.

Cursor loads every child of that directory as a plugin. The wiring scripts
parked a displaced link as `<link>.backup.<stamp>` beside the live one, so a
stale copy of the whole governance tree kept loading its `rules/` always-apply
for a month. Under a temporary HOME:

* the sibling lister sees it, the relocator moves it out to the backup root
  (never deletes), and the plugin directory is left with only the live link;
* `check_governance_wiring.sh --machine` FAILs on the sibling and names the
  remedy, and passes that section once the sibling is gone;
* `ensure_workspace_wired.sh` in links-only mode (the SessionStart path)
  relocates a sibling on its own, even when every link is already healthy;
* `l9_backup_aside` never leaves anything beside its source.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "ops" / "scripts"
LIB = SCRIPTS / "lib" / "plugin_siblings.sh"
CHECK = SCRIPTS / "check_governance_wiring.sh"
ENSURE = SCRIPTS / "ensure_workspace_wired.sh"
RELOCATE = SCRIPTS / "relocate_plugin_siblings.sh"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A HOME whose ~/.cursor-governance is this checkout and whose plugin dir
    holds the live link plus one stale sibling."""
    h = tmp_path / "home"
    (h / ".cursor" / "plugins" / "local").mkdir(parents=True)
    (h / ".cursor-governance").symlink_to(REPO)
    (h / ".cursor" / "plugins" / "local" / "l9-governance").symlink_to(h / ".cursor-governance")
    sibling = h / ".cursor" / "plugins" / "local" / "l9-governance.backup.20260814_232353"
    (sibling / "rules").mkdir(parents=True)
    (sibling / "rules" / "88-stale.mdc").write_text("stale\n")
    return h


def _env(home: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "TMPDIR", "LANG", "LC_ALL"}}
    env["HOME"] = str(home)
    env["L9_BACKUP_ROOT"] = str(home / ".cursor" / "l9" / "backups")
    # A temp HOME has no cloud-session.env; resolve the checkout explicitly.
    env["L9_GOVERNANCE_DIR"] = str(home / ".cursor-governance")
    return env


def _bash(home: Path, script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=_env(home),
        check=False,
    )


def _plugin_entries(home: Path) -> set[str]:
    return {p.name for p in (home / ".cursor" / "plugins" / "local").iterdir()}


def test_lister_sees_the_sibling_and_relocator_moves_it_out(home: Path) -> None:
    listed = _bash(home, f"source '{LIB}'; l9_plugin_siblings")
    assert listed.returncode == 0, listed.stderr
    assert listed.stdout.strip().endswith("l9-governance.backup.20260814_232353")

    moved = _bash(home, f"bash '{RELOCATE}'")
    assert moved.returncode == 0, moved.stderr
    assert "RELOCATED:" in moved.stdout
    assert _plugin_entries(home) == {"l9-governance"}
    backups = list((home / ".cursor" / "l9" / "backups" / "plugins").rglob("88-stale.mdc"))
    assert len(backups) == 1, "moved, not deleted: the stale rule must still exist under backups"

    again = _bash(home, f"bash '{RELOCATE}'")
    assert again.returncode == 0
    assert "OK: no l9-governance siblings" in again.stdout


def test_wiring_check_fails_on_a_sibling_and_passes_once_relocated(home: Path) -> None:
    before = _bash(home, f"bash '{CHECK}' --machine")
    assert before.returncode != 0
    assert "FAIL: plugin sibling loads as a second plugin" in before.stdout
    assert "relocate_plugin_siblings.sh" in before.stdout, "the remedy must be printed"

    _bash(home, f"bash '{RELOCATE}'")
    after = _bash(home, f"bash '{CHECK}' --machine")
    # Other machine checks (hooks.json, memory plane) are not wired under a
    # temp HOME, so only this section's verdict is asserted.
    assert "OK: no l9-governance siblings" in after.stdout
    assert "plugin sibling loads as a second plugin" not in after.stdout


def test_links_only_wire_relocates_a_sibling_even_when_links_are_healthy(home: Path) -> None:
    ws = home / "consumer"
    ws.mkdir()
    (home / ".cursor" / "plans").mkdir()
    first = _bash(home, f"L9_WIRE_LINKS_ONLY=1 bash '{ENSURE}' '{ws}'")
    assert first.returncode == 0, first.stderr + first.stdout
    assert "RELOCATED:" in first.stdout
    assert _plugin_entries(home) == {"l9-governance"}

    # Re-introduce a sibling with every link healthy: the short-circuit path
    # must still clear it.
    (home / ".cursor" / "plugins" / "local" / "l9-governance.backup.again").mkdir()
    second = _bash(home, f"L9_WIRE_LINKS_ONLY=1 bash '{ENSURE}' '{ws}'")
    assert second.returncode == 0, second.stderr + second.stdout
    assert "RELOCATED:" in second.stdout
    assert "already wired" in second.stdout
    assert _plugin_entries(home) == {"l9-governance"}


def test_backup_aside_never_leaves_a_neighbour(home: Path) -> None:
    src = home / "somewhere" / "thing"
    src.mkdir(parents=True)
    (src / "f").write_text("x\n")
    out = _bash(home, f"source '{LIB}'; l9_backup_aside '{src}'")
    assert out.returncode == 0, out.stderr
    dest = Path(out.stdout.strip())
    assert not src.exists()
    assert dest.is_dir() and (dest / "f").read_text() == "x\n"
    assert dest.parent.parent.parent == home / ".cursor" / "l9" / "backups"
    assert [p.name for p in (home / "somewhere").iterdir()] == [], "nothing beside the source"
