"""CI-030 / LOADER-1: the receipt CLIs read by default.

Read is the only action either CLI has. Requiring `--read` to select it meant
the obvious invocation exited 2 with a usage error instead of answering, which
is why CLAUDE.md had to describe a flag rather than a command. These tests pin
the new default and, just as importantly, that the old form still works —
hooks and documented call sites pass `--read` today.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLIS = (
    ROOT / "ops" / "scripts" / "claude_bootstrap_receipt.py",
    ROOT / "ops" / "scripts" / "governance_refresh_receipt.py",
)


def _run(cli: Path, *args: str, path: Path | None = None) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(cli), *args]
    if path is not None:
        argv += ["--path", str(path)]
    return subprocess.run(argv, capture_output=True, text=True, check=False)


@pytest.fixture()
def absent_receipt(tmp_path: Path) -> Path:
    return tmp_path / "no-such-receipt.json"


@pytest.mark.parametrize("cli", CLIS, ids=lambda p: p.stem)
def test_bare_invocation_reads(cli: Path, absent_receipt: Path) -> None:
    proc = _run(cli, path=absent_receipt)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "bare invocation must answer, not print usage"
    assert "usage:" not in proc.stderr.lower()


@pytest.mark.parametrize("cli", CLIS, ids=lambda p: p.stem)
def test_read_flag_still_accepted(cli: Path, absent_receipt: Path) -> None:
    """Compatibility is the point: existing hooks and docs pass --read."""
    bare = _run(cli, path=absent_receipt)
    flagged = _run(cli, "--read", path=absent_receipt)
    assert flagged.returncode == 0, flagged.stderr
    assert flagged.stdout == bare.stdout, "--read must mean exactly the default action"


@pytest.mark.parametrize("cli", CLIS, ids=lambda p: p.stem)
def test_json_form_is_machine_readable(cli: Path, absent_receipt: Path) -> None:
    proc = _run(cli, "--json", path=absent_receipt)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["state"], "a receipt read must always report a state"


@pytest.mark.parametrize("cli", CLIS, ids=lambda p: p.stem)
def test_absent_receipt_is_never_ready(cli: Path, absent_receipt: Path) -> None:
    """CLAUDE.md's claim, held to: an absent receipt means never_ran, not ready."""
    payload = json.loads(_run(cli, "--json", path=absent_receipt).stdout)
    assert payload["state"] != "ready"


def test_claude_md_documents_the_command_not_the_flag() -> None:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "python3 ops/scripts/claude_bootstrap_receipt.py" in text
    assert "python3 ops/scripts/governance_refresh_receipt.py" in text
