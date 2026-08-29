"""Adversarial E2E for Program-bound root autonomy at the campaign seam.

PR-003 closes the public enforcement proof opened by PR-001+002. Those landed
the mechanism: a PreToolUse wrapper that authorizes every worker effect through
the root capability gateway under a live Program parent, and a campaign-side
coverage check that refuses to record an attempt for a write nothing
authorized. What they did not land was a public run that *attacks* it.

That gap is not academic. Until this module existed, the campaign's own
mediation coverage was satisfied by the capability probe `grant.py` takes while
issuing the lease — a real allowed decision on the task's first writable path.
A provider could therefore write that path directly, with no hook in the loop
at all, and the campaign would report full mediation. The distinction this
suite pins down is `authorization_phase`: `grant_probe` proves the lease *holds*
the capability, `effect` proves a specific write went through the gateway, and
only the second answers coverage.

Every case here runs against real state:

* a real git worktree with a real HEAD;
* real canonical PEC state (`pec.state.StateDB`) for the Program parent;
* a real root-autonomy grant from `grant.grant_task_mutation`;
* the real `ClaudeCodeProvider` authority export, so the worker environment is
  the one the provider actually builds rather than one this test invented;
* the real `local_execution_gate_wrap.py`, run as a subprocess exactly as the
  hook launcher runs it;
* the real campaign functions from `run_campaign.py` for coverage and
  terminalization.

Only the downstream ops gate is a stub, and only so its stdin can be captured:
what is under test is what the wrapper hands it, and that it is never handed
anything at all when authorization fails.

Nothing here asserts that Program Execution succeeded. PEC owns that verdict.
What is asserted is the boundary: no effect without a pre-effect authorization,
and no root evidence surviving a verdict that rejected it.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

_PE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _PE_ROOT.parents[1]
_INTEGRATION = _PE_ROOT / "integrations" / "autonomy-control-plane"
_PEC_SCRIPTS = _PE_ROOT / "core" / "program-execution-controller-template" / "scripts"
_CLAUDE_ADAPTER = _PE_ROOT / "adapters" / "claude-code"

for _path in (str(_REPO_ROOT), str(_PE_ROOT), str(_INTEGRATION), str(_PEC_SCRIPTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from peer_execution.imports import load_module  # noqa: E402

WRAPPER = _REPO_ROOT / "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"

#: The stub stands in for `ops/autonomy/local_execution_gate.py` only so its
#: stdin is observable. It exits 0 unconditionally, so every denial in this
#: module is the wrapper's own — never the downstream gate's.
STUB_GATE = """import os
import pathlib
import sys

