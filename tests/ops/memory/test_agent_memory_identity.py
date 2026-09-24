"""Every agent memory names its author: the signed door at MCP spawn.

``ops/memory/run_memory_mcp.sh`` mints the ADR-0031 door from
L9_MEMORY_AGENT_AUTHORITY_JSON and refuses to start the server without one, so
the server never runs as the anonymous local-operator. Secrets here are random
and test-only; assertions look at variable presence, never values.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

from ops.memory import materialize_agent_authority as maa

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "ops" / "memory" / "run_memory_mcp.sh"
DOOR_VARS = (
    "L9_MEMORY_AGENTS_DOOR_SECRET",
    "L9_MEMORY_AGENT_ASSERTION",
    "L9_MEMORY_AGENT_SIGNING_KEYS_JSON",
    "L9_MEMORY_AGENT_GRANTS_JSON",
)


def _authority(*agents: str) -> dict:
    return {
        "agents_door_secret": secrets.token_hex(24),
        "agent_signing_keys": {
            a: secrets.token_hex(24) for a in agents or ("claude-code-desktop",)
        },
    }


def _private_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "authority"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    return directory


# --- materializer -------------------------------------------------------------


def test_scoping_refuses_the_human_door_peers_and_short_or_reused_keys() -> None:
    agent = "claude-code-desktop"
    good = _authority(agent)
    assert maa.scoped_tokens(good, agent) == good
    with pytest.raises(maa.AuthorityMaterializationError, match="human memory door"):
        maa.scoped_tokens({**good, "human_door_secret": "x" * 30}, agent)
    with pytest.raises(maa.AuthorityMaterializationError, match="no key beyond"):
        maa.scoped_tokens(
            {**good, "agent_signing_keys": {**good["agent_signing_keys"], "manus": "y" * 30}},
            agent,
        )
    with pytest.raises(maa.AuthorityMaterializationError, match="too short"):
        maa.scoped_tokens({**good, "agents_door_secret": "short"}, agent)
    door = good["agents_door_secret"]
    with pytest.raises(maa.AuthorityMaterializationError, match="reused"):
        maa.scoped_tokens({**good, "agent_signing_keys": {agent: door}}, agent)


def test_a_secret_carrying_another_identitys_key_is_refused() -> None:
    with pytest.raises(maa.AuthorityMaterializationError, match="no key beyond"):
        maa.scoped_tokens(
            _authority("claude-code-mobile", "claude-code-desktop"), "claude-code-mobile"
        )


def test_grants_come_from_the_registry_and_include_l9_ci_core(tmp_path: Path) -> None:
    directory = _private_dir(tmp_path)
    maa.materialize(ROOT, directory, _authority("claude-code-mobile"), "claude-code-mobile")
    for name in ("agent_tokens.local.json", "agent_grants.json"):
        assert stat.S_IMODE((directory / name).stat().st_mode) == 0o600
    grants = json.loads((directory / "agent_grants.json").read_text())["grants"][
        "claude-code-mobile"
    ]
    registry = yaml.safe_load((ROOT / "environment/agents/agent_registry.yaml").read_text())
    assigned = registry["agents"]["claude-code-mobile"]["assigned_groups"]
    assert "l9-ci-core" in assigned
    assert set(grants["write_namespaces"]) == set(assigned)


def test_a_non_private_directory_is_refused(tmp_path: Path) -> None:
    directory = tmp_path / "open"
    directory.mkdir()
    directory.chmod(0o755)
    with pytest.raises(maa.AuthorityMaterializationError, match="0700"):
        maa.materialize(ROOT, directory, _authority(), "claude-code-desktop")


def test_export_scopes_a_full_local_map_to_one_agent(tmp_path: Path) -> None:
    full = {
        "agents_door_secret": secrets.token_hex(24),
        "agent_signing_keys": {
            "claude-code-mobile": secrets.token_hex(24),
            "claude-code-desktop": secrets.token_hex(24),
            "manus": secrets.token_hex(24),
        },
        "human_door_secret": secrets.token_hex(24),
    }
    source = tmp_path / "agent_tokens.local.json"
    source.write_text(json.dumps(full))
    output = tmp_path / "claude-code-mobile-authority.json"
    maa.export_authority(source, ["claude-code-mobile"], output)
    exported = json.loads(output.read_text())
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert set(exported) == {"agents_door_secret", "agent_signing_keys"}
    assert set(exported["agent_signing_keys"]) == {"claude-code-mobile"}
    with pytest.raises(maa.AuthorityMaterializationError, match="no key beyond"):
        maa.export_authority(source, ["claude-code-mobile", "manus"], tmp_path / "bad.json")


# --- launcher -------------------------------------------------------------------


#: Surface markers are cleared so each test states its surface (hermetic on any runner).
SURFACE_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_", "CURSOR_AGENT")
MOBILE = {
    "CLAUDECODE": "1",
    "CLAUDE_CODE_REMOTE": "true",
    "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
}


def _launch(env_extra: dict[str, str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("L9_MEMORY_AGENT", "L9_MEMORY_ALLOW", "L9_MEMORY_SECRET"))
        and key not in ("L9_MEMORY_AGENTS_DOOR_SECRET", "L9_MEMORY_GRANTS_MAP")
        and not key.startswith(SURFACE_MARKERS)
    }
    env.update(
        HOME=str(tmp_path),  # no ~/.config/l9-memory maps
        TMPDIR=str(tmp_path),  # per-test: parallel launchers never share a temp dir
        L9_GOVERNANCE_DIR=str(ROOT),
        L9_MEMORY_AGENT_ID="claude-code",  # the projected family marker, refined by surface
        **env_extra,
    )
    probe = (
        "import os; print(os.environ['L9_MEMORY_AGENT_ID'], "
        f"' '.join(n for n in {DOOR_VARS!r} if os.environ.get(n)))"
    )
    return subprocess.run(
        ["bash", str(LAUNCHER), "-c", probe],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_without_a_door_the_server_refuses_to_start(tmp_path: Path) -> None:
    result = _launch(MOBILE, tmp_path)
    assert result.returncode == 1
    assert "refuse to launch: a memory must name the agent that wrote it" in result.stderr


def test_the_operator_opt_out_is_explicit_and_announced(tmp_path: Path) -> None:
    result = _launch({"L9_MEMORY_ALLOW_LOCAL_OPERATOR": "1", **MOBILE}, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "writes carry NO agent identity" in result.stderr


def test_the_hosted_secret_mints_the_mobile_door_at_spawn(tmp_path: Path) -> None:
    hosted = json.dumps(_authority("claude-code-mobile"))
    result = _launch({"L9_MEMORY_AGENT_AUTHORITY_JSON": hosted, **MOBILE}, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["claude-code-mobile", *DOOR_VARS]
    assert not list(tmp_path.glob("l9-memory-authority.*")), "the authority dir is removed"


def test_the_desktop_surface_gets_its_own_identity(tmp_path: Path) -> None:
    desktop = json.dumps(_authority("claude-code-desktop"))
    result = _launch({"L9_MEMORY_AGENT_AUTHORITY_JSON": desktop, "CLAUDECODE": "1"}, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[0] == "claude-code-desktop"


def test_cursor_is_its_own_identity_even_with_the_claude_marker(tmp_path: Path) -> None:
    cursor = json.dumps(_authority("cursor"))
    result = _launch({"L9_MEMORY_AGENT_AUTHORITY_JSON": cursor, "CURSOR_AGENT": "1"}, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[0] == "cursor"


def test_a_secret_for_another_surface_is_refused(tmp_path: Path) -> None:
    desktop_only = json.dumps(_authority("claude-code-desktop"))
    result = _launch({"L9_MEMORY_AGENT_AUTHORITY_JSON": desktop_only, **MOBILE}, tmp_path)
    assert result.returncode == 1
    assert "not a valid claude-code-mobile authority" in result.stderr


def test_new_identities_get_keys_without_replacing_existing_ones(tmp_path: Path) -> None:
    source = tmp_path / "agent_tokens.local.json"
    existing = secrets.token_hex(24)
    source.write_text(
        json.dumps(
            {
                "agents_door_secret": secrets.token_hex(24),
                "agent_signing_keys": {"cursor": existing},
            }
        )
    )
    added = maa.add_missing_keys(source, ["cursor", "claude-code-desktop", "claude-code-mobile"])
    keys = json.loads(source.read_text())["agent_signing_keys"]
    assert added == ["claude-code-desktop", "claude-code-mobile"]
    assert keys["cursor"] == existing
    assert stat.S_IMODE(source.stat().st_mode) == 0o600
    assert maa.add_missing_keys(source, ["claude-code-desktop"]) == []
