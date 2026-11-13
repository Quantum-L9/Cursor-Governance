"""Program Execution publishes only through the governance SSOT `make pr`.

PROGRAM_EXECUTION_MAKE_PR_FINISH_V1. Every other PE test replaces the remote
actions with `Hooks`, so a regression that swapped one remote action for
another would go unnoticed: the hook absorbs it either way. This fixture
asserts on the *executed subprocesses* instead.

A PATH shim in front of `git`, `gh`, and `make` records every invocation made
during a real smoke campaign — by the runner and by every child process it
spawns, since PATH is inherited. The recording is the evidence.

Stopped at `execute` (local only):

    git commit:   YES      git push: NO      gh: NO      make: NO

Finished at `pr` (the campaign finish):

    make -C <SSOT> pr WS=<integration worktree>, PR_REMEDIATE=0:  exactly once
    git push / gh pr create / gh pr merge by PE itself:            NO

The push, PR template and composer belong to that `make pr`; here a stand-in
SSOT records the call instead of performing it. The boundary is enforced in
three places and each is covered: the stage machine (nothing runs past `pr`),
the `run_cmd` choke point (no campaign subprocess publishes), and
campaign_publish (the one sanctioned argv).
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
    _projection_ok,
    _stack_ok,
)

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = (
    PE_ROOT.parents[1]
    / "skills/_archived/l9-pe-campaign-activate/scripts/compile_activation_files.py"
)

# Records argv, then hands off to the real binary so the campaign still works.
_RECORDING_SHIM = """#!/bin/sh
{{ printf '{name}'; for arg in "$@"; do printf ' %s' "$arg"; done; printf '\\n'; }} \
>> "$L9_TEST_SUBPROCESS_LOG"
exec {real} "$@"
"""

# Stands in for `make`: records argv and the publication environment, then
# writes the summary the SSOT `make pr` would leave in the published workspace.
_MAKE_PR_SHIM = """#!/bin/sh
{{ printf 'make'; for arg in "$@"; do printf ' %s' "$arg"; done; \
printf ' |PR_REMEDIATE=%s PR_BASE=%s PR_STACK=%s' "$PR_REMEDIATE" "$PR_BASE" "$PR_STACK"; \
printf '\\n'; }} >> "$L9_TEST_SUBPROCESS_LOG"
for arg in "$@"; do case "$arg" in WS=*) ws="${{arg#WS=}}";; esac; done
mkdir -p "$ws/.l9/pr"
head=$(git -C "$ws" rev-parse HEAD)
pr='"number":4242,"url":"https://example.test/pull/4242"'
printf '{{"repo":"o/r",%s,"head_sha":"%s","source":"github_api"}}' "$pr" "$head" \
> "$ws/.l9/pr/pr-summary.json"
"""

# `gh` must never run during Program Execution, and `make` must not run when the
# campaign stops at `execute`. Recording and then failing turns a silent
# regression into a loud one without hiding the record.
_REFUSING_SHIM = """#!/bin/sh
{{ printf '{name}'; for arg in "$@"; do printf ' %s' "$arg"; done; printf '\\n'; }} \
>> "$L9_TEST_SUBPROCESS_LOG"
echo "{name} must not run during autonomous Program Execution" >&2
exit 97
"""


def _install_shims(bin_dir: Path, *, make_pr: bool = False) -> None:
    """Put recording wrappers for git/gh/make ahead of the real binaries."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    real_git = shutil.which("git")
    if not real_git:
        raise unittest.SkipTest("git is required to certify the commit path")
    (bin_dir / "git").write_text(
        _RECORDING_SHIM.format(name="git", real=real_git), encoding="utf-8"
    )
    (bin_dir / "gh").write_text(_REFUSING_SHIM.format(name="gh"), encoding="utf-8")
    make = _MAKE_PR_SHIM.format() if make_pr else _REFUSING_SHIM.format(name="make")
    (bin_dir / "make").write_text(make, encoding="utf-8")
    for name in ("git", "gh", "make"):
        (bin_dir / name).chmod(0o755)