pathlib.Path(os.environ["L9_TEST_GATE_LOG"]).write_bytes(sys.stdin.buffer.read())
raise SystemExit(0)
"""

PROGRAM_LEASE_ID = "lease-program-e2e"
TASK_ID = "TASK-E2E"
WRITABLE = "docs/e2e/result.md"


def _grant_module() -> Any:
    return load_module(_INTEGRATION / "grant.py", "e2e_autonomy_grant")


def _campaign_module() -> Any:
    return load_module(_PE_ROOT / "scripts" / "run_campaign.py", "e2e_run_campaign")


def _provider_module() -> Any:
    return load_module(_CLAUDE_ADAPTER / "provider.py", "e2e_claude_provider")


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_AUTHOR_NAME": "E2E",
            "GIT_AUTHOR_EMAIL": "e2e@example.com",
            "GIT_COMMITTER_NAME": "E2E",
            "GIT_COMMITTER_EMAIL": "e2e@example.com",
        },
    )
    return completed.stdout.strip()


class Harness:
    """One live Program task: canonical parent, root grant, worker window."""

    def __init__(self, root: Path, *, requested_actions: list[str]) -> None:
        self.root = root
        self.workspace = root / "workspace"
        self.worktree = self.workspace / "worktrees" / TASK_ID
        self.worktree.mkdir(parents=True)
        _git(self.worktree, "init", "--initial-branch=pec/task-e2e")
        (self.worktree / "README.md").write_text("seed\n", encoding="utf-8")
        _git(self.worktree, "add", "README.md")
        _git(self.worktree, "commit", "-m", "seed")
        self.base_sha = _git(self.worktree, "rev-parse", "HEAD")
        self.contract: dict[str, Any] = {
            "program_id": "Program E2E",
            "task_id": TASK_ID,
            "objective": "Edit the declared path",
            "base_sha": self.base_sha,
            "requested_actions": list(requested_actions),
            "writable_paths": [WRITABLE],
            "contract_digest": "digest-e2e",
            "repository_id": "repo-e2e",
            "branch": "pec/task-e2e",
            "lease_id": PROGRAM_LEASE_ID,
            "worktree": str(self.worktree),
        }
        self.bind_parent()
        self.grants = _grant_module()
        self.grant = self.grants.grant_task_mutation(
            _REPO_ROOT,
            self.workspace,
            self.contract,
            attempt_number=1,
            agent_ref="claude-code",
            surface="claude-cli",
        )
        self.authority = self.grant["autonomy_authority"]
        self.gate_log = root / "gate-stdin.bin"
        self.stub_gate = root / "stub_gate.py"
        self.stub_gate.write_text(STUB_GATE, encoding="utf-8")

    # -- canonical Program parent ------------------------------------------

    def bind_parent(self, *, expires_in_seconds: int = 900, state: str = "EXECUTING") -> None:
        from pec.state import StateDB

        database = StateDB(self.workspace / "runtime" / "state.sqlite")
        try:
            database.upsert_task(
                {
                    "id": TASK_ID,
                    "title": TASK_ID,
                    "wave_id": "WAVE-1",
                    "workstream_id": "WS-1",
                    "target_id": "TARGET-E2E",
                    "repository_id": "repo-e2e",
                    "execution_kind": "code_change",
                    "objective": "Edit the declared path",
                    "risk_tier": "low",
                    "definition_status": "defined",
                }
            )
            now = datetime.now(tz=UTC)
            database.create_lease(
                {
                    "lease_id": PROGRAM_LEASE_ID,
                    "task_id": TASK_ID,
                    "repository_id": "repo-e2e",
                    "holder": "make-campaign",
                    "base_sha": self.base_sha,
                    "branch": "pec/task-e2e",
                    "worktree": str(self.worktree),
                    "contract_digest": "digest-e2e",
                    "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "expires_at": (now + timedelta(seconds=expires_in_seconds)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
            database.update_task(TASK_ID, lease_id=PROGRAM_LEASE_ID)
            for transition in ("ELIGIBLE", "LEASED", "PREPARED", "CONTRACTED", state):
                if database.task(TASK_ID)["runtime_state"] != transition:
                    database.transition_task(TASK_ID, transition)
        finally:
            database.close()

    def program_state(self) -> sqlite3.Connection:
        return sqlite3.connect(self.workspace / "runtime" / "state.sqlite")

    def runtime_state(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.authority["runtime_database"]))

    # -- the worker window --------------------------------------------------

    def worker_environment(self) -> dict[str, str]:
        """The authority the real Claude provider exports into a worker window.

        Built through `ClaudeCodeProvider._authority_environment` rather than
        assembled here, so a provider that stopped exporting a field this hook
        needs fails this suite instead of passing it.
        """
        provider_module = _provider_module()
        provider = provider_module.ClaudeCodeProvider(self.workspace, _REPO_ROOT)
        request = self._execution_request()
        environment = dict(provider._authority_environment(request))
        environment["L9_AUTONOMY_REQUIRED"] = "1"
        return environment

    def _execution_request(self) -> Any:
        from peer_execution.provider import CanonicalExecutionRequest

        digest = "sha256:" + "0" * 64
        return CanonicalExecutionRequest(
            execution_id=f"exec-{uuid.uuid4().hex}",
            task_id=TASK_ID,
            program_lock_digest=digest,
            rendered_contract_digest=digest,
            worktree_ref=str(self.worktree),
            objective="Edit the declared path",
            context_manifest_ref=str(self.workspace / "context.json"),
            context_manifest_digest=digest,
            rendered_contract=dict(self.contract),
            worker_instruction="edit the declared path",
            permission_profile_ref="profile-e2e",
            permission_profile={
                "profile_ref": "profile-e2e",
                "allowed_actions": list(self.contract["requested_actions"]),
            },
            inference_budget={"max_turns": 4},
            timeout_budget={"dispatch_seconds": 60, "poll_seconds": 5},
            requested_capabilities=tuple(self.contract["requested_actions"]),
            telemetry_context={"task_id": TASK_ID},
            agent_ref="claude-code",
            surface="claude-cli",
            provider_ref="claude-code-direct",
            execution_profile_ref="claude-code-autonomous",
            autonomy_authority=dict(self.authority),
        )

    def tool_call(
        self,
        event: dict[str, Any],
        *,
        environment: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        """Run one tool call through the live PreToolUse wrapper.

        Returns the wrapper's exit code and the bytes the downstream ops gate
        received — empty when the wrapper refused before ever reaching it.
        """
        if self.gate_log.exists():
            self.gate_log.unlink()
        raw = json.dumps(event).encode("utf-8")
        env = {
            **os.environ,
            **(self.worker_environment() if environment is None else environment),
            "L9_EXECUTION_GATE": str(self.stub_gate),
            "L9_TEST_GATE_LOG": str(self.gate_log),
        }
        completed = subprocess.run(
            [sys.executable, str(WRAPPER)],
            input=raw,
            capture_output=True,
            env={key: value for key, value in env.items() if value is not None},
            timeout=180,
        )
        replayed = self.gate_log.read_bytes() if self.gate_log.exists() else b""
        return completed.returncode, replayed

    def write_event(self, path: str) -> dict[str, Any]:
        return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "body\n"}}

    def mediated_write(self, relative: str = WRITABLE, body: str = "body\n") -> None:
        """Authorize a write through the wrapper, then perform it. In that order."""
        target = self.worktree / relative
        code, replayed = self.tool_call(self.write_event(str(target)))
        assert code == 0, "the authorized path must reach the downstream gate"
        assert replayed, "an allowed effect must reach the ops gate"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    # -- the campaign seam --------------------------------------------------

    def unit(self, baseline: dict[str, str] | None = None) -> dict[str, Any]:
        return {
            "task_id": TASK_ID,
            "worktree": str(self.worktree),
            "contract": dict(self.contract),
            "grant": self.grant,
            "pre_dispatch_baseline": baseline if baseline is not None else {},
        }


@pytest.fixture
def harness(tmp_path: Path) -> Iterator[Harness]:
    yield Harness(tmp_path, requested_actions=["inspect", "local_write"])


@pytest.fixture
def campaign() -> Any:
    return _campaign_module()


# ---------------------------------------------------------------------------
# The positive path. Everything below is measured against it: if the authorized
# write did not actually work, the denials prove nothing.
# ---------------------------------------------------------------------------


def test_a_mediated_write_is_authorized_and_covered(harness: Harness, campaign: Any) -> None:
    baseline = campaign.worktree_effect_baseline(harness.worktree)
    harness.mediated_write()
    changed = campaign.provider_effected_paths(harness.worktree, baseline)
    assert WRITABLE in changed
    assert campaign._require_mediated_effects(harness.unit(baseline), trace=None) == changed


def test_the_effect_decision_is_recorded_under_this_lease(harness: Harness) -> None:
    harness.mediated_write()
    decisions = harness.grants.lease_decisions(
        harness.grant,
        capability="repository.write_scoped",
        phase=harness.grants.AUTHORIZATION_PHASE_EFFECT,
    )
    assert [row["resource"] for row in decisions] == [WRITABLE]


# ---------------------------------------------------------------------------
# Session authority and identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dropped",
    [
        "L9_ADAPTER_SESSION_ID",
        "L9_LEASE_ID",
        "L9_AGENT_ID",
        "L9_AUTONOMY_DATABASE",
        "L9_AUTONOMY_ROOT",
        "L9_PROGRAM_WORKSPACE",
        "L9_PROGRAM_TASK_ID",
    ],
)
def test_incomplete_session_authority_blocks(harness: Harness, dropped: str) -> None:
    environment = harness.worker_environment()
    environment[dropped] = ""
    code, replayed = harness.tool_call(
        harness.write_event(str(harness.worktree / WRITABLE)),
        environment=environment,
    )
    assert code == 2
    assert replayed == b"", "a window without authority must not reach the ops gate"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("L9_ADAPTER_SESSION_ID", "adapter-session-forged"),
        ("L9_LEASE_ID", "lease-forged"),
        ("L9_AGENT_ID", "agent-forged"),
        ("L9_PROGRAM_TASK_ID", "TASK-SOMEONE-ELSE"),
    ],
)
def test_forged_identity_blocks(harness: Harness, field: str, value: str) -> None:
    environment = harness.worker_environment()
    environment[field] = value
    code, replayed = harness.tool_call(
        harness.write_event(str(harness.worktree / WRITABLE)),
        environment=environment,
    )
    assert code == 2
    assert replayed == b""


def test_a_mutating_window_without_authority_is_refused_by_the_provider(
    harness: Harness,
) -> None:
    """The export itself fails closed, before any window is ever launched."""
    provider_module = _provider_module()
    provider = provider_module.ClaudeCodeProvider(harness.workspace, _REPO_ROOT)
    request = harness._execution_request().model_copy(update={"autonomy_authority": None})
    with pytest.raises(ValueError, match="MUTATING_WINDOW_WITHOUT_ROOT_AUTHORITY"):
        provider._authority_environment(request)


# ---------------------------------------------------------------------------
# The Program parent
# ---------------------------------------------------------------------------


def test_expired_program_parent_blocks(harness: Harness) -> None:
    connection = harness.program_state()
    try:
        connection.execute(
            "UPDATE leases SET expires_at=? WHERE lease_id=?",
            ("2000-01-01T00:00:00Z", PROGRAM_LEASE_ID),
        )
        connection.commit()
    finally:
        connection.close()
    code, replayed = harness.tool_call(harness.write_event(str(harness.worktree / WRITABLE)))
    assert code == 2
    assert replayed == b""


def test_revoked_program_parent_blocks(harness: Harness) -> None:
    connection = harness.program_state()
    try:
        connection.execute("UPDATE leases SET active=0 WHERE lease_id=?", (PROGRAM_LEASE_ID,))
        connection.commit()
    finally:
        connection.close()
    code, replayed = harness.tool_call(harness.write_event(str(harness.worktree / WRITABLE)))
    assert code == 2
    assert replayed == b""


def test_stale_actual_worktree_head_blocks(harness: Harness) -> None:
    """The heartbeat is taken against the worktree's real HEAD, not a claim."""
    (harness.worktree / "drift.txt").write_text("drift\n", encoding="utf-8")
    _git(harness.worktree, "add", "drift.txt")
    _git(harness.worktree, "commit", "-m", "drift")
    code, replayed = harness.tool_call(harness.write_event(str(harness.worktree / WRITABLE)))
    assert code == 2
    assert replayed == b""


