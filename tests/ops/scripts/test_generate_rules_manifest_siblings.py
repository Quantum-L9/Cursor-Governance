"""RULES-MANIFEST.{json,yaml,md} must all heal, not just the json.

Regression: main() returned 0 as soon as RULES-MANIFEST.json matched the freshly
built manifest, without ever inspecting the .yaml and .md siblings. They are
separate files that drift independently, so a stale sibling could not be healed
by any local command — `--force` included, because force lives in
sync_generated_artifacts and this early return won underneath it. CI's
governance-self-check verifies all three paths, so the result was a red check
with no local way to clear it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops" / "scripts" / "generate_rules_manifest.py"
NAMES = ("RULES-MANIFEST.json", "RULES-MANIFEST.yaml", "RULES-MANIFEST.md")


def _run(root: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A throwaway root seeded with real rule sources."""
    rules = tmp_path / "rules"
    rules.mkdir()
    sources = sorted((REPO / "rules").glob("*.mdc"))[:4]
    assert sources, "no rules/*.mdc to seed from"
    for src in sources:
        shutil.copy2(src, rules / src.name)
    _run(tmp_path)
    for name in NAMES:
        assert (rules / name).is_file(), f"{name} not generated"
    return tmp_path


def _digests(root: Path) -> dict[str, str]:
    return {n: (root / "rules" / n).read_text(encoding="utf-8") for n in NAMES}


#: The timestamp surfaces under two different spellings: the ``generated_utc``
#: key in json/yaml, and a rendered ``Generated: `<ts>`…`` line in the markdown.
#: Filtering only the key left the markdown line in and made these assertions a
#: clock race that failed roughly one run in six.
_VOLATILE = ("generated_utc", "Generated: `")


def _digests_stable(root: Path) -> dict[str, list[str]]:
    """Contents minus every rendering of the generated timestamp.

    When the json is unreadable or does not match, the generator cannot recover
    the recorded timestamp, so a fresh one is written and byte equality is a
    clock race. The timestamp is deliberately volatile; everything else is the
    contract.
    """
    return {
        name: [ln for ln in text.splitlines() if not any(m in ln for m in _VOLATILE)]
        for name, text in _digests(root).items()
    }


def test_regenerating_is_idempotent(root: Path) -> None:
    before = _digests(root)
    out = _run(root)
    assert "CURRENT:" in out
    assert _digests(root) == before


@pytest.mark.parametrize("stale", ["RULES-MANIFEST.yaml", "RULES-MANIFEST.md"])
def test_stale_sibling_heals_while_json_is_current(root: Path, stale: str) -> None:
    good = _digests(root)
    target = root / "rules" / stale
    target.write_text(good[stale] + "\n<!-- drifted -->\n", encoding="utf-8")

    _run(root)

    assert target.read_text(encoding="utf-8") == good[stale], (
        f"{stale} was not healed while RULES-MANIFEST.json was current — "
        "this is the unclearable-gate regression"
    )
    # Healing a sibling must not disturb the others.
    assert _digests(root) == good


def test_stale_json_still_heals(root: Path) -> None:
    # `{}` is readable but does not match, so the recorded timestamp is
    # unrecoverable here too — compare modulo generated_utc.
    good = _digests_stable(root)
    (root / "rules" / "RULES-MANIFEST.json").write_text("{}\n", encoding="utf-8")
    _run(root)
    assert _digests_stable(root) == good


def test_all_three_stale_heal_together(root: Path) -> None:
    good = _digests_stable(root)
    for name in NAMES:
        (root / "rules" / name).write_text("drifted\n", encoding="utf-8")
    _run(root)
    # Compared modulo generated_utc: with no readable json the recorded
    # timestamp is unrecoverable, so a fresh one is correct here.
    assert _digests_stable(root) == good
