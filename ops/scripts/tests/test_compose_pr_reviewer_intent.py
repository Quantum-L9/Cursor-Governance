"""#912: an intent-written Reviewer focus stays replaceable by a later intent.

The first refresh swapped the composer's REVIEWER-FOCUS region for the author's
focus and dropped the markers, so on the next publish that text was
indistinguishable from a person's and a newer intent could not refresh it. The
author's focus now lives in its own intent-owned region; text a person writes
outside it still survives.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from compose_pr_body import PrIntent, compose_pr_body, refresh_body  # noqa: E402
from test_compose_pr_body import CANONICAL_TEMPLATE, _facts, _section  # noqa: E402

FIRST = "Look hardest at the App secret description."
SECOND = "Look hardest at the rotated secret path; the App section is gone."


def _intent(focus: str) -> PrIntent:
    return PrIntent(title="T", problem="", reviewer_focus=focus)


def test_a_later_intent_replaces_the_earlier_intent_focus() -> None:
    opened = compose_pr_body(_facts(["M\tops/a.py"], head="b" * 40), CANONICAL_TEMPLATE).body
    once, _ = refresh_body(opened, _facts(["M\tops/a.py"], head="c" * 40, intent=_intent(FIRST)))
    assert FIRST in _section(once, "Reviewer focus")
    twice, status = refresh_body(
        once, _facts(["M\tops/a.py"], head="d" * 40, intent=_intent(SECOND))
    )
    assert status == "updated"
    focus = _section(twice, "Reviewer focus")
    assert SECOND in focus
    assert FIRST not in focus


def test_composed_intent_focus_is_refreshable_too() -> None:
    composed = compose_pr_body(
        _facts(["M\tops/a.py"], head="b" * 40, intent=_intent(FIRST)), CANONICAL_TEMPLATE
    ).body
    body, _ = refresh_body(composed, _facts(["M\tops/a.py"], head="c" * 40, intent=_intent(SECOND)))
    assert SECOND in _section(body, "Reviewer focus")
    assert FIRST not in body


def test_person_text_beside_the_intent_focus_survives() -> None:
    composed = compose_pr_body(
        _facts(["M\tops/a.py"], head="b" * 40, intent=_intent(FIRST)), CANONICAL_TEMPLATE
    ).body
    human = "Reviewer note: also check the migration."
    marker_end = "<!-- REVIEWER-FOCUS-INTENT:END -->"
    edited = composed.replace(marker_end, marker_end + "\n\n" + human, 1)
    body, _ = refresh_body(edited, _facts(["M\tops/a.py"], head="c" * 40, intent=_intent(SECOND)))
    assert human in body
    assert SECOND in body


def test_without_a_new_intent_the_earlier_intent_focus_stays() -> None:
    composed = compose_pr_body(
        _facts(["M\tops/a.py"], head="b" * 40, intent=_intent(FIRST)), CANONICAL_TEMPLATE
    ).body
    body, _ = refresh_body(composed, _facts(["M\tops/a.py"], head="c" * 40))
    assert FIRST in _section(body, "Reviewer focus")
