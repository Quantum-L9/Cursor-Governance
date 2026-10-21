"""Behavioral tests for the coding-agent canonical-binding gate.

The gate is mechanical enforcement of the ``l9-coding-agent`` law that a
verified canonical binding precedes mutation: it denies file mutations only
while a run is active (``.l9/coding-agent/run.json``). It trusts no writable
label: a record is admitted only when the pack verifier, re-run on it, the
committed bundle and the pinned authority checkout, answers ``CURRENT``; a
reauthorization is only the operator-controlled hook environment. Everything
else passes untouched.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import coding_agent_binding_gate as gate  # noqa: E402

PACK_TESTS = (
    REPO / "skills" / "l9-coding-agent" / "tests" / "test_coding_agent_canonical_binding.py"
)

RUN = {
    "schema": gate.RUN_SCHEMA,
    "started_at": "2026-10-21T00:00:00Z",
    "binding_record": "binding.json",
    "authority_root": "authority",
}
REVISION = "a" * 40
RECORD = {
    "verifier": "l9-coding-agent/scripts/verify_canonical_binding.py",
    "status": "BOUND",
    "reason": "PROJECTION_BUNDLE_VERIFIED",
    "authority_root": {"repository": "Quantum-L9/.github", "revision": REVISION},
    "bundle": {"path": "bundle"},
}


def current(**_: Any) -> dict[str, Any]:
    return {"status": "CURRENT", "reason": "UNCHANGED"}


def start_run(workspace: Path, *, record: dict | None = RECORD, run: dict | None = None) -> Path:
    run_dir = workspace / gate.RUN_DIR
    run_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "authority").mkdir(exist_ok=True)
    (workspace / "bundle").mkdir(exist_ok=True)
    (run_dir / gate.RUN_FILE).write_text(json.dumps(run if run is not None else RUN))
    if record is not None:
        (run_dir / gate.RECORD_FILE).write_text(json.dumps(record))
    return run_dir


def edit(
    workspace: Path,
    rel: str = "src/app.py",
    tool: str = "Edit",
    *,
    env: dict[str, str] | None = None,
    reverify_fn: Any = current,
) -> gate.Decision:
    return gate.evaluate(
        tool,
        {"file_path": str(workspace / rel)},
        cwd=workspace,
        env=env or {},
        reverify_fn=reverify_fn,
    )


# --- nothing active, nothing gated ---------------------------------------------------


def test_no_active_run_allows_everything(tmp_path: Path) -> None:
    assert edit(tmp_path).allow
    assert gate.evaluate("Write", {"file_path": "relative.py"}, cwd=tmp_path, env={}).allow


def test_non_mutating_tools_are_ignored(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    assert gate.evaluate("Read", {"file_path": str(tmp_path / "x")}, cwd=tmp_path, env={}).allow
    assert gate.evaluate("Bash", {"command": "rm -rf src"}, cwd=tmp_path, env={}).allow


def test_run_is_found_above_a_nested_path_and_not_in_a_sibling_tree(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    start_run(workspace, record=None)
    assert not edit(workspace, rel="deep/er/file.py").allow
    other = tmp_path / "other"
    other.mkdir()
    assert edit(other).allow


# --- the record is admitted only by a live re-verification --------------------------


def test_bound_record_allows_only_when_the_verifier_says_current(tmp_path: Path) -> None:
    start_run(tmp_path)
    seen: dict[str, Any] = {}

    def spy(**kw: Any) -> dict[str, Any]:
        seen.update(kw)
        return current()

    decision = edit(tmp_path, reverify_fn=spy)
    assert decision.allow and decision.reason.startswith("canonical binding CURRENT")
    assert seen["record_path"] == (tmp_path / gate.RUN_DIR / gate.RECORD_FILE).resolve()
    assert seen["bundle"] == tmp_path / "bundle"
    assert seen["authority_root"] == tmp_path / "authority"
    assert seen["revision"] == REVISION


@pytest.mark.parametrize(
    "verdict",
    [
        {"status": "STALE", "reason": "SOURCE_DIGEST_CHANGED"},
        {"status": "REJECTED", "reason": "BUNDLE_BYTES_MISMATCH"},
        {"status": "BLOCKED", "reason": "AUTHORITY_REVISION_NOT_ON_ORIGIN_TRACKING_REF"},
        {"status": "BOUND", "reason": "PROJECTION_BUNDLE_VERIFIED"},
        {},
    ],
)
def test_a_self_labeled_bound_record_releases_nothing(tmp_path: Path, verdict: dict) -> None:
    """The label in the writable file is not the decision; the live verdict is."""
    start_run(tmp_path)
    decision = edit(tmp_path, reverify_fn=lambda **_: verdict)
    assert not decision.allow
    assert "did not re-verify" in decision.reason
    assert (verdict.get("reason") or "Unknown") in decision.reason


@pytest.mark.parametrize("tool", sorted(gate.MUTATING_TOOLS))
def test_active_run_without_a_record_denies_every_file_tool(tmp_path: Path, tool: str) -> None:
    start_run(tmp_path, record=None)
    decision = edit(tmp_path, tool=tool)
    assert not decision.allow
    assert "no verified canonical binding" in decision.reason
    assert "verify_canonical_binding.py --bundle" in decision.reason
    assert gate.REAUTHORIZED_ENV in decision.reason


@pytest.mark.parametrize("status", ["REJECTED", "BLOCKED", "STALE", None])
def test_non_bound_record_denies_without_re_verifying(tmp_path: Path, status: str | None) -> None:
    record = {**RECORD, "status": status, "reason": "SOURCE_DIGEST_NOT_CURRENT"}
    if status is None:
        record.pop("status")
    start_run(tmp_path, record=record)
    calls: list[int] = []
    decision = edit(tmp_path, reverify_fn=lambda **_: calls.append(1) or current())
    assert not decision.allow and not calls
    assert (status or "absent") in decision.reason
    assert "SOURCE_DIGEST_NOT_CURRENT" in decision.reason


def test_record_from_another_verifier_is_not_a_binding(tmp_path: Path) -> None:
    start_run(tmp_path, record={**RECORD, "verifier": "someone-else/verify.py"})
    assert not edit(tmp_path).allow


def test_handed_pair_record_without_a_bundle_cannot_be_re_verified(tmp_path: Path) -> None:
    record = {k: v for k, v in RECORD.items() if k != "bundle"}
    start_run(tmp_path, record=record)
    decision = edit(tmp_path)
    assert not decision.allow and "not a bundle-bound record" in decision.reason


def test_run_without_authority_root_cannot_be_re_verified(tmp_path: Path) -> None:
    start_run(tmp_path, run={k: v for k, v in RUN.items() if k != "authority_root"})
    decision = edit(tmp_path)
    assert not decision.allow and "names no authority_root" in decision.reason


def test_absent_authority_checkout_denies(tmp_path: Path) -> None:
    start_run(tmp_path, run={**RUN, "authority_root": "gone"})
    decision = edit(tmp_path)
    assert not decision.allow and "not a directory" in decision.reason


def test_malformed_run_state_fails_closed(tmp_path: Path) -> None:
    run_dir = start_run(tmp_path, record=None)
    (run_dir / gate.RUN_FILE).write_text("{not json")
    decision = edit(tmp_path)
    assert not decision.allow and "unreadable" in decision.reason
    (run_dir / gate.RUN_FILE).write_text(json.dumps({"schema": "l9.other/v1"}))
    decision = edit(tmp_path)
    assert not decision.allow and gate.RUN_SCHEMA in decision.reason


def test_malformed_record_fails_closed(tmp_path: Path) -> None:
    run_dir = start_run(tmp_path, record=None)
    (run_dir / gate.RECORD_FILE).write_text("[]")
    decision = edit(tmp_path)
    assert not decision.allow and "not a binding record" in decision.reason


# --- the writable state is not a door ------------------------------------------------


def test_run_state_files_are_not_file_tool_writable_while_a_run_is_active(
    tmp_path: Path,
) -> None:
    start_run(tmp_path)
    for rel in (f"{gate.RUN_DIR}/{gate.RECORD_FILE}", f"{gate.RUN_DIR}/{gate.RUN_FILE}"):
        decision = edit(tmp_path, rel=rel, tool="Write")
        assert not decision.allow and "run state" in decision.reason


def test_opening_a_run_is_not_gated(tmp_path: Path) -> None:
    # No run.json yet: writing it is the first act of a run, and nothing is active.
    rel = f"{gate.RUN_DIR}/{gate.RUN_FILE}"
    assert edit(tmp_path, rel=rel, tool="Write").allow


def test_file_based_reauthorization_is_not_a_grant(tmp_path: Path) -> None:
    run = {**RUN, "reauthorized_unknown": {"instruction": "proceed with the binding Unknown"}}
    start_run(tmp_path, record=None, run=run)
    assert not edit(tmp_path).allow


# --- only the operator carries a run past an Unknown ---------------------------------


def test_operator_reauthorization_carries_the_run(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    env = {gate.REAUTHORIZED_ENV: "proceed with the binding Unknown; I accept the gap"}
    decision = edit(tmp_path, env=env)
    assert decision.allow and "reauthorization" in decision.reason


@pytest.mark.parametrize("value", ["", "   ", "1", "true", "yes"])
def test_a_bare_reauthorization_flag_is_not_an_instruction(tmp_path: Path, value: str) -> None:
    start_run(tmp_path, record=None)
    assert not edit(tmp_path, env={gate.REAUTHORIZED_ENV: value}).allow


def test_breakglass_needs_a_reason_not_a_flag(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    assert not edit(tmp_path, env={gate.BREAKGLASS_ENV: "1"}).allow
    allowed = edit(tmp_path, env={gate.BREAKGLASS_ENV: "incident 42: binding authority offline"})
    assert allowed.allow and "breakglass" in allowed.reason


# --- the real verifier, end to end ----------------------------------------------------


def _pack_tests() -> Any:
    spec = importlib.util.spec_from_file_location("coding_agent_pack_tests", PACK_TESTS)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_real_verifier_admits_the_record_and_rejects_a_changed_bundle(tmp_path: Path) -> None:
    """A record the verifier printed is CURRENT; the same record over a changed bundle is not."""
    pack = _pack_tests()
    authority = tmp_path / "authority"
    (authority / "semantics").mkdir(parents=True)
    for name, doc in pack.SEMANTICS.items():
        pack.write_semantics(authority, name, doc)
    pack.git(authority, "init", "-q")
    pack.git(authority, "remote", "add", "origin", pack.ORIGIN)
    pack.commit_all(authority, "fixture law")
    revision = pack.git(authority, "rev-parse", "HEAD").strip()
    pack.git(authority, "update-ref", "refs/remotes/origin/main", revision)
    bundle = pack.build_bundle(authority, tmp_path / "bundle")

    run_dir = tmp_path / gate.RUN_DIR
    run_dir.mkdir(parents=True)
    proc = subprocess.run(
        [
            sys.executable,
            str(gate.VERIFIER),
            "--authority-root",
            str(authority),
            "--bundle",
            str(bundle),
            "--expect-revision",
            revision,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (run_dir / gate.RECORD_FILE).write_text(proc.stdout)
    (run_dir / gate.RUN_FILE).write_text(json.dumps({**RUN, "authority_root": str(authority)}))

    decision = gate.evaluate(
        "Edit", {"file_path": str(tmp_path / "src/app.py")}, cwd=tmp_path, env={}
    )
    assert decision.allow, decision.reason
    assert "re-verified: UNCHANGED" in decision.reason

    contracts = bundle / "projections" / "contracts.projection.json"
    contracts.write_bytes(contracts.read_bytes().replace(b"}", b" }", 1))
    decision = gate.evaluate(
        "Edit", {"file_path": str(tmp_path / "src/app.py")}, cwd=tmp_path, env={}
    )
    assert not decision.allow
    assert "REJECTED" in decision.reason and "BUNDLE_BYTES_MISMATCH" in decision.reason


# --- the CLI --------------------------------------------------------------------------


def _cli(payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "ops/autonomy/coding_agent_binding_gate.py")],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )


def _decision(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(proc.stdout)["hookSpecificOutput"]


def test_cli_denies_as_a_pretooluse_decision(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "x.py")},
        "cwd": str(tmp_path),
    }
    proc = _cli(json.dumps(event))
    assert proc.returncode == 0
    output = _decision(proc)
    assert output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith("coding-agent binding gate:")


def test_cli_is_silent_when_nothing_is_active(tmp_path: Path) -> None:
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "x.py")},
        "cwd": str(tmp_path),
    }
    proc = _cli(json.dumps(event))
    assert proc.returncode == 0 and proc.stdout == ""


@pytest.mark.parametrize("payload", ["", "{not json", "[]", "42"])
def test_cli_fails_closed_on_an_unreadable_event(payload: str) -> None:
    proc = _cli(payload)
    assert proc.returncode == 0
    output = _decision(proc)
    assert output["permissionDecision"] == "deny"
    assert "cannot read its event" in output["permissionDecisionReason"]
