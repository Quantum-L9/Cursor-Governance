"""session_start: a receipt, not a claim."""

from __future__ import annotations

from pathlib import Path

import pytest
from session import session_start
from tools.base import RuntimeContext


def _repo(tmp_path: Path) -> Path:
    script = tmp_path / "ops/autonomy/host_binding.py"
    script.parent.mkdir(parents=True)
    script.write_text("# stub\n", encoding="utf-8")
    refresh = tmp_path / "ops/scripts/ensure_authority_checkout.sh"
    refresh.parent.mkdir(parents=True)
    refresh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    return tmp_path


def _context(tmp_path: Path, binding_json: str, make_context) -> RuntimeContext:
    _repo(tmp_path)
    return make_context(
        {
            "host_binding.py": {"stdout": binding_json},
            "ensure_authority_checkout.sh": {"exit_code": 0},
            "rev-parse": {"stdout": "d0d2927\n"},
        }
    )


def test_receipt_reports_bound_session(
    tmp_path: Path, binding_json: str, make_context, monkeypatch
) -> None:
    authority = tmp_path / "authority"
    authority.mkdir()
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(authority))
    context = _context(tmp_path, binding_json, make_context)

    receipt = session_start.collect(context)
    assert receipt["schema"] == "l9.manus.session-receipt.v1"
    assert receipt["binding_status"] == "BOUND"
    assert receipt["bound"] is True
    assert receipt["authority_sha"] == "d0d2927"
    assert [step["step"] for step in receipt["steps"]] == [
        "authority_refresh",
        "projection_binding",
    ]
    assert receipt["idempotent"] is True


def test_receipt_is_idempotent(
    tmp_path: Path, binding_json: str, make_context, monkeypatch
) -> None:
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(tmp_path / "authority"))
    context = _context(tmp_path, binding_json, make_context)
    first = session_start.collect(context)
    second = session_start.collect(context)
    assert first["binding_status"] == second["binding_status"]
    assert first["authority_sha"] == second["authority_sha"]


def test_refresh_can_be_skipped(
    tmp_path: Path, binding_json: str, make_context, monkeypatch
) -> None:
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(tmp_path / "authority"))
    context = _context(tmp_path, binding_json, make_context)
    receipt = session_start.collect(context, refresh=False)
    assert receipt["steps"][0]["status"] == "skipped"


def test_unbound_receipt_says_so(tmp_path: Path, make_context, monkeypatch) -> None:
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(tmp_path / "authority"))
    not_bound = (
        '{"status": "NOT_BOUND", "host": "manus", '
        '"default": {"status": "NOT_BOUND", "reason": "UNVERIFIED"}}'
    )
    context = _context(tmp_path, not_bound, make_context)
    receipt = session_start.collect(context)
    assert receipt["bound"] is False
    assert receipt["binding_status"] == "NOT_BOUND"


def test_handler_validates_arguments(
    tmp_path: Path, binding_json: str, make_context, monkeypatch
) -> None:
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(tmp_path / "authority"))
    context = _context(tmp_path, binding_json, make_context)
    with pytest.raises(ValueError, match="refresh must be a boolean"):
        session_start.handle(context, {"refresh": "yes"})
