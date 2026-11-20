"""Pytest never delivers a handoff or friction report to the live GitHub tracker.

Regression for #846-#855: fixture friction from the Stop-hook harnesses was filed
as real ``[session-friction]`` issues in Cursor-Governance. The root conftest
guard (``_no_live_handoff_delivery``) is the fix; this pins it.
"""

from __future__ import annotations

import pytest

from ops.reports import handoff_delivery as hd


def test_friction_intake_points_at_a_nonexistent_sink_under_pytest() -> None:
    assert hd.intake_repository() == "l9-test-sink/no-such-intake"


def test_default_transport_refuses_the_real_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hd.shutil, "which", lambda name: "/usr/bin/gh")
    with pytest.raises(hd.TransportError, match="disabled under pytest"):
        hd.GhApi().request("POST", "repos/quantum-l9/cursor-governance/issues", {"title": "x"})


def test_deliver_with_the_default_transport_files_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hd.shutil, "which", lambda name: "/usr/bin/gh")
    pub = {"repo": "Org/website-bot", "number": 42, "label": "Org/website-bot#42"}
    items = [{"id": "fixture-friction", "detail": "d", "section": "environment friction"}]
    result = hd.deliver("governance-handoff", pub, "body", friction=items)
    assert result.urls == [] or not any("github.com" in u for u in result.urls)
