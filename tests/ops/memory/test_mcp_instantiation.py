"""Per-machine Cursor MCP instantiation (stage C7): real file, no legacy front door.

The memory entry is delegated to the package configurator against the bound
runtime; nothing here authors it. A symlinked target is always replaced with a
real file, because the configurator refuses symlinks by design.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from ops.memory import mcp_instantiation as inst
from ops.memory.runtime_binding import RuntimeBinding

ROOT = Path(__file__).resolve().parents[3]
MASTER = ROOT / "environment" / "mcp" / "master.mcp.json"
MEMORY_ARGS = ["-m", "l9_graphite_memory.server", "--transport", "stdio"]


def _master(**servers: Any) -> dict[str, Any]:
    return {"_comment": ["fixture"], "mcpServers": servers}


def _binding(tmp_path: Path, *, ok: bool = True) -> RuntimeBinding:
    venv = tmp_path / "venv" / "bin"
    venv.mkdir(parents=True, exist_ok=True)
    (venv / "python").write_text("", encoding="utf-8")
    (venv / "l9-memory").write_text("", encoding="utf-8")
    return RuntimeBinding(
        status="exact" if ok else "unbound",
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="2.3.0",
        expected_contract_version="memory-control-plane/v1",
        manifest_path=str(tmp_path / "memory-binding.json"),
        interpreter=str(venv / "python"),
        memory_cli=str(venv / "l9-memory"),
        reasons=() if ok else ("not bound",),
    )


def _authorized_onboarding() -> dict[str, Any]:
    from ops.memory.auth0_native_oauth import load_onboarding

    document = load_onboarding()
    document["issuer"]["domain"] = "tenant.example.invalid"
    document["issuer"]["issuer_url"] = "https://tenant.example.invalid/"
    document["resource"]["identifier"] = "https://memory.example/mcp"
    document["clients"]["cursor-native"]["client_id"] = "synthetic-cursor-public"
    document["clients"]["claude-account-connector"]["client_id"] = "synthetic-claude-public"
    return document


NATIVE_HTTP = {
    "type": "streamable-http",
    "url": "https://memory.example/mcp",
    "auth": {
        "CLIENT_ID": "synthetic-cursor-public",
        "scopes": ["memory.read", "memory.write"],
    },
}


class _Runner:
    def __init__(self, rc: int = 0, kind: str = "stdio") -> None:
        self.calls: list[list[str]] = []
        self.envs: list[dict[str, str]] = []
        self.rc = rc
        self.kind = kind

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        env = kwargs.get("env")
        self.envs.append(dict(env) if isinstance(env, dict) else {})
        if "-c" in argv:
            if self.kind == "http":
                payload: dict[str, Any] = dict(NATIVE_HTTP)
            elif self.kind == "secret":
                payload = {
                    "url": "https://memory.example/mcp",
                    "type": "streamable-http",
                    "headers": {"Authorization": "Bearer literal-secret"},
                }
            else:
                payload = {"command": "/tmp/python", "args": MEMORY_ARGS, "type": "stdio"}
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(argv, self.rc, json.dumps({"status": "complete"}), "")


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def test_render_copies_managed_servers_and_drops_the_legacy_front_door() -> None:
    master = _master(
        **{
            "Playwright": {"command": "npx", "args": ["@playwright/mcp@latest"], "_note": "x"},
            "graphiti-memory": {"url": "http://127.0.0.1:8100/mcp"},
            "l9-graphite-memory": {"command": "${L9_MEMORY_INTERPRETER}", "args": MEMORY_ARGS},
        }
    )
    existing = {
        "mcpServers": {
            "graphiti-memory": {"url": "http://127.0.0.1:8100/mcp"},
            "my-own": {"command": "/me/server"},
            "l9-graphite-memory": {"command": "/venv/bin/python", "args": MEMORY_ARGS},
        }
    }
    config, dropped, preserved = inst.render_machine_config(master, existing)
    servers = config["mcpServers"]
    assert servers["Playwright"] == {"command": "npx", "args": ["@playwright/mcp@latest"]}
    assert "graphiti-memory" not in servers
    assert servers["my-own"] == {"command": "/me/server"}
    assert "l9-graphite-memory" not in servers
    assert preserved == ["my-own"]
    assert set(dropped) == {"graphiti-memory", "l9-graphite-memory"}


def test_existing_http_memory_entry_is_dropped_before_package_install() -> None:
    """Known-bad: a hand-written HTTP URL used to survive as native Memory."""

    existing = {
        "mcpServers": {
            "my-own": {"command": "/me/server"},
            "l9-graphite-memory": {
                "type": "streamable-http",
                "url": "https://user:secret@graphiti.example/mcp",
            },
        }
    }
    config, dropped, preserved = inst.render_machine_config(_master(), existing)
    assert "l9-graphite-memory" not in config["mcpServers"]
    assert config["mcpServers"]["my-own"] == {"command": "/me/server"}
    assert preserved == ["my-own"]
    assert "package-owned" in dropped["l9-graphite-memory"]
    assert "secret" not in json.dumps(config)
    assert (
        inst.classify_managed_config(
            {
                "type": "streamable-http",
                "url": "https://user:secret@graphiti.example/mcp",
            }
        )
        == "unknown"
    )


def test_exact_native_memory_entry_is_preserved_only_with_package_evidence() -> None:
    expected = dict(NATIVE_HTTP)
    existing = {"mcpServers": {inst.MEMORY_KEY: dict(expected)}}
    config, dropped, preserved = inst.render_machine_config(
        _master(), existing, expected_native_memory=expected
    )
    assert config["mcpServers"][inst.MEMORY_KEY] == expected
    assert inst.MEMORY_KEY not in dropped
    assert preserved == []  # Package-owned, never an unmanaged consumer server.

    # HTTP-looking but not package-owned: reject without trying to infer provenance.
    foreign = {
        "mcpServers": {
            inst.MEMORY_KEY: {
                "type": "streamable-http",
                "url": "https://graphiti.example/mcp",
            }
        }
    }
    config, dropped, preserved = inst.render_machine_config(
        _master(), foreign, expected_native_memory=expected
    )
    assert inst.MEMORY_KEY not in config["mcpServers"]
    assert inst.MEMORY_KEY in dropped
    assert preserved == []

    # An unverified expectation is not admissible even when structurally equal.
    config, _, _ = inst.render_machine_config(
        _master(), existing, expected_native_memory={"type": "stdio", "command": "/tmp/a"}
    )
    assert inst.MEMORY_KEY not in config["mcpServers"]


def test_render_from_nothing_has_no_memory_entry_and_no_private_keys() -> None:
    config, dropped, preserved = inst.render_machine_config(
        _master(docs={"command": "tool", "_owner": "x"}), None
    )
    assert config == {"mcpServers": {"docs": {"command": "tool"}}}
    assert dropped == {} and preserved == []


def test_real_master_carries_no_legacy_front_door_and_no_secret_values() -> None:
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    assert "graphiti-memory" not in master["mcpServers"]
    assert "l9-graphite-memory" not in master["mcpServers"], "memory is never authored here"
    config, dropped, _ = inst.render_machine_config(master, None)
    text = json.dumps(config)
    assert "graphiti-memory" not in text
    assert "GRAPHITI" not in text
    assert dropped == {}
    # Credentials stay ${VAR} references; a rendered value would be a leak.
    for server in config["mcpServers"].values():
        for value in (server.get("env") or {}).values():
            assert str(value).startswith("${")


# ---------------------------------------------------------------------------
# instantiate
# ---------------------------------------------------------------------------


def test_symlink_is_replaced_with_a_real_file_and_the_master_survives(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(
        json.dumps(_master(Playwright={"command": "npx"}, **{"graphiti-memory": {"url": "x"}})),
        encoding="utf-8",
    )
    target = tmp_path / "cursor" / "mcp.json"
    target.parent.mkdir()
    target.symlink_to(master_path)
    receipt = inst.instantiate(path=target, master_path=master_path, skip_memory=True)
    assert receipt["status"] == "written"
    assert receipt["was_symlink_to"] == str(master_path)
    assert receipt["replaced_symlink"] == str(master_path)
    assert not target.is_symlink() and target.is_file()
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["mcpServers"] == {"Playwright": {"command": "npx"}}
    assert oct(target.stat().st_mode & 0o777) == "0o600"
    # The governed master is untouched.
    assert "graphiti-memory" in json.loads(master_path.read_text(encoding="utf-8"))["mcpServers"]


def test_check_mode_reports_drift_and_writes_nothing(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master(Playwright={"command": "npx"})), encoding="utf-8")
    target = tmp_path / "mcp.json"
    receipt = inst.instantiate(path=target, master_path=master_path, check=True, skip_memory=True)
    assert receipt["status"] == "drift" and inst.exit_code(receipt) == 2
    assert not target.exists()
    receipt = inst.instantiate(path=target, master_path=master_path, skip_memory=True)
    assert receipt["status"] == "written"
    receipt = inst.instantiate(path=target, master_path=master_path, check=True, skip_memory=True)
    assert receipt["status"] == "unchanged" and inst.exit_code(receipt) == 0


def test_existing_regular_file_is_backed_up_and_user_servers_preserved(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master(Playwright={"command": "npx"})), encoding="utf-8")
    target = tmp_path / "mcp.json"
    target.write_text(
        json.dumps({"mcpServers": {"mine": {"command": "/x"}, "graphiti-memory": {"url": "u"}}}),
        encoding="utf-8",
    )
    receipt = inst.instantiate(path=target, master_path=master_path, skip_memory=True)
    assert receipt["status"] == "written"
    assert receipt["backup"] and Path(receipt["backup"]).is_file()
    servers = json.loads(target.read_text(encoding="utf-8"))["mcpServers"]
    assert set(servers) == {"mine", "Playwright"}
    assert receipt["dropped"]["graphiti-memory"].startswith("legacy")


def test_memory_entry_is_delegated_to_the_bound_runtime(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master()), encoding="utf-8")
    target = tmp_path / "mcp.json"
    binding = _binding(tmp_path)
    runner = _Runner(kind="http")
    receipt = inst.instantiate(
        path=target,
        master_path=master_path,
        verify=True,
        binding_resolver=lambda: binding,
        runner=runner,
        onboarding=_authorized_onboarding(),
    )
    memory = receipt["memory"]
    assert memory["status"] == "verified"
    assert memory["interpreter_source"] == "runtime_binding:pinned_environment"
    inspect_call, install, verify = runner.calls
    assert "-c" in inspect_call
    assert install[0] == binding.memory_cli
    assert install[1:4] == ["client", "cursor", "install"]
    assert install[install.index("--path") + 1] == str(target)
    assert install[install.index("--interpreter") + 1] == binding.interpreter
    assert all(inst.ENV_MCP_LAUNCHER not in env for env in runner.envs)
    assert verify[1:4] == ["client", "cursor", "verify"] and "--path" in verify
    assert receipt["binding_status"] == "exact"
    assert receipt["authority"] == "none" and receipt["schema"] == inst.RECEIPT_SCHEMA


def test_verified_native_memory_survives_check_and_reinstall(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master()), encoding="utf-8")
    target = tmp_path / "mcp.json"
    native = dict(NATIVE_HTTP)
    original = (
        json.dumps(
            {"mcpServers": {"mine": {"command": "/mine"}, inst.MEMORY_KEY: native}},
            indent=2,
        )
        + "\n"
    )
    target.write_text(original, encoding="utf-8")
    binding = _binding(tmp_path)
    runner = _Runner(kind="http")

    check = inst.instantiate(
        path=target,
        master_path=master_path,
        check=True,
        binding_resolver=lambda: binding,
        runner=runner,
        onboarding=_authorized_onboarding(),
    )
    assert check["status"] == "unchanged"
    assert check["memory"]["status"] == "installed"
    assert inst.exit_code(check) == 0
    assert target.read_text(encoding="utf-8") == original

    install = inst.instantiate(
        path=target,
        master_path=master_path,
        binding_resolver=lambda: binding,
        runner=runner,
        onboarding=_authorized_onboarding(),
    )
    assert install["status"] == "unchanged"
    assert install["memory"]["status"] == "installed"
    assert install["preserved_unmanaged"] == ["mine"]
    assert target.read_text(encoding="utf-8") == original


def test_launcher_override_is_stripped_from_inspect_install_and_verify(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setenv(inst.ENV_MCP_LAUNCHER, "/tmp/legacy-launcher")
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master()), encoding="utf-8")
    runner = _Runner(kind="http")
    result = inst.instantiate(
        path=tmp_path / "mcp.json",
        master_path=master_path,
        verify=True,
        binding_resolver=lambda: _binding(tmp_path),
        runner=runner,
        onboarding=_authorized_onboarding(),
    )
    assert result["memory"]["status"] == "verified"
    assert len(runner.envs) == 3  # inspector + install + probe
    assert all(inst.ENV_MCP_LAUNCHER not in env for env in runner.envs)
    # Do not change the parent or leak its launcher into the managed client.
    assert os.environ[inst.ENV_MCP_LAUNCHER] == "/tmp/legacy-launcher"


def test_unbound_runtime_installs_nothing_and_says_why(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master()), encoding="utf-8")
    runner = _Runner()
    receipt = inst.instantiate(
        path=tmp_path / "mcp.json",
        master_path=master_path,
        binding_resolver=lambda: _binding(tmp_path, ok=False),
        runner=runner,
    )
    assert receipt["memory"]["status"] == "skipped"
    assert receipt["memory"]["binding_reasons"] == ["not bound"]
    assert runner.calls == []


def test_blocked_install_is_a_failure_exit(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master()), encoding="utf-8")
    receipt = inst.instantiate(
        path=tmp_path / "mcp.json",
        master_path=master_path,
        binding_resolver=lambda: _binding(tmp_path),
        runner=_Runner(rc=2, kind="http"),
        onboarding=_authorized_onboarding(),
    )
    assert receipt["memory"]["status"] == "blocked"
    assert inst.exit_code(receipt) == 1


def test_cli_writes_a_receipt_with_no_authority(tmp_path: Path) -> None:
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master(Playwright={"command": "npx"})), encoding="utf-8")
    target = tmp_path / "mcp.json"
    receipt_path = tmp_path / "receipt.json"
    code = inst.main(
        [
            "--path",
            str(target),
            "--master",
            str(master_path),
            "--skip-memory",
            "--receipt",
            str(receipt_path),
            "--json",
        ]
    )
    assert code == 0
    written = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert written["authority"] == "none"
    assert written["schema"] == inst.RECEIPT_SCHEMA
    assert written["status"] == "written"


def test_real_configurator_installs_and_verifies_into_the_rendered_file(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from ops.memory.agent_assertion import build_agent_mcp_env
    from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion

    # The probe launches the installed launcher. A runner has no workstation
    # door and no ~/.cursor-governance, so the test supplies a cursor door and
    # lets the script bind the checkout that contains it.
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.delenv("L9_GOVERNANCE_DIR", raising=False)
    data = tmp_path / "data"
    state = tmp_path / "state"
    data.mkdir()
    state.mkdir()
    monkeypatch.setenv("L9_MEMORY_DATA_DIR", str(data))
    monkeypatch.setenv("L9_MEMORY_STATE_DIR", str(state))
    door = build_agent_mcp_env(
        agent_id="cursor",
        agents_door_secret="mcp-rebind-agents-door-secret",
        signing_key="mcp-rebind-cursor-signing-key",
        grants={
            "cursor": {
                "principal_id": "cursor",
                "roles": ["orchestrator"],
                "read_namespaces": ["mcp-install-proof"],
                "write_namespaces": ["mcp-install-proof"],
            }
        },
        identity_assertion=build_runtime_identity_assertion({"CURSOR_AGENT": "1"}),
    )
    for key, value in door.items():
        monkeypatch.setenv(key, value)
    master_path = tmp_path / "master.json"
    master_path.write_text(json.dumps(_master(Playwright={"command": "npx"})), encoding="utf-8")
    target = tmp_path / "mcp.json"
    receipt = inst.instantiate(path=target, master_path=master_path, verify=True)
    assert receipt["binding_status"] in {"exact", "development_checkout"}, receipt
    assert receipt["memory"]["status"] == "upstream_blocked", receipt["memory"]
    servers = json.loads(target.read_text(encoding="utf-8"))["mcpServers"]
    assert "l9-graphite-memory" not in servers
    assert servers["Playwright"] == {"command": "npx"}
    again = inst.instantiate(path=target, master_path=master_path, check=True, skip_memory=True)
    assert again["status"] == "unchanged"
    assert again["preserved_unmanaged"] == []
