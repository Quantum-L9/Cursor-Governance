"""Tests for ops/scripts/emit_claude_readiness.py.

Readiness is evidence. These tests pin the truth rules: a skipped projection is
not PASS, a blocked required component forces overall BLOCKED, and overall is
READY only when every required dimension is READY. The integration test builds a
fake governance clone (git + Makefile facade + stub probe/merge/dispatcher) and
a fake $HOME with projection/bootstrap receipts, so no network or real clone is
touched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import emit_claude_readiness as er  # noqa: E402

READY, DEGRADED, BLOCKED, UNKNOWN = er.READY, er.DEGRADED, er.BLOCKED, er.UNKNOWN


# --- Pure aggregation + parsing -----------------------------------------------


def test_aggregate_ready_only_when_all_ready() -> None:
    assert er._aggregate({"a": READY, "b": READY}) == READY


def test_aggregate_blocked_dominates() -> None:
    assert er._aggregate({"a": READY, "b": DEGRADED, "c": BLOCKED}) == BLOCKED


def test_aggregate_degraded_when_any_degraded() -> None:
    assert er._aggregate({"a": READY, "b": DEGRADED}) == DEGRADED


def test_aggregate_unknown_never_reports_pass() -> None:
    assert er._aggregate({"a": READY, "b": UNKNOWN}) == DEGRADED


def test_projection_skipped_is_not_pass() -> None:
    receipt = {
        "domains": [
            {"domain": "plugins", "status": "skipped"},
            {"domain": "skills", "status": "ok"},
        ]
    }
    out = er._projection_statuses(receipt)
    assert out["plugins"] == DEGRADED
    assert out["skills"] == READY


def test_projection_missing_receipt_is_unknown() -> None:
    out = er._projection_statuses(None)
    assert set(out.values()) == {UNKNOWN}


def test_graphiti_tcp_is_not_authenticated() -> None:
    status, note = er._graphiti_health({"ok": False, "primary_blocker": "identity"})
    assert status == DEGRADED
    assert "identity" in note
    assert er._graphiti_health({"ok": True})[0] == READY


def test_configured_mcp_is_not_loaded_mcp() -> None:
    # No bootstrap word: a rendered projection alone is not a loaded server.
    status, _ = er._mcp_status(None, READY)
    assert status == DEGRADED


def test_sanitize_remote_strips_embedded_credential() -> None:
    # A token-authenticated clone must never leak its credential into the receipt.
    got = er._sanitize_remote("https://x-access-token:ghs_SECRET@github.com/o/r.git")
    assert got == "https://github.com/o/r.git"
    assert "ghs_SECRET" not in got
    assert "x-access-token" not in got


def test_sanitize_remote_passes_clean_urls() -> None:
    assert er._sanitize_remote("https://github.com/o/r.git") == "https://github.com/o/r.git"
    assert er._sanitize_remote("git@github.com:o/r.git") == "git@github.com:o/r.git"


def test_graphiti_blocker_is_a_constant_label() -> None:
    # Only known blocker classes are emitted; an unknown value is mapped away so
    # no probe-derived string is printed verbatim.
    _, note = er._graphiti_health({"ok": False, "primary_blocker": "identity"})
    assert "identity" in note
    _, other = er._graphiti_health({"ok": False, "primary_blocker": "ghs_leaked_token_value"})
    assert "ghs_leaked_token_value" not in other
    assert "unknown" in other


# --- Integration: build a fake governance clone + fake $HOME -------------------


def _init_fake_gov(tmp_path: Path, *, merge_denies: bool = True) -> Path:
    gov = tmp_path / "gov"
    (gov / "ops" / "scripts").mkdir(parents=True)
    (gov / "ops" / "secrets").mkdir(parents=True)
    (gov / "ops" / "autonomy").mkdir(parents=True)

    (gov / "Makefile").write_text(
        "l9-consumer-safe-list:\n\t@echo start pr pr-check improve\n", encoding="utf-8"
    )
    (gov / "ops" / "secrets" / "probe_broker.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'secret_boundary': 'model-controlled'}))\n",
        encoding="utf-8",
    )
    # The emitter imports merge_gate.evaluate() in-process (the CLI needs a git
    # work tree it does not have). A deny is a returned reason string; an allow
    # is None. merge_denies=False models the regression: the env boolean alone
    # authorizing a merge (evaluate returns None).
    reason = "None" if not merge_denies else '"env boolean is not an authority"'
    (gov / "ops" / "autonomy" / "merge_gate.py").write_text(
        f"def evaluate(tool_name, tool_input, *, root=None):\n    return {reason}\n",
        encoding="utf-8",
    )
    (gov / "ops" / "scripts" / "install_l9_dispatcher.sh").write_text(
        "#!/usr/bin/env bash\necho 'l9 dispatcher: OK'\nexit 0\n", encoding="utf-8"
    )
    (gov / "ops" / "scripts" / "install_l9_dispatcher.sh").chmod(0o755)

    subprocess.run(["git", "-C", str(gov), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(gov), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(gov), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(gov), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(gov), "commit", "-qm", "init"], check=True)
    subprocess.run(
        ["git", "-C", str(gov), "remote", "add", "origin", "https://example/gov.git"], check=True
    )
    # Fresh: origin/main == HEAD.
    subprocess.run(
        ["git", "-C", str(gov), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(gov),
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/main",
        ],
        check=True,
    )
    return gov


def _fake_home(tmp_path: Path, *, mcp: str = "READY") -> Path:
    home = tmp_path / "home"
    cl = home / ".l9" / "claude"
    cl.mkdir(parents=True)
    domains = [
        {"domain": d, "status": "ok"}
        for d in ("skills", "commands", "rules", "settings", "hooks", "plugins", "mcp")
    ]
    (cl / "projection-receipt.json").write_text(json.dumps({"domains": domains}), encoding="utf-8")
    (cl / "bootstrap-state.json").write_text(json.dumps({"mcp": mcp}), encoding="utf-8")
    return home


def _build(gov: Path, home: Path, monkeypatch) -> dict:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return er.build_receipt(gov=gov, workspace=str(gov))


def test_ready_only_when_all_components_pass(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["merge_authority_status"] == READY
    assert receipt["Makefile_facade_status"] == READY
    assert receipt["dispatcher_status"] == READY
    assert receipt["Graphiti_authenticated_health"] == READY
    assert receipt["overall_readiness"] == READY, receipt["warnings"]
    # Required fields present.
    for field in (
        "schema_version",
        "governance_repository",
        "governance_default_branch",
        "governance_SHA",
        "workspace",
        "failures",
        "warnings",
    ):
        assert field in receipt


def test_blocked_when_merge_authority_regresses(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=False)  # env boolean authorized a merge
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["merge_authority_status"] == BLOCKED
    assert receipt["overall_readiness"] == BLOCKED
    assert any("merge_authority" in f for f in receipt["failures"])


def test_degraded_when_mcp_not_loaded(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="DEGRADED")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["MCP_status"] == DEGRADED
    assert receipt["overall_readiness"] == DEGRADED


def test_stale_sha_prevents_ready(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    # Move origin/main ahead of HEAD → stale runtime clone.
    subprocess.run(
        ["git", "-C", str(gov), "commit", "-q", "--allow-empty", "-m", "ahead"], check=True
    )
    ahead = subprocess.run(
        ["git", "-C", str(gov), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(gov), "update-ref", "refs/remotes/origin/main", ahead], check=True
    )
    subprocess.run(["git", "-C", str(gov), "reset", "-q", "--hard", "HEAD~1"], check=True)
    receipt = _build(gov, home, monkeypatch)
    assert receipt["overall_readiness"] != READY
    assert any("freshness" in w for w in receipt["warnings"])
