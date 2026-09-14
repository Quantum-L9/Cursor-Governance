"""ADR-0031 assertion mint helpers (ops/memory/agent_assertion.py).

The security property under test (audit P570-F1): an agent launch context can
obtain ONLY its own principal's authority material. A peer's signing key can be
neither read, replaced, nor used from the environment this module builds, and
the verifier the package server runs rejects a forged peer assertion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from l9_graphite_memory.authz.signed_assertion import verify_assertion
from l9_graphite_memory.errors import AuthenticationError

from ops.memory import print_agent_assertion_env as helper
from ops.memory.agent_assertion import (
    ENV_AGENT_ASSERTION,
    ENV_AGENT_GRANTS_JSON,
    ENV_AGENT_ID,
    ENV_AGENT_SIGNING_KEYS_JSON,
    ENV_AGENTS_DOOR_SECRET,
    ENV_HUMAN_DOOR_SECRET,
    _fallback_mint_assertion,
    build_agent_mcp_env,
    env_from_local_secret_map,
    mint_assertion,
)

DOOR = "door-secret-at-least-24-chars!!"
HUMAN = "human-secret-at-least-24-chars!"
CURSOR_KEY = "cursor-signing-key-24chars!"
CLAUDE_KEY = "claude-code-signing-key-24chars!"
GRANTS = {
    "cursor": {"principal_id": "cursor", "roles": ["orchestrator"], "write_namespaces": ["*"]},
    "claude-code": {"principal_id": "claude-code", "roles": ["executor"], "write_namespaces": []},
}


def _two_principal_store(tmp_path: Path) -> tuple[Path, Path]:
    secrets = {
        "agents_door_secret": DOOR,
        "human_door_secret": HUMAN,
        "agent_signing_keys": {"cursor": CURSOR_KEY, "claude-code": CLAUDE_KEY},
    }
    sp = tmp_path / "tokens.json"
    gp = tmp_path / "grants.json"
    sp.write_text(json.dumps(secrets))
    gp.write_text(json.dumps({"schema_version": 1, "grants": GRANTS}))
    return sp, gp


def test_build_agent_mcp_env_omits_human_secret() -> None:
    env = build_agent_mcp_env(
        agent_id="cursor",
        agents_door_secret=DOOR,
        signing_key=CURSOR_KEY,
        grants={"cursor": {"role": "orchestrator"}},
    )
    assert env[ENV_AGENT_ID] == "cursor"
    assert ENV_AGENT_ASSERTION in env
    assert ENV_HUMAN_DOOR_SECRET not in env


def test_refuses_human_agent_id() -> None:
    with pytest.raises(ValueError, match="human"):
        build_agent_mcp_env(
            agent_id="human",
            agents_door_secret=DOOR,
            signing_key="human-signing-key-24chars!!",
            grants={},
        )


def test_refuses_a_principal_without_its_own_grant() -> None:
    with pytest.raises(KeyError, match="no grants for agent_id=claude-code"):
        build_agent_mcp_env(
            agent_id="claude-code",
            agents_door_secret=DOOR,
            signing_key=CLAUDE_KEY,
            grants={"cursor": GRANTS["cursor"]},
        )


def test_env_from_local_secret_map(tmp_path: Path) -> None:
    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("cursor", sp, gp)
    assert env[ENV_AGENTS_DOOR_SECRET] == DOOR
    assert ENV_HUMAN_DOOR_SECRET not in env
    assert HUMAN not in json.dumps(env)


def test_env_carries_only_the_launching_principals_material(tmp_path: Path) -> None:
    """P570-F1 closure, part 1: a peer's key and grants are not readable."""

    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("claude-code", sp, gp)

    assert json.loads(env[ENV_AGENT_SIGNING_KEYS_JSON]) == {"claude-code": CLAUDE_KEY}
    assert json.loads(env[ENV_AGENT_GRANTS_JSON]) == {"claude-code": GRANTS["claude-code"]}
    everything = "\n".join(env.values())
    assert CURSOR_KEY not in everything
    assert "orchestrator" not in everything
    assert HUMAN not in everything


def test_a_peer_assertion_cannot_be_used_from_a_launch_context(tmp_path: Path) -> None:
    """P570-F1 closure, part 2: a forged peer assertion is refused by the verifier.

    The package server verifies ``L9_MEMORY_AGENT_ASSERTION`` against the key
    map in ``L9_MEMORY_AGENT_SIGNING_KEYS_JSON`` selected by the claimed
    ``agent_id``. From claude-code's environment the only key present is
    claude-code's, so a token that claims ``cursor`` names an unknown agent —
    and even against the operator's full map it carries the wrong signature,
    because cursor's key was never available to mint with.
    """

    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("claude-code", sp, gp)
    exported_keys = json.loads(env[ENV_AGENT_SIGNING_KEYS_JSON])
    full_map = {"cursor": CURSOR_KEY, "claude-code": CLAUDE_KEY}

    # The genuine assertion verifies, and only as claude-code.
    assert verify_assertion(env[ENV_AGENT_ASSERTION], exported_keys) == "claude-code"
    assert verify_assertion(env[ENV_AGENT_ASSERTION], full_map) == "claude-code"

    # Forge: claim cursor, sign with the only key this context holds.
    forged = mint_assertion("cursor", CLAUDE_KEY)
    with pytest.raises(AuthenticationError, match="unknown agent_id"):
        verify_assertion(forged, exported_keys)
    with pytest.raises(AuthenticationError, match="invalid assertion signature"):
        verify_assertion(forged, full_map)

    # Replace: a launch context cannot make cursor's key appear by editing the
    # exported map, because it never had cursor's key to put there.
    tampered = dict(exported_keys, cursor=CLAUDE_KEY)
    with pytest.raises(AuthenticationError, match="invalid assertion signature"):
        verify_assertion(mint_assertion("cursor", tampered["cursor"]), full_map)


def test_fallback_mint_uses_the_package_wire_format() -> None:
    """A fallback-minted token must verify at the package server, not only locally."""

    token = _fallback_mint_assertion("claude-code", CLAUDE_KEY, ttl_seconds=60)
    assert verify_assertion(token, {"claude-code": CLAUDE_KEY}) == "claude-code"
    with pytest.raises(AuthenticationError):
        verify_assertion(token, {"claude-code": CURSOR_KEY})


def test_print_helper_emits_per_principal_env_only_to_a_pipe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    sp, gp = _two_principal_store(tmp_path)
    argv = [
        "--agent-id",
        "claude-code",
        "--secret-map",
        str(sp),
        "--grants-map",
        str(gp),
        "--format",
        "json",
    ]

    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert helper.main(argv) == 0
    out = capsys.readouterr().out
    env = json.loads(out)
    assert json.loads(env[ENV_AGENT_SIGNING_KEYS_JSON]) == {"claude-code": CLAUDE_KEY}
    assert CURSOR_KEY not in out and HUMAN not in out

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert helper.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert DOOR not in captured.err and CLAUDE_KEY not in captured.err


def test_print_helper_skip_message_names_no_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "absent.json"
    assert (
        helper.main(
            ["--secret-map", str(missing), "--grants-map", str(missing), "--format", "shell"]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(tmp_path) not in captured.err
