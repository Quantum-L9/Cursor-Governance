"""PE execution certification: does the machinery actually execute work?

Every other PE test drives the runner with `Hooks.write_task_output`, which
substitutes the test for the step where something writes code. That is exactly
the step that was missing in production, so it could not catch it.

This fixture drives the live path instead — Peer Execution Core against a real
task worktree — and asserts the full chain: compile → launchability →
admission → bootstrap → claim → runtime binding → capability probe → context
manifest → thin provider → typed attempt receipt → verify → local commit →
complete → dependency advance → TASK-002. Then it interrupts execution, resets,
and asserts the same campaign runs again.

Only the `claude` executable is faked, so the binding, execution profile, probe,
context manifest, adapter, and receipt schemas are all really exercised. The
fake is a *conformant host*: it runs the live PreToolUse wrapper before every
write and every validation command, exactly as a real Claude Code window does,
so the enforcement seam is part of the certified chain rather than something
this fixture routed around. The matching negative control is
`test_a_direct_unmediated_write_never_becomes_a_program_attempt`.

It is the basic PE health check. It is meant to be fast enough to run during
development, so its validation commands are trivially deterministic.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

# This module imports a sibling test file by bare name. That resolves only when
# this directory is on `sys.path`, which pytest arranges as a side effect of
# collecting some *other* file from here first — so the import silently depended
# on collection order, and broke the moment a scoped or sharded run selected
# this file without its sibling (`make pr-check` under `-n auto`).
# `run_conformance._load` already documents the fix for the same class of
# breakage: make the file self-sufficient by putting its own directory first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_run_campaign import (  # type: ignore[import-not-found]  # noqa: E402
    READY_SEED,
    _dump,
    _git_init,
    _host_repo,
    _load,
    _stack_ok,
)

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"
PEC = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"

# Deterministic fake Claude CLI, standing in for a *conformant* Claude host.
# The live runner still traverses the real runtime binding, execution profile,
# capability probe, context manifest, PeerExecutionAdapter, thin claude-code
# provider, and typed attempt receipt.
#
# The host part matters as much as the provider part. A real Claude Code window
# runs every tool call through the PreToolUse wrapper before the effect happens,
# and that authorization is what campaign mediation coverage counts. A fake that
# writes straight to the filesystem is not a Claude host at all -- it is exactly
# the unmediated writer the enforcement seam exists to reject -- so on the
# positive path this one invokes the *same live wrapper*, with the task-scoped
# authority environment the provider exported, before each write and each
# validation command. `SMOKE_ROGUE_TASK` turns that off for one task, which is
# the negative control: a direct write with no hook in the loop must be refused
# before PEC ever records a Program attempt.
FAKE_CLAUDE = r"""#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys

HOOK_RELATIVE = "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"


