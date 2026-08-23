"""Autonomous Program Execution is local-commit-only.

Every other PE test replaces the remote actions with `Hooks`, so a regression
that swapped one remote action for another would go unnoticed: the hook absorbs
it either way. This fixture asserts on the *executed subprocesses* instead.

A PATH shim in front of `git`, `gh`, and `make` records every invocation made
during a real smoke campaign — by the runner and by every child process it
spawns, since PATH is inherited. The recording is the evidence:

    git commit:   YES
    git push:     NO
    gh pr create: NO
    make pr:      NO
    gh pr merge:  NO

The boundary is enforced in three places and each is covered here: the stage
machine (execution ends at `execute`), the `run_cmd` choke point (no campaign
subprocess reaches a remote), and the individual publication functions.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

# `run_conformance.py` loads this file by path under a synthetic module name, so
# the sibling test modules below are not importable by name unless their own
# directory is on sys.path. pytest inserts it automatically; conformance does not.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from test_pe_smoke_campaign import (  # type: ignore[import-not-found]  # noqa: E402
    _peer_test_env,
)
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

# Records argv, then hands off to the real binary so the campaign still works.
_RECORDING_SHIM = """#!/bin/sh
{{ printf '{name}'; for arg in "$@"; do printf ' %s' "$arg"; done; printf '\\n'; }} \
>> "$L9_TEST_SUBPROCESS_LOG"
exec {real} "$@"
"""

# `gh` and `make` must never run during autonomous execution. Recording and then
# failing turns a silent regression into a loud one without hiding the record.
_REFUSING_SHIM = """#!/bin/sh
{{ printf '{name}'; for arg in "$@"; do printf ' %s' "$arg"; done; printf '\\n'; }} \
>> "$L9_TEST_SUBPROCESS_LOG"
echo "{name} must not run during autonomous Program Execution" >&2
exit 97
"""


def _install_shims(bin_dir: Path) -> None:
    """Put recording wrappers for git/gh/make ahead of the real binaries."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    real_git = shutil.which("git")
    if not real_git:
        raise unittest.SkipTest("git is required to certify the commit path")
    (bin_dir / "git").write_text(
        _RECORDING_SHIM.format(name="git", real=real_git), encoding="utf-8"
    )
    for name in ("gh", "make"):
        (bin_dir / name).write_text(_REFUSING_SHIM.format(name=name), encoding="utf-8")
    for name in ("git", "gh", "make"):
        (bin_dir / name).chmod(0o755)


