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


def test_memory_health_classifies_probe_not_broker() -> None:
    """Memory compact health is the canonical readiness probe, not a broker /whoami."""
    status, note = er._memory_health({"ok": False, "primary_blocker": "store"})
    assert status == DEGRADED
    assert "store" in note
    assert er._memory_health({"ok": True})[0] == READY
    assert er._memory_health({})[0] == UNKNOWN
    # Unknown blocker vocabulary is mapped away: no probe-derived text is printed.
    _, other = er._memory_health({"ok": False, "primary_blocker": "ghs_leaked_token_value"})
    assert "ghs_leaked_token_value" not in other
    assert "unknown" in other


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


def _levels(**overrides: str) -> dict[str, str]:
    base = {f"R{i}": "pass" for i in range(10)}
    base["R5"] = "skipped"
    base.update(overrides)
    return base


def _stub_interpreter(
    tmp_path: Path, *, carries_package: bool = True, name: str = "python"
) -> Path:
    """A REAL executable standing in for a bound interpreter.

    READY must mean "actually runnable": the previous fixtures exported a
    nonexistent `/venv/bin/python` and still expected READY, which positively
    encoded the false-ready the emitter exists to prevent (PR #548 review,
    F-548-005). The stub answers the package probe the emitter asks of it.
    """
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    stub = venv_bin / name
    stub.write_text(f"#!/bin/sh\nexit {0 if carries_package else 1}\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def tmp_path_of(gov: Path) -> Path:
    """The pytest tmp dir a fake gov lives in (`_init_fake_gov` puts it at tmp/gov)."""
    return gov.parent


def _render_memory_server(workspace: Path, command: str = "${L9_MEMORY_INTERPRETER}") -> None:
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"l9-graphite-memory": {"command": command}}}),
        encoding="utf-8",
    )


def test_memory_layers_map_to_three_dimensions(tmp_path: Path, monkeypatch) -> None:
    """R0/R1 -> cli, R2/R3/R6 -> control plane; mcp is Claude .mcp.json + env, not R4."""
    assert er._memory_cli_health(_levels())[0] == READY
    assert er._memory_control_plane_health(_levels())[0] == READY
    status, note = er._memory_cli_health(_levels(R0="fail"))
    assert status == DEGRADED and "unbound" in note
    status, note = er._memory_control_plane_health(_levels(R2="fail"))
    assert status == DEGRADED and "store" in note
    status, note = er._memory_control_plane_health(_levels(R6="fail"))
    assert status == DEGRADED and "namespace" in note
    # An unrunnable readiness report is UNKNOWN, never PASS.
    assert er._memory_cli_health(None)[0] == UNKNOWN
    assert er._memory_control_plane_health(None)[0] == UNKNOWN

    monkeypatch.delenv("L9_MEMORY_INTERPRETER", raising=False)
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED and "L9_MEMORY_INTERPRETER" in note
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED and "mcp.json" in note
    _render_memory_server(tmp_path)
    assert er._claude_mcp_health(tmp_path)[0] == READY


# --- F-548-005: readiness is executable binding truth, not configuration presence


def test_nonexistent_interpreter_is_not_ready(tmp_path: Path, monkeypatch) -> None:
    """The exact fixture the old tests accepted: an exported path that does not exist."""
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", "/venv/bin/python")
    _render_memory_server(tmp_path)
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED
    assert "not a file" in note and "mcp_config" in note


def test_non_executable_interpreter_is_not_ready(tmp_path: Path, monkeypatch) -> None:
    stub = _stub_interpreter(tmp_path)
    stub.chmod(0o644)
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(stub))
    _render_memory_server(tmp_path)
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED and "not executable" in note


def test_rendered_command_not_bound_to_the_interpreter_is_not_ready(
    tmp_path: Path, monkeypatch
) -> None:
    """What Claude would launch must be what was proven."""
    stub = _stub_interpreter(tmp_path)
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(stub))
    _render_memory_server(tmp_path, command="/usr/bin/python3")
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED and "not bound to L9_MEMORY_INTERPRETER" in note
    # The same path spelled out literally is the same binding.
    _render_memory_server(tmp_path, command=str(stub))
    assert er._claude_mcp_health(tmp_path)[0] == READY


def test_stale_interpreter_without_the_package_is_not_ready(tmp_path: Path, monkeypatch) -> None:
    """An interpreter that runs but no longer carries l9_graphite_memory is a stale binding."""
    stub = _stub_interpreter(tmp_path, carries_package=False)
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(stub))
    _render_memory_server(tmp_path)
    status, note = er._claude_mcp_health(tmp_path)
    assert status == DEGRADED and "stale binding" in note


