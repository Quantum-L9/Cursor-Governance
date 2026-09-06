"""Provider egress firewall: warning mode today, merge-blocking at C11."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "validate_memory_egress_boundary.py"

spec = importlib.util.spec_from_file_location("validate_memory_egress_boundary", SCRIPT)
assert spec and spec.loader
scanner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scanner  # dataclasses resolve annotations via sys.modules
spec.loader.exec_module(scanner)

TODAY = datetime(2026, 9, 5, tzinfo=UTC)


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "ops" / "graphiti").mkdir(parents=True)
    (tmp_path / "ops" / "graphiti" / "legacy.py").write_text(
        'call_tool("add_memory", payload)\nsearch_memory_facts\n', encoding="utf-8"
    )
    (tmp_path / "ops" / "memory").mkdir()
    (tmp_path / "ops" / "memory" / "clean.py").write_text("hydrate()\n", encoding="utf-8")
    (tmp_path / "ops" / "new_bypass.py").write_text("GRAPHITI_MCP_TOKEN\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "prose.md").write_text("add_memory is retired\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("add_memory\n", encoding="utf-8")
    return tmp_path


def _allowlist(entries: list[dict[str, str]]) -> tuple[Any, ...]:
    return tuple(scanner.AllowlistEntry(**entry) for entry in entries)


def test_production_scope_excludes_prose_and_tests(tmp_path: Path) -> None:
    findings, expired = scanner.scan(_tree(tmp_path), (), today=TODAY)
    paths = {item.path for item in findings}
    assert paths == {"ops/graphiti/legacy.py", "ops/new_bypass.py"}
    assert expired == []
    assert {item.token for item in findings} == {
        "add_memory",
        "search_memory_facts",
        "GRAPHITI_MCP_TOKEN",
    }


def test_exact_allowlist_entry_covers_only_its_path(tmp_path: Path) -> None:
    allow = _allowlist(
        [
            {
                "path": "ops/graphiti/legacy.py",
                "reason": "r",
                "retire_at_stage": "C11",
                "expires": "2026-12-31",
            }
        ]
    )
    findings, _ = scanner.scan(_tree(tmp_path), allow, today=TODAY)
    by_path = {item.path: item.allowlisted for item in findings}
    assert by_path["ops/graphiti/legacy.py"] is True
    assert by_path["ops/new_bypass.py"] is False


def test_expired_allowlist_entry_no_longer_covers(tmp_path: Path) -> None:
    allow = _allowlist(
        [
            {
                "path": "ops/graphiti/legacy.py",
                "reason": "r",
                "retire_at_stage": "C11",
                "expires": "2026-01-01",
            }
        ]
    )
    findings, expired = scanner.scan(_tree(tmp_path), allow, today=TODAY)
    assert [entry.path for entry in expired] == ["ops/graphiti/legacy.py"]
    assert all(item.allowlisted is False for item in findings)


def test_warning_mode_exits_zero_and_enforce_exits_one(tmp_path: Path, capsys) -> None:
    findings, expired = scanner.scan(_tree(tmp_path), (), today=TODAY)
    assert scanner.report(findings, expired, enforce=False, as_json=False) == 0
    assert "warning mode" in capsys.readouterr().out
    assert scanner.report(findings, expired, enforce=True, as_json=True) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["verdict"] == "FAIL" and summary["findings_unlisted"] == 3


def test_enforce_passes_a_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "clean.py").write_text("hydrate()\n", encoding="utf-8")
    findings, expired = scanner.scan(tmp_path, (), today=TODAY)
    assert scanner.report(findings, expired, enforce=True, as_json=True) == 0


def test_real_tree_inventory_is_fully_allowlisted_and_unexpired() -> None:
    """Warning-mode contract for C1: every legacy site is named, none has expired.

    The list must shrink as C3–C11 land; a new unlisted site is a regression.
    """

    _mode, allowlist = scanner.load_allowlist()
    findings, expired = scanner.scan(ROOT, allowlist)
    unlisted = sorted({item.path for item in findings if not item.allowlisted})
    assert unlisted == [], f"new provider egress outside the allowlist: {unlisted}"
    assert expired == []
    # The known legacy bypass is still present and still inventoried (stage C1).
    inventoried = {item.path for item in findings if item.allowlisted}
    assert "ops/graphiti/graphiti_memory_client.py" in inventoried
    assert "ops/graphiti/hydration/compile_session_packet.py" in inventoried
    assert "ops/graphiti/hydration/close_session.py" in inventoried


def test_ops_memory_is_provider_free() -> None:
    _mode, allowlist = scanner.load_allowlist()
    findings, _ = scanner.scan(ROOT, allowlist)
    assert not [item for item in findings if item.path.startswith("ops/memory/")]


def test_cli_entrypoint_runs_in_warning_mode() -> None:
    proc = subprocess.run(
        ["python3", str(SCRIPT), "--json"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["mode"] == "warning"
    assert summary["forbidden_tokens"] == list(scanner.FORBIDDEN_TOKENS)


@pytest.mark.parametrize("token", scanner.FORBIDDEN_TOKENS)
def test_every_forbidden_token_from_the_plan_is_scanned(token: str) -> None:
    assert scanner._TOKEN_RE.search(f"x {token} y")