def _stand_in_ssot(root: Path, log: Path) -> Path:
    """A directory carrying every marker campaign_publish requires of the SSOT.

    `l4_local.py` records its call; `make` is the shim above. Nothing here
    pushes or opens anything: the assertion is on what Program Execution asked
    the SSOT to do, which is the whole of its publication authority.
    """
    for marker in campaign_publish_module().SSOT_MARKERS:
        path = root / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    python = root / ".venv" / "bin" / "python"
    python.unlink()
    python.symlink_to(sys.executable)
    (root / "ops" / "autonomy" / "l4_local.py").write_text(
        "import sys\n"
        f"open({str(log)!r}, 'a').write('l4_local ' + ' '.join(sys.argv[1:]) + '\\n')\n",
        encoding="utf-8",
    )
    return root


def campaign_publish_module():
    return _load("campaign_publish_commit_only", PE_ROOT / "scripts/campaign_publish.py")


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


class PublicationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_commit_only", SCRIPT)
        cls.activate = _load("compile_activation_commit_only", ACTIVATE)

    # ---- the mandatory regression: a real campaign, recorded ----------------

    def test_campaign_stopped_at_execute_commits_and_never_publishes(self) -> None:
        """Run a complete campaign to `execute`; assert on what it actually ran."""
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
                    until="execute",
                    primary=tmp / "primary",
                    repo_root=root,
                    l9_root=l9,
                    fast=True,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        bind_projection=_projection_ok,
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

    def test_campaign_finish_publishes_only_through_the_ssot_make_pr(self) -> None:
        """Run a complete campaign to `pr`; the only publication act is the SSOT make pr."""
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
            _install_shims(bin_dir, make_pr=True)
            ssot = _stand_in_ssot(tmp / "ssot", log)

            env = {
                **_peer_test_env(tmp),
                "L9_TEST_SUBPROCESS_LOG": str(log),
                "L9_GOVERNANCE_DIR": str(ssot),
                "PATH": f"{bin_dir}{os.pathsep}{_peer_test_env(tmp)['PATH']}",
            }
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
                        bind_projection=_projection_ok,
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
            pec_workspace = Path(report.pec_workspace)
            publication = json.loads(
                (pec_workspace / "runtime" / "PUBLICATION.json").read_text(encoding="utf-8")
            )
            workspace = Path(publication["workspace"])

            self.assertEqual(report.stages_completed[-2:], ["execute", "pr"])
            self.assertEqual(report.host_pr, "https://example.test/pull/4242")
            self.assertEqual(report.host_pr_number, 4242)
            self.assertTrue(record.ran("git", "commit"), msg=record.lines)
            # Exactly one make, and it is the sanctioned SSOT ceremony.
            makes = [line for line in record.lines if line.startswith("make ")]
            self.assertEqual(
                makes,
                [
                    f"make -C {ssot.resolve()} pr WS={workspace} "
                    "|PR_REMEDIATE=0 PR_BASE=origin/main PR_STACK="
                ],
            )
            # The exact verified tree was authorized for L4 release first.
            l4 = [line for line in record.lines if line.startswith("l4_local ")]
            self.assertEqual(len(l4), 2, msg=l4)
            self.assertIn("begin --contract-id pe-demo-activate-v1 --base origin/main", l4[0])
            self.assertIn("authorize-release", l4[1])
            # PE itself never pushes, opens or merges: that is make pr's, and merge
            # is /l9-pr-remediation's.
            self.assertFalse(record.ran("git", "push"), msg=record.matching("push"))
            self.assertEqual([line for line in record.lines if line.startswith("gh ")], [])
            # The head is the verified campaign integration branch, base the remote default.
            self.assertEqual(publication["head_branch"], "campaign/demo-activate-v1")
            self.assertEqual(publication["base"], "origin/main")
            self.assertEqual(publication["route"], "make_pr_ssot")
            self.assertEqual(publication["merge"], "not_performed")
            # The composer's intent is bound to that head.
            intent = json.loads(
                (workspace / ".l9" / "pr" / "pr-intent.json").read_text(encoding="utf-8")
            )
            self.assertEqual(intent["schema"], "l9.pr_intent.v1")
            self.assertEqual(intent["head"], publication["head_sha"])
            self.assertTrue(intent["title"])
            self.assertIn("TASK-001", intent["reviewer_focus"])

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
        # Global options before the subcommand, a body without an explicit
        # method, the dispatcher spelling, and the publication scripts are all
        # the same remote act under a different surface.
        self.assertIsNotNone(classify(["gh", "--repo", "o/r", "pr", "merge", "1"]))
        self.assertIsNotNone(classify(["gh", "-R", "o/r", "pr", "create", "--fill"]))
        self.assertIsNotNone(classify(["gh", "api", "repos/o/r/pulls", "-f", "title=x"]))
        self.assertIsNotNone(classify(["gh", "api", "repos/o/r/pulls", "--input", "body.json"]))
        self.assertIsNotNone(classify(["gh", "api", "repos/o/r/pulls", "-F", "base=main"]))
        self.assertIsNotNone(classify(["l9", "pr"]))
        self.assertIsNotNone(classify(["bash", "ops/scripts/open_pr_after_gate.sh", "/ws"]))
        self.assertIsNotNone(classify(["python3", "ops/autonomy/stack_safe_merge.py", "--pr", "7"]))
        # Local work and reads stay allowed.
        for allowed in (
            ["git", "-C", "/repo", "commit", "-m", "work"],
            ["git", "-C", "/repo", "add", "--", "file.py"],
            ["git", "-C", "/repo", "rev-parse", "HEAD"],
            ["gh", "pr", "view", "--json", "number"],
            ["gh", "pr", "checks", "7"],
            ["gh", "api", "repos/o/r/pulls"],
            ["gh", "api", "-X", "GET", "repos/o/r/pulls"],
            ["gh", "--repo", "o/r", "pr", "view", "1"],
            ["l9", "pr-check"],
            ["make", "pr-check"],
            ["python3", "pec.py", "status"],
        ):
            self.assertIsNone(classify(allowed), msg=f"wrongly blocked: {allowed}")

    def test_run_cmd_refuses_a_publication_subprocess(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_cmd(["git", "-C", ".", "push", "origin", "main"], timeout=5)
            self.assertIn("publishes only through the governance SSOT make pr", str(ctx.exception))
            # `make pr` through the choke point is refused too: the one sanctioned
            # spawn is campaign_publish's, never run_cmd's.
            with self.assertRaises(self.mod.CampaignError):
                self.mod.run_cmd(["make", "-C", "/ssot", "pr", "WS=/ws"], timeout=5)

    def test_default_make_pr_only_hands_off_to_campaign_publish(self) -> None:
        import inspect

        source = inspect.getsource(self.mod.default_make_pr)
        self.assertIn("campaign_publish", source)
        for token in ("run_cmd(", '"gh"', '"push"', '"make"', "AUTHORIZE_SCRIPT"):
            self.assertNotIn(token, source, msg=f"default_make_pr carries {token}")
        publish = campaign_publish_module()
        ssot, workspace = Path("/ssot"), Path("/ws")
        argv = publish.sanctioned_make_pr_argv(ssot, workspace)
        self.assertEqual(argv, ["make", "-C", "/ssot", "pr", "WS=/ws"])
        self.assertTrue(publish.is_sanctioned_make_pr(argv, ssot, workspace))
        for other in (
            ["make", "pr"],
            ["make", "-C", "/ssot", "pr", "WS=/ws", "PR_STACK=auto"],
            ["make", "-C", "/elsewhere", "pr", "WS=/ws"],
            ["l9", "pr"],
        ):
            self.assertFalse(publish.is_sanctioned_make_pr(other, ssot, workspace), other)
        publish_source = (PE_ROOT / "scripts/campaign_publish.py").read_text(encoding="utf-8")
        for token in ('"push"', '"gh"', '"create"', "stack_safe_merge", "merge_method"):
            self.assertNotIn(token, publish_source, msg=f"campaign_publish carries {token}")

    def test_refused_publication_functions_carry_no_publication_machinery(self) -> None:
        """Audit Y7: the refusal is the whole function, not a guard over live code.

        `git push`, `gh pr create` and `gh pr merge` implementations used to sit
        under `refuse_publication()`, unreachable but readable as a live
        publication path. The runner carries none of it; its one publication
        act is campaign_publish's SSOT `make pr`.
        """
        import inspect

        for function in (
            self.mod.default_authorize_and_merge,
            self.mod.push_integration_branch,
            self.mod.maybe_open_task_pr,
        ):
            source = inspect.getsource(function)
            self.assertIn("refuse_publication(", source)
            for token in ("run_cmd(", '"gh"', '"push"', '"make"', "AUTHORIZE_SCRIPT"):
                self.assertNotIn(token, source, msg=f"{function.__name__} still carries {token}")
        # Every live campaign path refuses before any publish block, and no
        # publish block follows the refusal.
        refusing = [
            function
            for _, function in inspect.getmembers(self.mod, inspect.isfunction)
            if function.__module__ == self.mod.__name__
            and 'refuse_publication("merge recorded stack pull requests")'
            in inspect.getsource(function)
        ]
        self.assertGreaterEqual(len(refusing), 1, [f.__name__ for f in refusing])
        for function in refusing:
            source = inspect.getsource(function)
            after = source.split("refuse_publication(", 1)[1]
            for token in (
                "push_integration_branch",
                "default_make_pr",
                "default_authorize_and_merge",
                "hooks.make_pr",
                "hooks.push_integration",
                "hooks.authorize_and_merge",
            ):
                self.assertNotIn(
                    token, after, msg=f"{function.__name__} keeps {token} after refusal"
                )

    def test_publication_functions_refuse_without_release(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            for call in (
                lambda: self.mod.push_integration_branch(Path("/tmp"), "demo-activate-v1"),
                lambda: self.mod.default_authorize_and_merge("o/r", 7),
            ):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    call()
                self.assertIn(
                    "publishes only through the governance SSOT make pr", str(ctx.exception)
                )

    # ---- the boundary -------------------------------------------------------

    def test_campaign_default_finishes_with_the_ssot_make_pr(self) -> None:
        import inspect

        signature = inspect.signature(self.mod.run_campaign)
        self.assertEqual(signature.parameters["until"].default, "pr")
        self.assertEqual(self.mod.AUTONOMOUS_LAST_STAGE, "pr")
        self.assertEqual(self.mod.LOCAL_LAST_STAGE, "execute")
        parsed = self.mod.build_parser().parse_args([])
        self.assertEqual(parsed.until, "pr")

    def test_nothing_runs_past_the_pr_stage(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            self.mod.refuse_live_until_shortcut("execute")
            self.mod.refuse_live_until_shortcut("pr")
            for stage in ("close", "merge"):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    self.mod.refuse_live_until_shortcut(stage)
                self.assertIn(
                    "publishes only through the governance SSOT make pr", str(ctx.exception)
                )

    def test_no_pre_execution_push_of_the_integration_branch(self) -> None:
        """The integration branch is never pushed to set work up."""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("push {campaign_id} integration branch before execute", source)
        self.assertIn("No pre-execution push", source)

    # ---- legacy release env cannot widen authority -------------------------

    def test_release_environment_never_reopens_publication(self) -> None:
        with unittest.mock.patch.dict(
            "os.environ", {"L9_PE_RELEASE_AUTHORIZED": "operator release"}
        ):
            self.assertFalse(self.mod.release_authorized())
            for call in (
                lambda: self.mod.refuse_publication("push a branch"),
                lambda: self.mod.refuse_live_until_shortcut("close"),
                lambda: self.mod.refuse_live_until_shortcut("merge"),
            ):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    call()
                self.assertIn(
                    "publishes only through the governance SSOT make pr", str(ctx.exception)
                )


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

    def test_fast_does_not_open_another_publish_path(self) -> None:
        with unittest.mock.patch.dict("os.environ", {"L9_PE_FAST": "1"}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.push_integration_branch(Path("/tmp"), "demo-activate-v1")
            self.assertIn("publishes only through the governance SSOT make pr", str(ctx.exception))
            # The finish under FAST is the same SSOT make pr, refused without a
            # launch pointer rather than improvised.
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.default_make_pr(Path("/tmp/no-such-pec"), "demo-activate-v1")
            self.assertIn("launch pointer", str(ctx.exception))

    def test_fast_does_not_open_the_merge_path(self) -> None:
        with unittest.mock.patch.dict("os.environ", {"L9_PE_FAST": "1"}, clear=False):
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.default_authorize_and_merge("o/r", 7)
            self.assertIn("publishes only through the governance SSOT make pr", str(ctx.exception))
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
        self.assertNotIn(
            "LOCAL_ACCEPT",
            (PE_ROOT / "scripts/campaign_publish.py").read_text(encoding="utf-8"),
        )
        merge_gate = PE_ROOT.parents[1] / "ops/autonomy/merge_gate.py"
        if merge_gate.is_file():
            self.assertNotIn("LOCAL_ACCEPT", merge_gate.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