# ---------------------------------------------------------------------------
# Resource escapes and operation grammar
# ---------------------------------------------------------------------------


def test_absolute_and_traversal_escapes_block(harness: Harness) -> None:
    for path in (
        str(harness.root / "outside.txt"),
        "../../outside.txt",
        "/etc/passwd",
    ):
        code, replayed = harness.tool_call(harness.write_event(path))
        assert code == 2, path
        assert replayed == b"", path


def test_symlinked_parent_escape_blocks(harness: Harness) -> None:
    outside = harness.root / "outside"
    outside.mkdir()
    (harness.worktree / "docs").symlink_to(outside, target_is_directory=True)
    code, replayed = harness.tool_call(harness.write_event(WRITABLE))
    assert code == 2
    assert replayed == b""


def test_non_canonical_shell_grammar_blocks(harness: Harness) -> None:
    for command in (
        "git push origin HEAD",
        'python3 -c "import os"',
        "rm -rf / && echo done",
        "echo $(cat /etc/passwd)",
        "",
    ):
        code, replayed = harness.tool_call(
            {"tool_name": "Bash", "tool_input": {"command": command}}
        )
        assert code == 2, command
        assert replayed == b"", command


def test_a_canonical_validation_command_is_admitted(harness: Harness) -> None:
    """The grammar is a filter, not a blanket refusal of every shell call."""
    code, replayed = harness.tool_call(
        {"tool_name": "Bash", "tool_input": {"command": "git status --short"}}
    )
    assert code == 0
    assert replayed


