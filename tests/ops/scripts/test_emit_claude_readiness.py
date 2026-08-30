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


def test_projection_skipped_is_not_pass(monkeypatch) -> None:
    """A skipped required domain is not PASS.

    The hosted marketplace exception is a separate case
    (`test_plugin_marketplace_skip_is_ready`), so SKIP_PLUGIN_MARKETPLACE must be
    cleared here: every hosted Claude session exports it, which leaked into this
    test and made it assert the opposite of its own name.
    """
    monkeypatch.delenv("SKIP_PLUGIN_MARKETPLACE", raising=False)
    receipt = {
        "domains": [
            {"domain": "plugins", "status": "skipped"},
            {"domain": "skills", "status": "ok"},
        ]
    }
    out = er._projection_statuses(receipt)
    assert out["plugins"] == DEGRADED
    assert out["skills"] == READY


def test_plugin_marketplace_skip_is_ready() -> None:
    receipt = {
        "domains": [
            {
                "domain": "plugins",
                "status": "skipped",
                "detail": {"reason": "marketplace disabled by the platform"},
            }
        ]
    }
    out = er._projection_statuses(receipt)
    assert out["plugins"] == READY


def test_projection_missing_receipt_is_unknown() -> None:
    out = er._projection_statuses(None)
    assert set(out.values()) == {UNKNOWN}


def test_graphiti_health_classifies_probe_not_broker() -> None:
    """Graphiti compact health is the CLI/MCP probe, not a capability-broker /whoami."""
    status, note = er._graphiti_health({"ok": False, "primary_blocker": "identity"})
    assert status == DEGRADED
    assert "identity" in note
    assert "GRAPHITI_MCP_URL" not in note
    assert er._graphiti_health({"ok": True})[0] == READY
    assert er._graphiti_health({})[0] == UNKNOWN


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


def test_uv_version_parses_the_build_suffix(monkeypatch) -> None:
    # uv reports "uv 0.8.0 (<commit> <date> <triple>)". A consumer comparing
    # against `required-version` should not have to parse that.
    monkeypatch.setattr(
        er, "_run", lambda *a, **k: (0, "uv 0.8.0 (3cdf50e09 2026-06-19 x86_64-linux-gnu)", "")
    )
    assert er._uv_version() == "0.8.0"


def test_uv_version_is_empty_when_uv_cannot_report(monkeypatch) -> None:
    # "not observed" must stay distinguishable from "an old version".
    monkeypatch.setattr(er, "_run", lambda *a, **k: (127, "", "not found"))
    assert er._uv_version() == ""


def test_graphiti_http_403_is_allowlist() -> None:
    status, note = er._classify_graphiti_http_code(403)
    assert status == DEGRADED
    assert "allowlist" in note
    assert "identity" in er._classify_graphiti_http_code(401)[1]
    assert er._classify_graphiti_http_code(405)[0] == READY


def test_graphiti_mcp_http_health_rejects_file_scheme(monkeypatch) -> None:
    monkeypatch.delenv("L9_GRAPHITI_PROBE_SKIP", raising=False)
    monkeypatch.setenv("GRAPHITI_MCP_URL", "file:///etc/passwd")
    status, note = er._graphiti_mcp_http_health()
    assert status == DEGRADED
    assert "config" in note


def test_graphiti_mcp_http_health_rejects_non_allowlisted_https(monkeypatch) -> None:
    monkeypatch.delenv("L9_GRAPHITI_PROBE_SKIP", raising=False)
    monkeypatch.setenv("GRAPHITI_MCP_URL", "https://evil.example/graphiti/mcp")
    status, note = er._graphiti_mcp_http_health()
    assert status == DEGRADED
    assert "config" in note


