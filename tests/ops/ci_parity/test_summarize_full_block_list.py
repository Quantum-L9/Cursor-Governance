"""#950: ci-parity prints every BLOCK finding.

`summarize` sliced the blocking list to 40 entries, so a run with 93 findings
hid 53 of them with no hint they existed. Every BLOCK line is printed; advisory
notes may stay capped but the hidden count is named.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import run  # noqa: E402


def _finding(i: int, severity: str = "error") -> dict[str, Any]:
    return {
        "tool": "t",
        "rule": f"R{i}",
        "severity": severity,
        "path": f"f{i}.py",
        "line": i,
        "message": "m",
        "related": [],
    }


def test_every_blocking_finding_is_printed() -> None:
    ctx: Any = SimpleNamespace(sha="a" * 40, base="b" * 40)
    records = [
        {"lane": "x", "status": "ok", "blocking": [_finding(i) for i in range(93)], "advisory": []}
    ]
    text, count = run.summarize(ctx, records, label="commit")
    assert count == 93
    assert sum(1 for line in text.splitlines() if line.startswith("  BLOCK ")) == 93
    assert "f92.py:92:" in text


def test_capped_advisory_names_the_hidden_count() -> None:
    ctx: Any = SimpleNamespace(sha="a" * 40, base="b" * 40)
    advisory = [_finding(i, "warning") for i in range(20)]
    records = [{"lane": "x", "status": "ok", "blocking": [], "advisory": advisory}]
    text, _ = run.summarize(ctx, records, label="commit")
    assert sum(1 for line in text.splitlines() if line.startswith("  note  ")) == 15
    assert "5 more advisory" in text
