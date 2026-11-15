"""#864: G_PLAN_EITHER_OR fires on exclusive-choice phrasing, not on the word "either".

"publishing either end-session handoff" uses "either" as a determiner and locks
nothing; "either fold X or exempt it" leaves a decision open. Both directions are
pinned here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills" / "l9-plan" / "scripts"))

import validate_plan_kernel_receipt as v  # noqa: E402


def _either_errors(body: str) -> list[str]:
    return [e for e in v.check_content_gates(body) if e.startswith("G_PLAN_EITHER_OR")]


@pytest.mark.parametrize(
    "line",
    [
        "Success: publishing either end-session handoff succeeds.",
        "Either way the receipt is rewritten.",
        "Neither path is touched; either file may be read first.",
    ],
)
def test_determiner_either_is_not_an_open_lock(line: str) -> None:
    assert _either_errors(line) == []


@pytest.mark.parametrize(
    "line",
    [
        "Either fold the helper into lib or exempt it from the gate.",
        "We either keep the shim, or delete it.",
        "Post-pytest sync: drop or keep.",
        "Generated copy: fold or exempt.",
    ],
)
def test_exclusive_choice_without_blocker_fails(line: str) -> None:
    assert _either_errors(line)


def test_exclusive_choice_with_blocker_passes() -> None:
    body = "Either fold the helper or exempt it.\nblocker: owner decides in #12"
    assert _either_errors(body) == []