def test_working_cli_and_dead_mcp_are_not_one_word(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(er, "_graphiti_cli_health", lambda _gov: (READY, "cli authenticated"))
    monkeypatch.setattr(
        er,
        "_graphiti_mcp_http_health",
        lambda: (DEGRADED, "not authenticated (blocker: allowlist)"),
    )
    _stub_github(monkeypatch)
    receipt = er.build_receipt(gov=gov, workspace=str(gov))
    assert receipt["memory_cli_status"] == READY
    assert receipt["memory_mcp_status"] == DEGRADED
    assert receipt["Graphiti_authenticated_health"] == READY
    assert receipt["overall_readiness"] == DEGRADED


def test_graphiti_probe_does_not_call_broker(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    called = {"broker": False}

    def _no_broker(*_a, **_k):
        called["broker"] = True
        raise AssertionError("probe_broker must not run")

    monkeypatch.setattr(er, "_graphiti_cli_health", lambda _gov: (READY, "cli authenticated"))
    monkeypatch.setattr(er, "_graphiti_mcp_http_health", lambda: (READY, "front door reachable"))
    monkeypatch.setattr(er, "_broker_probe", _no_broker, raising=False)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _stub_github(monkeypatch)
    receipt = er.build_receipt(gov=gov, workspace=str(gov))
    assert called["broker"] is False
    assert receipt["Graphiti_authenticated_health"] == READY
    # Only known blocker classes are emitted; an unknown value is mapped away so
    # no probe-derived string is printed verbatim.
    _, note = er._graphiti_health({"ok": False, "primary_blocker": "identity"})
    assert "identity" in note
    _, other = er._graphiti_health({"ok": False, "primary_blocker": "ghs_leaked_token_value"})
    assert "ghs_leaked_token_value" not in other
    assert "unknown" in other


# --- Integration: build a fake governance clone + fake $HOME -------------------


def _init_fake_gov(
    tmp_path: Path, *, merge_denies: bool = True, interpreter_ok: bool = True
) -> Path:
    gov = tmp_path / "gov"
    (gov / "ops" / "scripts").mkdir(parents=True)
    (gov / "ops" / "secrets").mkdir(parents=True)
    (gov / "ops" / "autonomy").mkdir(parents=True)

    # CI-009 importability probe: readiness runs gov/.venv/bin/python3 to import
    # the core deps. A working interpreter execs the real test-runner python (a
    # symlink would relocate sys.prefix into the empty fake .venv and break
    # imports); a broken one exits non-zero on import.
    venv_bin = gov / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_py = venv_bin / "python3"
    if interpreter_ok:
        fake_py.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    else:
        fake_py.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    fake_py.chmod(0o755)

    (gov / "Makefile").write_text(
        "l9-consumer-safe-list:\n\t@echo start pr pr-check improve\n", encoding="utf-8"
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


def _stub_github(monkeypatch, *, git=READY, gh=READY) -> None:
    """Keep the GitHub capability probes off the network in unit tests.

    Both are functional probes by design (`git ls-remote`, `gh api user`), so a
    test that did not stub them would depend on the runner's credentials.
    """
    monkeypatch.setattr(er, "_github_git_status", lambda _gov: (git, "stub git"))
    monkeypatch.setattr(er, "_github_gh_status", lambda: (gh, "stub gh"))


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
    monkeypatch.setattr(er, "_graphiti_cli_health", lambda _gov: (READY, "cli authenticated"))
    monkeypatch.setattr(er, "_graphiti_mcp_http_health", lambda: (READY, "front door reachable"))
    _stub_github(monkeypatch)
    return er.build_receipt(gov=gov, workspace=str(gov))


def test_ready_only_when_all_components_pass(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["merge_authority_status"] == READY
    assert receipt["Makefile_facade_status"] == READY
    assert receipt["dispatcher_status"] == READY
    assert receipt["Graphiti_authenticated_health"] == READY
    assert receipt["interpreter_importable_status"] == READY
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


def test_old_uv_is_an_observation_not_a_readiness_verdict(tmp_path: Path, monkeypatch) -> None:
    # The whole point of recording uv is that the version is EVIDENCE. An old uv
    # is a fact about the environment, not a defect, so it must never reach
    # _aggregate — a version field that can turn a healthy session DEGRADED
    # would make operators stop reading the receipt.
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setattr(er, "_uv_version", lambda: "0.8.0")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["uv_version"] == "0.8.0"
    assert receipt["overall_readiness"] == READY, receipt["warnings"]
    assert not any("uv" in w for w in receipt["warnings"])
    assert not any("uv" in f for f in receipt["failures"])


def test_unobserved_uv_neither_degrades_nor_prints_blank(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setattr(er, "_uv_version", lambda: "")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["uv_version"] == ""
    assert receipt["overall_readiness"] == READY, receipt["warnings"]
    # Legible in a pasted SessionStart block rather than a dangling "uv_version=".
    assert "uv_version=unobserved" in er._compact(receipt)


def test_compact_prints_uv_version_when_observed(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setattr(er, "_uv_version", lambda: "0.11.23")
    receipt = _build(gov, home, monkeypatch)
    assert "uv_version=0.11.23" in er._compact(receipt)


def test_blocked_when_merge_authority_regresses(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=False)  # env boolean authorized a merge
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["merge_authority_status"] == BLOCKED
    assert receipt["overall_readiness"] == BLOCKED
    assert any("merge_authority" in f for f in receipt["failures"])


def test_degraded_when_interpreter_cannot_import(tmp_path: Path, monkeypatch) -> None:
    # CI-009: an environment whose interpreter cannot import core deps must not
    # report READY — the importability dimension is DEGRADED and drags overall.
    gov = _init_fake_gov(tmp_path, merge_denies=True, interpreter_ok=False)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["interpreter_importable_status"] == DEGRADED
    assert receipt["overall_readiness"] != READY


def test_unknown_when_venv_interpreter_missing(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    # Remove the fake interpreter so the probe cannot determine importability.
    (gov / ".venv" / "bin" / "python3").unlink()
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["interpreter_importable_status"] == UNKNOWN
    assert receipt["overall_readiness"] != READY


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


# --- Truthfulness regressions (startup ceremony audit) -------------------------


def test_path_blockers_do_not_claim_an_auth_problem() -> None:
    """An egress denial must not be worded as a missing credential.

    Saying "not authenticated" over an allow-list miss invites pasting
    GRAPHITI_MCP_TOKEN, which the environment contract forbids outright.
    """
    assert er._blocker_sentence("allowlist").startswith("not reachable")
    assert er._blocker_sentence("reachability").startswith("not reachable")
    assert er._blocker_sentence("identity").startswith("not authenticated")


def test_timestamp_is_generation_time_not_the_commit_date(tmp_path: Path, monkeypatch) -> None:
    """The receipt must not appear to predate the inputs it summarizes.

    `timestamp` used to carry the governance commit date, so a receipt written
    at 17:13 reported 16:57 — earlier than the bootstrap-state.json it
    summarizes. The clock is pinned here rather than compared for inequality: a
    fake clone committed in the same second as the receipt makes an inequality
    assertion pass or fail by coincidence.
    """
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path)
    monkeypatch.setattr(er, "_now_iso", lambda: "2099-01-01T00:00:00+00:00")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["timestamp"] == "2099-01-01T00:00:00+00:00"
    assert receipt["governance_commit_time"] == er._git(gov, "log", "-1", "--format=%cI")


def test_github_capability_is_reported(tmp_path: Path, monkeypatch) -> None:
    """An absent gh CLI must surface at startup, not at publish time."""
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(er, "_graphiti_cli_health", lambda _gov: (READY, "cli authenticated"))
    monkeypatch.setattr(er, "_graphiti_mcp_http_health", lambda: (READY, "front door reachable"))
    _stub_github(monkeypatch, git=READY, gh=DEGRADED)
    receipt = er.build_receipt(gov=gov, workspace=str(gov))
    assert receipt["github_git_status"] == READY
    assert receipt["github_gh_status"] == DEGRADED
    assert receipt["overall_readiness"] == DEGRADED


def test_command_collisions_downgrade_the_command_domain(tmp_path: Path, monkeypatch) -> None:
    """Dropped commands must not sit behind a READY command projection."""
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path)
    cl = home / ".l9" / "claude"
    domains = [
        {"domain": d, "status": "ok"}
        for d in ("skills", "rules", "settings", "hooks", "plugins", "mcp")
    ]
    domains.append(
        {
            "domain": "commands",
            "status": "ok",
            "collisions": ["command-skill-collision:l9-pr-remediation"],
        }
    )
    (cl / "projection-receipt.json").write_text(json.dumps({"domains": domains}), encoding="utf-8")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["command_projection_status"] == DEGRADED
    assert receipt["skill_projection_status"] == READY
    assert "l9-pr-remediation" in receipt["notes"]["command_projection_status"]


def test_facade_count_ignores_toolchain_preamble(tmp_path: Path, monkeypatch) -> None:
    """The target count must not drift with incidental preamble lines."""
    gov = tmp_path / "gov"
    gov.mkdir()
    (gov / "Makefile").write_text("all:\n", encoding="utf-8")
    monkeypatch.setattr(
        er,
        "_run",
        lambda *_a, **_k: (
            0,
            "UV: cached locked environment\nOK: gov-python /x/y/python\nstart pr pr-check\n",
            "",
        ),
    )
    status, note = er._makefile_facade(gov)
    assert status == READY
    assert note == "3 CONSUMER_SAFE targets"
