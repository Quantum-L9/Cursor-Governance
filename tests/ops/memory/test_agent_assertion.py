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
    ENV_IDENTITY_ASSERTION_HMAC,
    ENV_IDENTITY_ASSERTION_JSON,
    _fallback_mint_assertion,
    build_agent_mcp_env,
    env_from_local_secret_map,
    identity_assertion_hmac,
    local_assertion_digest,
    mint_assertion,
)
from ops.memory.agent_identity import (
    normalized_runtime_evidence,
    runtime_evidence_digest,
)


def _identity(agent_id: str) -> dict:
    actor = f"l9.actor-registry/global@1#{agent_id}"
    return {
        "schema": "l9.identity-assertion/v1",
        "subject_ref": actor,
        "product_ref": "l9-graphiti-memory:product/l9-graphite-memory",
        "resolved_dimensions": {
            "actor_identity": actor,
            "surface_identity": "unknown",
            "release_identity": "unknown",
            "runtime_identity": "unknown",
            "constellation_identity": "unknown",
        },
        "result": "resolved",
    }


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
        identity_assertion=_identity("cursor"),
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
            identity_assertion=_identity("human"),
        )


def test_refuses_a_principal_without_its_own_grant() -> None:
    with pytest.raises(KeyError, match="no grants for agent_id=claude-code"):
        build_agent_mcp_env(
            agent_id="claude-code",
            agents_door_secret=DOOR,
            signing_key=CLAUDE_KEY,
            grants={"cursor": GRANTS["cursor"]},
            identity_assertion=_identity("claude-code"),
        )


def test_env_from_local_secret_map(tmp_path: Path) -> None:
    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("cursor", sp, gp, _identity("cursor"))
    assert env[ENV_AGENTS_DOOR_SECRET] == DOOR
    assert ENV_HUMAN_DOOR_SECRET not in env
    assert HUMAN not in json.dumps(env)


def test_env_carries_only_the_launching_principals_material(tmp_path: Path) -> None:
    """P570-F1 closure, part 1: a peer's key and grants are not readable."""

    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("claude-code", sp, gp, _identity("claude-code"))

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
    env = env_from_local_secret_map("claude-code", sp, gp, _identity("claude-code"))
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

    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    # A cloud session's own marker must not leak into the desktop case under test.
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert helper.main(argv) == 0
    out = capsys.readouterr().out.strip()
    path = Path(out)
    assert path.is_file()
    assert DOOR not in out and CLAUDE_KEY not in out
    assert CURSOR_KEY not in out and HUMAN not in out
    env = json.loads(path.read_text(encoding="utf-8"))
    path.unlink()
    assert json.loads(env[ENV_AGENT_SIGNING_KEYS_JSON]) == {"claude-code": CLAUDE_KEY}

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert helper.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert DOOR not in captured.err and CLAUDE_KEY not in captured.err


def test_print_helper_skip_message_names_no_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    # A cloud session's own marker must not leak into the desktop case under test.
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
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


_PROJECTION_DIGEST = "sha256:9d7491d507b7204caeaa9892019ab39a5e459cf507c59fa192fa238e3a953c5c"
_AUTHORITY = "9b27869dd893fcd28f76f99c9184a90435542c76"
GOLDEN_KEY = "golden-identity-hmac-key"
GOLDEN_DIGEST = "sha256:cf7b14bef03986dbabbb926267a470b0ea14d24154ae99e1d95dc4242de21ab4"
GOLDEN_HMAC = "ae9a689df2cdd819fe8fa980b5474030e0d64ec333a31d2f641b7cb74f076108"