def test_a_nameless_effect_blocks(harness: Harness) -> None:
    code, replayed = harness.tool_call({"tool_input": {"file_path": WRITABLE}})
    assert code == 2
    assert replayed == b""


# ---------------------------------------------------------------------------
# Publication and capability inflation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name", ["git_push", "gh_pr_merge"])
def test_publication_attempts_block(harness: Harness, tool_name: str) -> None:
    code, replayed = harness.tool_call({"tool_name": tool_name, "tool_input": {"path": WRITABLE}})
    assert code == 2
    assert replayed == b""


def test_local_write_without_commit_never_inflates_into_commit(harness: Harness) -> None:
    """DG-001 at the effect edge, end to end.

    The task requested `local_write` and not `commit`, so the lease never
    accepted `git.commit_local` — and no amount of successful writing under it
    turns into commit authority.
    """
    assert harness.grant["authorized"] == ["repository.write_scoped"]
    harness.mediated_write()
    code, replayed = harness.tool_call(
        {"tool_name": "git_commit", "tool_input": {"path": WRITABLE}}
    )
    assert code == 2
    assert replayed == b""
    capabilities = {
        row["capability"]
        for row in harness.grants.lease_decisions(harness.grant, allowed_only=True)
    }
    assert "git.commit_local" not in capabilities