def test_interpreter_probe_that_cannot_run_is_unknown_never_ready(
    tmp_path: Path, monkeypatch
) -> None:
    stub = _stub_interpreter(tmp_path)
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(stub))
    _render_memory_server(tmp_path)
    monkeypatch.setattr(er, "_interpreter_carries_memory_package", lambda _p: None)
    status, note = er._claude_mcp_health(tmp_path)
    assert status == UNKNOWN and "did not complete" in note


def test_the_package_probe_asks_the_bound_interpreter_itself(tmp_path: Path) -> None:
    """Executed, not inferred: the probe runs the interpreter and reads its exit."""
    yes = _stub_interpreter(tmp_path, carries_package=True, name="yes-python")
    no = _stub_interpreter(tmp_path, carries_package=False, name="no-python")
    assert er._interpreter_carries_memory_package(yes) is True
    assert er._interpreter_carries_memory_package(no) is False
    assert er._interpreter_carries_memory_package(tmp_path / "missing") is None


def test_memory_probe_reads_no_provider_url(monkeypatch) -> None:
    """Stage C9: the probe is the canonical readiness report, not an HTTP front door."""
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="fail"))
    monkeypatch.delenv("L9_MEMORY_INTERPRETER", raising=False)
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    probe = er.memory_probe(Path("/nowhere"))
    assert probe["cli"]["status"] == READY
    assert probe["control_plane"]["status"] == READY
    assert probe["mcp"]["status"] == DEGRADED
    assert not hasattr(er, "_graphiti_mcp_http_health")
    assert not hasattr(er, "graphiti_mcp_url")
    assert not hasattr(er, "_memory_mcp_health")


def test_claude_mcp_ready_when_cursor_r4_would_fail(tmp_path: Path, monkeypatch) -> None:
    """Claude mcp is workspace .mcp.json + interpreter, not Cursor diagnostics R4."""
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    _render_memory_server(tmp_path)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="fail"))
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    probe = er.memory_probe(tmp_path, tmp_path)
    assert probe["mcp"]["status"] == READY
    assert probe["cli"]["status"] == READY
    assert probe["control_plane"]["status"] == READY


def test_memory_probe_skip_env_honors_both_names(monkeypatch) -> None:
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R0="fail"))
    monkeypatch.delenv("L9_MEMORY_PROBE_SKIP", raising=False)
    monkeypatch.setenv("L9_GRAPHITI_PROBE_SKIP", "1")
    assert er.memory_probe(Path("/nowhere"))["cli"]["status"] == READY
    monkeypatch.delenv("L9_GRAPHITI_PROBE_SKIP", raising=False)
    monkeypatch.setenv("L9_MEMORY_PROBE_SKIP", "1")
    assert er.memory_probe(Path("/nowhere"))["cli"]["status"] == READY


def test_bound_cli_and_missing_mcp_entry_are_not_one_word(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="fail"))
    receipt = er.build_receipt(gov=gov, workspace=str(gov))
    assert receipt["memory_cli_status"] == READY
    assert receipt["memory_control_plane_status"] == READY
    assert receipt["memory_mcp_status"] == DEGRADED
    assert receipt["overall_readiness"] == DEGRADED


def test_a_server_the_projection_gated_out_is_an_unbound_interpreter(
    tmp_path: Path, monkeypatch
) -> None:
    """The Claude authority over `.mcp.json` is the projection, not `~/.cursor`.

    R4 asks the memory package for `client cursor status`, which reads
    `~/.cursor/mcp.json`; grading a Claude surface from a Cursor artifact was
    a permanent false DEGRADED on Web and Mobile, and R4 is no longer read.
    But the projection gates l9-graphite-memory out on exactly one condition —
    L9_MEMORY_INTERPRETER unbound — and since PR #548 the SessionStart binder
    is what establishes that variable, so a gated-out memory server is a
    binding that did not happen, not a state governance intends. It reads
    DEGRADED with the gating named; only `context7` (a platform-proxied
    credential) is an absence by design.
    """
    monkeypatch.delenv("L9_MEMORY_INTERPRETER", raising=False)
    gated = frozenset({er._MEMORY_MCP_SERVER})
    status, note = er._claude_mcp_health(tmp_path, gated_out=gated)
    assert status == DEGRADED
    assert "L9_MEMORY_INTERPRETER" in note and "gated" in note
    # Gating cannot upgrade a bound-and-rendered verdict either way.
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    _render_memory_server(tmp_path)
    assert er._claude_mcp_health(tmp_path, gated_out=gated)[0] == READY
    assert er._claude_mcp_health(tmp_path, gated_out=frozenset({"context7"}))[0] == READY


