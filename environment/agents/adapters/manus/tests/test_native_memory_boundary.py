"""Offline Manus native boundary: no credential/transport invention or false ready."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
for root in (REPOSITORY, ADAPTER):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

validator = importlib.import_module("validate_manus_adapter")
authority = importlib.import_module("materialize_memory_authority")
renderer = importlib.import_module("render_memory_mcp_connector")

IDENTITY_PATHS = (
    "environment/agents/agent_registry.yaml",
    "governance/authority-bindings/canonical-agent-identity.yaml",
    "generated/governance/canonical_identity.yaml",
    "generated/governance/canonical_identity.receipt.yaml",
)


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    for relative in IDENTITY_PATHS:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / relative, destination)
    target = tmp_path / "environment/agents/adapters/manus"
    target.mkdir(parents=True)
    for path in ADAPTER.iterdir():
        if path.is_file():
            shutil.copyfile(path, target / path.name)
    return tmp_path


def _load(root: Path, relative: str):
    return yaml.safe_load((root / relative).read_text(encoding="utf-8"))


def _save(root: Path, relative: str, data) -> None:
    (root / relative).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _mutate_binding(root: Path, updates: dict) -> None:
    registry = _load(root, IDENTITY_PATHS[0])
    registry["agents"]["manus"].update(updates)
    _save(root, IDENTITY_PATHS[0], registry)


def _refresh_fixture_digest(root: Path) -> None:
    # Only fixture receipts are updated, through the existing digest owner.
    from ops.memory.identity_projection import projection_output_digest

    receipt = _load(root, IDENTITY_PATHS[3])
    receipt["output"]["digest"] = projection_output_digest((root / IDENTITY_PATHS[2]).read_bytes())
    _save(root, IDENTITY_PATHS[3], receipt)


def test_layered_validation_pass_is_not_native_or_live_readiness(fixture_root: Path) -> None:
    report = validator.validation_report(fixture_root)
    assert report["errors"] == []
    assert report["structural"]["status"] == "PASS"
    assert report["canonical_identity"]["status"] == "PASS"
    assert report["native_binding"]["status"] == "UPSTREAM_BLOCKED"
    assert report["native_binding"]["native_client"] == "UNBOUND"
    assert report["live"]["status"] == "UNKNOWN"
    assert report["live"]["authentication"] == "unverified"
    assert report["memory_ready"] is False
    assert validator.validate(fixture_root) == []


@pytest.mark.parametrize("tamper", [None, "projection_bytes", "receipt_revision"])
def test_fresh_process_never_imports_caller_root_code(
    fixture_root: Path, tamper: str | None
) -> None:
    marker = fixture_root / "caller-code-executed"
    hostile = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "raise RuntimeError('caller data root must never supply executable code')\n"
    )
    for relative in (
        "ops/__init__.py",
        "ops/memory/__init__.py",
        "ops/memory/identity_projection.py",
        "ops/memory/agent_identity.py",
    ):
        path = fixture_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(hostile, encoding="utf-8")
    if tamper == "projection_bytes":
        path = fixture_root / IDENTITY_PATHS[2]
        path.write_bytes(path.read_bytes() + b"\n# caller artifact tamper\n")
    elif tamper == "receipt_revision":
        receipt = _load(fixture_root, IDENTITY_PATHS[3])
        receipt["projection"]["source_revision"] = "0" * 40
        _save(fixture_root, IDENTITY_PATHS[3], receipt)

    # Isolated startup, with a hostile cwd, proves safety without cached ops modules.
    code = (
        "import json, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(ADAPTER)!r})\n"
        "import validate_manus_adapter as validator\n"
        "assert not any(n == 'ops' or n.startswith('ops.') for n in sys.modules)\n"
        "saved = list(sys.path)\n"
        f"errors = validator.canonical_identity_errors(Path({str(fixture_root)!r}))\n"
        "assert sys.path == saved\n"
        "from ops.memory import agent_identity, identity_projection\n"
        f"source = Path({str(REPOSITORY)!r})\n"
        "assert Path(agent_identity.__file__).is_relative_to(source)\n"
        "assert Path(identity_projection.__file__).is_relative_to(source)\n"
        "print(json.dumps(errors))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code],
        cwd=fixture_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert not marker.exists(), result.stderr
    assert result.returncode == 0, result.stderr
    errors = json.loads(result.stdout)
    if tamper is None:
        assert errors == []
    else:
        expected = "digest" if tamper == "projection_bytes" else "source_revision"
        assert any(expected in error for error in errors)


@pytest.mark.parametrize("relative", IDENTITY_PATHS)
def test_missing_identity_owner_artifact_fails_canonical(fixture_root: Path, relative: str) -> None:
    (fixture_root / relative).unlink()
    report = validator.validation_report(fixture_root)
    assert report["canonical_identity"]["status"] == "FAIL"
    assert report["errors"]
    assert report["memory_ready"] is False
    with pytest.raises(authority.AuthorityMaterializationError):
        authority._manus_grants(fixture_root)


def test_projection_byte_tamper_refuses_before_grant_derivation(fixture_root: Path) -> None:
    path = fixture_root / IDENTITY_PATHS[2]
    path.write_bytes(path.read_bytes() + b"\n# tampered fixture\n")
    assert any("digest" in error for error in validator.validate(fixture_root))
    with pytest.raises(authority.AuthorityMaterializationError, match="digest"):
        authority._manus_grants(fixture_root)


@pytest.mark.parametrize("kind,identity", [("actors", "manus"), ("surfaces", "manus-cloud")])
def test_valid_digest_does_not_admit_noncurrent_subject(
    fixture_root: Path, kind: str, identity: str
) -> None:
    projection = _load(fixture_root, IDENTITY_PATHS[2])
    next(item for item in projection[kind] if item["id"] == identity)["status"] = "retired"
    _save(fixture_root, IDENTITY_PATHS[2], projection)
    _refresh_fixture_digest(fixture_root)
    assert any("current" in error for error in validator.canonical_identity_errors(fixture_root))
    with pytest.raises(authority.AuthorityMaterializationError, match="current"):
        authority._manus_grants(fixture_root)


@pytest.mark.parametrize(
    "updates",
    [
        {"actor_ref": "l9.actor-registry/global@1#cursor"},
        {"actor_ref": "l9.actor-registry/global@1#unknown"},
        {"actor_ref": "anything#manus"},
        {"actor_ref": None},
        {"binding_status": "retired"},
        {"binding_status": "ACTIVE"},
        {"agent_id": "cursor"},
        {"agent_id": "manus"},
        {"source": "manus"},
        {"status": "active"},
        {"binding_status": "retired", "status": "active", "agent_id": "cursor"},
        {"surface_refs": []},
        {"surface_refs": ["l9.surface-registry/global@1#unknown"]},
        {"surface_refs": ["l9.surface-registry/global@1#cursor"]},
    ],
)
def test_v2_identity_status_and_surface_bypasses_refuse(fixture_root: Path, updates: dict) -> None:
    _mutate_binding(fixture_root, updates)
    assert validator.canonical_identity_errors(fixture_root)
    with pytest.raises(authority.AuthorityMaterializationError):
        authority._manus_grants(fixture_root)


@pytest.mark.parametrize("schema", [None, "l9.cursor-governance.agent-bindings/v1", "v2"])
def test_exact_v2_schema_required(fixture_root: Path, schema) -> None:
    registry = _load(fixture_root, IDENTITY_PATHS[0])
    registry["schema"] = schema
    _save(fixture_root, IDENTITY_PATHS[0], registry)
    assert validator.canonical_identity_errors(fixture_root)
    with pytest.raises(authority.AuthorityMaterializationError, match="v2"):
        authority._manus_grants(fixture_root)


def test_complete_canonical_owner_checks_peer_bindings_too(fixture_root: Path) -> None:
    registry = _load(fixture_root, IDENTITY_PATHS[0])
    peer = next(key for key in registry["agents"] if key != "manus")
    registry["agents"][peer]["principal_id"] = registry["agents"]["manus"]["principal_id"]
    _save(fixture_root, IDENTITY_PATHS[0], registry)
    assert any(
        "duplicate principal" in error
        for error in validator.canonical_identity_errors(fixture_root)
    )


@pytest.mark.parametrize(
    "artifact,field,value",
    [
        (1, "canonical", False),
        (2, "canonical", True),
        (3, "schema", "invalid"),
    ],
)
def test_complete_canonical_owner_schema_authority_checks(
    fixture_root: Path, artifact: int, field: str, value
) -> None:
    data = _load(fixture_root, IDENTITY_PATHS[artifact])
    data[field] = value
    _save(fixture_root, IDENTITY_PATHS[artifact], data)
    if artifact == 2:
        _refresh_fixture_digest(fixture_root)
    assert validator.canonical_identity_errors(fixture_root)


def test_receipt_coordinates_must_match_projection(fixture_root: Path) -> None:
    receipt = _load(fixture_root, IDENTITY_PATHS[3])
    receipt["projection"]["source_revision"] = "0" * 40
    _save(fixture_root, IDENTITY_PATHS[3], receipt)
    assert any(
        "source_revision" in error for error in validator.canonical_identity_errors(fixture_root)
    )


def test_pure_grants_require_nonempty_namespace_scope(fixture_root: Path) -> None:
    _mutate_binding(fixture_root, {"assigned_groups": []})
    with pytest.raises(authority.AuthorityMaterializationError, match="namespace scope"):
        authority._manus_grants(fixture_root)


@pytest.mark.parametrize("authority_file", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_renderer_cli_never_creates_or_overwrites_output(
    tmp_path: Path, authority_file: bool, existing: bool
) -> None:
    output = tmp_path / "nested" / "draft.json"
    if existing:
        output.parent.mkdir()
        output.write_bytes(b"unchanged fixture bytes\n")
        output.chmod(0o644)
    command = [
        str(REPOSITORY / ".venv/bin/python"),
        "-B",
        str(ADAPTER / "render_memory_mcp_connector.py"),
        "--governance",
        "/missing",
        "--output",
        str(output),
    ]
    if authority_file:
        unread = tmp_path / "unread-authority-fifo"
        os.mkfifo(unread)
        command.extend(["--authority-file", str(unread)])
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    assert result.returncode == 2
    assert "UPSTREAM_BLOCKED" in result.stderr
    assert result.stdout == ""
    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before
    if existing:
        assert output.read_bytes() == b"unchanged fixture bytes\n"
        assert output.stat().st_mode & 0o777 == 0o644
    else:
        assert not output.parent.exists()


@pytest.mark.parametrize("governance", ["/missing", "fixture"])
def test_retired_launcher_never_calls_fake_mint_server_python_or_mktemp(
    tmp_path: Path, governance: str
) -> None:
    fake_root = tmp_path / "fixture"
    binaries = fake_root / ".venv/bin"
    helpers = fake_root / "ops/memory"
    binaries.mkdir(parents=True)
    helpers.mkdir(parents=True)
    marker = tmp_path / "must-not-exist"
    for path in (
        binaries / "python",
        binaries / "l9-memory-server",
        binaries / "mktemp",
        helpers / "export_agent_assertion_env.sh",
    ):
        path.write_text(f"#!/bin/bash\nprintf called > '{marker}'\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    (fake_root / "CANONICAL_LAW.md").write_text("fixture", encoding="utf-8")
    selected = str(fake_root) if governance == "fixture" else governance
    env = {
        "HOME": str(tmp_path),
        "PATH": str(binaries) + ":/usr/bin:/bin",
        "XDG_RUNTIME_DIR": str(tmp_path),
    }
    env.update(
        {
            name: "synthetic-stale-secret"
            for name in (
                "L9_MEMORY_AGENTS_DOOR_SECRET",
                "L9_MEMORY_AGENT_ASSERTION",
                "L9_MEMORY_AGENT_SIGNING_KEYS_JSON",
                "L9_MEMORY_AGENT_GRANTS_JSON",
                "L9_MEMORY_IDENTITY_ASSERTION_JSON",
                "L9_MEMORY_IDENTITY_ASSERTION_HMAC",
                "L9_MANUS_MEMORY_AUTHORITY_JSON",
            )
        }
    )
    env["L9_ASSERTION_EXPORT_STATUS"] = "failed"
    result = subprocess.run(
        ["bash", str(ADAPTER / "serve_memory_mcp.sh"), "--governance", selected],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "UPSTREAM_BLOCKED" in result.stderr
    assert "synthetic-stale-secret" not in result.stderr
    assert not marker.exists()
    assert not list(tmp_path.glob("l9-manus-memory.*"))


@pytest.mark.parametrize("lifecycle_enabled", [False, True])
def test_governance_launcher_strips_inherited_memory_but_preserves_other_config(
    tmp_path: Path, lifecycle_enabled: bool
) -> None:
    fake_root = tmp_path / "governance"
    binaries = fake_root / ".venv/bin"
    binaries.mkdir(parents=True)
    (fake_root / "CANONICAL_LAW.md").write_text("fixture", encoding="utf-8")
    # The fake locked interpreter reports names only; it never starts a service.
    python = binaries / "python"
    python.write_text(
        "#!/bin/bash\n"
        "for name in ${!L9_MEMORY_@}; do printf 'unexpected:%s\\n' \"$name\"; done\n"
        '[ -z "${L9_MANUS_MEMORY_AUTHORITY_JSON+x}" ] || echo unexpected:authority\n'
        '[ -z "${L9_ASSERTION_EXPORT_STATUS+x}" ] || echo unexpected:export_status\n'
        "printf 'governance:%s\\n' \"${L9_GOVERNANCE_SURFACE:-}\"\n"
        "printf 'argv:%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/bin",
        "L9_GOVERNANCE_SURFACE": "manus",
        "L9_MEMORY_AGENT_ASSERTION": "stale",
        "L9_MEMORY_AGENT_SIGNING_KEYS_JSON": "stale",
        "L9_MEMORY_AGENT_GRANTS_JSON": "stale",
        "L9_MEMORY_IDENTITY_ASSERTION_JSON": "stale",
        "L9_MEMORY_IDENTITY_ASSERTION_HMAC": "stale",
        "L9_MEMORY_AGENTS_DOOR_SECRET": "stale",
        "L9_MEMORY_SECRET_MAP": "/unread",
        "L9_MEMORY_GRANTS_MAP": "/unread",
        "L9_MEMORY_FUTURE_SECRET": "stale",
        "L9_MEMORY_HUMAN_DOOR_SECRET": "stale",
        "L9_MANUS_MEMORY_AUTHORITY_JSON": "stale",
        "L9_ASSERTION_EXPORT_STATUS": "failed",
    }
    command = ["bash", str(ADAPTER / "serve_mcp.sh"), "--governance", str(fake_root)]
    if lifecycle_enabled:
        command += ["--enable-memory-lifecycle", "--auth-token-file", "/unread-governance-token"]
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "unexpected:" not in result.stdout
    assert "governance:manus" in result.stdout
    assert "stale" not in result.stdout + result.stderr
    if lifecycle_enabled:
        assert "argv:--auth-token-file" in result.stdout


def test_governance_launcher_keeps_lifecycle_bearer_guard(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(ADAPTER / "serve_mcp.sh"),
            "--governance",
            str(REPOSITORY),
            "--enable-memory-lifecycle",
        ],
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "requires --auth-token-file" in result.stderr


def test_mcp_stubs_refuse_before_workspace_resolution_or_subprocess() -> None:
    import mcp_server

    service = mcp_server.GovernanceMcpService(REPOSITORY, memory_lifecycle_enabled=True)
    with (
        mock.patch.object(
            service, "_resolve_workspace", side_effect=AssertionError("no fs resolution")
        ),
        mock.patch.object(mcp_server, "_run", side_effect=AssertionError("no subprocess")),
    ):
        for tool in ("memory_lifecycle_start", "memory_lifecycle_close"):
            result = service.call_tool(
                tool,
                {
                    "workspace": "/missing",
                    "summary": "private task content",
                    "task": "private task content",
                },
            )
            assert not result.get("isError")
            assert result["structuredContent"]["status"] == "UPSTREAM_BLOCKED"
            assert "private task content" not in json.dumps(result)


@pytest.mark.parametrize("flag", ["--enable-memory-lifecycle", "--allow-bootstrap-apply"])
def test_server_cli_requires_auth_for_enabled_guards(flag: str) -> None:
    import mcp_server

    with pytest.raises(SystemExit) as refused:
        mcp_server.main(["--governance-root", str(REPOSITORY), flag])
    assert refused.value.code == 2


def test_only_manus_start_envelope_is_health_only() -> None:
    data = json.loads(
        (REPOSITORY / "ops/config/memory-hook-envelopes.json").read_text(encoding="utf-8")
    )
    start = data["surfaces"]["manus-session-start"]
    assert start["allowed_operations"] == ["resolve", "health", "capabilities"]
    assert start["record_classes"] == []
    assert start["max_records"] == start["max_bytes"] == 0
    assert start["provenance_required"] is True


def test_shared_contract_retires_startup_hydration_not_on_demand_owner() -> None:
    contract = (REPOSITORY / "environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    events = contract.split("## Platform event binding\n", 1)[1].split("## Hydration honesty\n", 1)[
        0
    ]
    assert (
        "| Session memory health-only | `sessionStart` | `SessionStart` via "
        "`memory_prefetch.py` (health only) |"
    ) in events
    assert "Session hydrate" not in events
    assert "CANONICAL_LAW §8.9" in events
    assert "not a repository-write" in events
    honesty = contract.split("## Hydration honesty\n", 1)[1].split("## Close\n", 1)[0]
    assert "### Retired SessionStart hydration description" in honesty
    assert "not the current SessionStart contract" in honesty
    assert "on-demand hydration" in honesty
    assert "`ops/graphiti/hydration`" in honesty
    assert "`ops/scripts/classify_hydrate_state.py`" in honesty