def test_a_commit_task_does_receive_commit_authority(tmp_path: Path) -> None:
    """The mirror image: narrowing is by requested action, not a blanket deny."""
    committer = Harness(tmp_path, requested_actions=["inspect", "local_write", "commit"])
    assert "git.commit_local" in committer.grant["authorized"]


# ---------------------------------------------------------------------------
# Mediation coverage: the campaign-side half
# ---------------------------------------------------------------------------


def test_a_direct_unmediated_write_is_not_a_program_attempt(
    harness: Harness, campaign: Any
) -> None:
    baseline = campaign.worktree_effect_baseline(harness.worktree)
    target = harness.worktree / WRITABLE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("written with no hook in the loop\n", encoding="utf-8")
    with pytest.raises(campaign.CampaignError, match="unmediated"):
        campaign._require_mediated_effects(harness.unit(baseline), trace=None)


def test_a_grant_probe_does_not_stand_in_for_effect_mediation(
    harness: Harness, campaign: Any
) -> None:
    """The defect PR-003 closes, stated as an assertion.

    `grant.py` probes `repository.write_scoped` against the task's first
    writable path while issuing the lease. That is a real allowed decision on
    the very path a rogue provider would target, so before the phase
    distinction it silently satisfied coverage for a write the gateway never
    saw.
    """
    grants = harness.grants
    assert WRITABLE in grants.authorized_resources(harness.grant)
    assert grants.authorized_resources(
        harness.grant, phase=grants.AUTHORIZATION_PHASE_GRANT_PROBE
    ) == {WRITABLE}
    assert (
        grants.authorized_resources(harness.grant, phase=grants.AUTHORIZATION_PHASE_EFFECT) == set()
    )
    assert grants.unmediated_changed_paths(harness.grant, [WRITABLE]) == [WRITABLE]

    harness.mediated_write()
    assert grants.unmediated_changed_paths(harness.grant, [WRITABLE]) == []


def test_coverage_counts_only_this_tasks_own_lease(tmp_path: Path, campaign: Any) -> None:
    """A sibling task's effect decision never vouches for this task's write."""
    first = Harness(tmp_path / "a", requested_actions=["inspect", "local_write"])
    second = Harness(tmp_path / "b", requested_actions=["inspect", "local_write"])
    first.mediated_write()
    assert first.grants.unmediated_changed_paths(second.grant, [WRITABLE]) == [WRITABLE]


