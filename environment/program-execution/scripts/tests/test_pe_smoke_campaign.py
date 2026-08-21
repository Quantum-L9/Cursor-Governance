"""PE execution certification: does the machinery actually execute work?

Every other PE test drives the runner with `Hooks.write_task_output`, which
substitutes the test for the step where something writes code. That is exactly
the step that was missing in production, so it could not catch it.

This fixture runs a real worker process against a real task worktree and
asserts the full chain: compile → launchability → admission → bootstrap →
claim → worker handoff → modification → validation → verify → complete →
dependency advance → TASK-002. Then it interrupts execution, resets, and
asserts the same campaign runs again.

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

from test_run_campaign import (  # type: ignore[import-not-found]
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

# A worker is any command that edits the worktree and exits 0. This one writes
# the brief's declared output, which is the smallest thing a real worker does.
SMOKE_WORKER = """#!/usr/bin/env python3
import os, pathlib, json
contract = json.loads(os.environ["L9_PE_CONTRACT"])
worktree = pathlib.Path(os.environ["L9_PE_WORKTREE"])
task_id = os.environ["L9_PE_TASK_ID"]
for rel in contract.get("writable_paths") or []:
    target = worktree / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"{task_id} implemented by the smoke worker.\\n" + ("verified " * 8) + "\\n",
        encoding="utf-8",
    )
"""


def _worker_command(tmp: Path) -> str:
    script = tmp / "smoke_worker.py"
    script.write_text(SMOKE_WORKER, encoding="utf-8")
    script.chmod(0o755)
    return f"{sys.executable} {script}"


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
            with unittest.mock.patch.dict("os.environ", {"L9_PE_WORKER_CMD": _worker_command(tmp)}):
                report, l9, elapsed = self._run_smoke(tmp, campaign_source=True)

            self.assertIn("execute", report.stages_completed)
            workspace = l9 / "programs/demo-activate-v1"
            states = {
                item["id"]: item["runtime_state"] for item in _pec(workspace, "status")["tasks"]
            }
            self.assertEqual(states["TASK-001"], "COMPLETED")
            self.assertEqual(states["TASK-002"], "COMPLETED", msg="dependency did not advance")
            for task_id in ("TASK-001", "TASK-002"):
                brief = workspace / "runtime/worker" / f"{task_id}.BRIEF.md"
                self.assertTrue(brief.is_file(), msg=f"{task_id} never reached a worker")
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
            with unittest.mock.patch.dict("os.environ", {"L9_PE_WORKER_CMD": _worker_command(tmp)}):
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
                brief = workspace / "runtime/worker" / f"{task_id}.BRIEF.md"
                self.assertTrue(brief.is_file(), msg=f"no worker brief rendered for {task_id}")

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

    def test_interrupted_task_worktree_can_be_reset_and_recreated(self) -> None:
        """create worktree → interrupt → reset → recreate the same task → succeeds."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            with unittest.mock.patch.dict(
                "os.environ",
                {"L9_PE_WORKER_CMD": _worker_command(tmp), "L9_CAMPAIGN_UNTIL_DEBUG": "1"},
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

    def test_implementation_task_without_a_worker_fails_before_verification(self) -> None:
        """Zero implementation must be an execution-path defect, not a PASS."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            env = {key: value for key, value in os.environ.items() if key != "L9_PE_WORKER_CMD"}
            with unittest.mock.patch.dict("os.environ", env, clear=True):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    self._run_smoke(tmp)
            message = str(ctx.exception)
            self.assertIn("cursor-foreground", message)
            self.assertIn("certify zero implementation", message)
            self.assertIn("L9_PE_WORKER_CMD", message)


if __name__ == "__main__":
    unittest.main()
