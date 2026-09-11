"""SessionStart must read RuntimeBinding.binding_status, not a missing status key."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "ops" / "hooks" / "session_start_bootstrap.sh"
PARSE = (
    "import sys,json; d=json.load(sys.stdin); "
    "print(d.get('binding_status') or d.get('status') or 'unbound')"
)
USABLE = "exact|compatible|development_checkout"


def test_bootstrap_reads_binding_status_and_treats_compatible_as_usable() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert PARSE in text
    assert USABLE in text
    assert ".get('status','unbound')" not in text


def _parse(payload: dict) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", PARSE],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout.strip()


def test_session_start_parser_prefers_binding_status() -> None:
    assert _parse({"binding_status": "compatible"}) == "compatible"
    assert _parse({"status": "unbound"}) == "unbound"
    assert _parse({}) == "unbound"
