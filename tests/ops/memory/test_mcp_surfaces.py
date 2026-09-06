"""MCP surfaces for the memory control plane: Claude Code template + Claude Desktop render.

The memory package owns the shape of its MCP entry. Claude Code's project
scope can only carry a ``${VAR}`` interpreter, so the template *declares* that
shape and these tests hold it equal to the package. Claude Desktop cannot
expand variables at all, so a renderer derives its file from the master
inventory under Desktop's constraints and hands the memory entry to the
package's configurator.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "mcp.template.json"
MASTER = ROOT / "environment" / "mcp" / "master.mcp.json"
PROJECTION = ROOT / "ops" / "scripts" / "claude_projection.py"
RENDERER = (
    ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-desktop"
    / "render_claude_desktop_config.py"
)

MEMORY_ARGS = ["-m", "l9_graphite_memory.server", "--transport", "stdio"]


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


projection = _load("claude_projection_under_test", PROJECTION)
desktop = _load("render_claude_desktop_config", RENDERER)


# ---------------------------------------------------------------------------
# Claude Code: template declares the package's entry, gated on the interpreter
# ---------------------------------------------------------------------------


def test_template_memory_entry_matches_the_package_shape_and_is_secret_free() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    entry = template["mcpServers"]["l9-graphite-memory"]
    assert entry["type"] == "stdio"
    assert entry["command"] == "${L9_MEMORY_INTERPRETER}"
    assert entry["args"] == MEMORY_ARGS
    assert "L9_MEMORY_INTERPRETER" in entry["_requires_env"]
    for forbidden in ("env", "url", "headers"):
        assert forbidden not in entry


def test_memory_entry_renders_only_when_the_interpreter_is_bound() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    without = projection.render_mcp(template, None, environ={"GRAPHITI_MCP_URL": "x"})
    assert "l9-graphite-memory" not in without["mcpServers"]
    with_var = projection.render_mcp(
        template,
        None,
        environ={"GRAPHITI_MCP_URL": "x", "L9_MEMORY_INTERPRETER": "/venv/bin/python"},
    )
    rendered = with_var["mcpServers"]["l9-graphite-memory"]
    # Claude Code expands ${VAR} at load; the render keeps the reference, never a path.
    assert rendered["command"] == "${L9_MEMORY_INTERPRETER}"
    assert rendered["args"] == MEMORY_ARGS
    assert not any(key.startswith("_") for key in rendered)


def test_committed_projection_is_current_for_an_unbound_environment() -> None:
    """CI renders without L9_MEMORY_INTERPRETER, so the committed .mcp.json omits the entry."""

    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    committed = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    environ = {
        k: v
        for k, v in os.environ.items()
        if k not in {"L9_MEMORY_INTERPRETER", "CONTEXT7_API_KEY"}
    }
    environ.setdefault("GRAPHITI_MCP_URL", "https://example.invalid/mcp")
    rendered = projection.render_mcp(template, committed, environ=environ)
    assert rendered["mcpServers"] == committed["mcpServers"]


@pytest.mark.skipif(
    not os.environ.get("L9_MEMORY_DEV_CHECKOUT"),
    reason="L9_MEMORY_DEV_CHECKOUT unset: the package-shape proof needs the memory checkout",
)
def test_template_argv_equals_the_packages_managed_entry() -> None:
    interpreter = Path(os.environ["L9_MEMORY_DEV_CHECKOUT"]) / ".venv" / "bin" / "python"
    out = subprocess.run(
        [
            str(interpreter),
            "-c",
            "import json\n"
            "from l9_graphite_memory.client_config.cursor import managed_server_entry\n"
            "e = managed_server_entry('/x/python')\n"
            "print(json.dumps({'key': e.key, 'args': list(e.args)}))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    shape = json.loads(out.stdout)
    assert shape["key"] == "l9-graphite-memory"
    assert shape["args"] == MEMORY_ARGS


# ---------------------------------------------------------------------------
# Claude Desktop renderer
# ---------------------------------------------------------------------------


def _master(**servers: Any) -> dict[str, Any]:
    return {"mcpServers": servers}


def test_stdio_servers_copy_with_absolute_commands(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    config, skipped, preserved = desktop.render_config(
        _master(Playwright={"command": "npx", "args": ["@playwright/mcp@latest"]}), None, {}
    )
    assert config["mcpServers"]["Playwright"] == {
        "command": "/usr/local/bin/npx",
        "args": ["@playwright/mcp@latest"],
    }
    assert skipped == {} and preserved == []


def test_remote_servers_and_secret_env_are_skipped_by_name(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    master = _master(
        **{
            "graphiti-memory": {"url": "http://127.0.0.1:8100/mcp"},
            "firecrawl-mcp": {
                "command": "npx",
                "args": ["-y", "firecrawl-mcp"],
                "env": {"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"},
            },
        }
    )
    config, skipped, _ = desktop.render_config(master, None, {"FIRECRAWL_API_KEY": "live-value"})
    assert config["mcpServers"] == {}
    assert "Connectors" in skipped["graphiti-memory"]
    assert "secret-free" in skipped["firecrawl-mcp"]
    assert "live-value" not in json.dumps(config)


def test_non_secret_env_expands_and_unset_env_skips(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/opt/{name}")
    master = _master(
        docs={"command": "tool", "env": {"DOCS_ROOT": "${DOCS_ROOT}"}},
        other={"command": "tool", "env": {"OTHER_ROOT": "${OTHER_ROOT}"}},
    )
    config, skipped, _ = desktop.render_config(master, None, {"DOCS_ROOT": "/srv/docs"})
    assert config["mcpServers"]["docs"]["env"] == {"DOCS_ROOT": "/srv/docs"}
    assert "OTHER_ROOT" in skipped["other"]


def test_desktop_user_servers_and_the_memory_entry_are_preserved(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/opt/{name}")
    existing = {
        "globalShortcut": "Cmd+Space",
        "mcpServers": {
            "my-own": {"command": "/me/server"},
            "l9-graphite-memory": {"command": "/venv/bin/python", "args": MEMORY_ARGS},
            "Playwright": {"command": "/stale/npx", "args": []},
        },
    }
    config, skipped, preserved = desktop.render_config(
        _master(Playwright={"command": "npx", "args": ["@playwright/mcp@latest"]}), existing, {}
    )
    assert config["globalShortcut"] == "Cmd+Space"
    assert preserved == ["l9-graphite-memory", "my-own"]
    assert config["mcpServers"]["l9-graphite-memory"]["command"] == "/venv/bin/python"
    assert config["mcpServers"]["Playwright"]["command"] == "/opt/npx"  # managed entry refreshed
    assert skipped == {}


def test_memory_entry_is_delegated_to_the_package_configurator(tmp_path: Path) -> None:
    venv = tmp_path / "venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("", encoding="utf-8")
    (venv / "l9-memory").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"status": "complete"}), "")

    receipt = desktop._memory_entry(
        config_path=tmp_path / "claude_desktop_config.json",
        interpreter=str(venv / "python"),
        check=True,
        verify=False,
        runner=runner,
    )
    assert receipt["status"] == "installed"
    argv = calls[0]
    assert argv[0] == str(venv / "l9-memory")
    assert argv[1:4] == ["client", "cursor", "install"]
    assert "--dry-run" in argv and "--path" in argv and "--interpreter" in argv


def test_memory_entry_without_interpreter_is_skipped_not_invented(tmp_path: Path) -> None:
    receipt = desktop._memory_entry(
        config_path=tmp_path / "c.json", interpreter=None, check=False, verify=False
    )
    assert receipt["status"] == "skipped"


def test_cli_check_mode_reports_drift_without_writing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/opt/{name}")
    master = tmp_path / "master.json"
    master.write_text(
        json.dumps(_master(Playwright={"command": "npx", "args": []})), encoding="utf-8"
    )
    target = tmp_path / "claude_desktop_config.json"
    code = desktop.main(
        ["--master", str(master), "--path", str(target), "--check", "--skip-memory", "--json"]
    )
    assert code == 2 and not target.exists()
    code = desktop.main(["--master", str(master), "--path", str(target), "--skip-memory", "--json"])
    assert code == 0
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["mcpServers"]["Playwright"]["command"] == "/opt/npx"
    assert (
        desktop.main(["--master", str(master), "--path", str(target), "--check", "--skip-memory"])
        == 0
    )


def test_real_master_renders_without_secrets(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda name: f"/opt/{name}")
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    config, skipped, _ = desktop.render_config(master, None, {"FIRECRAWL_API_KEY": "must-not-leak"})
    text = json.dumps(config)
    assert "must-not-leak" not in text and "${" not in text
    assert "graphiti-memory" in skipped  # legacy url front door never reaches Desktop
