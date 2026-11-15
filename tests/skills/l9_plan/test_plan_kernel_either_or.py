"""#864: G_PLAN_EITHER_OR fires on exclusive-choice phrasing, not on the word "either".

"publishing either end-session handoff" uses "either" as a determiner and locks
nothing; "either fold X or exempt it" leaves a decision open. Both directions are
pinned here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "l9-plan" / "scripts"


def _load_validator() -> ModuleType:
    """Load the pack's validator without leaking its sibling modules.

    The pack imports bare names (``paths``) that other skill packs also define
    (``skills/l9-plan-simple/scripts/paths.py``). Leaving this directory on
    ``sys.path`` or its modules in ``sys.modules`` made a later test in the same
    worker import the wrong ``paths`` (full-suite ImportError on main).
    """
    before = set(sys.modules)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "_plan_kernel_receipt_either_or", SCRIPTS / "validate_plan_kernel_receipt.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))
        for name in set(sys.modules) - before:
            origin = getattr(sys.modules[name], "__file__", None) or ""
            if Path(origin).resolve().parent == SCRIPTS.resolve():
                del sys.modules[name]


v = _load_validator()


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