def test_changes_without_any_grant_are_refused(harness: Harness, campaign: Any) -> None:
    baseline = campaign.worktree_effect_baseline(harness.worktree)
    target = harness.worktree / WRITABLE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ungranted\n", encoding="utf-8")
    unit = harness.unit(baseline)
    unit["grant"] = None
    with pytest.raises(campaign.CampaignError, match="no root autonomy grant"):
        campaign._require_mediated_effects(unit, trace=None)


# ---------------------------------------------------------------------------
# Terminal lifecycle
# ---------------------------------------------------------------------------


def test_a_successful_result_releases_the_lease_and_its_claims(harness: Harness) -> None:
    harness.mediated_write()
    submitted = harness.grants.submit_task_result(
        harness.grant,
        changed_files=[WRITABLE],
        candidate_sha=None,
        contract_digest="digest-e2e",
    )
    assert submitted["submitted"] is True
    assert submitted["lease_status"] != "ACTIVE"
    connection = harness.runtime_state()
    try:
        live_claims = connection.execute(
            "SELECT COUNT(*) FROM claims WHERE lease_id=? AND status='ACTIVE'",
            (harness.grant["lease_id"],),
        ).fetchone()[0]
    finally:
        connection.close()
    assert live_claims == 0, "a finished worker kept a live resource claim"


def test_a_released_lease_authorizes_nothing_further(harness: Harness) -> None:
    harness.mediated_write()
    released = harness.grants.release_task_grant(harness.grant, reason="ACTION_COMPLETED")
    assert released["released"] is True
    code, replayed = harness.tool_call(harness.write_event(str(harness.worktree / WRITABLE)))
    assert code == 2
    assert replayed == b""


def test_pec_rejection_invalidates_the_root_supporting_evidence(harness: Harness) -> None:
    """PEC owns the verdict; root autonomy owns only its own evidence.

    A rejected attempt must not leave a valid root ExecutionResult standing
    behind it.
    """
    harness.mediated_write()
    submitted = harness.grants.submit_task_result(
        harness.grant,
        changed_files=[WRITABLE],
        candidate_sha=None,
        contract_digest="digest-e2e",
    )
    artifact_id = submitted["artifact_id"]
    outcome = harness.grants.invalidate_task_support(
        harness.grant,
        artifact_id=artifact_id,
        reason="FAILED_LOCAL: controller rejected the attempt",
    )
    assert outcome["invalidated"] is True
    connection = harness.runtime_state()
    try:
        row = connection.execute(
            "SELECT status, invalidation_reason FROM artifacts WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row[0] == "INVALID"
    assert "FAILED_LOCAL" in str(row[1])


def test_root_autonomy_never_writes_program_state(harness: Harness) -> None:
    """Everything above ran, and canonical Program truth is untouched by it."""
    connection = harness.program_state()
    try:
        task = connection.execute(
            "SELECT runtime_state FROM tasks WHERE id=?", (TASK_ID,)
        ).fetchone()
        attempts = connection.execute(
            "SELECT COUNT(*) FROM attempts WHERE task_id=?", (TASK_ID,)
        ).fetchone()[0]
    finally:
        connection.close()
    harness.mediated_write()
    harness.grants.release_task_grant(harness.grant, reason="ACTION_COMPLETED")
    connection = harness.program_state()
    try:
        after = connection.execute(
            "SELECT runtime_state FROM tasks WHERE id=?", (TASK_ID,)
        ).fetchone()
        attempts_after = connection.execute(
            "SELECT COUNT(*) FROM attempts WHERE task_id=?", (TASK_ID,)
        ).fetchone()[0]
    finally:
        connection.close()
    assert after[0] == task[0]
    assert attempts_after == attempts == 0


def test_coverage_refuses_to_run_without_a_named_phase(harness: Harness) -> None:
    """`phase=None` would mean "count any decision" — the hole itself."""
    with pytest.raises(harness.grants.AutonomyGrantError, match="COVERAGE_PHASE_REQUIRED"):
        harness.grants.unmediated_changed_paths(harness.grant, [WRITABLE], phase="")