class SubprocessRecord:
    """The executed-subprocess log, queried the way the contract is written."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def ran(self, *tokens: str) -> bool:
        """True when some recorded command contains all tokens in order."""
        for line in self.lines:
            argv = line.split()
            index = 0
            for token in tokens:
                while index < len(argv) and argv[index] != token:
                    index += 1
                if index == len(argv):
                    break
                index += 1
            else:
                return True
        return False

    def matching(self, *tokens: str) -> list[str]:
        return [line for line in self.lines if all(token in line.split() for token in tokens)]


class LocalCommitOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_commit_only", SCRIPT)
        cls.activate = _load("compile_activation_commit_only", ACTIVATE)

    # ---- the mandatory regression: a real campaign, recorded ----------------

    def test_autonomous_smoke_campaign_commits_and_never_publishes(self) -> None:
        """Run a complete autonomous campaign; assert on what it actually ran."""
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = _host_repo(tmp / "host")
            _dump(root / "intent.yaml", READY_SEED)
            l9 = tmp / "l9"
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)

            log = tmp / "subprocesses.log"
            log.write_text("", encoding="utf-8")
            bin_dir = tmp / "shim-bin"
            _install_shims(bin_dir)

            env = {
                **_peer_test_env(tmp),
                "L9_TEST_SUBPROCESS_LOG": str(log),
                "PATH": f"{bin_dir}{os.pathsep}{_peer_test_env(tmp)['PATH']}",
            }
            # No release transition is open: this is a plain autonomous run.
            env.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with unittest.mock.patch.dict("os.environ", env):
                os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
                report = self.mod.run_campaign(
                    root / "intent.yaml",
                    primary=tmp / "primary",
                    repo_root=root,
                    l9_root=l9,
                    fast=True,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        compile_activation=self.activate.compile_activation,
                    ),
                )

            record = SubprocessRecord(
                [
                    line.strip()
                    for line in log.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            )

            # The campaign really executed — otherwise "no push" is vacuous.
            self.assertIn("execute", report.stages_completed)
            self.assertNotIn("pr", report.stages_completed)
            self.assertNotIn("close", report.stages_completed)
            self.assertTrue(
                record.lines, msg="no subprocess was recorded; shim did not take effect"
            )

            # git commit: YES
            self.assertTrue(
                record.ran("git", "commit"),
                msg=f"campaign made no local commit; recorded: {record.lines}",
            )
            # git push: NO
            self.assertFalse(
                record.ran("git", "push"),
                msg=f"campaign pushed: {record.matching('push')}",
            )
            # gh pr create / gh pr merge: NO (and gh never ran at all)
            self.assertFalse(
                record.ran("gh", "pr", "create"),
                msg=f"campaign opened a PR: {record.matching('gh')}",
            )
            self.assertFalse(
                record.ran("gh", "pr", "merge"),
                msg=f"campaign merged a PR: {record.matching('gh')}",
            )
            self.assertEqual(
                [line for line in record.lines if line.startswith("gh ")],
                [],
                msg="gh must not run during autonomous execution",
            )
            # make pr: NO
            self.assertFalse(
                record.ran("make", "pr"),
                msg=f"campaign invoked the publish path: {record.matching('make')}",
            )

    # ---- the choke point ----------------------------------------------------

    def test_publication_command_names_every_remote_action(self) -> None:
        classify = self.mod.publication_command
        self.assertIsNotNone(classify(["git", "-C", "/repo", "push", "-u", "origin", "main"]))
        self.assertIsNotNone(classify(["gh", "pr", "create", "--repo", "o/r"]))
        self.assertIsNotNone(classify(["gh", "pr", "merge", "7", "--squash"]))
        self.assertIsNotNone(classify(["gh", "pr", "edit", "7", "--body", "x"]))
        self.assertIsNotNone(classify(["gh", "api", "-X", "POST", "repos/o/r/pulls"]))
        self.assertIsNotNone(classify(["make", "pr"]))
        self.assertIsNotNone(classify(["make", "-C", "/repo", "PR_REMEDIATE=0", "pr"]))
        self.assertIsNotNone(classify(["python3", "/x/authorize_campaign_merge.py", "--pr", "7"]))
        # Local work and reads stay allowed.
        for allowed in (
            ["git", "-C", "/repo", "commit", "-m", "work"],
            ["git", "-C", "/repo", "add", "--", "file.py"],
            ["git", "-C", "/repo", "rev-parse", "HEAD"],
            ["gh", "pr", "view", "--json", "number"],
            ["gh", "pr", "checks", "7"],
            ["gh", "api", "repos/o/r/pulls"],
            ["make", "pr-check"],
            ["python3", "pec.py", "status"],
        ):
            self.assertIsNone(classify(allowed), msg=f"wrongly blocked: {allowed}")

    def test_run_cmd_refuses_a_publication_subprocess(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_cmd(["git", "-C", ".", "push", "origin", "main"], timeout=5)
            self.assertIn("local-commit-only", str(ctx.exception))

    def test_publication_functions_refuse_without_release(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            for call in (
                lambda: self.mod.push_integration_branch(Path("/tmp"), "demo-activate-v1"),
                lambda: self.mod.default_make_pr(Path("/tmp"), "demo-activate-v1"),
                lambda: self.mod.default_authorize_and_merge("o/r", 7),
            ):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    call()
                self.assertIn("local-commit-only", str(ctx.exception))

    # ---- the boundary -------------------------------------------------------

    def test_autonomous_default_stops_at_execute(self) -> None:
        import inspect

        signature = inspect.signature(self.mod.run_campaign)
        self.assertEqual(signature.parameters["until"].default, "execute")
        self.assertEqual(self.mod.AUTONOMOUS_LAST_STAGE, "execute")
        parsed = self.mod.build_parser().parse_args([])
        self.assertEqual(parsed.until, "execute")

    def test_publication_stage_requires_the_release_transition(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            self.mod.refuse_live_until_shortcut("execute")
            for stage in ("pr", "close", "merge"):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    self.mod.refuse_live_until_shortcut(stage)
                self.assertIn("local-commit-only", str(ctx.exception))

    def test_no_pre_execution_push_of_the_integration_branch(self) -> None:
        """The integration branch is never pushed to set work up."""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("push {campaign_id} integration branch before execute", source)
        self.assertIn("No pre-execution push", source)

    # ---- the release transition still works (authority preserved) -----------

    def test_release_transition_reopens_publication(self) -> None:
        """Publication is moved, not deleted: a governed release still runs it."""
        with unittest.mock.patch.dict(
            "os.environ", {"L9_PE_RELEASE_AUTHORIZED": "operator release"}
        ):
            self.assertTrue(self.mod.release_authorized())
            # No raise: the gate is open.
            self.mod.refuse_publication("push a branch")
            self.mod.refuse_live_until_shortcut("close")
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            self.assertFalse(self.mod.release_authorized())


class FastModeDoesNotWidenAuthorityTests(unittest.TestCase):
    """FAST mode buys speed. It must not buy authority.

    PE-FAST-002 relaxes preparation ceremony and grants acceptance from local
    evidence alone, which is exactly the shape of change that quietly widens what
    a campaign is allowed to do. The three transitions that leave this machine --
    publish, merge, deploy -- are asserted closed under FAST here, separately from
    the general local-commit-only fixture above, so a future relaxation of FAST
    cannot pass by only being tested in strict mode.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_fast_authority", SCRIPT)
        prepare_state = PE_ROOT / "scripts/pe_prepare_state.py"
        cls.prepare = _load("pe_prepare_state_fast_authority", prepare_state)

    def test_fast_does_not_open_the_publish_path(self) -> None:
        with unittest.mock.patch.dict("os.environ", {"L9_PE_FAST": "1"}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            for call in (
                lambda: self.mod.push_integration_branch(Path("/tmp"), "demo-activate-v1"),
                lambda: self.mod.default_make_pr(Path("/tmp"), "demo-activate-v1"),
            ):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    call()
                self.assertIn("local-commit-only", str(ctx.exception))

    def test_fast_does_not_open_the_merge_path(self) -> None:
        with unittest.mock.patch.dict("os.environ", {"L9_PE_FAST": "1"}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.default_authorize_and_merge("o/r", 7)
            self.assertIn("local-commit-only", str(ctx.exception))
            self.assertIsNotNone(
                self.mod.publication_command(["gh", "pr", "merge", "7", "--squash"])
            )

    def test_a_local_acceptance_is_never_authority_for_leaving_the_machine(self) -> None:
        """The record says so, and no publication path consults it."""
        with tempfile.TemporaryDirectory() as raw:
            path = self.prepare.record_local_acceptance(
                Path(raw) / "LOCAL_ACCEPTANCE.json",
                campaign_id="demo-activate-v1",
                revision="abc1234",
                compile_key="k" * 16,
                launchability={"launchable": True, "task_count": 2, "inferred": True},
            )
            record = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(record["authority"], "local_only")
        self.assertEqual(sorted(record["not_sufficient_for"]), ["deploy", "merge", "publish"])

        # A declaration inside the record is not a guarantee. What makes it true
        # is that nothing on the way out of this machine reads the record: the
        # publication functions, their shared refusal, and the merge gate.
        import inspect

        for function in (
            self.mod.push_integration_branch,
            self.mod.default_make_pr,
            self.mod.default_authorize_and_merge,
            self.mod.refuse_publication,
        ):
            self.assertNotIn(
                "LOCAL_ACCEPT",
                inspect.getsource(function),
                msg=f"{function.__name__} consults a local acceptance",
            )
        merge_gate = PE_ROOT.parents[1] / "ops/autonomy/merge_gate.py"
        if merge_gate.is_file():
            self.assertNotIn("LOCAL_ACCEPT", merge_gate.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
