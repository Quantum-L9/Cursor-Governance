"""Seams a real Claude Code window exercises and a scripted fake does not.

Each case here was found by running a live two-task campaign through the real
`claude` executable. The scripted host in `test_pe_smoke_campaign.py` returns a
perfectly shaped payload and writes nothing but its declared path, so none of
these could fail there:

* the worker window must carry Program Execution's own PreToolUse hook, because
  the host-wide wrapper does not reach Program Execution;
* a real model shapes `validation_results` however the instruction lets it;
* a real host writes session bookkeeping into its working directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_PE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _PE_ROOT.parents[1]
_INTEGRATION = _PE_ROOT / "integrations" / "autonomy-control-plane"

for _path in (str(_REPO_ROOT), str(_PE_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from peer_execution import execution  # noqa: E402
from peer_execution.context import build_context_manifest  # noqa: E402
from peer_execution.imports import load_module  # noqa: E402

RECEIPTS = ".l9/memory/receipts"


def _campaign() -> Any:
    return load_module(_PE_ROOT / "scripts" / "run_campaign.py", "seams_run_campaign")


def _provider() -> Any:
    return load_module(_PE_ROOT / "adapters/claude-code/provider.py", "seams_claude_provider")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=seam", "-c", "user.email=seam@example.com", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    repo = tmp_path / "worktree"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


# -- the worker window carries PE's own hook --------------------------------


def test_the_provider_registers_the_pe_effect_hook_for_every_effect_tool(tmp_path: Path) -> None:
    module = _provider()
    provider = module.ClaudeCodeProvider(tmp_path, _REPO_ROOT)
    settings = json.loads(provider._worker_settings())
    (entry,) = settings["hooks"]["PreToolUse"]
    assert set(entry["matcher"].split("|")) >= {"Bash", "Edit", "Write"}
    (hook,) = entry["hooks"]
    assert hook["type"] == "command"
    assert str(_INTEGRATION / "worker_effect_hook.py") in hook["command"]


def test_the_provider_exports_exactly_what_the_hook_checks() -> None:
    hook = load_module(_INTEGRATION / "worker_effect_hook.py", "seams_worker_effect_hook")
    assert _provider()._AUTHORITY_ENVIRONMENT == hook.AUTHORITY_ENVIRONMENT


def test_the_probe_blocks_when_the_hook_surface_is_missing(tmp_path: Path) -> None:
    """A window that could not be mediated is never admitted."""
    probe = _provider().ClaudeCodeProvider(tmp_path, tmp_path).probe(None)
    assert probe.status == "BLOCKED"


def test_the_host_wide_wrapper_still_does_not_reach_program_execution() -> None:
    wrapper = (
        _REPO_ROOT / "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"
    )
    text = wrapper.read_text(encoding="utf-8")
    assert "program-execution" not in text
    assert "L9_PROGRAM_" not in text


# -- a real model's validation claims ---------------------------------------


def test_the_instruction_states_the_shape_the_receipt_schema_enforces() -> None:
    manifest = build_context_manifest(
        {
            "task_id": "TASK-SEAM",
            "program_lock_digest": "sha256:" + "1" * 64,
            "contract_digest": "sha256:" + "2" * 64,
            "base_sha": "3" * 40,
            "worktree": "/tmp/worktree",
            "writable_paths": ["docs/a.md"],
            "validation_commands": ["git status --short"],
            "required_evidence_ids": [],
        }
    )
    instruction = manifest["worker_instruction"]
    for field in ("command", "status", "exit_code", "evidence", "claimed_status"):
        assert field in instruction
    assert "residual_unknowns is a blocking field" in instruction
    # The Controller's `worker_validation_claim` gate compares the claimed
    # commands with the contract's; a live resumed window added its own.
    assert "exactly one entry per command" in instruction
    assert "no other entry" in instruction


@pytest.mark.parametrize(
    "item",
    [
        {"command": "git status --short", "status": "PASS", "exit_code": 0, "evidence": "ok"},
        {"command": "git status --short", "status": "UNKNOWN", "exit_code": None, "evidence": None},
    ],
)
def test_a_schema_shaped_validation_claim_is_kept(item: dict[str, Any]) -> None:
    assert execution._is_validation_claim(item)


@pytest.mark.parametrize(
    "item",
    [
        # What the live model returned before the instruction named the shape.
        {"command": "git status --short", "exit_code": 0, "id": "VAL-1", "result": "PASS"},
        {"command": "", "status": "PASS", "exit_code": 0, "evidence": None},
        {"command": "x", "status": "GREEN", "exit_code": 0, "evidence": None},
        {"command": "x", "status": "PASS", "exit_code": True, "evidence": None},
        {"command": "x", "status": "PASS", "exit_code": 0, "evidence": None, "note": "extra"},
    ],
)
def test_a_claim_the_schema_cannot_carry_is_not_one(item: dict[str, Any]) -> None:
    assert not execution._is_validation_claim(item)


# -- a real host's session bookkeeping --------------------------------------


def _host_receipt(worktree: Path, name: str) -> str:
    target = worktree / RECEIPTS / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}\n", encoding="utf-8")
    return f"{RECEIPTS}/{name}"


def test_host_session_receipts_are_moved_out_and_preserved(worktree: Path, tmp_path: Path) -> None:
    campaign = _campaign()
    baseline = campaign.worktree_effect_baseline(worktree)
    relative = _host_receipt(worktree, "claude-code__0f1e2d3c-session.json")
    assert relative in campaign.provider_effected_paths(worktree, baseline)
    destination = tmp_path / "residue"
    moved = campaign.relocate_host_session_residue(worktree, destination, baseline)
    assert moved == [relative]
    assert (destination / "claude-code__0f1e2d3c-session.json").is_file()
    assert campaign.provider_effected_paths(worktree, baseline) == []


def test_a_write_anywhere_else_is_still_an_effect(worktree: Path, tmp_path: Path) -> None:
    """The relocation is one directory wide; it is not a way around coverage."""
    campaign = _campaign()
    baseline = campaign.worktree_effect_baseline(worktree)
    (worktree / ".l9" / "memory").mkdir(parents=True)
    (worktree / ".l9" / "memory" / "notes.json").write_text("{}\n", encoding="utf-8")
    nested = worktree / RECEIPTS / "deeper"
    nested.mkdir(parents=True)
    (nested / "x.json").write_text("{}\n", encoding="utf-8")
    (worktree / "docs").mkdir()
    (worktree / "docs" / "a.md").write_text("unmediated\n", encoding="utf-8")
    assert campaign.relocate_host_session_residue(worktree, tmp_path / "residue", baseline) == []
    assert campaign.provider_effected_paths(worktree, baseline) == [
        ".l9/memory/notes.json",
        f"{RECEIPTS}/deeper/x.json",
        "docs/a.md",
    ]
    unit = {
        "task_id": "TASK-SEAM",
        "worktree": str(worktree),
        "grant": None,
        "pre_dispatch_baseline": baseline,
    }
    with pytest.raises(campaign.CampaignError, match="no root autonomy grant"):
        campaign._require_mediated_effects(unit, trace=None)


def test_tracked_and_pre_dispatch_receipts_are_left_alone(worktree: Path, tmp_path: Path) -> None:
    campaign = _campaign()
    tracked = _host_receipt(worktree, "tracked.json")
    _git(worktree, "add", "-f", tracked)
    _git(worktree, "commit", "-q", "-m", "track a receipt")
    (worktree / tracked).write_text('{"edited": true}\n', encoding="utf-8")
    before = _host_receipt(worktree, "before-dispatch.json")
    baseline = campaign.worktree_effect_baseline(worktree)
    assert campaign.relocate_host_session_residue(worktree, tmp_path / "residue", baseline) == []
    assert (worktree / tracked).is_file()
    assert (worktree / before).is_file()


def test_a_symlinked_receipt_directory_is_never_followed(worktree: Path, tmp_path: Path) -> None:
    campaign = _campaign()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.json").write_text("{}\n", encoding="utf-8")
    (worktree / ".l9" / "memory").mkdir(parents=True)
    (worktree / RECEIPTS).symlink_to(outside, target_is_directory=True)
    assert campaign.relocate_host_session_residue(worktree, tmp_path / "residue", {}) == []
    assert (outside / "keep.json").is_file()


# -- a worker window is not an operator session ------------------------------


def _inspect_request(worktree: Path) -> Any:
    from peer_execution.provider import CanonicalExecutionRequest

    digest = "sha256:" + "0" * 64
    return CanonicalExecutionRequest(
        execution_id="exec-seam",
        task_id="TASK-SEAM",
        program_lock_digest=digest,
        rendered_contract_digest=digest,
        worktree_ref=str(worktree),
        objective="Inspect",
        context_manifest_ref=str(worktree / "context.json"),
        context_manifest_digest=digest,
        rendered_contract={"task_id": "TASK-SEAM", "validation_commands": []},
        worker_instruction="inspect",
        permission_profile_ref="profile-seam",
        permission_profile={"profile_ref": "profile-seam", "allowed_actions": ["inspect"]},
        inference_budget={"max_turns": 2},
        timeout_budget={"dispatch_seconds": 30, "poll_seconds": 5},
        requested_capabilities=("inspect",),
        telemetry_context={"task_id": "TASK-SEAM"},
        agent_ref="claude-code",
        surface="claude-code-cli",
        provider_ref="claude-code-direct",
        execution_profile_ref="claude-code-autonomous",
        autonomy_authority=None,
    )


def test_the_window_loads_no_operator_settings_and_no_mcp_server(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _provider()
    launched: dict[str, Any] = {}

    def capture(argv: list[str], **kwargs: Any) -> Any:
        launched["argv"] = list(argv)
        raise RuntimeError("captured before launch")

    monkeypatch.setattr(module, "run_argv", capture)
    with pytest.raises(RuntimeError, match="captured before launch"):
        module.ClaudeCodeProvider(worktree, _REPO_ROOT).invoke(_inspect_request(worktree))
    argv = launched["argv"]
    assert argv[argv.index("--setting-sources") + 1] == "project,local"
    assert "user" not in argv[argv.index("--setting-sources") + 1].split(",")
    assert "--strict-mcp-config" in argv
    assert "--mcp-config" not in argv
    # No authority, so no mutation tools and no effect hook to register.
    assert "--settings" not in argv
    allowed = argv[argv.index("--allowedTools") + 1].split(",")
    assert "Write" not in allowed and "Edit" not in allowed


def test_read_denials_the_operator_settings_carried_are_stated_by_the_renderer() -> None:
    renderer = load_module(
        _PE_ROOT / "adapters/claude-code/permission_renderer.py", "seams_permission_renderer"
    )
    denied = renderer.render_permissions({"allowed_actions": ["inspect", "local_write"]}, {})[
        "denied"
    ]
    assert {"Read(./.env)", "Read(./.mcp.json)"} <= set(denied)


# -- the worker is handed the program's projection ----------------------------

PROJECTION_BINDING = _REPO_ROOT / "governance/authority-bindings/coding-agent-execution.yaml"


def _bound_views() -> dict[str, Any]:
    """A projection binding record over the committed bundle, as bootstrap writes it."""
    import hashlib

    import yaml

    binding = yaml.safe_load(PROJECTION_BINDING.read_text(encoding="utf-8"))
    bundle = _REPO_ROOT / binding["bundle"]["path"]
    lock = json.loads((bundle / binding["bundle"]["lock"]).read_text(encoding="utf-8"))
    return {
        "profile_ref": binding["upstream"]["profile_ref"],
        "bundle_revision": lock["authority"]["revision"],
        "views": [
            {
                "path": str(path.relative_to(_REPO_ROOT)),
                "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted((bundle / "projections").glob("*.projection.json"))
        ],
    }


def _contract() -> dict[str, Any]:
    return {
        "task_id": "TASK-SEAM",
        "program_lock_digest": "sha256:" + "1" * 64,
        "contract_digest": "sha256:" + "2" * 64,
        "base_sha": "3" * 40,
        "worktree": "/tmp/worktree",
        "writable_paths": ["docs/a.md"],
        "validation_commands": ["git status --short"],
        "required_evidence_ids": [],
    }


def test_the_bound_projection_is_reverified_and_carried_whole() -> None:
    from peer_execution.context import projection_context

    context = projection_context(_bound_views(), _REPO_ROOT)
    assert context["profile_ref"] == "l9.projection/coding-agent-execution@1"
    assert {view["source_ref"] for view in context["views"]} == {
        "l9.source/invariants@1",
        "l9.source/contracts@1",
        "l9.source/authority-model@1",
    }
    for view in context["views"]:
        on_disk = json.loads((_REPO_ROOT / view["path"]).read_text(encoding="utf-8"))
        assert view["payload"] == on_disk["payload"]


def test_the_worker_instruction_carries_every_view_payload() -> None:
    from peer_execution.context import build_context_manifest, projection_context
    from peer_execution.digests import canonical_json
    from peer_execution.schema_registry import SchemaRegistry

    projection = projection_context(_bound_views(), _REPO_ROOT)
    manifest = build_context_manifest(_contract(), projection)
    instruction = manifest["worker_instruction"]
    for view in projection["views"]:
        assert canonical_json(view["payload"]) in instruction
    # The rendered contract stays the last line, so a host parses it unchanged.
    assert json.loads(instruction.splitlines()[-1])["task_id"] == "TASK-SEAM"
    # The manifest records which views were handed, by digest, not their payloads.
    recorded = manifest["projection"]
    assert [view["digest"] for view in recorded["views"]] == [
        view["digest"] for view in projection["views"]
    ]
    assert all("payload" not in view for view in recorded["views"])
    assert SchemaRegistry(_PE_ROOT).validate_context_manifest(manifest) == []
    unbound = build_context_manifest(_contract())
    assert "projection" not in unbound
    assert unbound["manifest_digest"] != manifest["manifest_digest"]


def test_a_view_that_moved_after_binding_is_never_handed(tmp_path: Path) -> None:
    import shutil

    from peer_execution.context import projection_context

    record = _bound_views()
    for view in record["views"]:
        target = tmp_path / view["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_REPO_ROOT / view["path"], target)
    assert projection_context(record, tmp_path)["views"]
    drifted = tmp_path / record["views"][0]["path"]
    document = json.loads(drifted.read_text(encoding="utf-8"))
    document["payload"]["injected"] = "widen me"
    drifted.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="PROJECTION_VIEW_DRIFT"):
        projection_context(record, tmp_path)


def test_a_view_outside_the_repository_is_refused(tmp_path: Path) -> None:
    from peer_execution.context import projection_context

    record = _bound_views()
    outside = tmp_path / "outside.json"
    outside.write_text('{"payload": {"x": 1}}', encoding="utf-8")
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "link.json").symlink_to(outside)
    for path, code in (("../outside.json", "PROJECTION_VIEW_ESCAPES"), ("link.json", "ESCAPES")):
        escaped = {**record, "views": [{"path": path, "digest": "sha256:" + "0" * 64}]}
        with pytest.raises(ValueError, match=code):
            projection_context(escaped, tmp_path / "repo")
    with pytest.raises(ValueError, match="PROJECTION_VIEWS_ABSENT"):
        projection_context({**record, "views": []}, _REPO_ROOT)


def test_only_the_argv_transport_bounds_the_instruction(worktree: Path) -> None:
    """The size bound is the Claude CLI's argv limit, not the instruction's.

    The provider-neutral builder accepts a large instruction, so a provider that
    hands over the request as a file is not refused; the Claude provider, which
    passes it as one argv string, refuses it before launching anything.
    """
    from peer_execution import context as module

    module_provider = _provider()
    limit = module_provider.MAX_ARGV_INSTRUCTION_BYTES
    projection = module.projection_context(_bound_views(), _REPO_ROOT)
    bloated = {
        **projection,
        "views": [{**projection["views"][0], "payload": {"padding": "x" * limit}}],
    }
    manifest = module.build_context_manifest(_contract(), bloated)
    assert len(manifest["worker_instruction"].encode("utf-8")) > limit
    request = _inspect_request(worktree).model_copy(
        update={"worker_instruction": manifest["worker_instruction"]}
    )
    with pytest.raises(ValueError, match="WORKER_INSTRUCTION_TOO_LARGE"):
        module_provider.ClaudeCodeProvider(worktree, _REPO_ROOT).invoke(request)
    fits = _inspect_request(worktree)
    assert module_provider.ClaudeCodeProvider._instruction_argument(fits) == fits.worker_instruction


def test_the_campaign_dispatches_nothing_without_a_recorded_binding(tmp_path: Path) -> None:
    campaign = _campaign()
    with pytest.raises(campaign.CampaignError) as caught:
        campaign.bound_projection_context(tmp_path)
    assert caught.value.error_code == "PROJECTION_BINDING_UNRECORDED"
    (tmp_path / "runtime").mkdir()
    record = _bound_views()
    record["views"][0] = {**record["views"][0], "digest": "sha256:" + "0" * 64}
    (tmp_path / "runtime" / "coding-projection-binding.json").write_text(
        json.dumps({"bootstrap": record, "verified": []}), encoding="utf-8"
    )
    with pytest.raises(campaign.CampaignError) as caught:
        campaign.bound_projection_context(tmp_path)
    assert caught.value.error_code == "PROJECTION_NOT_HANDED"


def test_an_adapter_without_a_projection_carrier_is_refused() -> None:
    from peer_execution.front_door import bind_projection

    bind_projection(adapter=object(), projection=None)
    with pytest.raises(ValueError, match="ADAPTER_CANNOT_CARRY_PROJECTION"):
        bind_projection(adapter=object(), projection={"views": []})
