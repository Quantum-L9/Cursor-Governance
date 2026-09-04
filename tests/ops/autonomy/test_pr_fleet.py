"""pr_fleet.py: inventory once, safe waves, bounded assignments, fail-closed acceptance.

Every case is a fleet shape the remediator meets: independent PRs, a real
file overlap, a generated-only overlap, a stacked pair, a waiting PR, and a
mixed board. The velocity numbers compare the wave plan to the serial v4.6 hot
path the pack shipped with; they are deterministic counts, not timings.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))
sys.path.insert(0, str(REPO))

import pr_fleet  # noqa: E402

TARGET = "Quantum-L9/Cursor-Governance"
SHA = {n: f"{n:x}" * 40 for n in range(1, 8)}  # 40 hex chars per PR


def _pr(number: int, files: list[str], *, head: str | None = None, base: str = "main") -> dict:
    return {
        "number": number,
        "title": f"pr {number}",
        "created_at": f"2026-09-0{number}T00:00:00Z",
        "head": {"ref": head or f"feat/pr-{number}", "sha": SHA[number][:40]},
        "base": {"ref": base},
        "draft": False,
        "files": files,
    }


def _probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prs: list[dict]) -> None:
    path = tmp_path / "fleet-probe.json"
    path.write_text(json.dumps({"prs": prs}), encoding="utf-8")
    monkeypatch.setenv("L9_PR_FLEET_PROBE_FILE", str(path))


CURSOR = pr_fleet.profile_caps("cursor")
CLAUDE = pr_fleet.profile_caps("claude_cloud")

INDEPENDENT = [
    _pr(1, ["ops/a.py"]),
    _pr(2, ["ops/b.py"]),
    _pr(3, ["skills/x/SKILL.md"]),
]
OVERLAP = [_pr(1, ["ops/a.py", "ops/shared.py"]), _pr(2, ["ops/shared.py"])]
GENERATED_ONLY = [
    _pr(1, ["ops/a.py", "ops/generated/skill-registry.json"]),
    _pr(2, ["ops/b.py", "ops/generated/skill-registry.json"]),
]
STACKED = [_pr(1, ["ops/a.py"], head="feat/parent"), _pr(2, ["ops/b.py"], base="feat/parent")]


def test_caps_come_from_the_execution_profile_owner() -> None:
    assert CURSOR == {
        "surface": "cursor",
        "max_parallel": 4,
        "max_mutation_lanes": 2,
        "owner": CURSOR["owner"],
    }
    assert CLAUDE["max_mutation_lanes"] == 128 and CLAUDE["max_parallel"] == 480
    assert "execution_profile.py" in CURSOR["owner"]


def test_independent_prs_all_mutate_in_the_first_wave(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, INDEPENDENT)
    result = pr_fleet.plan(TARGET, surface="claude_cloud")
    first = result["waves"]["first_wave"]
    assert first["remediate"] == [1, 2, 3]
    assert first["blocked_claim"] == [] and first["blocked_cap"] == []
    assert result["waves"]["wave_count"] == 1
    assert all(pr["independent"] for pr in result["prs"])
    assert result["merge_order"] == [1, 2, 3]


def test_real_file_overlap_serializes_the_second_pr(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, OVERLAP)
    result = pr_fleet.plan(TARGET, surface="claude_cloud")
    first = result["waves"]["first_wave"]
    assert first["remediate"] == [1]
    assert first["blocked_claim"] == [{"pr": 2, "conflicts_with": [1]}]
    assert result["waves"]["mutation_waves"][1]["remediate"] == [2]
    assert result["overlap"] == [
        {"prs": [1, 2], "files": ["ops/shared.py"], "generated_only": False}
    ]
    assert not any(pr["independent"] for pr in result["prs"])
    # Read-only recon for the blocked PR still launches in the first wave.
    assert first["recon"] == [2]


def test_generated_only_overlap_does_not_serialize(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, GENERATED_ONLY)
    result = pr_fleet.plan(TARGET, surface="claude_cloud")
    assert result["overlap"][0]["generated_only"] is True
    assert result["waves"]["first_wave"]["remediate"] == [1, 2]
    assert all(pr["independent"] for pr in result["prs"])


def test_stacked_child_merges_after_parent_and_mutates_concurrently(
    tmp_path: Path, monkeypatch
) -> None:
    _probe(tmp_path, monkeypatch, list(reversed(STACKED)))
    result = pr_fleet.plan(TARGET, surface="claude_cloud")
    assert result["stack_edges"] == [{"child": 2, "parent": 1}]
    assert result["merge_order"] == [1, 2]
    assert result["waves"]["first_wave"]["remediate"] == [1, 2]
    assert not any(pr["independent"] for pr in result["prs"])


def test_cursor_mutation_cap_defers_the_third_pr(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, INDEPENDENT)
    result = pr_fleet.plan(TARGET, surface="cursor")
    first = result["waves"]["first_wave"]
    assert first["remediate"] == [1, 2]
    assert first["blocked_cap"] == [3]
    assert first["recon"] == [3]  # read lane fills the remaining total cap
    assert first["launch_count"] == 3 <= CURSOR["max_parallel"]
    assert result["waves"]["mutation_waves"][1]["remediate"] == [3]


def test_waiting_pr_gets_a_background_watcher(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, INDEPENDENT)
    prs = pr_fleet.inventory(TARGET)
    plan = pr_fleet.waves(
        prs, caps=CLAUDE, order=[1, 2, 3], boards={1: "merge", 2: "wait", 3: "fix"}
    )
    assert plan["first_wave"]["watch"] == [2]
    assert plan["first_wave"]["remediate"] == [1, 2, 3]


def test_fingerprint_reuses_the_inventory_until_a_head_moves(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, INDEPENDENT)
    first = pr_fleet.plan(TARGET, surface="claude_cloud")
    again = pr_fleet.plan(TARGET, surface="claude_cloud", prior=first)
    assert again["unchanged"] is True
    moved = [dict(INDEPENDENT[0], head={"ref": "feat/pr-1", "sha": "f" * 40}), *INDEPENDENT[1:]]
    _probe(tmp_path, monkeypatch, moved)
    third = pr_fleet.plan(TARGET, surface="claude_cloud", prior=first)
    assert third["unchanged"] is False


def test_plan_fails_closed_on_missing_head_sha(tmp_path: Path, monkeypatch) -> None:
    broken = [dict(INDEPENDENT[0], head={"ref": "feat/pr-1", "sha": ""})]
    _probe(tmp_path, monkeypatch, broken)
    with pytest.raises(pr_fleet.FleetError):
        pr_fleet.plan(TARGET, surface="claude_cloud")


# ---------------------------------------------------------------------------
# assignments and acceptance
# ---------------------------------------------------------------------------


def _packet(kind: str = "remediate", number: int = 1) -> dict[str, Any]:
    pr = pr_fleet._normalize_pr(INDEPENDENT[number - 1])
    return pr_fleet.build_assignment(TARGET, pr, kind=kind, run_id="run1", graph_id="abcd")


def _document(packet: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    doc = {
        "schema": "l9.cursor-subagent.result.v1",
        "schema_version": "1.0.0",
        "result_id": f"result-{packet['assignment_id']}",
        "result_kind": packet["result_kind"],
        "status": "completed",
        "identity": {
            "campaign_id": packet["campaign_id"],
            "graph_id": packet["graph_id"],
            "action_id": packet["action_id"],
            "agent_id": packet["agent_id"],
            "lease_id": packet["lease_id"],
            "base_sha": packet["base_sha"],
        },
        "assignment": {
            "role": packet["role"],
            "objective": packet["objective"],
            "input_artifact_ids": [],
            "allowed_paths": list(packet["allowed_paths"]),
            "forbidden_paths": list(packet["forbidden_paths"]),
        },
        "deliverable": {
            "summary": "One bounded result.",
            "findings": [],
            "files_read": ["ops/a.py"],
            "files_changed": ["ops/a.py"] if packet["kind"] == "remediate" else [],
            "evidence": [],
            "commands_executed": [
                {
                    "command": "L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo",
                    "exit_code": 0,
                }
            ],
            "validations": [
                {
                    "validation_id": "precommit-repo",
                    "method": "make precommit-repo",
                    "result": "PASS",
                }
            ],
            "unresolved_items": [],
            "recommended_next_actions": [],
            "reuse_assessment": {"reusable_data_found": False, "confidence": 1.0},
            "visibility": "repository_local",
        },
        "provenance": {"produced_at": "2026-09-04T12:00:00Z"},
    }
    for dotted, value in overrides.items():
        target = doc
        parts = dotted.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return doc


def test_assignment_carries_every_delegation_contract_input() -> None:
    packet = _packet()
    for field in (
        "campaign_id",
        "graph_id",
        "action_id",
        "agent_id",
        "lease_id",
        "base_sha",
        "role",
        "objective",
        "allowed_paths",
        "forbidden_paths",
    ):
        assert packet[field], field
    assert packet["role"] == "pr_remediation" and packet["result_kind"] == "PRRemediationReport"
    assert packet["lease_id"].startswith("no-root-lease-")
    assert "ops/a.py" in packet["allowed_paths"]
    assert any(path.startswith("ops/generated/") for path in packet["allowed_paths"])
    assert ".github/workflows/*" in packet["forbidden_paths"]
    assert packet["cursor"]["managed_task_type"] == "l9-pr-remediation"
    assert packet["cursor"]["run_in_background"] is True
    recon = _packet("recon")
    assert recon["role"] == "recon" and recon["mutation"] is False
    assert recon["cursor"]["managed_task_type"] == "l9-recon"
    prompt = pr_fleet.render_prompt(packet)
    assert packet["base_sha"] in prompt and "Natural-language completion is invalid" in prompt


def test_correct_document_is_accepted() -> None:
    packet = _packet()
    out = pr_fleet.accept(packet, _document(packet), use_gateway=False)
    assert out["status"] == "ACCEPTED", out
    assert out["files_changed"] == ["ops/a.py"]


def test_stale_base_sha_is_rejected() -> None:
    packet = _packet()
    out = pr_fleet.accept(
        packet, _document(packet, **{"identity.base_sha": "0" * 40}), use_gateway=False
    )
    assert out["status"] == "REJECTED" and "base_sha" in out["reason"]


def test_wrong_lease_action_or_role_is_rejected() -> None:
    packet = _packet()
    for key, value in (
        ("identity.lease_id", "no-root-lease-other"),
        ("identity.action_id", "remediate-pr9-run1"),
        ("assignment.role", "test"),
    ):
        doc = _document(packet, **{key: value})
        if key == "assignment.role":
            doc["result_kind"] = "TestReport"
        out = pr_fleet.accept(packet, doc, use_gateway=False)
        assert out["status"] == "REJECTED", key


def test_change_outside_the_writable_grant_is_rejected() -> None:
    packet = _packet()
    out = pr_fleet.accept(
        packet,
        _document(packet, **{"deliverable.files_changed": ["ops/a.py", "ops/other.py"]}),
        use_gateway=False,
    )
    assert out["status"] == "REJECTED" and "outside the allowed paths" in out["reason"]
    out = pr_fleet.accept(
        packet,
        _document(packet, **{"deliverable.files_changed": [".github/workflows/ci.yml"]}),
        use_gateway=False,
    )
    assert out["status"] == "REJECTED"


def test_recon_reporting_changed_files_is_rejected() -> None:
    packet = _packet("recon")
    out = pr_fleet.accept(
        packet, _document(packet, **{"deliverable.files_changed": ["ops/a.py"]}), use_gateway=False
    )
    assert out["status"] == "REJECTED" and "must not report changed files" in out["reason"]


def test_partial_document_is_never_promoted_to_success() -> None:
    packet = _packet()
    out = pr_fleet.accept(packet, _document(packet, status="partial"), use_gateway=False)
    assert out["status"] == "ACCEPTED_INCOMPLETE" and out["document_status"] == "partial"


def test_narrative_only_completion_is_rejected() -> None:
    packet = _packet()
    out = pr_fleet.accept(packet, {"summary": "done, tests pass"}, use_gateway=False)
    assert out["status"] == "REJECTED"


def test_recorded_assignment_flows_through_the_results_gateway(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("L9_RUNTIME_ROOT", tmp)
        monkeypatch.delenv("L9_ROOT", raising=False)
        packet = _packet()
        pr_fleet.record_lifecycle_assignment(packet, Path(tmp))
        out = pr_fleet.accept(packet, _document(packet))
        assert out["status"] == "ACCEPTED", out
        assert out["gateway"]["status"] == "ACCEPTED"
        assert out["gateway"]["receipt_digest"]
        # A host that reports a non-success stop outranks the document.
        bad = pr_fleet.accept(packet, _document(packet), host_status="cancelled")
        assert bad["status"] == "REJECTED" and "host" in bad["reason"]


# ---------------------------------------------------------------------------
# velocity: serial v4.6 hot path versus the wave plan
# ---------------------------------------------------------------------------


def test_velocity_model_shows_the_wave_plan_ahead_on_every_counter(
    tmp_path: Path, monkeypatch
) -> None:
    fleet = [
        _pr(1, ["ops/a.py"]),
        _pr(2, ["ops/b.py"]),
        _pr(3, ["ops/c.py", "ops/generated/skill-registry.json"]),
        _pr(4, ["ops/d.py", "ops/generated/skill-registry.json"]),
        _pr(5, ["ops/e.py"], head="feat/parent"),
        _pr(6, ["ops/f.py"], base="feat/parent"),
    ]
    _probe(tmp_path, monkeypatch, fleet)
    result = pr_fleet.plan(TARGET, surface="claude_cloud")
    model = result["velocity"]
    serial, waves = model["serial"], model["waves"]
    assert serial["first_wave_parallelism"] == 1
    assert waves["first_wave_parallelism"] == 6 and waves["first_wave_mutators"] == 6
    assert waves["remote_queries_preflight"] < serial["remote_queries_preflight"]
    assert waves["duplicate_stack_probes_at_merge"] == 0 < serial["duplicate_stack_probes_at_merge"]
    assert waves["main_agent_foreground_waits"] == 0 < serial["main_agent_foreground_waits"]
    assert waves["blocked_claim_first_wave"] == 0


def test_cli_plan_and_assign_roundtrip(tmp_path: Path, monkeypatch) -> None:
    _probe(tmp_path, monkeypatch, INDEPENDENT)
    monkeypatch.chdir(tmp_path)
    assert pr_fleet.main(["plan", "--repo", TARGET, "--surface", "claude_cloud", "--json"]) == 0
    receipt = json.loads((tmp_path / ".l9" / "pr" / "fleet.json").read_text(encoding="utf-8"))
    assert receipt["open_prs"] == 3
    assert (
        pr_fleet.main(
            ["assign", "--repo", TARGET, "--kind", "remediate", "--run-id", "r1", "--json"]
        )
        == 0
    )
    assignments = sorted((tmp_path / ".l9" / "pr" / "assignments").glob("*.json"))
    assert [p.name for p in assignments] == [
        "remediate-pr1-r1.json",
        "remediate-pr2-r1.json",
        "remediate-pr3-r1.json",
    ]
    packet = json.loads(assignments[0].read_text(encoding="utf-8"))
    doc_path = tmp_path / "result.json"
    doc_path.write_text(json.dumps(_document(packet)), encoding="utf-8")
    assert (
        pr_fleet.main(
            [
                "accept",
                "--assignment",
                packet["assignment_id"],
                "--result",
                str(doc_path),
                "--no-gateway",
            ]
        )
        == 0
    )
    doc_path.write_text(
        json.dumps(_document(packet, **{"identity.base_sha": "0" * 40})), encoding="utf-8"
    )
    assert (
        pr_fleet.main(
            [
                "accept",
                "--assignment",
                packet["assignment_id"],
                "--result",
                str(doc_path),
                "--no-gateway",
            ]
        )
        == 1
    )
    assert os.environ.get("L9_PR_FLEET_PROBE_FILE")
