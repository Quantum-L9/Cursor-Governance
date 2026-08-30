"""Publish-path breakglass receipt: standing env is inert; receipt expires."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import breakglass_receipt as bg  # noqa: E402


NOW = datetime(2026, 8, 29, 15, 0, 0, tzinfo=UTC)


def test_standing_env_without_receipt_is_inert(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(bg.OVERRIDE_ENV, "incident-1234")
    monkeypatch.setenv(bg.RECEIPT_ENV, str(tmp_path / "missing.json"))
    assert bg.active_publish_path_reason(now=NOW) == ""
    verdict = bg.evaluate(None, now=NOW)
    assert verdict["standing_env_inert"] is True
    assert verdict["in_force"] is False


def test_valid_receipt_grants_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "grant.json"
    bg.write_receipt(issuer="ops", reason="incident-1234", hours=2, path=path, now=NOW)
    monkeypatch.setenv(bg.RECEIPT_ENV, str(path))
    assert bg.active_publish_path_reason(now=NOW) == "incident-1234"
    later = NOW + timedelta(hours=3)
    assert bg.active_publish_path_reason(now=later) == ""


def test_status_line_names_age(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "grant.json"
    bg.write_receipt(issuer="human", reason="ops-window", hours=1, path=path, now=NOW)
    monkeypatch.setenv(bg.RECEIPT_ENV, str(path))
    line = bg.status_line(now=NOW + timedelta(seconds=90))
    assert "in force" in line
    assert "age=90s" in line