def test_r4_is_never_consulted_for_the_claude_mcp_verdict(tmp_path: Path, monkeypatch) -> None:
    """The Cursor client-config level cannot degrade or pass a Claude surface."""
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    _render_memory_server(tmp_path)
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="fail"))
    assert er.memory_probe(tmp_path, tmp_path)["mcp"]["status"] == READY
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="pass"))
    monkeypatch.delenv("L9_MEMORY_INTERPRETER")
    assert er.memory_probe(tmp_path, tmp_path)["mcp"]["status"] == DEGRADED


def test_gated_out_servers_are_read_from_the_receipt_not_the_environment(monkeypatch) -> None:
    """Same discipline as the plugins carve-out: evidence where the claim is made."""
    monkeypatch.delenv("L9_MEMORY_INTERPRETER", raising=False)
    assert er._gated_out_servers(None) == frozenset()
    assert er._gated_out_servers({"domains": [{"domain": "mcp", "status": "ok"}]}) == frozenset()
    receipt = {
        "domains": [
            {"domain": "mcp", "status": "ok", "detail": {"gated_out_servers": ["context7"]}}
        ]
    }
    assert er._gated_out_servers(receipt) == frozenset({"context7"})


def test_probe_without_a_projection_lets_r4_decide_alone() -> None:
    """No ambient $HOME read: an unsupplied projection means no gating is known."""
    import inspect

    source = inspect.getsource(er.memory_probe)
    assert "Path.home()" not in source


def test_gated_memory_entry_is_degraded_and_names_the_gating(tmp_path: Path, monkeypatch) -> None:
    """An unbound interpreter is a binding that did not happen: DEGRADED, warned, legible."""
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY", gated_out=[er._MEMORY_MCP_SERVER, "context7"])
    monkeypatch.delenv("L9_MEMORY_INTERPRETER", raising=False)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels(R4="fail"))
    receipt = _build_with_levels(gov, home, monkeypatch)
    assert receipt["memory_mcp_status"] == DEGRADED
    assert receipt["overall_readiness"] == DEGRADED
    assert any("L9_MEMORY_INTERPRETER" in w and "gated" in w for w in receipt["warnings"])


def test_a_rendered_but_unbound_memory_entry_still_degrades(tmp_path: Path, monkeypatch) -> None:
    """The cascade that arms the repair stays available for a real defect."""
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY", gated_out=[])
    # Rendered, but bound to some other python than the proven one.
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    _render_memory_server(gov, command="/usr/bin/python3")
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels())
    receipt = _build_with_levels(gov, home, monkeypatch)
    assert receipt["memory_mcp_status"] == DEGRADED
    assert receipt["overall_readiness"] == DEGRADED
    assert any("not bound to L9_MEMORY_INTERPRETER" in w for w in receipt["warnings"])


def test_ready_requires_a_real_executable_binding_end_to_end(tmp_path: Path, monkeypatch) -> None:
    """The full receipt: nonexistent interpreter is not READY; a real stub is."""
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", "/venv/bin/python")
    _render_memory_server(gov)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels())
    receipt = _build_with_levels(gov, home, monkeypatch)
    assert receipt["memory_mcp_status"] == DEGRADED
    assert receipt["overall_readiness"] != READY
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path)))
    receipt = _build_with_levels(gov, home, monkeypatch)
    assert receipt["memory_mcp_status"] == READY
    assert receipt["overall_readiness"] == READY, receipt["warnings"]


def test_memory_probe_does_not_call_broker(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    called = {"broker": False}

    def _no_broker(*_a, **_k):
        called["broker"] = True
        raise AssertionError("probe_broker must not run")

    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels())
    monkeypatch.setattr(er, "_broker_probe", _no_broker, raising=False)
    home = _fake_home(tmp_path, mcp="READY")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    receipt = er.build_receipt(gov=gov, workspace=str(gov))
    assert called["broker"] is False
    assert receipt["memory_control_plane_status"] == READY


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