def _golden_body() -> dict:
    actor = "l9.actor-registry/global@1#claude-code"
    return {
        "schema": "l9.identity-assertion/v1",
        "subject_ref": actor,
        "product_ref": "l9-graphiti-memory:product/l9-graphite-memory",
        "resolved_dimensions": {
            "actor_identity": actor,
            "constellation_identity": "unknown",
            "release_identity": "unknown",
            "runtime_identity": "unknown",
            "surface_identity": "l9.surface-registry/global@1#claude-code-cli",
        },
        "bindings": [
            "l9.cursor-governance/identity-binding@1",
            "l9.cursor-governance/agent-bindings@2#claude-code",
        ],
        "evidence_refs": [
            "l9.projection/cursor-governance-identity@1",
            "l9.cursor-governance/identity-binding@1",
            "l9.cursor-governance/agent-bindings@2#claude-code",
        ],
        "resolver_ref": "l9.cursor-governance/resolver/runtime-agent-identity@1",
        "governing_coordinates": {
            "actor_registry_digest": (
                "sha256:34fbe4abc246e21c28401941025317be52c109c88335577616a2648cc93c6f6f"
            ),
            "agent_bindings_ref": "l9.cursor-governance/agent-bindings@2",
            "global_identity_authority_revision": _AUTHORITY,
            "identity_binding_ref": "l9.cursor-governance/identity-binding@1",
            "identity_projection_digest": _PROJECTION_DIGEST,
            "identity_projection_ref": "l9.projection/cursor-governance-identity@1",
            "surface_registry_digest": (
                "sha256:d7200409ff02141a274ff8c9221d31429f6a6fae27539e6d9c8d20f1a6eba988"
            ),
        },
        "result": "resolved",
        "provenance": {
            "runtime_evidence_digest": (
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
        },
    }


def _resolved(env: dict[str, str]) -> dict:
    return helper.build_runtime_identity_assertion(env)


def test_cursor_resolves_actor_and_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    assertion = _resolved({"CURSOR_AGENT": "1"})
    dims = assertion["resolved_dimensions"]
    assert dims["actor_identity"] == "l9.actor-registry/global@1#cursor"
    assert dims["surface_identity"] == "l9.surface-registry/global@1#cursor-ide"
    assert assertion["result"] == "resolved"


def test_claude_cli_resolves_actor_and_surface() -> None:
    assertion = _resolved({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"})
    dims = assertion["resolved_dimensions"]
    assert dims["actor_identity"] == "l9.actor-registry/global@1#claude-code"
    assert dims["surface_identity"] == "l9.surface-registry/global@1#claude-code-cli"


def test_claude_remote_mobile_resolves_mobile_surface() -> None:
    assertion = _resolved(
        {
            "CLAUDE_CODE_REMOTE": "true",
            "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
            "CLAUDE_CODE_SESSION_ID": "session-secret-must-not-leak",
        }
    )
    dims = assertion["resolved_dimensions"]
    assert dims["actor_identity"] == "l9.actor-registry/global@1#claude-code"
    assert dims["surface_identity"] == "l9.surface-registry/global@1#claude-code-mobile"
    encoded = json.dumps(assertion)
    assert "session-secret-must-not-leak" not in encoded
    evidence = normalized_runtime_evidence(
        {
            "CLAUDE_CODE_REMOTE": "true",
            "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
            "CLAUDE_CODE_SESSION_ID": "session-secret-must-not-leak",
        }
    )
    assert evidence["CLAUDE_CODE_SESSION_ID_present"] is True
    assert "session-secret-must-not-leak" not in json.dumps(evidence)


def test_unknown_claude_remote_entrypoint_refuses_identity() -> None:
    with pytest.raises(Exception, match="no memory identity|no registered|ENTRYPOINT"):
        _resolved({"CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_unknown"})


def _full_principal(agent_id: str) -> dict[str, object]:
    """A workstation principal: door claims plus the four fields the door rejects."""
    return {
        "principal_id": agent_id,
        "user_id": "operator",
        "roles": ["orchestrator"],
        "read_namespaces": ["*"],
        "write_namespaces": ["stale-namespace-not-from-registry"],
        "promote_namespaces": [],
        "is_admin": False,
        "tenant_id": "l9",
        "organization_id": "quantum-l9",
        "workspace_id": "igor-workspace",
        "agent_id": agent_id,
    }


def _export_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    agent_id: str,
) -> dict[str, str]:
    secrets = {
        "agents_door_secret": DOOR,
        "human_door_secret": HUMAN,
        "agent_signing_keys": {"cursor": CURSOR_KEY, "claude-code": CLAUDE_KEY},
    }
    grants = {
        "schema_version": 1,
        "grants": {agent_id: _full_principal(agent_id)},
    }
    secret_path = tmp_path / "tokens.json"
    grants_path = tmp_path / "grants.json"
    secret_path.write_text(json.dumps(secrets), encoding="utf-8")
    grants_path.write_text(json.dumps(grants), encoding="utf-8")
    before = grants_path.read_bytes()
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert (
        helper.main(
            [
                "--secret-map",
                str(secret_path),
                "--grants-map",
                str(grants_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert grants_path.read_bytes() == before
    out = capsys.readouterr().out.strip()
    assert DOOR not in out and CURSOR_KEY not in out and CLAUDE_KEY not in out
    path = Path(out)
    env = json.loads(path.read_text(encoding="utf-8"))
    path.unlink()
    return env


def test_stale_cursor_principal_exports_a_legal_door_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from l9_graphite_memory.authz.signed_assertion import AgentDoorGrant

    from ops.memory.materialize_agent_authority import agent_grants

    monkeypatch.setenv("CURSOR_AGENT", "1")
    for name in (
        "CLAUDECODE",
        "CLAUDE_CODE_REMOTE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION_ID",
        "L9_MEMORY_AGENT_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    env = _export_env(tmp_path, monkeypatch, capsys, "cursor")
    grant = json.loads(env[ENV_AGENT_GRANTS_JSON])["cursor"]
    AgentDoorGrant.model_validate(grant)
    for forbidden in ("tenant_id", "organization_id", "workspace_id", "agent_id"):
        assert forbidden not in grant
    assert grant == agent_grants(helper._ROOT, "cursor")["grants"]["cursor"]
    assertion = json.loads(env[ENV_IDENTITY_ASSERTION_JSON])
    assert assertion["resolved_dimensions"]["actor_identity"] == "l9.actor-registry/global@1#cursor"


def test_remote_mobile_exports_claude_actor_and_a_legal_door_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from l9_graphite_memory.authz.signed_assertion import AgentDoorGrant

    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "remote_mobile")
    monkeypatch.setenv("CLAUDECODE", "1")
    env = _export_env(tmp_path, monkeypatch, capsys, "claude-code")
    grant = json.loads(env[ENV_AGENT_GRANTS_JSON])["claude-code"]
    AgentDoorGrant.model_validate(grant)
    for forbidden in ("tenant_id", "organization_id", "workspace_id", "agent_id"):
        assert forbidden not in grant
    assertion = json.loads(env[ENV_IDENTITY_ASSERTION_JSON])
    dims = assertion["resolved_dimensions"]
    assert dims["actor_identity"] == "l9.actor-registry/global@1#claude-code"
    assert dims["surface_identity"] == "l9.surface-registry/global@1#claude-code-mobile"


def test_unknown_remote_entrypoint_refuses_export(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "remote_unknown")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert helper.main(["--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "remote_unknown" in captured.err


def test_adapter_without_surface_evidence_is_unknown() -> None:
    assertion = _resolved({"L9_MEMORY_AGENT_ID": "codex"})
    dims = assertion["resolved_dimensions"]
    assert dims["actor_identity"] == "l9.actor-registry/global@1#codex"
    assert dims["surface_identity"] == "unknown"
    assert assertion["result"] == "resolved"
    assert "codex-cli" not in dims["surface_identity"]


def test_actor_ref_comes_from_the_binding_not_a_guess() -> None:
    import yaml

    registry = yaml.safe_load(
        (helper._ROOT / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
    )
    assertion = _resolved({"CURSOR_AGENT": "1"})
    assert assertion["subject_ref"] == registry["agents"]["cursor"]["actor_ref"]
    assert assertion["subject_ref"] == assertion["resolved_dimensions"]["actor_identity"]


def test_resolved_surface_must_be_in_the_binding() -> None:
    import yaml

    from ops.memory.agent_identity import surface_ref_from_binding

    registry = yaml.safe_load(
        (helper._ROOT / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
    )
    binding = registry["agents"]["claude-code"]
    cli = surface_ref_from_binding("claude-code-cli", binding)
    assert cli == "l9.surface-registry/global@1#claude-code-cli"
    assert cli in binding["surface_refs"]
    assert surface_ref_from_binding("claude-code-desktop", binding) == "unknown"
    desktop = _resolved({"CLAUDECODE": "1"})
    assert desktop["resolved_dimensions"]["actor_identity"].endswith("#claude-code")
    assert desktop["resolved_dimensions"]["surface_identity"] == "unknown"


def test_assertion_carries_authority_revision_and_projection_digest() -> None:
    assertion = _resolved({"CURSOR_AGENT": "1"})
    coords = assertion["governing_coordinates"]
    assert coords["global_identity_authority_revision"] == _AUTHORITY
    assert coords["identity_projection_digest"] == _PROJECTION_DIGEST


def test_assertion_digest_is_deterministic() -> None:
    first = _resolved({"CURSOR_AGENT": "1"})
    second = _resolved({"CURSOR_AGENT": "1"})
    assert first["assertion_digest"] == second["assertion_digest"]
    assert first["assertion_digest"] == local_assertion_digest(first)


def test_golden_identity_hmac_vector() -> None:
    body = _golden_body()
    assert local_assertion_digest(body) == GOLDEN_DIGEST
    assert identity_assertion_hmac(GOLDEN_DIGEST, GOLDEN_KEY) == GOLDEN_HMAC


def test_authentication_token_wire_format_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    import secrets
    import time

    monkeypatch.setattr(time, "time", lambda: 1_700_000_000)
    monkeypatch.setattr(secrets, "token_hex", lambda n: "ab" * n)
    token = _fallback_mint_assertion("claude-code", GOLDEN_KEY, ttl_seconds=3600)
    assert token == (
        "claude-code.1700003600.abababababababababababababababab."
        "16b37add9b79e72250b4560ea23571d3340a9959208e4e13598c898014f663c4"
    )
    assert verify_assertion(token, {"claude-code": GOLDEN_KEY}) == "claude-code"


def test_launch_env_omits_human_secret_and_peer_material(tmp_path: Path) -> None:
    sp, gp = _two_principal_store(tmp_path)
    env = env_from_local_secret_map("claude-code", sp, gp, _identity("claude-code"))
    assert ENV_IDENTITY_ASSERTION_JSON in env
    assert ENV_IDENTITY_ASSERTION_HMAC in env
    assert ENV_HUMAN_DOOR_SECRET not in env
    everything = "\n".join(env.values())
    assert HUMAN not in everything
    assert CURSOR_KEY not in everything
    identity = json.loads(env[ENV_IDENTITY_ASSERTION_JSON])
    assert identity["assertion_digest"].startswith("sha256:")
    assert env[ENV_IDENTITY_ASSERTION_HMAC] == identity_assertion_hmac(
        identity["assertion_digest"], CLAUDE_KEY
    )


def test_session_start_env_contains_identity_assertion() -> None:
    bootstrap = helper._ROOT / "ops/hooks/session_start_bootstrap.sh"
    text = bootstrap.read_text(encoding="utf-8")
    start = text.index("ADR-0031: mint signed agent assertion")
    block = text[start : text.index('COMBINED="$COMBINED"', start)]
    assert "L9_MEMORY_IDENTITY_ASSERTION_JSON" in block
    assert "L9_MEMORY_IDENTITY_ASSERTION_HMAC" in block
    assert "L9_MEMORY_HUMAN_DOOR_SECRET" in text
    assert text.count('assertion_env.pop("L9_MEMORY_HUMAN_DOOR_SECRET"') == 1
    evidence = normalized_runtime_evidence({"CURSOR_AGENT": "1"})
    again = normalized_runtime_evidence({"CURSOR_AGENT": "1"})
    assert runtime_evidence_digest(evidence) == runtime_evidence_digest(again)