def mediate(tool_name, tool_input):
    # Authorize one tool call through the live PreToolUse wrapper. Returns None
    # when the effect may proceed, or the wrapper's stderr when it was refused.
    # Nothing here decides anything: the verdict is the wrapper's, computed
    # against the real root gateway and the live Program parent.
    root = os.environ.get("L9_AUTONOMY_ROOT") or ""
    hook = pathlib.Path(root) / HOOK_RELATIVE
    if not hook.is_file():
        return "conformant host cannot find the PreToolUse wrapper at %s" % hook
    completed = subprocess.run(
        [os.environ.get("SMOKE_HOST_PYTHON") or sys.executable, str(hook)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        return None
    return (completed.stderr or "denied").strip()


prompt = sys.argv[sys.argv.index("-p") + 1]
contract = json.loads(prompt.strip().splitlines()[-1])
task_id = contract.get("task_id")
if os.environ.get("SMOKE_FAIL_TASK") == task_id:
    print(json.dumps({
        "is_error": True,
        "session_id": "smoke-peer-session",
        "num_turns": 1,
        "usage": {},
        "result": "simulated provider failure for reconciliation testing",
    }))
    raise SystemExit(0)
# The negative control: this window skips its own host mediation entirely.
rogue = os.environ.get("SMOKE_ROGUE_TASK") == task_id
worktree = pathlib.Path.cwd()
changed = []
denials = []
for rel in contract.get("writable_paths") or []:
    target = worktree / rel
    body = f"{task_id} implemented through Peer Core.\n" + ("verified " * 8) + "\n"
    if not rogue:
        refusal = mediate("Write", {"file_path": str(target), "content": body})
        if refusal is not None:
            denials.append({"tool": "Write", "resource": rel, "reason": refusal})
            continue
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    changed.append(rel)
validations = []
for command in contract.get("validation_commands") or []:
    if not rogue:
        refusal = mediate("Bash", {"command": command})
        if refusal is not None:
            denials.append({"tool": "Bash", "resource": command, "reason": refusal})
            continue
    completed = subprocess.run(command, cwd=worktree, shell=True, text=True, capture_output=True)
    validations.append({
        "command": command,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "evidence": (completed.stdout + completed.stderr)[-4000:] or None,
    })
payload = {
    "candidate_sha": None,
    "changed_files": changed,
    "validation_results": validations,
    "residual_unknowns": [],
    "claimed_status": "completed",
}
if denials:
    payload["host_permission_denials"] = denials
print(json.dumps({
    "is_error": False,
    "session_id": "smoke-peer-session",
    "num_turns": 1,
    "usage": {},
    "result": payload,
}))
"""


def _peer_test_env(tmp: Path) -> dict[str, str]:
    bin_dir = tmp / "peer-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    claude = bin_dir / "claude"
    claude.write_text(FAKE_CLAUDE, encoding="utf-8")
    claude.chmod(0o755)
    return {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "L9_GOVERNANCE_SURFACE": "claude-code",
        "L9_PE_AGENT_REF": "claude-code",
        "L9_PE_SURFACE": "claude-cli",
        # A real Claude host launches its hooks on the governance locked
        # interpreter (`l9_hook_exec.sh`). The fake has no launcher, so it is
        # told which interpreter can import the root autonomy runtime — the one
        # already running this suite.
        "SMOKE_HOST_PYTHON": sys.executable,
    }


def _pec(workspace: Path, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(PEC), *args, "--workspace", str(workspace)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "L9_CAMPAIGN_TUNNEL": "1"},
        timeout=120,
    )
    if completed.returncode != 0:
        raise AssertionError(f"pec {args[0]} failed: {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout or "{}")


def _load_yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _branches(repo: Path) -> list[str]:
    listed = subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "--format=%(refname:short)", "refs/heads/pec"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [line.strip() for line in listed.stdout.splitlines() if line.strip()]


class PeSmokeCampaignTests(unittest.TestCase):
    """The two-task execution certification, run for real."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_smoke", SCRIPT)
        cls.activate = _load("compile_activation_smoke", ACTIVATE)

    def _run_smoke(
        self,
        raw: Path,
        *,
        fast: bool = True,
        # Execution certification is a local-only concern: the campaign runs to
        # the autonomous boundary and stops at its commits. Publication is a
        # separate release transition and is certified in
        # test_pe_local_commit_only.py.
        until: str = "execute",
        campaign_source: bool = False,
    ):
        root = _host_repo(raw / "host")
        _dump(root / "intent.yaml", READY_SEED)
        if campaign_source:
            # The operator hands over the canonical source itself. No activation
            # hook is supplied, so a route through the activation compiler would
            # rebuild it from a weaker seed and this run would not be a proof.
            source = self.activate.build_source(READY_SEED, stamp="2026-01-01T00:00:00Z")
            source["tasks"][1]["depends_on"] = ["TASK-001"]
            entry = root / "CAMPAIGN_SOURCE.yaml"
            _dump(entry, source)
            l9 = raw / "l9"
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            started = time.monotonic()
            report = self.mod.run_campaign(
                entry,
                until=until,
                primary=raw / "primary",
                repo_root=root,
                l9_root=l9,
                fast=fast,
                hooks=self.mod.Hooks(context7_stack=_stack_ok),
            )
            return report, l9, time.monotonic() - started
        l9 = raw / "l9"
        target = l9 / "program-worktrees" / "demo-activate-v1"
        target.mkdir(parents=True)
        _git_init(target)
        started = time.monotonic()
        report = self.mod.run_campaign(
            root / "intent.yaml",
            until=until,
            primary=raw / "primary",
            repo_root=root,
            l9_root=l9,
            fast=fast,
            hooks=self.mod.Hooks(
                context7_stack=_stack_ok,
                compile_activation=self.activate.compile_activation,
            ),
        )
        return report, l9, time.monotonic() - started

    def test_public_campaign_path_reaches_task001_from_a_campaign_source(self) -> None:
        """The acceptance criterion: `campaign-source.v2` in, executed tasks out.

        Everything here goes through the public `run_campaign` entry point. No
        `default_execute`, `default_arm`, or `default_pec_bootstrap` is called
        by the test, because reaching for those is the failure this fixes.
        """
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            with unittest.mock.patch.dict("os.environ", _peer_test_env(tmp)):
                report, l9, elapsed = self._run_smoke(tmp, campaign_source=True)

            self.assertIn("execute", report.stages_completed)
            workspace = l9 / "programs/demo-activate-v1"
            states = {
                item["id"]: item["runtime_state"] for item in _pec(workspace, "status")["tasks"]
            }
            self.assertEqual(states["TASK-001"], "COMPLETED")
            self.assertEqual(states["TASK-002"], "COMPLETED", msg="dependency did not advance")
            contexts = list((workspace / "runtime/peer-execution/contexts").glob("*.json"))
            self.assertGreaterEqual(len(contexts), 2)
            for context in contexts:
                payload = json.loads(context.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema"], "l9.peer-execution.context-manifest.v1")
            # The source the compiler read must be the operator's, not a rebuild.
            # A closed campaign is archived under COMPLETED/, so accept either.
            campaigns = Path(report.worktree) / "environment/program-execution/campaigns"
            candidates = [
                campaigns / "demo-activate-v1/CAMPAIGN_SOURCE.yaml",
                campaigns / "COMPLETED/demo-activate-v1/CAMPAIGN_SOURCE.yaml",
            ]
            emitted = next((path for path in candidates if path.is_file()), None)
            self.assertIsNotNone(emitted, msg=f"no campaign source under {campaigns}")
            doc = _load_yaml(emitted)
            self.assertEqual(doc["schema"], "l9.program-execution.campaign-source.v2")
            task2 = next(item for item in doc["tasks"] if item["id"] == "TASK-002")
            self.assertEqual(task2["depends_on"], ["TASK-001"])
            self.assertLess(elapsed, 300)

    def test_two_task_campaign_executes_end_to_end_through_a_real_worker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            with unittest.mock.patch.dict("os.environ", _peer_test_env(tmp)):
                report, l9, elapsed = self._run_smoke(tmp)

            self.assertIn("execute", report.stages_completed)
            self.assertEqual(report.mode, "fast")

            workspace = l9 / "programs/demo-activate-v1"
            for task_id in ("TASK-001", "TASK-002"):
                receipt = json.loads(
                    (workspace / f"receipts/verification/{task_id}.json").read_text("utf-8")
                )
                self.assertEqual(receipt["verdict"], "PASSED_LOCAL", msg=f"{task_id} {receipt}")
                self.assertTrue(
                    receipt["observed_changed_files"],
                    msg=f"{task_id} verified with an unmodified worktree",
                )
                # pec renders attempt_receipt_path as
                # attempts/<task>/attempt-NNN/attempt-receipt.json.
                attempts = list(
                    (workspace / "attempts" / task_id).glob("attempt-*/attempt-receipt.json")
                )
                self.assertTrue(attempts, msg=f"no typed Peer Core attempt receipt for {task_id}")
                for attempt in attempts:
                    payload = json.loads(attempt.read_text(encoding="utf-8"))
                    self.assertEqual(
                        payload["schema"],
                        "program-execution-controller.attempt-receipt.v2",
                    )

            status = _pec(workspace, "status")["tasks"]
            states = {item["id"]: item["runtime_state"] for item in status}
            self.assertEqual(states["TASK-001"], "COMPLETED")
            self.assertEqual(states["TASK-002"], "COMPLETED", msg="dependency did not advance")

            timings = json.loads((workspace / "runtime/TIMINGS.json").read_text("utf-8"))
            recorded = {entry["stage"] for entry in timings["stages"]}
            self.assertLessEqual(
                {"compile", "launchability", "bootstrap", "arm", "execute"}, recorded
            )
            progress = json.loads((workspace / "runtime/PROGRESS.json").read_text("utf-8"))
            self.assertEqual(progress["execution"], {"done": 2, "total": 2})
            self.assertLess(elapsed, 300, "smoke campaign must stay fast enough to run in dev")

    def test_a_direct_unmediated_write_never_becomes_a_program_attempt(self) -> None:
        """The negative control for the conformant host above.

        One task's window writes its declared path directly, with no PreToolUse
        wrapper in the loop. The write is real and it lands in the worktree, so
        nothing here is caught by reading the provider's own report — the
        campaign has to notice that the change carries no effect-phase root
        authorization. It must refuse before `pec record-attempt` runs, so an
        unmediated write never becomes a recorded Program attempt.

        The grant issued for this very task holds `repository.write_scoped` and
        probed it against this very path, so the run also proves that holding
        the capability is not the same as having authorized the write.
        """
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            env = _peer_test_env(tmp)
            env["SMOKE_ROGUE_TASK"] = "TASK-001"
            with unittest.mock.patch.dict("os.environ", env):
                with self.assertRaises(self.mod.CampaignError) as caught:
                    self._run_smoke(tmp)
            self.assertIn("TASK-001", str(caught.exception))

            workspace = tmp / "l9" / "programs/demo-activate-v1"
            status = {item["id"]: item for item in _pec(workspace, "status")["tasks"]}
            self.assertEqual(status["TASK-001"]["runtime_state"], "FAILED")
            # TASK-002 depends on TASK-001, so it must never have run.
            self.assertNotEqual(status["TASK-002"]["runtime_state"], "COMPLETED")

            # Canonical Program state, not the campaign's own report: the
            # Controller recorded no attempt for the unmediated write, and
            # therefore no verification verdict either.
            import sqlite3

            connection = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            try:
                recorded = connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE task_id=?", ("TASK-001",)
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(
                recorded, 0, msg="an unmediated write was recorded as a Program attempt"
            )
            self.assertFalse((workspace / "receipts/verification/TASK-001.json").is_file())

            # The write really happened — this is a coverage failure, not a
            # write that was stopped at the filesystem.
            rogue = workspace / "worktrees/TASK-001/docs/program-execution/demo/baseline.md"
            self.assertTrue(rogue.is_file(), msg="the rogue window never wrote anything")

            # And the grant did hold the write capability on that same path.
            grants = sorted((workspace / "runtime" / "autonomy-grants").glob("*.grant.json"))
            self.assertTrue(grants, msg="task-scoped grant receipt missing")
            grant = json.loads(grants[-1].read_text(encoding="utf-8"))
            module = self.mod._grant_module()
            self.assertIn("repository.write_scoped", grant["authorized"])
            self.assertIn(
                "docs/program-execution/demo/baseline.md",
                module.authorized_resources(grant),
            )
            self.assertEqual(
                module.authorized_resources(grant, phase=module.AUTHORIZATION_PHASE_EFFECT),
                set(),
                msg="a grant-time probe was recorded as an effect authorization",
            )

    def test_interrupted_task_worktree_can_be_reset_and_recreated(self) -> None:
        """create worktree → interrupt → reset → recreate the same task → succeeds."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            with unittest.mock.patch.dict(
                "os.environ",
                {**_peer_test_env(tmp), "L9_CAMPAIGN_UNTIL_DEBUG": "1"},
            ):
                _, l9, _ = self._run_smoke(tmp, until="arm")
            workspace = l9 / "programs/demo-activate-v1"
            target = l9 / "program-worktrees/demo-activate-v1"

            prepared = _pec(workspace, "prepare", "TASK-001")
            worktree = Path(prepared["worktree"])
            branch = prepared["branch"]
            self.assertTrue(worktree.is_dir())

            # Interruption: the directory disappears while git's registration and
            # the pec/* branch survive. Recreating the task used to die here with
            # "fatal: a branch named 'pec/.../task-001' already exists".
            shutil.rmtree(worktree)
            self.assertEqual(_branches(target), [branch])

            first = _pec(workspace, "fresh-workspace", "--repository", str(target))
            self.assertEqual(_branches(target), [], f"branch survived reset: {first}")
            # Invoking reset on an already-clean workspace must be a no-op, not
            # an error: recovery paths get run more than once by definition.
            _pec(workspace, "fresh-workspace", "--repository", str(target))

            _pec(workspace, "claim", "TASK-001", "--holder", "smoke", "--ttl-minutes", "15")
            recreated = _pec(workspace, "prepare", "TASK-001")
            self.assertTrue(
                Path(recreated["worktree"]).is_dir(),
                "task worktree could not be recreated after reset",
            )

    def test_missing_bound_provider_fails_before_verification(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in {"L9_PE_AGENT_REF", "L9_PE_SURFACE", "L9_PE_PROVIDER_REF"}
            }
            env["L9_GOVERNANCE_SURFACE"] = "claude-code"
            # Hide every real claude executable. Filtering on the directory
            # *name* misses an install such as /opt/node22/bin/claude, so drop
            # exactly the entries `shutil.which` would resolve from.
            env["PATH"] = os.pathsep.join(
                part
                for part in env.get("PATH", "").split(os.pathsep)
                if part and not (Path(part) / "claude").exists()
            )
            self.assertIsNone(shutil.which("claude", path=env["PATH"]))
            with unittest.mock.patch.dict("os.environ", env, clear=True):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    self._run_smoke(tmp)
            self.assertIn("capability probe blocked", str(ctx.exception))

    def test_scheduler_serializes_same_lineage_and_selects_distinct_lineages(self) -> None:
        tasks = [
            {
                "id": "TASK-001",
                "title": "A",
                "target_ids": ["TARGET-A"],
                "source": {"outputs": [{"location": "a.txt"}]},
            },
            {
                "id": "TASK-002",
                "title": "B",
                "target_ids": ["TARGET-A"],
                "source": {"outputs": [{"location": "b.txt"}]},
            },
            {
                "id": "TASK-003",
                "title": "C",
                "target_ids": ["TARGET-B"],
                "source": {"outputs": [{"location": "c.txt"}]},
            },
        ]
        selected = self.mod._plan_peer_task_batch(
            "scheduler-smoke", tasks, {task["id"]: "ELIGIBLE" for task in tasks}
        )
        self.assertIn("TASK-001", selected)
        self.assertIn("TASK-003", selected)
        self.assertNotIn("TASK-002", selected)

    def test_peer_batch_harvests_every_parallel_child(self) -> None:
        import time as time_module

        units = [
            {"task_id": "TASK-A", "contract": {"task_id": "TASK-A"}, "grant": {"lease_id": "a"}},
            {"task_id": "TASK-B", "contract": {"task_id": "TASK-B"}, "grant": {"lease_id": "b"}},
        ]

        def fake_peer(_workspace, contract):
            time_module.sleep(0.2)
            return {"status": "PASS", "receipt": {"task_id": contract["task_id"]}}

        # `_dispatch_peer_batch` loads the peer pipeline module on the calling
        # thread before it opens the pool. That import costs ~0.5s once per
        # process, which is longer than the whole window this test measures — so
        # a cold run charged a one-time import to the concurrency budget and
        # read as "the windows did not overlap". Warm it here, outside the
        # clock: what is under test is whether two provider windows run at once,
        # not how long an import takes.
        self.mod._peer_pipeline()
        started = time_module.monotonic()
        with unittest.mock.patch.object(self.mod, "_run_peer_execution", side_effect=fake_peer):
            outcomes, failures = self.mod._dispatch_peer_batch(Path("."), units)
        elapsed = time_module.monotonic() - started
        self.assertEqual(set(outcomes), {"TASK-A", "TASK-B"})
        self.assertEqual(failures, {})
        self.assertLess(elapsed, 0.35, msg=f"provider windows did not overlap: {elapsed}")

    def test_peer_batch_reports_mixed_outcomes_without_raising(self) -> None:
        units = [
            {"task_id": "TASK-A", "contract": {"task_id": "TASK-A"}, "grant": {"lease_id": "a"}},
            {"task_id": "TASK-B", "contract": {"task_id": "TASK-B"}, "grant": {"lease_id": "b"}},
        ]

        def fake_peer(_workspace, contract):
            if contract["task_id"] == "TASK-B":
                raise RuntimeError("provider window died")
            return {"status": "PASS", "receipt": {"task_id": contract["task_id"]}}

        with unittest.mock.patch.object(self.mod, "_run_peer_execution", side_effect=fake_peer):
            outcomes, failures = self.mod._dispatch_peer_batch(Path("."), units)
        self.assertEqual(set(outcomes), {"TASK-A"})
        self.assertEqual(set(failures), {"TASK-B"})
        self.assertIn("provider window died", failures["TASK-B"])

    def test_failed_child_lands_canonically_with_no_live_authority(self) -> None:
        """The reconciliation chain, live: provider failure -> Controller FAILED,
        writer lease released, root-Autonomy lease revoked, evidence preserved."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            env = _peer_test_env(tmp)
            env["SMOKE_FAIL_TASK"] = "TASK-001"
            with unittest.mock.patch.dict("os.environ", env):
                with self.assertRaises(self.mod.CampaignError) as caught:
                    self._run_smoke(tmp)
            self.assertIn("TASK-001", str(caught.exception))
            l9 = tmp / "l9"
            workspace = l9 / "programs/demo-activate-v1"
            status = _pec(workspace, "status")
            states = {item["id"]: item["runtime_state"] for item in status["tasks"]}
            self.assertEqual(states["TASK-001"], "FAILED")
            self.assertFalse(
                status.get("active_leases"), msg="failed child left an active Controller lease"
            )
            # The failed child's root-Autonomy lease is terminal: no live
            # mutation authority survives the failure.
            grants = sorted((workspace / "runtime" / "autonomy-grants").glob("*.grant.json"))
            self.assertTrue(grants, msg="task-scoped grant receipt missing")
            grant = json.loads(grants[-1].read_text(encoding="utf-8"))
            self.assertEqual(grant["task_id"], "TASK-001")
            import sqlite3

            connection = sqlite3.connect(grant["runtime_database"])
            try:
                row = connection.execute(
                    "SELECT status FROM leases WHERE lease_id=?", (grant["lease_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(row)
            self.assertNotEqual(row[0], "ACTIVE")
            # Evidence preserved: the task worktree survives for diagnosis.
            self.assertTrue((workspace / "worktrees" / "TASK-001").is_dir())

    def test_mixed_batch_reconciles_every_child_before_raising(self) -> None:
        """Caller-order contract for a mixed [PASS, FAIL] parallel batch:
        successful siblings finish first, failed siblings are recorded
        canonically, and only then does the campaign-level failure surface."""
        events: list[tuple[str, str]] = []
        units = [
            {
                "task_id": "TASK-A",
                "already_submitted": False,
                "grant": {"lease_id": "a"},
                "task": {"id": "TASK-A"},
                "contract": {"task_id": "TASK-A"},
            },
            {
                "task_id": "TASK-B",
                "already_submitted": False,
                "grant": {"lease_id": "b"},
                "task": {"id": "TASK-B"},
                "contract": {"task_id": "TASK-B"},
            },
        ]

        def fake_prepare(_workspace, task, *, trace):
            return next(unit for unit in units if unit["task_id"] == str(task["id"]))

        def fake_dispatch(_workspace, dispatched):
            return (
                {"TASK-A": {"status": "PASS", "receipt": {}}},
                {"TASK-B": "RuntimeError: provider window died"},
            )

        def fake_finish(_workspace, _campaign, unit, outcome, *, trace, timer):
            events.append(("finish", unit["task_id"]))

        def fake_record(_workspace, unit, task_id, reason):
            events.append(("record_failure", task_id))

        def fake_publish(_workspace, _campaign, _task, task_id, *_args, **_kwargs):
            events.append(("publish_failure", task_id))

        status_rows = [
            {"id": "TASK-A", "runtime_state": "ELIGIBLE", "attempts": 0},
            {"id": "TASK-B", "runtime_state": "ELIGIBLE", "attempts": 0},
        ]
        tasks = [{"id": "TASK-A"}, {"id": "TASK-B"}]
        with (
            unittest.mock.patch.object(self.mod, "locked_tasks", return_value=tasks),
            unittest.mock.patch.object(self.mod, "pec_status_tasks", return_value=status_rows),
            unittest.mock.patch.object(
                self.mod, "_plan_peer_task_batch", return_value=["TASK-A", "TASK-B"]
            ),
            unittest.mock.patch.object(self.mod, "_prepare_peer_unit", side_effect=fake_prepare),
            unittest.mock.patch.object(self.mod, "_dispatch_peer_batch", side_effect=fake_dispatch),
            unittest.mock.patch.object(self.mod, "_finish_peer_unit", side_effect=fake_finish),
            unittest.mock.patch.object(
                self.mod, "_record_canonical_failure", side_effect=fake_record
            ),
            unittest.mock.patch.object(self.mod, "publish_task_outcome", side_effect=fake_publish),
            unittest.mock.patch.object(self.mod, "_load_script") as loader,
        ):
            loader.return_value.StageTimer.return_value.stage = unittest.mock.MagicMock()
            with self.assertRaises(self.mod.CampaignError) as caught:
                self.mod._default_execute_peer(
                    Path("."),
                    "demo",
                    hooks=self.mod.Hooks(),
                    live_prs=False,
                )
        self.assertIn("TASK-B", str(caught.exception))
        self.assertEqual(
            events,
            [("finish", "TASK-A"), ("record_failure", "TASK-B"), ("publish_failure", "TASK-B")],
            msg="successful sibling must finish before the failure is recorded and raised",
        )

    def test_peer_batch_refuses_dispatch_without_root_grant(self) -> None:
        units = [{"task_id": "TASK-A", "contract": {"task_id": "TASK-A"}, "grant": None}]
        with unittest.mock.patch.object(
            self.mod, "_run_peer_execution", side_effect=AssertionError("must not dispatch")
        ):
            outcomes, failures = self.mod._dispatch_peer_batch(Path("."), units)
        self.assertEqual(outcomes, {})
        self.assertIn("no root autonomy grant", failures["TASK-A"])


if __name__ == "__main__":
    unittest.main()