def _fake_home(tmp_path: Path, *, mcp: str = "READY", gated_out: list[str] | None = None) -> Path:
    home = tmp_path / "home"
    cl = home / ".l9" / "claude"
    cl.mkdir(parents=True)
    domains: list[dict] = [
        {"domain": d, "status": "ok"}
        for d in ("skills", "commands", "rules", "settings", "hooks", "plugins", "mcp")
    ]
    if gated_out is not None:
        for entry in domains:
            if entry["domain"] == "mcp":
                entry["detail"] = {"gated_out_servers": list(gated_out), "managed_servers": []}
    (cl / "projection-receipt.json").write_text(json.dumps({"domains": domains}), encoding="utf-8")
    (cl / "bootstrap-state.json").write_text(json.dumps({"mcp": mcp}), encoding="utf-8")
    return home


def _build(gov: Path, home: Path, monkeypatch) -> dict:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("L9_MEMORY_INTERPRETER", str(_stub_interpreter(tmp_path_of(gov))))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _render_memory_server(gov)
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(er, "_memory_levels", lambda _gov: _levels())
    return er.build_receipt(gov=gov, workspace=str(gov))


def _build_with_levels(gov: Path, home: Path, monkeypatch) -> dict:
    """`_build` without pinning the memory levels, so a caller can choose them."""
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    for name in er._MEMORY_PROBE_SKIP_ENVS:
        monkeypatch.delenv(name, raising=False)
    return er.build_receipt(gov=gov, workspace=str(gov))


def test_ready_only_when_all_components_pass(tmp_path: Path, monkeypatch) -> None:
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["merge_authority_status"] == READY
    assert receipt["Makefile_facade_status"] == READY
    assert receipt["dispatcher_status"] == READY
    assert receipt["memory_control_plane_status"] == READY
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


def test_memory_transport_is_a_posture_not_a_measured_credential(
    tmp_path: Path, monkeypatch
) -> None:
    """Stage C9: memory is stdio to the bound runtime; there is no bearer to measure.

    The receipt reports the transport as a constant observation and never a
    dimension, and the retired provider fields never come back under any
    spelling — a token in the environment changes nothing, because nothing on
    this surface reads one.
    """
    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)
    assert receipt["memory_transport"] == er.MEMORY_TRANSPORT == "stdio-control-plane"
    assert receipt["memory_control_plane_status"] == READY
    assert receipt["overall_readiness"] == READY, receipt["warnings"]

    monkeypatch.setenv("GRAPHITI_MCP_TOKEN", "probe-only-not-a-real-token")
    again = _build(gov, home, monkeypatch)
    assert again["memory_transport"] == "stdio-control-plane"

    for retired in (
        "Graphiti_reachability",
        "Graphiti_authenticated_health",
        "graphiti_transport_auth",
    ):
        assert retired not in receipt
        assert retired not in receipt["notes"]
    assert "authenticated" not in str(receipt["notes"].get("memory_control_plane_status", ""))


def test_receipt_carries_a_write_time_and_expires(tmp_path: Path, monkeypatch) -> None:
    """A receipt whose age is unknowable must not be reported as current.

    Historical `timestamp` was git %cI (commit date) and read like a write
    time, so freshness inverted. Both clocks are now the UTC write instant;
    commit date lives under governance_committed_at.
    """
    from datetime import UTC, datetime, timedelta

    gov = _init_fake_gov(tmp_path, merge_denies=True)
    home = _fake_home(tmp_path, mcp="READY")
    receipt = _build(gov, home, monkeypatch)

    assert receipt["generated_at"], "receipt must record when it was written"
    assert receipt["timestamp"] == receipt["generated_at"]
    assert receipt["ttl_seconds"] == er.RECEIPT_TTL_SECONDS
    datetime.strptime(receipt["generated_at"], er._TIMESTAMP_FORMAT)

    commit_date = subprocess.run(
        ["git", "-C", str(gov), "log", "-1", "--format=%cI"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert receipt["governance_committed_at"] == commit_date

    assert er.receipt_freshness(receipt)["state"] == er.FRESH

    written = datetime.strptime(receipt["generated_at"], er._TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    later = written + timedelta(seconds=er.RECEIPT_TTL_SECONDS + 1)
    assert er.receipt_freshness(receipt, now=later)["state"] == er.EXPIRED

    # Absence is a distinct state from expiry.
    assert er.receipt_freshness(None)["state"] == er.NEVER_RAN
    # So is a receipt predating generated_at — unknowable age is never fresh.
    assert er.receipt_freshness({"schema_version": er.SCHEMA_VERSION})["state"] == er.EXPIRED


# --- SessionStart reuse: the receipt is handed back only while it is believable


def _fresh_receipt(sha: str = "abc123", workspace: str = "/ws") -> dict:
    from datetime import UTC, datetime

    return {
        "schema_version": er.SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime(er._TIMESTAMP_FORMAT),
        "ttl_seconds": er.RECEIPT_TTL_SECONDS,
        "governance_SHA": sha,
        "workspace": workspace,
        "overall_readiness": READY,
        "governance_default_branch": "main",
    }


def test_reusable_receipt_requires_fresh_same_workspace_and_live_sha(
    tmp_path: Path, monkeypatch
) -> None:
    """Deterministic invalidation: TTL, workspace, and the checked-out SHA.

    The SessionStart hook re-ran every probe (~6 s, 5.3 s of it the memory
    diagnostics) on every startup, resume and compaction to re-measure a
    receipt that already declares its own validity window. Reuse is allowed
    only inside that window and only for the same workspace and revision.
    """
    from datetime import UTC, datetime, timedelta

    gov = tmp_path / "gov"
    monkeypatch.setattr(er, "_git", lambda _g, *a: "abc123" if a == ("rev-parse", "HEAD") else "")
    receipt = _fresh_receipt()

    assert er.reusable_receipt(receipt, gov=gov, workspace="/ws") is receipt
    assert er.reusable_receipt(receipt, gov=gov, workspace="/elsewhere") is None
    assert er.reusable_receipt(_fresh_receipt(sha="def456"), gov=gov, workspace="/ws") is None
    stale = datetime.now(UTC) - timedelta(seconds=er.RECEIPT_TTL_SECONDS + 1)
    expired = {**receipt, "generated_at": stale.strftime(er._TIMESTAMP_FORMAT)}
    assert er.reusable_receipt(expired, gov=gov, workspace="/ws") is None
    assert er.reusable_receipt(None, gov=gov, workspace="/ws") is None
    assert er.reusable_receipt({**receipt, "schema_version": "x"}, gov=gov, workspace="/ws") is None

    # An unknowable live SHA is not a match — a missing probe must not
    # manufacture reuse out of a receipt that may describe another revision.
    monkeypatch.setattr(er, "_git", lambda _g, *a: "")
    assert er.reusable_receipt(receipt, gov=gov, workspace="/ws") is None


def test_compact_names_the_receipt_source() -> None:
    receipt = _fresh_receipt()
    assert "receipt_source=rebuilt" in er._compact(receipt)
    assert "receipt_source=reused" in er._compact(receipt, source=er.REUSED)


def test_reuse_fresh_skips_every_probe_and_leaves_the_file_untouched(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """With a believable receipt on disk, `--read --reuse-fresh` runs no probe."""
    path = tmp_path / "readiness-receipt.json"
    receipt = _fresh_receipt(workspace=str(tmp_path))
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setenv("L9_READINESS_RECEIPT_FILE", str(path))
    monkeypatch.setattr(er, "_git", lambda _g, *a: "abc123" if a == ("rev-parse", "HEAD") else "")

    def _must_not_run(**_kwargs):  # pragma: no cover - the assertion IS the call
        raise AssertionError("build_receipt ran despite a reusable receipt")

    monkeypatch.setattr(er, "build_receipt", _must_not_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "emit_claude_readiness.py",
            "--root",
            str(tmp_path),
            "--workspace",
            str(tmp_path),
            "--read",
            "--reuse-fresh",
        ],
    )
    assert er.main() == 0
    out = capsys.readouterr().out
    assert "receipt_source=reused" in out
    assert "receipt_freshness=fresh" in out
    assert path.read_bytes() == before, "reuse must not rewrite the receipt"


def test_reuse_fresh_rebuilds_when_the_sha_moved(tmp_path: Path, monkeypatch, capsys) -> None:
    path = tmp_path / "readiness-receipt.json"
    path.write_text(json.dumps(_fresh_receipt(sha="old", workspace=str(tmp_path))) + "\n")
    monkeypatch.setenv("L9_READINESS_RECEIPT_FILE", str(path))
    monkeypatch.setattr(er, "_git", lambda _g, *a: "new" if a == ("rev-parse", "HEAD") else "")
    calls: list[dict] = []

    def _fake_build(**kwargs):
        calls.append(kwargs)
        return _fresh_receipt(sha="new", workspace=str(tmp_path))

    monkeypatch.setattr(er, "build_receipt", _fake_build)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "emit_claude_readiness.py",
            "--root",
            str(tmp_path),
            "--workspace",
            str(tmp_path),
            "--read",
            "--reuse-fresh",
        ],
    )
    assert er.main() == 0
    assert len(calls) == 1, "a moved SHA must rebuild"
    assert "receipt_source=rebuilt" in capsys.readouterr().out
    assert json.loads(path.read_text(encoding="utf-8"))["governance_SHA"] == "new"
