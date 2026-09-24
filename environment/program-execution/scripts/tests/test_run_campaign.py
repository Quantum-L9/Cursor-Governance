from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"

HOST_POLICY = """schema: l9.program-execution.campaign-execution-policy.v1
campaigns:
  - id: bounded-replanning-v1
    integration_branch: campaign/bounded-replanning-v1
    pr_base: campaign/bounded-replanning-v1
    execute_order: 1
    lane: pe_host

owner:
  authority_id: AUTH-001
"""

HOST_PROFILE = """campaign_execution:
  merge: forbidden
  campaigns:
    bounded-replanning-v1:
      integration_branch: campaign/bounded-replanning-v1

authority_order:
  - CANONICAL_LAW.campaign_execution_pr_no_merge
"""

HOST_STATUS = """schema: l9.program-execution.campaign-status-ledger.v1
updated: "2026-08-15T00:00:00Z"
campaigns:
  - id: bounded-replanning-v1
    lifecycle: complete
"""

ACTIVATE_SEED = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "tasks": [
        {"title": "Lock current state", "objective": "Record baseline."},
        {"title": "Implement change", "objective": "Edit declared paths only."},
    ],
}

READY_SEED = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "plan_status": "Ready",
    "tasks": [
        {
            "id": "TASK-001",
            "paths": ["docs/program-execution/demo/baseline.md"],
            "title": "Lock current state",
            "objective": "Record baseline.",
            "actions": ["inspect_repository_head"],
            "consumers": ["pec"],
            "entrypoints": ["make campaign"],
            "validation": [{"command": "git status --short"}],
            "nugget_id": "nugget-task-001",
            "acceptance": [
                {
                    "id": "AC-001",
                    "statement": "Baseline is recorded.",
                    "required_evidence_types": ["runtime_behavior"],
                }
            ],
        },
        {
            "id": "TASK-002",
            "paths": ["docs/program-execution/demo/change.md"],
            "title": "Implement change",
            "objective": "Edit declared paths only.",
            "actions": ["edit_only_declared_paths"],
            "consumers": ["pec"],
            "entrypoints": ["make campaign"],
            "validation": [{"command": "git status --short"}],
            "nugget_id": "nugget-task-002",
            "acceptance": [
                {
                    "id": "AC-002",
                    "statement": "Declared paths contain the change.",
                    "required_evidence_types": ["runtime_behavior"],
                }
            ],
        },
    ],
}

INTENT_V1 = {
    "schema": "program-execution.intent.v1",
    "objective": "Make repo X achieve Y.",
    "targets": ["Quantum-L9/l9-ci-core"],
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_GIT_IDENTITY = (
    "-c",
    "user.email=test@example.com",
    "-c",
    "user.name=Test",
)

_GIT_HOST_LEAKS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _isolated_git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _GIT_HOST_LEAKS:
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _write_task_output(worktree: Path, rel: str, title: str) -> str:
    path = worktree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{Path(rel).stem} implemented for tests: {title}\n" + ("x" * 48) + "\n",
        encoding="utf-8",
    )
    git_env = _isolated_git_env()
    subprocess.run(
        ["git", "-C", str(worktree), "add", "--", rel],
        check=True,
        capture_output=True,
        env=git_env,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            # The worktree under test is created by the PE controller, not by
            # `_git_init`, so it carries no committer identity and CI runners
            # have no global one either. Bind it per-invocation: the fixture
            # owns the commit, so it must supply the identity that commit needs.
            *_GIT_IDENTITY,
            "commit",
            "-m",
            f"pec: {Path(rel).stem} output",
        ],
        check=True,
        capture_output=True,
        env=git_env,
    )
    sha = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    )
    return sha.stdout.strip()


def _stack_ok(seed, primed_dir):
    path = Path(primed_dir) / str(seed["campaign_id"]) / "stack-proof.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "l9.program-execution.stack-proof.v1",
        "status": "pass",
        "tools": [],
        "path": str(path),
    }
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    return receipt


def _dump(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


ARCHITECTURE_DOC = """\
# Router reasoning capability

DeepSeek MUST be the primary governed reasoning provider.

Perplexity is research only and MUST NOT serve reasoning traffic.

## Budget

Budget downgrade MUST remain within the capability family.
"""


#: The same document carried up over the deterministic auto-promotion contract.
#: `ARCHITECTURE_DOC` deliberately stays *below* it so one fixture proves prose
#: keeps its ordinary route and the other proves `make campaign` ingests
#: architecture-grade prose with no frontmatter and no source edit. The H1 is
#: shared, so both compile to the same campaign identity.
QUALIFYING_ARCHITECTURE_DOC = (
    ARCHITECTURE_DOC
    + """
## Authority and ownership

The routing architecture names one owner per capability family; the router is
the sole owner of provider selection.

## Implementation plan

Phase 1 rewrites the provider registry and its adapter manifest.

## Acceptance and validation

Every regression test MUST pass before release. Rollback is a revert.
"""
)


SEEN_TARGET_CHECKOUTS: list[object] = []


def _architecture_hook(intent, *, target, admission, repo_root, primed_dir, target_checkout=None):
    """Run the real architecture compiler with the deterministic extractor.

    Real compilation, no live model: the route under test is the wiring, and a
    test that needed a model could not assert on it.
    """
    SEEN_TARGET_CHECKOUTS.append(target_checkout)
    module = _load(
        "compile_architecture_intent_route_test",
        SCRIPT.parent / "compile_architecture_intent.py",
    )
    return module.compile_architecture_intent(
        Path(intent),
        target=target,
        admission=admission,
        repo_root=repo_root,
        target_checkout=target_checkout,
        cache_root=primed_dir,
        extractor_name="deterministic",
    )


def _host_repo(tmp: Path) -> Path:
    (tmp / "environment/program-execution/campaigns").mkdir(parents=True)
    (tmp / "ops/autonomy").mkdir(parents=True)
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml").write_text(
        HOST_POLICY, encoding="utf-8"
    )
    (tmp / "ops/autonomy/surface_profile.yaml").write_text(HOST_PROFILE, encoding="utf-8")
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").write_text(
        HOST_STATUS, encoding="utf-8"
    )
    _dump(tmp / "intent.yaml", READY_SEED)
    return tmp


#: Where `_git_init` keeps the fixture's bare origin. Inside `.git/` so it never
#: shows in porcelain, never lands outside the TemporaryDirectory when the repo
#: *is* the temp root, and travels with the tree when a test quarantines it.
_FIXTURE_ORIGIN = Path(".git") / "l9-test-origin.git"

#: Known bytes for a tracked `.claude/settings.json`; the preservation tests
#: compare the file byte-for-byte after cleanup.
_TRACKED_SETTINGS = '{"permissions": {"allow": ["Bash(make pr)"]}}\n'


def _git_init(path: Path) -> None:
    """A checkout fixture: one commit, published to a local bare ``origin``.

    An exclusive PE checkout always has a remote lineage to prove, and
    `_bind_exclusive_remote_lineage` fails closed when origin cannot confirm
    one. A fixture that models a checkout therefore carries a reachable origin
    whose ``main`` is the fixture's HEAD; `_git_publish` re-syncs it after the
    test commits more.
    """
    env = _isolated_git_env()
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, env=env)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=path, check=True, env=env
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, env=env)
    (path / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, env=env
    )
    origin = path / _FIXTURE_ORIGIN
    subprocess.run(
        ["git", "init", "--bare", "-q", "--initial-branch=main", str(origin)],
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin)],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )
    _git_publish(path)
    subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )


def _git_publish(path: Path) -> str:
    """Push the fixture's HEAD to its origin ``main``; return the published SHA."""
    env = _isolated_git_env()
    subprocess.run(
        ["git", "push", "-q", "origin", "HEAD:refs/heads/main"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _github_redirect(repository_id: str, target: Path) -> dict[str, str]:
    """Environment that routes the GitHub URL run_campaign hardcodes to a local repo.

    `default_ensure_target_checkout` rewrites origin to
    ``https://github.com/<repository_id>.git`` after a donor clone, so a fetch
    would otherwise reach the network. ``url.<local>.insteadOf`` keeps the test
    hermetic without changing what the code under test does.
    """
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"url.{target}.insteadOf",
        "GIT_CONFIG_VALUE_0": f"https://github.com/{repository_id}.git",
    }


class RunCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_under_test", SCRIPT)
        cls.activate = _load("compile_activation_under_test", ACTIVATE)

    def test_cli_refuses_until_shortcut(self) -> None:
        """The live path runs to the autonomous boundary — no short, no long."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("L9_CAMPAIGN_UNTIL_DEBUG", None)
            os.environ.pop("L9_PE_RELEASE_AUTHORIZED", None)
            # Stopping early is still a shortcut around the live path.
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.refuse_live_until_shortcut("activate")
            self.assertIn("CAMPAIGN_UNTIL is not a live campaign path", str(ctx.exception))
            # Running past it is publication, which autonomy may not do.
            for stage in ("pr", "close", "merge"):
                with self.assertRaises(self.mod.CampaignError) as ctx:
                    self.mod.refuse_live_until_shortcut(stage)
                self.assertIn("local-commit-only", str(ctx.exception))
            self.mod.refuse_live_until_shortcut("execute")
        with patch.dict(os.environ, {"L9_CAMPAIGN_UNTIL_DEBUG": "1"}):
            self.mod.refuse_live_until_shortcut("activate")

    def test_integration_branch_starts_at_the_remote_lineage_when_one_exists(self) -> None:
        """A fresh clone must not mint campaign/<id> from its default-branch HEAD."""
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            origin = temp / "origin"
            origin.mkdir()
            _git_init(origin)
            env = _isolated_git_env()
            subprocess.run(
                ["git", "-C", str(origin), "checkout", "-q", "-b", "campaign/demo"],
                check=True,
                env=env,
            )
            (origin / "integrated.txt").write_text("integrated\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(origin), "add", "integrated.txt"], check=True, env=env)
            subprocess.run(
                ["git", *_GIT_IDENTITY, "-C", str(origin), "commit", "-qm", "integrated"],
                check=True,
                env=env,
            )
            integrated = subprocess.run(
                ["git", "-C", str(origin), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(origin), "checkout", "-q", "-"], check=True, env=env)
            clone = temp / "clone"
            subprocess.run(
                ["git", "clone", "-q", str(origin), str(clone)],
                check=True,
                capture_output=True,
                env=env,
            )
            # The clone's HEAD is the default branch; origin/campaign/demo is ahead.
            self.mod.fetch_stack_refs(clone, "demo")
            branch = self.mod.ensure_integration_branch(clone, "demo")
            local = subprocess.run(
                ["git", "-C", str(clone), "rev-parse", branch],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            self.assertEqual(local, integrated)

    def test_stub_heuristic_applies_to_the_primary_output_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            (temp / "__init__.py").write_text("", encoding="utf-8")
            (temp / "note.txt").write_text("note complete: Title\n", encoding="utf-8")
            (temp / "blob.bin").write_bytes(b"\xff\xfe\x00binary")
            self.assertTrue(self.mod.is_stub_output(temp / "__init__.py", "Title"))
            self.assertFalse(self.mod.is_stub_output(temp / "__init__.py", "Title", primary=False))
            self.assertTrue(self.mod.is_stub_output(temp / "note.txt", "Title", primary=False))
            self.assertFalse(self.mod.is_stub_output(temp / "blob.bin", "Title", primary=False))

    def test_generated_data_database_follows_the_campaign_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            l9 = Path(raw) / "l9"
            workspace = l9 / "programs" / "demo-activate-v1"
            workspace.mkdir(parents=True)
            self.assertEqual(
                self.mod.generated_data_database(workspace),
                (l9 / "generated-data" / "pipeline.sqlite3").resolve(),
            )

    def test_commit_identity_is_supplied_only_when_the_checkout_has_none(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            _git_init(repo)
            self.assertEqual(self.mod._commit_identity_args(repo), [])
            bare = Path(raw) / "bare"
            bare.mkdir()
            env = _isolated_git_env()
            env["GIT_CONFIG_GLOBAL"] = str(Path(raw) / "no-global-config")
            env["GIT_CONFIG_NOSYSTEM"] = "1"
            subprocess.run(["git", "init", "-q", str(bare)], check=True, env=env)
            with patch.dict(os.environ, env, clear=True):
                args = self.mod._commit_identity_args(bare)
            self.assertIn("user.email=make-campaign@l9.local", args)

    def test_launch_pointer_is_written_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "program"
            (workspace / "runtime").mkdir(parents=True)
            path = self.mod.write_launch_pointer(
                workspace,
                campaign_id="demo-activate-v1",
                blueprint=str(Path(raw) / "blueprint"),
                target_worktree=str(Path(raw) / "target"),
                host_worktree=str(Path(raw) / "host"),
                stage="activate",
            )
            self.assertEqual(json.loads(path.read_text())["campaign_id"], "demo-activate-v1")
            self.assertEqual([p.name for p in (workspace / "runtime").glob("*.tmp")], [])

    def test_launch_pointer_reads_human_ack_identity_not_program_owner(self) -> None:
        """A shared program-owner default must never become a fabricated human.

        `PROGRAM.owner` now carries the Program Execution default, so a pointer
        that reused it would claim an organization acknowledged the launch.
        The human identity is PHASE0's, and only PHASE0's.
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace = root / "program"
            blueprint = root / "blueprint"
            (workspace / "runtime").mkdir(parents=True)
            blueprint.mkdir()
            _dump(blueprint / "PROGRAM.yaml", {"program": {"owner": "Quantum AI Partners"}})
            _dump(
                blueprint / "PHASE0_USER_CONFIG.yaml",
                {"operator_ack": {"name": "Igor Beylin", "acknowledged_at": None}},
            )
            path = self.mod.write_launch_pointer(
                workspace,
                campaign_id="demo-activate-v1",
                blueprint=str(blueprint),
                target_worktree=str(root / "target"),
                host_worktree=str(root / "host"),
                stage="activate",
            )
            launch = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(launch["operator_ack_from"], "Igor Beylin")

    def test_rejects_intent_v1(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "intent.yaml"
            _dump(path, INTENT_V1)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.load_activate_seed(path)
            self.assertIn("program-execution.intent.v1", str(ctx.exception))
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.resolve_operator_intent(path, host_root=Path(raw))
            self.assertIn("program-execution.intent.v1", str(ctx.exception))

    def test_refuses_dirty_primary_writes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            primary.mkdir()
            _git_init(primary)
            (primary / "dirty.txt").write_text("no\n", encoding="utf-8")
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.refuse_write_to_dirty_primary(primary, primary)
            self.assertIn("dirty primary", str(ctx.exception))

    def test_require_remote_campaign_branch_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.require_remote_campaign_branch(root, "demo-activate-v1")
            self.assertIn("remote campaign/demo-activate-v1 missing", str(ctx.exception))

    def test_does_not_push_campaign_branch_before_execute(self) -> None:
        """Execution is local: nothing reaches a remote to set the work up."""
        order: list[str] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            self.mod.run_campaign(
                root / "intent.yaml",
                until="execute",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=emit,
                    compile_source=lambda source, target: None,
                    validate_blueprint=lambda target: [],
                    admit=lambda blueprint: {},
                    pec_bootstrap=lambda workspace, blueprint: {
                        "ok": True,
                        "draft": False,
                        "output": "ok",
                    },
                    arm=lambda workspace, campaign_id: None,
                    push_integration=lambda worktree, campaign_id: order.append("push"),
                    execute=lambda workspace, campaign_id: order.append("execute") or {},
                    make_pr=lambda worktree, campaign_id: {
                        "number": 1,
                        "url": "https://example.test/1",
                    },
                    close=lambda workspace, campaign_id: order.append("close") or {},
                ),
            )
        self.assertEqual(order, ["execute"])
        self.assertNotIn("push", order)

    def test_write_and_commit_output_refuses_before_git_without_commit_authority(self) -> None:
        """local_write is not commit authority; the refusal precedes `git add`."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            (root / "done.md").write_text(
                "done.md holds real work, long enough to clear the stub floor\n",
                encoding="utf-8",
            )
            head_before = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.write_and_commit_output(
                    root, "done.md", "Title", writable=["done.md"], commit_authorized=False
                )
            self.assertIn("does not request the 'commit' action", str(ctx.exception))
            # Nothing was staged and no commit was created.
            staged = subprocess.run(
                ["git", "-C", str(root), "diff", "--cached", "--name-only"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(staged, "")
            head_after = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(head_after, head_before)

    def test_contract_allows_commit_reads_the_requested_actions(self) -> None:
        self.assertFalse(
            self.mod.contract_allows_commit({"requested_actions": ["inspect", "local_write"]})
        )
        self.assertTrue(
            self.mod.contract_allows_commit(
                {"requested_actions": ["inspect", "local_write", "commit"]}
            )
        )
        self.assertFalse(self.mod.contract_allows_commit({}))

    def test_write_and_commit_output_refuses_stub(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.write_and_commit_output(
                    root,
                    "docs/program-execution/TASK-001.md",
                    "x",
                    commit_authorized=True,
                )
            self.assertIn("refuse stub", str(ctx.exception))

    def test_until_activate_emits_allowed_set(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="activate",
                primary=other_primary,
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            campaign_dir = root / "environment/program-execution/campaigns/demo-activate-v1"
            names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
            self.assertEqual(names, self.mod.ALLOWED_CAMPAIGN_FILES)
            self.assertEqual(report.stages_completed, ["activate"])
            self.assertTrue(
                (Path(raw) / "l9" / "primed" / "demo-activate-v1" / "stack-proof.json").is_file()
            )
            self.assertNotIn("INTENT.yaml", names)
            ledger = yaml.safe_load(
                (root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").read_text(
                    encoding="utf-8"
                )
            )
            row = next(item for item in ledger["campaigns"] if item["id"] == "demo-activate-v1")
            self.assertEqual(row["lifecycle"], "in_progress")
            self.assertEqual(row["launched_by"], "make campaign")
            self.assertIn("operator_ack", row["notes"])
            policy = yaml.safe_load(
                (
                    root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
                ).read_text(encoding="utf-8")
            )
            prow = next(item for item in policy["campaigns"] if item["id"] == "demo-activate-v1")
            self.assertEqual(prow["lifecycle"], "in_progress")

    def test_architecture_intent_routes_to_the_direct_campaign_source_path(self) -> None:
        """Architecture prose enters via the rich route, not brief → activate.

        `compile_activation` is passed as a hook that fails if called: routing
        the compiled source back through activation would rebuild the campaign
        from a weaker seed and flatten the tasks, validations, dependencies, and
        prohibitions the architecture compiler just recovered.
        """

        def _refuse_activation(*args, **kwargs):
            raise AssertionError("architecture route must not rebuild through activation")

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            (root / "arch.md").write_text(QUALIFYING_ARCHITECTURE_DOC, encoding="utf-8")
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            report = self.mod.run_campaign(
                root / "arch.md",
                until="activate",
                primary=other_primary,
                repo_root=root,
                l9_root=Path(raw) / "l9",
                target_override="Quantum-L9/LLM-Router",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=_refuse_activation,
                    compile_architecture=_architecture_hook,
                ),
            )
            self.assertEqual(report.campaign_id, "router-reasoning-capability-v1")
            source = yaml.safe_load(
                (
                    root
                    / "environment/program-execution/campaigns"
                    / report.campaign_id
                    / "CAMPAIGN_SOURCE.yaml"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(source["schema"], "l9.program-execution.campaign-source.v2")
            self.assertEqual({task["definition_status"] for task in source["tasks"]}, {"ready"})
            self.assertEqual(source["intent_provenance"]["coverage"]["status"], "PASS")
            self.assertTrue(source["prohibited_paths"])

    def test_an_existing_target_checkout_reaches_the_architecture_compiler(self) -> None:
        """Repository grounding is unreachable if the route never passes a checkout."""
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            (root / "arch.md").write_text(QUALIFYING_ARCHITECTURE_DOC, encoding="utf-8")
            checkout = Path(raw) / "target-clone"
            (checkout / "src").mkdir(parents=True)
            (checkout / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest run", "lint": "eslint src/"}}),
                encoding="utf-8",
            )
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            SEEN_TARGET_CHECKOUTS.clear()
            report = self.mod.run_campaign(
                root / "arch.md",
                until="activate",
                primary=other_primary,
                repo_root=root,
                l9_root=Path(raw) / "l9",
                target_override="Quantum-L9/LLM-Router",
                target_checkout=checkout,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_architecture=_architecture_hook,
                ),
            )
            self.assertEqual(SEEN_TARGET_CHECKOUTS, [checkout.resolve()])
            source = yaml.safe_load(
                (
                    root
                    / "environment/program-execution/campaigns"
                    / report.campaign_id
                    / "CAMPAIGN_SOURCE.yaml"
                ).read_text(encoding="utf-8")
            )
            commands = {
                entry.get("command")
                for task in source["tasks"]
                for entry in task["validation"]
                if entry.get("command")
            }
            self.assertIn("npm test", commands)

    def test_a_missing_target_checkout_is_never_created(self) -> None:
        """Grounding is read-only; a path that does not exist resolves to None."""
        with tempfile.TemporaryDirectory() as raw:
            absent = Path(raw) / "not-there"
            self.assertIsNone(self.mod.existing_target_checkout(absent))
            self.assertFalse(absent.exists())
            self.assertIsNone(self.mod.existing_target_checkout(None))
            present = Path(raw) / "there"
            present.mkdir()
            self.assertEqual(self.mod.existing_target_checkout(present), present.resolve())

    def test_architecture_compile_failure_creates_no_workspace(self) -> None:
        """A source that cannot be compiled must never mint a program."""

        def _fail(*args, **kwargs):
            module = self.mod.architecture_module()
            raise module.ArchitectureCompileError("semantic coverage did not converge")

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            (root / "arch.md").write_text(QUALIFYING_ARCHITECTURE_DOC, encoding="utf-8")
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            l9_root = Path(raw) / "l9"
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "arch.md",
                    until="activate",
                    primary=other_primary,
                    repo_root=root,
                    l9_root=l9_root,
                    target_override="Quantum-L9/LLM-Router",
                    hooks=self.mod.Hooks(context7_stack=_stack_ok, compile_architecture=_fail),
                )
            self.assertIn("nothing_executed: true", str(ctx.exception))
            self.assertFalse((l9_root / "programs").exists())
            self.assertFalse((l9_root / "blueprints").exists())
            campaigns = root / "environment/program-execution/campaigns"
            self.assertEqual(
                [path.name for path in campaigns.iterdir() if path.is_dir()],
                [],
                msg="no campaign directory may exist after a failed architecture compile",
            )

    def test_unmarked_markdown_below_the_contract_still_routes_to_the_brief_compiler(
        self,
    ) -> None:
        """Prose that does not satisfy the contract keeps its ordinary route.

        There is no caller-supplied override to test alongside this any more:
        the only way this memo could reach the architecture representation is
        by satisfying the deterministic contract or declaring the schema.
        """
        module = self.mod.campaign_input_module()
        with tempfile.TemporaryDirectory() as raw:
            memo = Path(raw) / "memo.md"
            memo.write_text(ARCHITECTURE_DOC, encoding="utf-8")
            found = module.classify(memo)
            self.assertIs(found.kind, module.CampaignInputKind.BRIEF)
            self.assertEqual(found.admission, "")
            self.assertNotIn(
                "forced_kind",
                inspect.signature(module.classify).parameters,
                msg="no caller may force the architecture representation",
            )

    def test_self_describing_architecture_markdown_needs_no_force(self) -> None:
        module = self.mod.campaign_input_module()
        with tempfile.TemporaryDirectory() as raw:
            doc = Path(raw) / "declared.md"
            doc.write_text(
                "---\n"
                "schema: l9.program-execution.architecture-intent.v1\n"
                "target: Quantum-L9/LLM-Router\n"
                "---\n\n" + ARCHITECTURE_DOC,
                encoding="utf-8",
            )
            found = module.classify(doc)
            self.assertIs(found.kind, module.CampaignInputKind.ARCHITECTURE_INTENT_V1)
            self.assertEqual(found.route, "architecture -> campaign_source -> blueprint -> PEC")

    def test_compile_fingerprint_ignores_retired_preregistration_artifacts(self) -> None:
        """A retired allowlist file is neither an input nor a compile dependency."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "CAMPAIGN_SOURCE.yaml"
            source.write_text("schema: x\n", encoding="utf-8")
            proof = root / "stack-proof.json"
            proof.write_text("{}\n", encoding="utf-8")
            before = self.mod.pe_trace.fingerprint(source, proof)
            allowlist = root / "retired-allowlist.yaml"
            allowlist.write_text("campaign_ids:\n  - unrelated-v1\n", encoding="utf-8")
            self.assertEqual(self.mod.pe_trace.fingerprint(source, proof), before)

    def test_phase0_ack_is_not_forged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()
            (blueprint / "PHASE0_USER_CONFIG.yaml").write_text(
                "schema: program-execution-blueprint.phase0-user-config.v2\n"
                "operator_ack:\n  name: Igor Beylin\n  acknowledged_at: null\n"
                "program_deploying: false\n"
                "completeness:\n  phase0_complete: false\n"
                "notes: template\n",
                encoding="utf-8",
            )
            self.mod.annotate_phase0_without_forging_ack(blueprint)
            data = yaml.safe_load((blueprint / "PHASE0_USER_CONFIG.yaml").read_text())
            self.assertIsNone(data["operator_ack"]["acknowledged_at"])
            self.assertEqual(data["operator_ack"]["name"], "Igor Beylin")
            self.assertFalse(data["program_deploying"])
            self.assertFalse(data["completeness"]["phase0_complete"])
            self.assertIn("never forge", data["notes"])

    def test_pec_runtime_marked_active(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "program"
            payload = self.mod.activate_pec_runtime(workspace, campaign_id="demo-activate-v1")
            self.assertEqual(payload["runtime_status"], "active")
            stored = json.loads(
                (workspace / "runtime" / "campaign-status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["runtime_status"], "active")
            self.assertEqual(stored["campaign_id"], "demo-activate-v1")
            self.assertTrue(stored["activated_at"])

    def test_no_merge_on_red_checks(self) -> None:
        merged: list[tuple[str, int]] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            status = repo_root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
            status.parent.mkdir(parents=True, exist_ok=True)
            if not status.is_file():
                status.write_text(HOST_STATUS, encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="merge",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=Path(raw) / "l9",
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=emit,
                        compile_source=lambda source, target: None,
                        validate_blueprint=lambda target: [],
                        admit=lambda blueprint: {"accepted": True},
                        pec_bootstrap=lambda workspace, blueprint: {
                            "ok": True,
                            "draft": False,
                            "output": "lock",
                        },
                        arm=lambda workspace, campaign_id: {"task_id": "TASK-001"},
                        make_pr=lambda worktree, campaign_id: {
                            "number": 99,
                            "url": "https://example.test/99",
                        },
                        pr_status=lambda host_repo, number: {
                            "number": 99,
                            "url": "https://example.test/99",
                            "green": False,
                            "mergeable": False,
                            "sha": "",
                        },
                        authorize_and_merge=lambda host_repo, number: (
                            merged.append((host_repo, number)) or {}
                        ),
                    ),
                )
            self.assertEqual(ctx.exception.exit_code, 2)
            self.assertIn("permanently local-commit-only", str(ctx.exception))
            self.assertEqual(merged, [])

    def test_until_activate_from_memo(self) -> None:
        fixture = (
            PE_ROOT.parents[1]
            / "skills/l9-pe-campaign-activate/scripts/fixtures/pe-memory-class.md"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            brief = Path(raw) / "PE- Memory.md"
            brief.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            report = self.mod.run_campaign(
                brief,
                until="activate",
                primary=other_primary,
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            campaign_dir = root / "environment/program-execution/campaigns/pe-memory"
            self.assertEqual(report.stages_completed, ["activate"])
            self.assertTrue((campaign_dir / "source-integrity-receipt.json").is_file())

    def test_refuses_hash_campaign_id(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.refuse_hash_campaign_id("pe-8c9f6de43b25")
        self.assertIn("intent.v1", str(ctx.exception))

    def test_commit_host_emit_ignores_unrelated_isolate_dirt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            campaign = root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "environment/program-execution/campaigns/demo-activate-v1"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "emit once"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            (root / "ops/autonomy").mkdir(parents=True)
            (root / "ops/autonomy/surface_profile.yaml").write_text("x: 1\n", encoding="utf-8")
            (root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").write_text(
                "dirty: true\n", encoding="utf-8"
            )
            self.mod.commit_host_emit(root, "demo-activate-v1")
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("CAMPAIGN_STATUS.yaml", status.stdout)
            self.assertIn("ops/", status.stdout)
            log = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(log.stdout.strip(), "emit once")

    def _retry_receipt(
        self, workspace: Path, task_id: str, attempt_id: str, failure_class: str | None
    ) -> Path:
        root = workspace / "runtime" / "peer-execution" / "retry-receipts"
        root.mkdir(parents=True, exist_ok=True)
        target = root / f"{task_id}-{attempt_id}.json"
        target.write_text(
            json.dumps(
                {
                    "schema": self.mod.PEER_RETRY_RECEIPT_SCHEMA,
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "status": "FAIL",
                    "failure_class": failure_class,
                    "reason": "provider_status_fail",
                }
            ),
            encoding="utf-8",
        )
        return target

    def test_terminal_recovery_reads_only_a_known_terminal_peer_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self.assertIsNone(self.mod._terminal_peer_retry_receipt(workspace, "TASK-001"))
            self._retry_receipt(workspace, "TASK-001", "attempt-a", "SAFE_BEFORE_DISPATCH")
            self.assertIsNone(self.mod._terminal_peer_retry_receipt(workspace, "TASK-001"))
            self._retry_receipt(workspace, "TASK-001", "attempt-b", "AMBIGUOUS_SIDE_EFFECT")
            self.assertIsNone(self.mod._terminal_peer_retry_receipt(workspace, "TASK-001"))
            newest = self._retry_receipt(workspace, "TASK-001", "attempt-c", "KNOWN_TERMINAL")
            os.utime(newest, (time.time() + 5, time.time() + 5))
            receipt = self.mod._terminal_peer_retry_receipt(workspace, "TASK-001")
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["attempt_id"], "attempt-c")
            # Another task's receipt is never this task's evidence.
            self.assertIsNone(self.mod._terminal_peer_retry_receipt(workspace, "TASK-002"))
            # A receipt of a foreign schema is not evidence either.
            (workspace / "runtime/peer-execution/retry-receipts/TASK-003-x.json").write_text(
                json.dumps({"task_id": "TASK-003", "failure_class": "KNOWN_TERMINAL"}),
                encoding="utf-8",
            )
            self.assertIsNone(self.mod._terminal_peer_retry_receipt(workspace, "TASK-003"))

    def test_terminal_recovery_preconditions_fail_closed(self) -> None:
        """No receipt, a non-terminal class, or a live attempt: the guard still holds."""
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            calls: list[tuple[str, ...]] = []

            def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
                calls.append((command, *rest))
                if command == "status":
                    return {
                        "tasks": [{"id": "TASK-001", "runtime_state": "FAILED"}],
                        "live_execution_attempts": [
                            {"task_id": "TASK-001", "attempt_id": "attempt-live"}
                        ],
                    }
                raise AssertionError(f"unexpected pec {command}")

            with unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec):
                # No receipt at all: not even status is consulted.
                self.assertFalse(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
                self.assertEqual(calls, [])
                # KNOWN_TERMINAL receipt but the Controller still holds a live attempt.
                self._retry_receipt(workspace, "TASK-001", "attempt-live", "KNOWN_TERMINAL")
                self.assertFalse(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
                self.assertEqual([c[0] for c in calls], ["status"])
            # And the guard itself: FAILED without a recoverable receipt is refused
            # with the original message, unchanged.
            with (
                unittest.mock.patch.object(
                    self.mod,
                    "pec_status_tasks",
                    return_value=[{"id": "TASK-009", "runtime_state": "FAILED"}],
                ),
                self.assertRaises(self.mod.CampaignError) as caught,
            ):
                self.mod._prepare_peer_unit(workspace, {"id": "TASK-009"}, trace=None)
            self.assertIn("does not blind-retry", str(caught.exception))

    def test_terminal_recovery_goes_through_the_controller_front_door(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            repository = workspace / "repo"
            repository.mkdir()
            (workspace / "runtime").mkdir()
            (workspace / "runtime" / "LAUNCH.json").write_text(
                json.dumps({"campaign_id": "CAMP", "target_worktree": str(repository)}),
                encoding="utf-8",
            )
            self._retry_receipt(workspace, "TASK-001", "attempt-dead", "KNOWN_TERMINAL")
            calls: list[tuple[str, ...]] = []

            def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
                calls.append((command, *rest))
                if command == "status":
                    return {"tasks": [], "live_execution_attempts": []}
                if command == "fresh-workspace":
                    return {"recovery": {"status": "RECOVERED"}}
                raise AssertionError(f"unexpected pec {command}")

            revoked: list[str] = []
            grant = {"lease_id": "lease-dead", "task_id": "TASK-001"}
            fake_grants = unittest.mock.Mock()
            fake_grants.latest_grant_receipt.return_value = (1, grant)
            fake_grants.revoke_task_grant.side_effect = lambda g, *, reason: revoked.append(reason)
            with (
                unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=fake_grants),
            ):
                self.assertTrue(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
            self.assertEqual(calls[0][0], "status")
            fresh = calls[1]
            self.assertEqual(fresh[0], "fresh-workspace")
            self.assertIn("--task-id", fresh)
            self.assertEqual(fresh[fresh.index("--task-id") + 1], "TASK-001")
            self.assertEqual(fresh[fresh.index("--repository") + 1], str(repository))
            self.assertEqual(fresh[fresh.index("--actor") + 1], "make-campaign")
            self.assertIn("KNOWN_TERMINAL", fresh[fresh.index("--reason") + 1])
            self.assertEqual(len(revoked), 1)
            self.assertIn("recovered", revoked[0])

    def test_terminal_recovery_emits_revoke_success_not_grant_presence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            repository = workspace / "repo"
            repository.mkdir()
            (workspace / "runtime").mkdir()
            (workspace / "runtime" / "LAUNCH.json").write_text(
                json.dumps({"campaign_id": "CAMP", "target_worktree": str(repository)}),
                encoding="utf-8",
            )
            self._retry_receipt(workspace, "TASK-001", "attempt-dead", "KNOWN_TERMINAL")
            events: list[dict[str, Any]] = []

            def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
                if command == "status":
                    return {
                        "tasks": [
                            {
                                "id": "TASK-001",
                                "repository_local_path": str(repository),
                                "consumed_attempts": 0,
                                "max_attempts": 3,
                            }
                        ],
                        "live_execution_attempts": [],
                    }
                if command == "fresh-workspace":
                    return {"recovery": {"status": "RECOVERED"}}
                raise AssertionError(f"unexpected pec {command}")

            grant = {"lease_id": "lease-dead", "task_id": "TASK-001"}
            fake_grants = unittest.mock.Mock()
            fake_grants.latest_grant_receipt.return_value = (1, grant)
            fake_grants.revoke_task_grant.return_value = {
                "revoked": False,
                "reason": "grant carries no live runtime binding",
            }
            with (
                unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=fake_grants),
                unittest.mock.patch.object(
                    self.mod, "emit", side_effect=lambda *a, **k: events.append(k)
                ),
            ):
                self.assertTrue(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
            self.assertEqual(events[-1]["metadata"]["grant_revoked"], False)

    def _recovery_workspace(self, raw: str) -> tuple[Path, Path]:
        workspace = Path(raw)
        repository = workspace / "repo"
        repository.mkdir()
        (workspace / "runtime").mkdir()
        (workspace / "runtime" / "LAUNCH.json").write_text(
            json.dumps({"campaign_id": "CAMP", "target_worktree": str(repository)}),
            encoding="utf-8",
        )
        self._retry_receipt(workspace, "TASK-001", "attempt-dead", "KNOWN_TERMINAL")
        return workspace, repository

    def _recovery_pec(self, repository: Path, calls: list[str]) -> Any:
        def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
            calls.append(command)
            if command == "status":
                return {
                    "tasks": [
                        {
                            "id": "TASK-001",
                            "repository_local_path": str(repository),
                            "consumed_attempts": 1,
                            "max_attempts": 3,
                        }
                    ],
                    "live_execution_attempts": [],
                }
            if command == "fresh-workspace":
                return {"recovery": {"status": "RECOVERED"}}
            raise AssertionError(f"unexpected pec {command}")

        return fake_pec

    def test_terminal_recovery_halts_when_the_old_lease_is_still_active(self) -> None:
        """A revoke that fails while the lease stays ACTIVE stops recovery cold.

        Nothing about the Controller workspace changes: `fresh-workspace` is
        never issued, so the task stays FAILED with its receipt in place and the
        next front-door pass retries this same step instead of finding a STALE
        task whose old window still holds live mutation authority.
        """
        with tempfile.TemporaryDirectory() as raw:
            workspace, repository = self._recovery_workspace(raw)
            calls: list[str] = []
            events: list[dict[str, Any]] = []
            fake_grants = unittest.mock.Mock()
            fake_grants.latest_grant_receipt.return_value = (
                1,
                {"lease_id": "lease-live", "task_id": "TASK-001"},
            )
            fake_grants.revoke_task_grant.side_effect = RuntimeError("autonomy store unreachable")
            fake_grants.grant_lease_status.return_value = "ACTIVE"
            with (
                unittest.mock.patch.object(
                    self.mod, "pec_cmd", side_effect=self._recovery_pec(repository, calls)
                ),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=fake_grants),
                unittest.mock.patch.object(
                    self.mod, "emit", side_effect=lambda *a, **k: events.append(k)
                ),
                self.assertRaises(self.mod.CampaignError) as ctx,
            ):
                self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
            self.assertEqual(ctx.exception.error_code, "GRANT_RETIREMENT_FAILED")
            self.assertIn("lease-live", str(ctx.exception))
            self.assertNotIn("fresh-workspace", calls)
            self.assertEqual(events, [])

    def test_terminal_recovery_continues_when_a_failed_revoke_left_no_live_lease(self) -> None:
        """The lease row, not the exception, decides; the report stays truthful."""
        with tempfile.TemporaryDirectory() as raw:
            workspace, repository = self._recovery_workspace(raw)
            calls: list[str] = []
            events: list[dict[str, Any]] = []
            fake_grants = unittest.mock.Mock()
            fake_grants.latest_grant_receipt.return_value = (
                1,
                {"lease_id": "lease-dead", "task_id": "TASK-001"},
            )
            fake_grants.revoke_task_grant.side_effect = RuntimeError("autonomy store unreachable")
            fake_grants.grant_lease_status.return_value = "REVOKED"
            with (
                unittest.mock.patch.object(
                    self.mod, "pec_cmd", side_effect=self._recovery_pec(repository, calls)
                ),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=fake_grants),
                unittest.mock.patch.object(
                    self.mod, "emit", side_effect=lambda *a, **k: events.append(k)
                ),
            ):
                self.assertTrue(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
            self.assertIn("fresh-workspace", calls)
            metadata = events[-1]["metadata"]
            self.assertEqual(metadata["grant_revoked"], False)
            self.assertEqual(metadata["grant_lease_status"], "REVOKED")

    def test_terminal_recovery_retires_authority_before_touching_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace, repository = self._recovery_workspace(raw)
            order: list[str] = []
            fake_grants = unittest.mock.Mock()
            fake_grants.latest_grant_receipt.return_value = (
                1,
                {"lease_id": "lease-1", "task_id": "TASK-001"},
            )
            fake_grants.revoke_task_grant.side_effect = lambda *a, **k: (
                order.append("revoke") or {"revoked": True}
            )
            fake_grants.grant_lease_status.return_value = "REVOKED"
            pec = self._recovery_pec(repository, order)
            with (
                unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=pec),
                unittest.mock.patch.object(self.mod, "_grant_module", return_value=fake_grants),
                unittest.mock.patch.object(self.mod, "emit"),
            ):
                self.assertTrue(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
                )
            self.assertLess(order.index("revoke"), order.index("fresh-workspace"))

    def test_terminal_recovery_refuses_when_consumed_generations_meet_budget(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._retry_receipt(workspace, "TASK-001", "attempt-dead", "KNOWN_TERMINAL")

            def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
                if command == "status":
                    return {
                        "tasks": [
                            {
                                "id": "TASK-001",
                                "consumed_attempts": 1,
                                "max_attempts": 1,
                            }
                        ],
                        "live_execution_attempts": [],
                    }
                raise AssertionError(f"unexpected pec {command}")

            with (
                unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec),
                self.assertRaises(self.mod.CampaignError) as caught,
            ):
                self.mod._recover_terminal_peer_task(workspace, "TASK-001", trace=None)
            self.assertEqual(caught.exception.error_code, "RETRY_BUDGET_EXHAUSTED")

    def test_terminal_recovery_uses_the_task_registered_repository(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            campaign_target = workspace / "campaign-target"
            campaign_target.mkdir()
            task_repo = workspace / "task-repo"
            task_repo.mkdir()
            (workspace / "runtime").mkdir()
            (workspace / "runtime" / "LAUNCH.json").write_text(
                json.dumps({"campaign_id": "CAMP", "target_worktree": str(campaign_target)}),
                encoding="utf-8",
            )
            self._retry_receipt(workspace, "TASK-002", "attempt-dead", "KNOWN_TERMINAL")
            calls: list[tuple[str, ...]] = []

            def fake_pec(ws: Path, command: str, *rest: str) -> dict[str, Any]:
                calls.append((command, *rest))
                if command == "status":
                    return {
                        "tasks": [
                            {
                                "id": "TASK-002",
                                "repository_id": "org/other",
                                "repository_local_path": str(task_repo),
                                "consumed_attempts": 0,
                                "max_attempts": 3,
                            }
                        ],
                        "live_execution_attempts": [],
                    }
                if command == "fresh-workspace":
                    return {"recovery": {"status": "RECOVERED"}}
                raise AssertionError(f"unexpected pec {command}")

            with unittest.mock.patch.object(self.mod, "pec_cmd", side_effect=fake_pec):
                self.assertTrue(
                    self.mod._recover_terminal_peer_task(workspace, "TASK-002", trace=None)
                )
            fresh = [c for c in calls if c[0] == "fresh-workspace"][0]
            self.assertEqual(fresh[fresh.index("--repository") + 1], str(task_repo))
            self.assertNotEqual(fresh[fresh.index("--repository") + 1], str(campaign_target))

    def test_stale_unittest_yields_to_inferred_pytest(self) -> None:
        self.assertTrue(
            self.mod.stale_unittest_should_yield_to_pytest(
                "python3 -m unittest tests/test_x.py",
                "python3 -m pytest tests/test_x.py --tb=short -q --no-cov",
            )
        )
        self.assertFalse(
            self.mod.stale_unittest_should_yield_to_pytest(
                "python3 -c 'print(0)'",
                "python3 -m pytest tests/test_x.py --tb=short -q --no-cov",
            )
        )

    def test_adoptable_inferred_command_accepts_bash_n(self) -> None:
        self.assertTrue(self.mod.adoptable_inferred_command("bash -n ops/scripts/run_pr_gate.sh"))
        self.assertTrue(self.mod.adoptable_inferred_command("python3 -m unittest tests/x.py"))
        self.assertTrue(
            self.mod.adoptable_inferred_command("python3 -m pytest tests/x.py --tb=short -q")
        )
        self.assertTrue(self.mod.adoptable_inferred_command("test -s 'ops/scripts/run_pr_gate.sh'"))
        self.assertTrue(self.mod.adoptable_inferred_command("ls -1 'a' 'b' >/dev/null"))
        self.assertFalse(self.mod.adoptable_inferred_command("true"))
        self.assertFalse(self.mod.adoptable_inferred_command(""))

    def test_fill_inferred_validation_keeps_declared_commands(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "docs/program-execution").mkdir(parents=True)
            (root / "docs/program-execution/TASK-001.md").write_text("x\n", encoding="utf-8")
            contract_path = root / "TASK-001.json"
            contract = {
                "task_id": "TASK-001",
                "writable_paths": ["docs/program-execution/TASK-001.md"],
                "validation_commands": ["git status --short"],
            }
            filled = self.mod.fill_inferred_validation(contract_path, contract, root)
            self.assertEqual(filled.get("validation_commands"), ["git status --short"])

    def test_fill_inferred_validation_from_writable_tests(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "ops/scripts/tests").mkdir(parents=True)
            (root / "ops/scripts/tests/test_resolve_stack_tip.py").write_text(
                "def test_ok():\n    assert True\n", encoding="utf-8"
            )
            contract_path = root / "TASK-001.json"
            contract = {
                "task_id": "TASK-001",
                "writable_paths": [
                    "ops/scripts/resolve_stack_tip.py",
                    "ops/scripts/tests/test_resolve_stack_tip.py",
                ],
                "validation_commands": [],
            }
            filled = self.mod.fill_inferred_validation(contract_path, contract, root)
            self.assertEqual(filled.get("validation_commands"), [])
            launch = self.mod._load_script(
                "launchability",
                self.mod.PE_ROOT / "scripts/launchability.py",
            )
            inferred = launch.infer_validation_commands(contract, root)
            self.assertTrue(inferred[0].startswith("python3 -m pytest"))
            self.assertIn("--no-cov", inferred[0])
            self.assertIn("test_resolve_stack_tip.py", inferred[0])

    def test_live_lock_missing_seed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            rendered = workspace / "contracts" / "rendered"
            rendered.mkdir(parents=True)
            (rendered / "TASK-001.json").write_text(
                json.dumps({"writable_paths": ["docs/program-execution/TASK-001.md"]}),
                encoding="utf-8",
            )
            seed = {
                "tasks": [
                    {
                        "id": "T1",
                        "paths": ["ops/scripts/resolve_stack_tip.py"],
                    }
                ]
            }
            self.assertTrue(self.mod.live_lock_missing_seed_paths(seed, workspace))
            (rendered / "TASK-001.json").write_text(
                json.dumps({"writable_paths": ["ops/scripts/resolve_stack_tip.py"]}),
                encoding="utf-8",
            )
            self.assertFalse(self.mod.live_lock_missing_seed_paths(seed, workspace))
            seed["tasks"].append({"id": "T2", "paths": ["ops/scripts/agent_worktree_start.sh"]})
            self.assertFalse(
                self.mod.live_lock_missing_seed_paths(seed, workspace),
                "unrendered later tasks are not a live-lock mismatch",
            )

    def test_load_pec_module_allowlists_file_not_import_path(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.load_pec_module("os")
        self.assertIn("allowlist", str(ctx.exception))
        loaded = self.mod.load_pec_module("exec_env")
        self.assertTrue(hasattr(loaded, "resolve_exec_env"))
        self.assertTrue(str(loaded.__file__).endswith("pec/exec_env.py"))

    def test_draft_bootstrap_is_not_a_live_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)

            def emit(intent: Path, repo_root: Path) -> dict[str, object]:
                campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
                campaign.mkdir(parents=True, exist_ok=True)
                (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
                (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
                return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="bootstrap",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=Path(raw) / "l9",
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=emit,
                        compile_source=lambda source, target: None,
                        validate_blueprint=lambda target: [],
                        admit=lambda blueprint: {},
                        pec_bootstrap=lambda workspace, blueprint: {
                            "ok": True,
                            "draft": True,
                            "output": "draft-honest",
                        },
                    ),
                )
            self.assertIn("admission-draft", str(ctx.exception))

    def test_until_arm_records_tunnel_stages(self) -> None:
        calls: list[str] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            l9 = Path(raw) / "l9"
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="arm",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=emit,
                    compile_source=lambda source, target: calls.append("compile") or None,
                    validate_blueprint=lambda target: calls.append("validate") or [],
                    admit=lambda blueprint: calls.append("admit") or {},
                    pec_bootstrap=lambda workspace, blueprint: (
                        calls.append("bootstrap") or {"ok": True, "draft": False, "output": "ok"}
                    ),
                    arm=lambda workspace, campaign_id: calls.append("arm") or {},
                ),
            )
            self.assertEqual(
                report.stages_completed,
                ["activate", "blueprint", "admit", "bootstrap", "arm"],
            )
            self.assertEqual(calls, ["compile", "validate", "admit", "bootstrap", "arm"])
            launch = json.loads(
                (l9 / "programs/demo-activate-v1/runtime/LAUNCH.json").read_text(encoding="utf-8")
            )
            self.assertEqual(launch["campaign_id"], "demo-activate-v1")
            self.assertTrue(launch["only_pec_workspace"])
            self.assertEqual(launch["claimed_task"], "TASK-001")
            self.assertTrue(launch["reconcile_required"])
            self.assertFalse(launch["load_operator_brief"])
            self.assertFalse(launch["operator_ack_required"])
            self.assertTrue(launch["pec_ready_empty_is_expected"])
            self.assertEqual(launch["max_task_minutes"], 15)
            self.assertIn("write_tree", launch)

    def test_quarantine_moves_occupied_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            occupied = Path(raw) / "programs" / "demo-activate-v1"
            occupied.mkdir(parents=True)
            leftover = occupied / "runtime" / "state.sqlite"
            leftover.parent.mkdir(parents=True)
            leftover.write_text("stale\n", encoding="utf-8")
            moved = self.mod.quarantine_occupied(occupied)
            self.assertIsNotNone(moved)
            self.assertFalse(occupied.exists())
            self.assertTrue((moved / "runtime" / "state.sqlite").is_file())

    def test_quarantines_dirty_target_and_rebinds_from_donor(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / "target"
            dest.mkdir()
            _git_init(dest)
            (dest / "dirty.txt").write_text("no\n", encoding="utf-8")
            donor = Path(raw) / "donor"
            donor.mkdir()
            _git_init(donor)
            env = _isolated_git_env()
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(donor),
                    "remote",
                    "set-url",
                    "origin",
                    "https://github.com/Quantum-L9/Cursor-Governance.git",
                ],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(donor), "update-ref", "refs/remotes/origin/main", "HEAD"],
                check=True,
                capture_output=True,
                env=env,
            )
            with patch.dict(
                os.environ,
                _github_redirect("Quantum-L9/Cursor-Governance", donor / _FIXTURE_ORIGIN),
            ):
                self.mod.default_ensure_target_checkout(
                    dest, "Quantum-L9/Cursor-Governance", donor=donor
                )
            self.assertTrue((dest / "README.md").is_file())
            self.assertFalse((dest / "dirty.txt").exists())
            stale = list((Path(raw) / "stale").glob("target-*"))
            self.assertEqual(len(stale), 1)
            self.assertTrue((stale[0] / "dirty.txt").is_file())

    def test_real_admit_bootstrap_reconcile_claims_task_001(self) -> None:
        """No mocks on the live tunnel: leftover pec dir cannot block claim."""
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            leftover = l9 / "programs" / "demo-activate-v1" / "runtime"
            leftover.mkdir(parents=True)
            (leftover / "state.sqlite").write_text("stale-draft\n", encoding="utf-8")
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="arm",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            self.assertEqual(
                report.stages_completed,
                ["activate", "blueprint", "admit", "bootstrap", "arm"],
            )
            workspace = l9 / "programs" / "demo-activate-v1"
            self.assertTrue((workspace / "runtime" / "state.sqlite").is_file())
            stale_dirs = list((l9 / "programs" / "stale").glob("demo-activate-v1-*"))
            self.assertEqual(len(stale_dirs), 1)
            pec = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
            status = subprocess.run(
                [sys.executable, str(pec), "status", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            self.assertFalse(payload.get("admission_draft"))
            task = next(item for item in payload["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "LEASED")
            task_two = next(item for item in payload["tasks"] if item["id"] == "TASK-002")
            self.assertNotEqual(task_two["runtime_state"], "LEASED")
            self.assertEqual(task_two["definition_status"], "ready")
            self.assertEqual(payload["current"]["task_id"], "TASK-001")
            self.assertTrue((workspace / "runtime" / "TASK-002.source.json").is_file())
            stack = json.loads((workspace / "runtime" / "STACK.json").read_text(encoding="utf-8"))
            self.assertEqual(stack["integration_branch"], "campaign/demo-activate-v1")
            self.assertEqual(stack["stack"][0]["pr_base"], "campaign/demo-activate-v1")
            self.assertEqual(stack["stack"][1]["pr_base"], "pec/w0/task-001")
            self.assertNotIn("main", stack["stack"][0]["pr_base"])
            card = (workspace / "runtime" / "TASK-001.md").read_text(encoding="utf-8")
            self.assertIn("Budget: 15 minutes", card)
            self.assertIn("never main", card)
            self.assertNotIn("PE- Memory", card)
            self.assertLess(len(card.splitlines()), 18)
            self.assertTrue((workspace / "runtime" / "TASK-002.md").is_file())

    def test_pr_stack_never_uses_main(self) -> None:
        stack = self.mod.build_pr_stack(
            "demo-activate-v1",
            [
                {"id": "TASK-001", "title": "First", "wave_id": "W0"},
                {"id": "TASK-002", "title": "Second", "wave_id": "W1"},
            ],
        )
        bases = [item["pr_base"] for item in stack["stack"]]
        self.assertEqual(bases, ["campaign/demo-activate-v1", "pec/w0/task-001"])
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.refuse_unstacked_pr_base("origin/main")
        self.assertIn("stack", str(ctx.exception))

    def test_run_cmd_times_out(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.run_cmd([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
        self.assertIn("timed out after 1s", str(ctx.exception))

    def test_host_campaign_ids_only_complete_or_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            status = root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
            status.write_text(
                "schema: l9.program-execution.campaign-status-ledger.v1\n"
                "campaigns:\n"
                "  - id: live-one\n    lifecycle: in_progress\n"
                "  - id: done-one\n    lifecycle: complete\n"
                "  - id: dead-one\n    lifecycle: cancelled\n",
                encoding="utf-8",
            )
            ids = self.mod.host_campaign_ids(root)
            self.assertIn("done-one", ids)
            self.assertIn("dead-one", ids)
            self.assertNotIn("live-one", ids)

    def test_donor_rejected_when_origin_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            donor = Path(raw) / "donor"
            dest = Path(raw) / "dest"
            donor.mkdir()
            _git_init(donor)
            self.assertFalse(self.mod.donor_matches_repository(donor, "Quantum-L9/l9-ci-core"))
            with self.assertRaises(self.mod.CampaignError):
                self.mod.default_ensure_target_checkout(
                    dest, "Quantum-L9/definitely-missing-repo-xyz", donor=donor
                )

    def test_isolate_quarantines_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            worktree = Path(raw) / "wt"
            primary.mkdir()
            _git_init(primary)
            subprocess.run(
                ["git", "-C", str(primary), "branch", "feat/demo-activate-v1"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(primary),
                    "worktree",
                    "add",
                    str(worktree),
                    "feat/demo-activate-v1",
                ],
                check=True,
                capture_output=True,
            )
            (worktree / "dirty.txt").write_text("no\n", encoding="utf-8")
            self.assertTrue(self.mod.is_dirty(worktree))

            def fake_git(*args: str) -> str:
                if args[:2] == ("fetch", "origin"):
                    return ""
                raise self.mod.CampaignError("stop after quarantine")

            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.isolate_worktree(primary, "demo-activate-v1", worktree, git_fn=fake_git)
            self.assertIn("stop after quarantine", str(ctx.exception))
            self.assertFalse(worktree.exists())
            stale = list((Path(raw) / "stale").glob("wt-*"))
            self.assertEqual(len(stale), 1)
            self.assertTrue((stale[0] / "dirty.txt").is_file())

    def test_isolate_wires_new_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            worktree = Path(raw) / "wt"
            primary.mkdir()
            _git_init(primary)
            subprocess.run(
                ["git", "-C", str(primary), "branch", "-M", "main"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(primary), "branch", "feat/demo-activate-v1"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(primary), "update-ref", "refs/remotes/origin/main", "HEAD"],
                check=True,
                capture_output=True,
            )
            wired: list[Path] = []

            def fake_git(*args: str) -> str:
                if args[:2] == ("fetch", "origin"):
                    return ""
                if args[:2] == ("worktree", "add"):
                    subprocess.run(
                        ["git", "-C", str(primary), *args],
                        check=True,
                        capture_output=True,
                    )
                    return ""
                raise AssertionError(args)

            original = self.mod.ensure_workspace_wired

            def spy(workspace: Path) -> None:
                wired.append(workspace)

            self.mod.ensure_workspace_wired = spy  # type: ignore[method-assign]
            try:
                got = self.mod.isolate_worktree(
                    primary, "demo-activate-v1", worktree, git_fn=fake_git
                )
            finally:
                self.mod.ensure_workspace_wired = original  # type: ignore[method-assign]
            self.assertEqual(got, worktree)
            self.assertEqual(wired, [worktree])
            self.assertTrue(worktree.is_dir())

    def test_isolate_resets_leftover_feat_branch_to_origin_main(self) -> None:
        """A local feat/<id> with extra commits is not the exclusive isolate base."""
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            worktree = Path(raw) / "wt"
            primary.mkdir()
            _git_init(primary)
            env = _isolated_git_env()
            subprocess.run(
                ["git", "-C", str(primary), "branch", "-M", "main"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(primary), "update-ref", "refs/remotes/origin/main", "HEAD"],
                check=True,
                capture_output=True,
                env=env,
            )
            base = subprocess.run(
                ["git", "-C", str(primary), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(primary), "checkout", "-q", "-b", "feat/demo-activate-v1"],
                check=True,
                env=env,
            )
            (primary / "local-only.txt").write_text("leftover\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(primary), "add", "local-only.txt"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", *_GIT_IDENTITY, "-C", str(primary), "commit", "-qm", "leftover"],
                check=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(primary), "checkout", "-q", "main"],
                check=True,
                env=env,
            )

            def fake_git(*args: str) -> str:
                if args[:2] == ("fetch", "origin"):
                    return ""
                if args[:2] == ("worktree", "add"):
                    subprocess.run(
                        ["git", "-C", str(primary), *args],
                        check=True,
                        capture_output=True,
                        env=env,
                    )
                    return ""
                raise AssertionError(args)

            original = self.mod.ensure_workspace_wired
            self.mod.ensure_workspace_wired = lambda _workspace: None  # type: ignore[method-assign]
            try:
                self.mod.isolate_worktree(primary, "demo-activate-v1", worktree, git_fn=fake_git)
            finally:
                self.mod.ensure_workspace_wired = original  # type: ignore[method-assign]
            head = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            self.assertEqual(head, base)
            self.assertFalse((worktree / "local-only.txt").exists())

    def test_remote_lineage_prefers_odoo_staging(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            _git_init(repo)
            env = _isolated_git_env()
            subprocess.run(
                ["git", "-C", str(repo), "branch", "-M", "Staging"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/Staging", "HEAD"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/Staging",
                ],
                check=True,
                capture_output=True,
                env=env,
            )
            ref = self.mod.remote_lineage_ref(
                repo,
                repository_id="cryptoxdog/IB-Odoo_19",
                declared="origin/Staging",
            )
            self.assertEqual(ref, "origin/Staging")

    def test_existing_checkout_fetches_remote_default_before_trusting_stale_ref(self) -> None:
        """An exclusive checkout whose origin/main is stale is rebound to the live tip.

        The remote-tracking ref proves what origin *had* when the checkout was
        made. Nothing later in the run fetches the default branch, so the
        admission SHA and campaign/<id> would otherwise be based on that day.
        """
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            env = _isolated_git_env()
            seed = temp / "seed"
            seed.mkdir()
            _git_init(seed)
            remote = seed / _FIXTURE_ORIGIN
            dest = temp / "target"
            subprocess.run(
                ["git", "clone", "-q", str(remote), str(dest)],
                check=True,
                capture_output=True,
                env=env,
            )
            stale = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "origin/main"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            # origin advances after the checkout was created.
            (seed / "advanced.txt").write_text("newer\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(seed), "add", "advanced.txt"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", *_GIT_IDENTITY, "-C", str(seed), "commit", "-qm", "advance origin"],
                check=True,
                env=env,
            )
            tip = _git_publish(seed)
            self.assertNotEqual(tip, stale)

            got = self.mod.default_ensure_target_checkout(dest, "Quantum-L9/Cursor-Governance")

            self.assertEqual(got, dest.resolve())
            head = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            self.assertEqual(head, tip, "checkout was bound to the stale remote-tracking ref")
            tracking = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "origin/main"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            self.assertEqual(tracking, tip)
            self.assertTrue((dest / "advanced.txt").is_file())

    def test_existing_checkout_stops_when_lineage_unprovable_after_fetch(self) -> None:
        """No remote-tracking ref and an unreachable origin: stop, never return."""
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            env = _isolated_git_env()
            dest = temp / "target"
            dest.mkdir()
            _git_init(dest)
            subprocess.run(
                ["git", "-C", str(dest), "remote", "set-url", "origin", str(temp / "missing.git")],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(dest), "symbolic-ref", "--delete", "refs/remotes/origin/HEAD"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(dest), "update-ref", "-d", "refs/remotes/origin/main"],
                check=True,
                capture_output=True,
                env=env,
            )
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.default_ensure_target_checkout(dest, "Quantum-L9/Cursor-Governance")
            self.assertIn("remote lineage", str(ctx.exception))

    def test_existing_remote_tracking_ref_is_not_lineage_when_origin_cannot_confirm_it(
        self,
    ) -> None:
        """origin/main exists locally but origin is unreachable: the ref is not trusted."""
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            env = _isolated_git_env()
            dest = temp / "target"
            dest.mkdir()
            _git_init(dest)
            subprocess.run(
                ["git", "-C", str(dest), "remote", "set-url", "origin", str(temp / "missing.git")],
                check=True,
                capture_output=True,
                env=env,
            )
            verify = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "--verify", "origin/main"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(verify.returncode, 0, "fixture must keep a stale origin/main")
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod._bind_exclusive_remote_lineage(
                    dest, repository_id="Quantum-L9/Cursor-Governance"
                )
            self.assertIn("remote lineage", str(ctx.exception))

    def _checkout_tracking_settings(self, dest: Path) -> str:
        """A checkout that tracks `.claude/settings.json`, published to its origin."""
        env = _isolated_git_env()
        dest.mkdir()
        _git_init(dest)
        settings = dest / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text(_TRACKED_SETTINGS, encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(dest), "add", "--", ".claude/settings.json"],
            check=True,
            capture_output=True,
            env=env,
        )
        subprocess.run(
            ["git", *_GIT_IDENTITY, "-C", str(dest), "commit", "-qm", "track settings"],
            check=True,
            env=env,
        )
        return _git_publish(dest)

    def test_strip_session_residue_keeps_tracked_settings_and_removes_untracked(self) -> None:
        """P-PE-TRACKED-CONFIG at the campaign-side cleanup site."""
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / "target"
            self._checkout_tracking_settings(dest)
            settings = dest / ".claude" / "settings.json"
            commands = dest / ".claude" / "commands"
            commands.mkdir()
            (commands / "session.md").write_text("residue\n", encoding="utf-8")
            receipts = dest / ".l9" / "memory" / "receipts"
            receipts.mkdir(parents=True)
            (receipts / "unknown-agent__1.json").write_text("{}\n", encoding="utf-8")

            self.mod.strip_session_residue(dest)

            self.assertEqual(settings.read_text(encoding="utf-8"), _TRACKED_SETTINGS)
            self.assertFalse(commands.exists())
            self.assertFalse((receipts / "unknown-agent__1.json").exists())
            self.assertFalse(self.mod.has_foreign_session_residue(dest))
            self.assertFalse(self.mod.is_dirty(dest))

    def test_untracked_settings_file_is_still_residue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / "target"
            dest.mkdir()
            _git_init(dest)
            settings = dest / ".claude" / "settings.json"
            settings.parent.mkdir()
            settings.write_text('{"untracked": true}\n', encoding="utf-8")
            self.assertTrue(self.mod.has_foreign_session_residue(dest))
            self.mod.strip_session_residue(dest)
            self.assertFalse(settings.exists())
            self.assertFalse(self.mod.has_foreign_session_residue(dest))

    def test_existing_checkout_with_tracked_settings_is_reused_not_quarantined(self) -> None:
        """Re-preparing a checkout that tracks its settings must not quarantine it.

        Deleting the tracked file made the tree dirty, which sent the whole
        checkout to `stale/` and re-cloned it on every campaign run.
        """
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            dest = temp / "target"
            tip = self._checkout_tracking_settings(dest)
            settings = dest / ".claude" / "settings.json"
            commands = dest / ".claude" / "commands"
            commands.mkdir()
            (commands / "session.md").write_text("residue\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                _github_redirect("Quantum-L9/Cursor-Governance", dest / _FIXTURE_ORIGIN),
            ):
                got = self.mod.default_ensure_target_checkout(dest, "Quantum-L9/Cursor-Governance")

            self.assertEqual(got, dest.resolve())
            self.assertEqual(list((temp / "stale").glob("target-*")), [])
            self.assertEqual(settings.read_text(encoding="utf-8"), _TRACKED_SETTINGS)
            self.assertFalse(commands.exists())
            self.assertFalse(self.mod.is_dirty(dest))
            head = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=_isolated_git_env(),
            ).stdout.strip()
            self.assertEqual(head, tip)

    def test_integration_branch_starts_from_origin_staging_not_dirty_head(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            origin = temp / "origin"
            origin.mkdir()
            _git_init(origin)
            env = _isolated_git_env()
            subprocess.run(
                ["git", "-C", str(origin), "branch", "-M", "Staging"],
                check=True,
                capture_output=True,
                env=env,
            )
            staging = subprocess.run(
                ["git", "-C", str(origin), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            clone = temp / "clone"
            subprocess.run(
                ["git", "clone", "-q", str(origin), str(clone)],
                check=True,
                capture_output=True,
                env=env,
            )
            (clone / "local-only.txt").write_text("operator\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(clone), "add", "local-only.txt"],
                check=True,
                env=env,
            )
            subprocess.run(
                ["git", *_GIT_IDENTITY, "-C", str(clone), "commit", "-qm", "local leftover"],
                check=True,
                env=env,
            )
            branch = self.mod.ensure_integration_branch(
                clone,
                "demo",
                repository_id="cryptoxdog/IB-Odoo_19",
                source_of_truth="origin/Staging",
            )
            local = subprocess.run(
                ["git", "-C", str(clone), "rev-parse", branch],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            self.assertEqual(local, staging)

    def test_policy_remediation_scope_is_stacked_only(self) -> None:
        policy = yaml.safe_load(
            (PE_ROOT / "campaigns/CAMPAIGN_EXECUTION_POLICY.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            policy["publish"]["remediations"]["scope"],
            "stacked_prs_opened_by_this_run",
        )
        self.assertNotEqual(
            policy["publish"]["remediations"]["scope"],
            "all_open_prs_in_target_repo",
        )

    def test_two_task_fixture_reaches_completed(self) -> None:
        """The full campaign path: both tasks verified and committed locally.

        `L9_PE_RELEASE_AUTHORIZED` is set here on purpose: it must not reopen
        publication, so the run still ends at `execute` and opens no PR.
        """
        opened: list[str] = []
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            with patch.dict(os.environ, {"L9_PE_RELEASE_AUTHORIZED": "test release transition"}):
                report = self.mod.run_campaign(
                    root / "intent.yaml",
                    until="execute",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=self.activate.compile_activation,
                        make_pr=lambda worktree, campaign_id: (
                            opened.append(campaign_id)
                            or {"number": 7, "url": "https://example.test/7"}
                        ),
                    ),
                )
            self.assertEqual(opened, [])
            self.assertIn("execute", report.stages_completed)
            self.assertNotIn("close", report.stages_completed)
            receipt = json.loads(
                (l9 / "programs/demo-activate-v1/receipts/verification/TASK-001.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(receipt["kernel_verdict"], "PASS")
            self.assertEqual(
                sorted({gate for gate in receipt["gates"].values()}),
                ["PASS"],
                msg=f"non-PASS gates: {receipt['gates']}",
            )
            self.assertEqual(
                [item["command"] for item in receipt["validations"]],
                ["git status --short"],
            )

    def test_blueprint_fingerprint_survives_recompilation(self) -> None:
        """A recompiled Blueprint must fingerprint alike, or no repeat is ever seen."""
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            (blueprint / "schemas").mkdir(parents=True)
            (blueprint / "PROGRAM.yaml").write_text(
                "campaign_id: demo-activate-v1\nsnapshot_at: '2026-08-18T18:00:00+00:00'\n",
                encoding="utf-8",
            )
            (blueprint / "MANIFEST.yaml").write_text(
                "files:\n- path: PROGRAM.yaml\n  sha256: " + ("a" * 64) + "\n",
                encoding="utf-8",
            )
            before = self.mod.blueprint_fingerprint(blueprint)

            # Recompile: same program, new emission stamp, new derived digest.
            (blueprint / "PROGRAM.yaml").write_text(
                "campaign_id: demo-activate-v1\nsnapshot_at: '2026-08-18T19:45:12+00:00'\n",
                encoding="utf-8",
            )
            (blueprint / "MANIFEST.yaml").write_text(
                "files:\n- path: PROGRAM.yaml\n  sha256: " + ("b" * 64) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(before, self.mod.blueprint_fingerprint(blueprint))

            # A real content change must still register.
            (blueprint / "PROGRAM.yaml").write_text(
                "campaign_id: other-campaign-v1\nsnapshot_at: '2026-08-18T19:45:12+00:00'\n",
                encoding="utf-8",
            )
            self.assertNotEqual(before, self.mod.blueprint_fingerprint(blueprint))

    def test_campaign_run_creates_events_jsonl(self) -> None:
        """A real close-through run leaves telemetry the harvester can read.

        Publication moved out of autonomous execution, so driving the chain
        through `close` opens the release transition explicitly -- the same
        setup `test_two_task_fixture_reaches_completed` uses. The subject here
        is the telemetry the run emits, not the release gate itself, which keeps
        its own coverage in the refusal tests.
        """
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            with patch.dict(os.environ, {"L9_PE_RELEASE_AUTHORIZED": "test release transition"}):
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="execute",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=self.activate.compile_activation,
                        make_pr=lambda worktree, campaign_id: {"number": 7, "url": "http://x/7"},
                    ),
                )
            workspace = l9 / "programs/demo-activate-v1"
            events_path = workspace / "telemetry/events.jsonl"
            self.assertTrue(events_path.is_file())
            self.assertTrue((workspace / "telemetry/run-summary.json").is_file())
            self.assertTrue((workspace / "telemetry/run-summary.md").is_file())

            events = [json.loads(line) for line in events_path.read_text().splitlines() if line]
            self.assertEqual({item["schema"] for item in events}, {"pe.execution-trace.v1"})
            self.assertEqual(len({item["run_id"] for item in events}), 1)
            operations = {item["operation"] for item in events}
            for operation in (
                "campaign_run",
                "input_classification",
                "compile_campaign_source",
                "blueprint_validation",
                "acceptance",
                "pec_bootstrap",
                "arm",
                "execute",
                "validation_command",
                "pec_verify",
            ):
                self.assertIn(operation, operations)
            lifecycle = {item["event_type"] for item in events}
            for event_type in (
                "TASK_ELIGIBLE",
                "TASK_SELECTED",
                "TASK_WORKTREE_READY",
                "TASK_WORKER_STARTED",
                "TASK_FIRST_WRITE",
                "TASK_VALIDATION_STARTED",
                "TASK_VALIDATION_FINISHED",
                "TASK_VERIFY_STARTED",
                "TASK_VERIFY_FINISHED",
                "TASK_COMPLETED",
            ):
                self.assertIn(event_type, lifecycle)

            summary = json.loads((workspace / "telemetry/run-summary.json").read_text())
            self.assertEqual(summary["campaign_id"], "demo-activate-v1")
            self.assertEqual(summary["task_counts"], {"completed": 2, "attempted": 2})
            self.assertIsNotNone(summary["timing"]["time_to_first_write_ms"])
            self.assertGreater(summary["timing"]["preparation_ms"], 0)
            # The campaign_run span is the wall clock, not a preparation cost.
            self.assertLess(summary["timing"]["preparation_ms"], summary["wall_clock_ms"])
            campaign_run = [
                item
                for item in events
                if item["operation"] == "campaign_run" and item["status"] == "PASSED"
            ]
            self.assertEqual([item["category"] for item in campaign_run], ["campaign"])
            self.assertEqual(summary["operation_counts"]["compile_campaign_source"], 1)
            self.assertEqual(summary["operation_counts"]["pec_bootstrap"], 1)
            self.assertEqual(summary["operation_counts"]["pec_verify"], 2)
            self.assertEqual(summary["operation_counts"]["validation_command"], 2)
            self.assertEqual(summary["failure_counts"], {})
            for task_id in ("TASK-001", "TASK-002"):
                task = summary["per_task"][task_id]
                self.assertTrue(task["completed"])
                self.assertEqual(task["attempts"], 1)
                self.assertIsNotNone(task["eligible_to_first_write_ms"])

    def test_default_repo_root_derives_write_root_from_l9(self) -> None:
        """`main()` runs with repo_root=None; the isolate stage must not crash.

        The write_root default is the production entry path: the Makefile
        `campaign` target does not pass --repo-root, and every other test in
        this module passes repo_root= explicitly, so a dropped default here
        would leave the whole suite green while every real CLI run dies with
        UnboundLocalError.

        When repo_root is None the primary IS the host repo, so this models
        production: primary is a real git repo with an origin the isolate
        stage can fetch.
        """
        with tempfile.TemporaryDirectory() as raw:
            primary = _host_repo(Path(raw) / "primary")
            _git_init(primary)
            # The production primary's main contains the whole host repo, so the
            # isolated worktree inherits the policy files the compile step
            # patches. Include them in the init commit.
            git_env = _isolated_git_env()
            subprocess.run(
                ["git", "add", "-A"], cwd=primary, check=True, capture_output=True, env=git_env
            )
            subprocess.run(
                ["git", "commit", "-m", "init", "--amend", "--no-edit"],
                cwd=primary,
                check=True,
                capture_output=True,
                env=git_env,
            )
            origin = Path(raw) / "origin.git"
            origin.mkdir()
            subprocess.run(
                ["git", "init", "--bare", str(origin)],
                check=True,
                capture_output=True,
                env=git_env,
            )
            subprocess.run(
                ["git", "remote", "set-url", "origin", str(origin)],
                cwd=primary,
                check=True,
                capture_output=True,
                env=git_env,
            )
            subprocess.run(
                ["git", "push", "origin", "HEAD:main"],
                cwd=primary,
                check=True,
                capture_output=True,
                env=git_env,
            )
            l9 = Path(raw) / "l9"
            # Same planted target the other execute-through tests use. Without
            # it, repo_root=None falls through to a GitHub clone of the live
            # host, and a shallow SSOT on this machine fails history_walkable.
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            report = self.mod.run_campaign(
                primary / "intent.yaml",
                until="execute",
                primary=primary,
                # repo_root left None, worktree left None -- the main() shape.
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                    make_pr=lambda worktree, campaign_id: {"number": 7, "url": "http://x/7"},
                ),
            )
            self.assertEqual(
                str(report.worktree),
                str((l9 / "gov-worktrees" / "demo-activate-v1").resolve()),
            )

    def test_validation_commands_record_exit_code_not_command_text(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw)
            _git_init(worktree)
            trace = self.mod.pe_trace.ExecutionTrace(worktree, "demo-activate-v1")
            results = self.mod.run_declared_validations(
                worktree,
                [
                    "python3 -c 'print(0)'",
                    'python3 -c \'import sys; sys.stderr.write("boom-detail"); '
                    + "raise SystemExit(3)'",
                ],
                trace=trace,
                task_id="TASK-001",
            )
            self.assertEqual([item["exit_code"] for item in results], [0, 3])
            spans = [
                item
                for item in self.mod.pe_trace.read_events(worktree)
                if item["operation"] == "validation_command" and item["status"] != "STARTED"
            ]
            self.assertEqual([item["status"] for item in spans], ["PASSED", "FAILED"])
            self.assertEqual(spans[1]["error_code"], "VALIDATION_COMMAND_FAILED")
            self.assertEqual(spans[0]["safe_metadata"]["exit_code"], 0)
            self.assertEqual(spans[1]["safe_metadata"]["exit_code"], 3)
            self.assertEqual(spans[0]["task_id"], "TASK-001")
            # Position identifies which declared command this span is; the
            # command text and the resolved cwd are deliberately not persisted.
            self.assertEqual(spans[0]["safe_metadata"]["count"], 1)
            self.assertEqual(spans[0]["safe_metadata"]["validation_count"], 2)
            for span in spans:
                self.assertNotIn("resolved_cwd", span["safe_metadata"])
                self.assertNotIn("command", span["safe_metadata"])
            # The failing command's output tail reaches the attempt receipt,
            # never the trace.
            self.assertIsNone(spans[1]["safe_message"])
            self.assertIn("boom-detail", results[1]["evidence"])

    def test_campaign_failure_still_generates_summary(self) -> None:
        """A campaign that dies mid-preparation still leaves a harvestable trace."""

        def _explode(source: Path, blueprint: Path) -> None:
            raise RuntimeError("compile blew up")

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            with self.assertRaises(RuntimeError):
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="execute",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        compile_activation=self.activate.compile_activation,
                        compile_source=_explode,
                    ),
                )
            workspace = l9 / "programs/demo-activate-v1"
            self.assertTrue((workspace / "telemetry/events.jsonl").is_file())
            summary = json.loads((workspace / "telemetry/run-summary.json").read_text())
            self.assertTrue((workspace / "telemetry/run-summary.md").is_file())
            # One root cause, counted once, even though it unwound through
            # the enclosing campaign_run span as well.
            self.assertEqual(summary["failure_counts"]["RuntimeError"]["count"], 1)
            events = [
                json.loads(line)
                for line in (workspace / "telemetry/events.jsonl").read_text().splitlines()
                if line
            ]
            failed = [item for item in events if item["status"] == "FAILED"]
            self.assertEqual(
                [item["operation"] for item in failed],
                ["compile_campaign_source", "campaign_run"],
            )
            self.assertEqual(failed[0]["safe_message"], "compile blew up")
            self.assertEqual(failed[0]["error_class"], "RuntimeError")
            self.assertFalse(failed[0]["safe_metadata"]["propagated"])
            self.assertTrue(failed[1]["safe_metadata"]["propagated"])

    def test_trace_command_harvests_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            trace = self.mod.pe_trace.ExecutionTrace(workspace, "demo-activate-v1")
            with trace.span("compile", "compile_campaign_source", input_fingerprint="abc"):
                pass
            with trace.span("compile", "compile_campaign_source", input_fingerprint="abc"):
                pass
            self.assertEqual(self.mod.main(["trace", "--workspace", str(workspace)]), 0)
            summary = json.loads((workspace / "telemetry/run-summary.json").read_text())
            self.assertEqual(summary["repeated_operations"][0]["executions"], 2)
            self.assertEqual(summary["repeated_operations"][0]["extra_executions"], 1)
            self.assertTrue((workspace / "telemetry/run-summary.md").is_file())

    def test_trace_command_reports_missing_trace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(self.mod.main(["trace", "--workspace", raw]), 2)

    def test_until_stages_unchanged(self) -> None:
        self.assertEqual(
            self.mod.UNTIL_STAGES,
            (
                "activate",
                "blueprint",
                "admit",
                "bootstrap",
                "arm",
                "execute",
            ),
        )

    def test_plan_window_writes_nuggets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            l9 = Path(raw) / "l9"
            self.mod.run_campaign(
                root / "intent.yaml",
                until="activate",
                primary=Path(raw) / "other-primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            nuggets = l9 / "primed" / "demo-activate-v1" / "nuggets.json"
            self.assertTrue(nuggets.is_file())
            payload = json.loads(nuggets.read_text(encoding="utf-8"))
            self.assertTrue(
                any(item.get("cites") == "stack-proof.json" for item in payload["nuggets"])
            )

    def test_pec_verify_budget_follows_the_contract_command_count(self) -> None:
        """RC-F8: N commands get N per-command budgets, not one shared one."""
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            rendered = workspace / "contracts" / "rendered"
            rendered.mkdir(parents=True)
            (rendered / "TASK-003.json").write_text(
                json.dumps({"validation_commands": ["a", "b", "c"]}), encoding="utf-8"
            )
            self.assertEqual(
                self.mod.pec_verify_timeout(workspace, "TASK-003"),
                self.mod.VALIDATION_TIMEOUT_S * 3 + self.mod.PEC_TIMEOUT_S,
            )
            self.assertEqual(
                self.mod.pec_verify_timeout(workspace, "TASK-404"), self.mod.VALIDATION_TIMEOUT_S
            )
            captured: list[int] = []

            def fake_run_cmd(cmd, timeout=0, **_kwargs):  # noqa: ANN001
                captured.append(int(timeout))
                return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

            with patch.object(self.mod, "run_cmd", fake_run_cmd):
                self.mod.pec_cmd(workspace, "verify", "TASK-003")
            self.assertEqual(captured, [self.mod.VALIDATION_TIMEOUT_S * 3 + self.mod.PEC_TIMEOUT_S])

    def test_launch_pointer_records_the_stage_and_never_a_constant_state(self) -> None:
        """RC-F11: what the pointer says follows the runtime, not the writer."""
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "programs" / "demo-v1"
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()
            (blueprint / "PROGRAM.yaml").write_text(
                "program:\n  id: demo-v1\n  owner: AUTH-001\n", encoding="utf-8"
            )
            common = {
                "campaign_id": "demo-v1",
                "blueprint": str(blueprint),
                "target_worktree": str(Path(raw) / "target"),
                "host_worktree": str(Path(raw) / "host"),
            }
            path = self.mod.write_launch_pointer(workspace, stage="activate", **common)
            launch = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(launch["stage_reached"], "activate")
            self.assertEqual(launch["runtime_status"], "not_bootstrapped")
            self.assertIsNone(launch["claimed_task"])
            self.assertIsNone(launch["execution_card"])
            # PROGRAM.owner is program accountability, not a human who
            # acknowledged anything. With no PHASE0 contract there is no ack
            # identity to report, and inventing one from the owner is the bug
            # test_launch_pointer_reads_human_ack_identity_not_program_owner pins.
            self.assertIsNone(launch["operator_ack_from"])
            self.assertFalse(self.mod.resumable_workspace(workspace))
            (workspace / "runtime" / "campaign-status.json").write_text(
                json.dumps({"runtime_status": "active"}), encoding="utf-8"
            )
            (workspace / "runtime" / "TASK-001.md").write_text("card\n", encoding="utf-8")
            path = self.mod.write_launch_pointer(workspace, stage="arm", **common)
            launch = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(launch["runtime_status"], "active")
            self.assertEqual(launch["claimed_task"], "TASK-001")
            self.assertTrue(launch["execution_card"].endswith("TASK-001.md"))
            with self.assertRaises(ValueError):
                self.mod.write_launch_pointer(workspace, stage="publish", **common)

    def test_one_runtime_root_with_two_spellings(self) -> None:
        """L9_ROOT and L9_RUNTIME_ROOT resolve the same root; a contradiction refuses."""
        with tempfile.TemporaryDirectory() as raw:
            with patch.dict(os.environ, {"L9_ROOT": raw, "L9_RUNTIME_ROOT": ""}):
                self.assertEqual(self.mod.campaign_runtime_root(), Path(raw).resolve())
            with patch.dict(os.environ, {"L9_ROOT": "", "L9_RUNTIME_ROOT": raw}):
                self.assertEqual(self.mod.campaign_runtime_root(), Path(raw).resolve())
            other = Path(raw) / "other"
            other.mkdir()
            with (
                patch.dict(os.environ, {"L9_ROOT": raw, "L9_RUNTIME_ROOT": str(other)}),
                self.assertRaises(RuntimeError) as ctx,
            ):
                self.mod.campaign_runtime_root()
            self.assertIn("different roots", str(ctx.exception))

    def test_pec_verify_uses_validation_timeout(self) -> None:
        captured: list[int] = []

        def fake_run_cmd(cmd, timeout=0, **_kwargs):  # noqa: ANN001
            captured.append(int(timeout))
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

        with patch.object(self.mod, "run_cmd", fake_run_cmd):
            self.mod.pec_cmd(Path("."), "verify", "TASK-003")
            self.mod.pec_cmd(Path("."), "status")
        self.assertEqual(captured[0], self.mod.VALIDATION_TIMEOUT_S)
        self.assertEqual(captured[1], self.mod.PEC_TIMEOUT_S)

    def test_incomplete_skips_change(self) -> None:
        decision = self.mod.dispatch_kernel_change(
            {"kernel_verdict": "INCOMPLETE", "gates": {"validation": "INCOMPLETE"}}
        )
        self.assertEqual(decision["action"], "skip_change")
        self.assertFalse(decision["diagnosed"])

    def test_fail_diagnoses_then_reverifies(self) -> None:
        calls: list[str] = []
        result = self.mod.apply_fail_change(
            {"kernel_verdict": "FAIL", "gates": {"validation": "FAIL"}},
            rewrite=lambda: calls.append("rewrite"),
            reverify=lambda: calls.append("reverify") or {"kernel_verdict": "PASS"},
        )
        self.assertEqual(decision := result["action"], "change")
        self.assertTrue(result["diagnosed"])
        self.assertEqual(calls, ["rewrite", "reverify"])
        self.assertEqual(result["reverify"]["kernel_verdict"], "PASS")
        self.assertEqual(decision, "change")

    def test_local_clone_refused_from_linked_worktree(self) -> None:
        """clone --local from a worktree of a shallow primary yields a hollow target."""
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            worktree = Path(raw) / "wt"
            primary.mkdir()
            _git_init(primary)
            subprocess.run(
                ["git", "-C", str(primary), "branch", "feat/pipe"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(primary), "worktree", "add", str(worktree), "feat/pipe"],
                check=True,
                capture_output=True,
            )
            self.assertTrue(self.mod.is_linked_worktree(worktree))
            self.assertFalse(self.mod.may_clone_local(worktree))
            self.assertTrue(self.mod.may_clone_local(primary))
            self.assertTrue(self.mod.history_walkable(primary))

    def test_history_walkable_rejects_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            _git_init(repo)
            (repo / "second.txt").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "second.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-m", "two"],
                check=True,
                capture_output=True,
            )
            parent = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD^"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (repo / ".git" / "objects" / parent[:2] / parent[2:]).unlink()
            self.assertFalse(self.mod.history_walkable(repo))

    def test_github_repository_is_decided_by_host_not_substring(self) -> None:
        """CodeQL: `"github.com" in url` accepted any URL mentioning GitHub."""
        parse = self.mod.github_repository_from_url
        self.assertEqual(parse("https://github.com/Quantum-L9/Repo.git"), "Quantum-L9/Repo")
        self.assertEqual(parse("git@github.com:Quantum-L9/Repo.git"), "Quantum-L9/Repo")
        self.assertEqual(parse("ssh://git@github.com/Quantum-L9/Repo"), "Quantum-L9/Repo")
        self.assertIsNone(parse("https://evil.example/github.com/Quantum-L9/Repo"))
        self.assertIsNone(parse("https://github.com.evil.example/Quantum-L9/Repo"))
        self.assertIsNone(parse("https://gitlab.example/Quantum-L9/Repo"))
        self.assertIsNone(parse(""))

    def test_ensure_target_history_refuses_a_lookalike_origin(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            _git_init(repo)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "set-url",
                    "origin",
                    "https://github.com/Other/Repo.git",
                ],
                check=True,
                capture_output=True,
            )
            # A walkable, non-shallow checkout returns before the origin is
            # read; mark it shallow so the repair path (and its guard) runs.
            head = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (repo / ".git" / "shallow").write_text(head + "\n", encoding="utf-8")
            self.assertTrue(self.mod.is_shallow_repo(repo))
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.ensure_target_history(repo, "Quantum-L9/unused")
            self.assertIn("Other/Repo", str(ctx.exception))

    def test_ensure_target_history_passes_walkable_repo(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            _git_init(repo)
            self.mod.ensure_target_history(repo, "Quantum-L9/unused")
            self.assertTrue(self.mod.history_walkable(repo))

    def test_write_and_commit_output_commits_every_declared_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            for name in ("one.md", "two.md"):
                (root / name).write_text(
                    f"{name} holds real work, long enough to clear the stub floor\n",
                    encoding="utf-8",
                )
            sha = self.mod.write_and_commit_output(
                root, "one.md", "Title", writable=["one.md", "two.md"], commit_authorized=True
            )
            listed = subprocess.run(
                ["git", "-C", str(root), "show", "--name-only", "--pretty=", sha],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("one.md", listed)
            self.assertIn("two.md", listed)

    def test_resumable_workspace_needs_active_launch_and_lock(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "programs" / "demo-activate-v1"
            runtime = workspace / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "state.sqlite").write_text("stale-draft\n", encoding="utf-8")
            self.assertFalse(self.mod.resumable_workspace(workspace))
            (runtime / "program-lock.json").write_text('{"tasks": []}\n', encoding="utf-8")
            (runtime / "LAUNCH.json").write_text(
                json.dumps(
                    {
                        "campaign_id": "demo-activate-v1",
                        "runtime_status": "active",
                        "host_lifecycle": "in_progress",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(self.mod.resumable_workspace(workspace))

    def test_active_runtime_resumes_instead_of_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            workspace = l9 / "programs" / "demo-activate-v1"
            runtime = workspace / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "program-lock.json").write_text('{"tasks": []}\n', encoding="utf-8")
            (runtime / "LAUNCH.json").write_text(
                json.dumps(
                    {
                        "schema": "l9.program-execution.launch-pointer.v1",
                        "campaign_id": "demo-activate-v1",
                        "runtime_status": "active",
                        "host_lifecycle": "in_progress",
                        "host_worktree": str(root),
                        "target_worktree": str(l9 / "program-worktrees" / "demo-activate-v1"),
                        "blueprint": str(l9 / "blueprints" / "demo-activate-v1"),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            executed: list[tuple[str, str]] = []
            # The fixture runtime carries no Controller state; identity
            # admission is the Controller's and is pinned in its own suite.
            with (
                unittest.mock.patch.object(
                    self.mod, "admit_resume_identity", return_value={"decision": "EXACT_MATCH"}
                ),
                unittest.mock.patch.object(
                    self.mod, "reconcile_resumed_source", return_value={"status": "CURRENT"}
                ),
            ):
                report = self.mod.run_campaign(
                    root / "intent.yaml",
                    until="execute",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        execute=lambda space, campaign_id: (
                            executed.append((str(space), campaign_id)) or {}
                        ),
                    ),
                )
            self.assertEqual(report.stages_completed, ["resume", "execute"])
            self.assertTrue((runtime / "program-lock.json").is_file())
            self.assertFalse((l9 / "programs" / "stale").exists())
            self.assertEqual(executed, [(str(workspace.resolve()), "demo-activate-v1")])

    def test_host_status_edit_keeps_comments(self) -> None:
        """load_yaml then dump_yaml strips the prose these SSOT files carry."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            status = root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
            policy = root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
            profile = root / "ops/autonomy/surface_profile.yaml"
            for path in (status, policy, profile):
                path.parent.mkdir(parents=True, exist_ok=True)
            status.write_text(
                "schema: l9.program-execution.campaign-status-ledger.v1\n"
                'updated: "2026-01-01T00:00:00Z"\n'
                "# Mutable live ledger. Does not rewrite CAMPAIGN_SOURCE.yaml.\n"
                "campaigns:\n"
                "  - id: other-campaign\n"
                "    lifecycle: complete\n"
                "  - id: demo-activate-v1\n"
                "    lifecycle: planned\n",
                encoding="utf-8",
            )
            policy.write_text(
                "schema: l9.program-execution.campaign-execution-policy.v1\n"
                'updated: "2026-01-01T00:00:00Z"\n'
                "# Execution order is authority, not preference.\n"
                "campaigns:\n"
                "  - id: demo-activate-v1\n"
                "    lifecycle: planned\n"
                "    execute_order: 1\n",
                encoding="utf-8",
            )
            profile.write_text(
                "# Autonomy Surface Profile - SSOT. Consumers must not fork this prose.\n"
                "schema_version: 1\n"
                "campaign_execution:\n"
                "  campaigns:\n"
                "    demo-activate-v1:\n"
                "      integration_branch: campaign/demo-activate-v1\n"
                "      lifecycle: planned\n"
                "\nauthority_order:\n"
                "  - CANONICAL_LAW\n",
                encoding="utf-8",
            )
            self.mod.mark_host_campaign_active(
                root,
                "demo-activate-v1",
                pec_workspace="/l9/programs/demo-activate-v1",
                blueprint="/l9/blueprints/demo-activate-v1",
                target_worktree="/l9/program-worktrees/demo-activate-v1",
            )
            for path in (status, policy, profile):
                body = path.read_text(encoding="utf-8")
                self.assertIn("#", body, msg=f"{path.name} lost its comments")
                yaml.safe_load(body)
            self.assertIn("Mutable live ledger", status.read_text(encoding="utf-8"))
            self.assertIn("Execution order is authority", policy.read_text(encoding="utf-8"))
            self.assertIn("must not fork this prose", profile.read_text(encoding="utf-8"))

            status_doc = yaml.safe_load(status.read_text(encoding="utf-8"))
            entry = next(x for x in status_doc["campaigns"] if x["id"] == "demo-activate-v1")
            self.assertEqual(entry["lifecycle"], "in_progress")
            self.assertEqual(entry["launched_by"], "make campaign")
            self.assertEqual(entry["worktree"], "/l9/program-worktrees/demo-activate-v1")
            closed = next(x for x in status_doc["campaigns"] if x["id"] == "other-campaign")
            self.assertEqual(closed["lifecycle"], "complete")

            policy_doc = yaml.safe_load(policy.read_text(encoding="utf-8"))
            policy_entry = policy_doc["campaigns"][0]
            self.assertEqual(policy_entry["lifecycle"], "in_progress")
            self.assertEqual(policy_entry["execute_order"], 1)

            profile_doc = yaml.safe_load(profile.read_text(encoding="utf-8"))
            block = profile_doc["campaign_execution"]["campaigns"]["demo-activate-v1"]
            self.assertEqual(block["lifecycle"], "in_progress")
            self.assertEqual(block["integration_branch"], "campaign/demo-activate-v1")
            self.assertEqual(profile_doc["authority_order"], ["CANONICAL_LAW"])

    def test_already_satisfied_task_keeps_head_instead_of_failing(self) -> None:
        """A task whose declared files already hold the work has nothing to commit."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            (root / "done.md").write_text(
                "this deliverable already exists at the campaign base commit\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", "done.md"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "base"], check=True, capture_output=True
            )
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(
                self.mod.write_and_commit_output(
                    root, "done.md", "Title", writable=["done.md"], commit_authorized=True
                ),
                head,
            )


class CampaignInputRoutingTests(unittest.TestCase):
    """The front door must route or refuse — never leave a caller improvising.

    The bug these cover: a fully specified campaign-source.v2 keeps its
    `campaign_id` under `metadata`, so the activate-seed heuristic rejected it
    and the brief compiler was handed YAML. The public path refused a valid
    input, and the pipeline got driven by hand instead.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_routing", SCRIPT)
        cls.activate = _load("compile_activation_routing", ACTIVATE)
        cls.ci = cls.mod.campaign_input_module()

    def _source(self) -> dict:
        return self.activate.build_source(READY_SEED, stamp="2026-01-01T00:00:00Z")

    def test_declared_frontmatter_that_does_not_parse_is_rejected_not_rerouted(self) -> None:
        """One YAML error in an architecture-intent header must not become a brief."""
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "design.md"
            path.write_text(
                "---\n"
                "schema: l9.program-execution.architecture-intent.v1\n"
                "title: Router: microscope\n"
                "target: Quantum-L9/LLM-Router\n"
                "---\n\n# Router\n\nBody.\n",
                encoding="utf-8",
            )
            with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                self.ci.classify(path)
            self.assertIn("frontmatter does not parse", str(ctx.exception))

    def test_unparsable_yaml_is_reported_as_a_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "broken.yaml"
            path.write_text("schema: [unclosed\n", encoding="utf-8")
            found = self.ci.classify(path)
            self.assertIs(found.kind, self.ci.CampaignInputKind.UNKNOWN)
            rejection = self.ci.reject(found)
            self.assertIn("does not parse", str(rejection))
            self.assertNotIn("The file parsed", str(rejection))

    def test_campaign_source_v2_is_classified_by_schema_not_extension(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            _dump(path, self._source())
            found = self.ci.classify(path)
            self.assertIs(found.kind, self.ci.CampaignInputKind.CAMPAIGN_SOURCE_V2)
            self.assertTrue(found.supported)
            self.assertEqual(found.route, "campaign_source -> blueprint -> PEC")

            # Same content, a name that suggests nothing, still routes the same.
            renamed = Path(raw) / "whatever.txt"
            _dump(renamed, self._source())
            self.assertIs(
                self.ci.classify(renamed).kind, self.ci.CampaignInputKind.CAMPAIGN_SOURCE_V2
            )

    def test_activate_seed_and_brief_still_classify(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            seed = Path(raw) / "intent.yaml"
            _dump(seed, READY_SEED)
            self.assertIs(self.ci.classify(seed).kind, self.ci.CampaignInputKind.ACTIVATE)
            memo = Path(raw) / "brief.md"
            memo.write_text("# campaign memo\n\nsome prose\n", encoding="utf-8")
            self.assertIs(self.ci.classify(memo).kind, self.ci.CampaignInputKind.BRIEF)

    def test_unsupported_program_intent_fails_with_reason_and_fix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "intent.yaml"
            _dump(path, INTENT_V1)
            with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                self.mod.classify_campaign_input(path)
            payload = ctx.exception.to_dict()
            self.assertEqual(payload["error_code"], "PE_CAMPAIGN_INPUT_REJECTED")
            self.assertEqual(payload["detected_input_kind"], "program-execution.intent.v1")
            self.assertTrue(payload["nothing_executed"])
            self.assertFalse(payload["manual_stage_bypass_permitted"])
            self.assertIn("campaign-source.v2", payload["supported_input_kinds"])
            self.assertTrue(payload["reason"])
            self.assertIn("campaign-source.v2", payload["fix"])

    def test_rejected_input_reports_nothing_executed_and_forbids_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "intent.yaml"
            _dump(path, INTENT_V1)
            with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                self.mod.classify_campaign_input(path)
            rendered = ctx.exception.render()
            self.assertIn("nothing_executed: true", rendered)
            self.assertIn("tasks_started: 0", rendered)
            self.assertIn("PUBLIC_CAMPAIGN_FRONT_DOOR_REJECTED", rendered)
            self.assertIn("manual_stage_bypass_permitted: false", rendered)
            self.assertIn("default_", rendered)

    def test_unknown_input_fails_before_workspace_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            l9 = Path(raw) / "l9"
            junk = root / "junk.yaml"
            _dump(junk, {"schema": "something.else.v9", "hello": "world"})
            with self.assertRaises(self.ci.CampaignInputRejected):
                self.mod.run_campaign(
                    junk,
                    until="execute",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(context7_stack=_stack_ok),
                )
            # Nothing may exist: no runtime root, no blueprint, no pec workspace.
            self.assertFalse(l9.exists(), msg="rejection created runtime state")
            self.assertFalse(
                (root / "environment/program-execution/campaigns/demo-activate-v1").exists()
            )

    def test_legacy_campaign_source_v1_fails_before_workspace_creation(self) -> None:
        """A v1-shaped document must not be rebuilt as an activate seed."""
        for schema in sorted(self.ci.LEGACY_CAMPAIGN_SCHEMAS):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as raw:
                root = _host_repo(Path(raw))
                l9 = Path(raw) / "l9"
                legacy = root / "legacy.yaml"
                _dump(legacy, {"schema": schema, **READY_SEED})
                with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                    self.mod.run_campaign(
                        legacy,
                        until="execute",
                        primary=Path(raw) / "primary",
                        repo_root=root,
                        l9_root=l9,
                        hooks=self.mod.Hooks(context7_stack=_stack_ok),
                    )
                payload = ctx.exception.to_dict()
                self.assertEqual(payload["schema"], schema)
                self.assertTrue(payload["nothing_executed"])
                self.assertFalse(payload["workspace_created"])
                self.assertEqual(payload["tasks_started"], 0)
                self.assertFalse(l9.exists(), msg="legacy rejection created runtime state")
                self.assertFalse(
                    (root / "environment/program-execution/campaigns/demo-activate-v1").exists(),
                    msg="legacy rejection generated an activate campaign",
                )

    def test_campaign_source_v2_routes_directly_to_compile_source(self) -> None:
        seen: dict[str, object] = {}

        def compile_source(source: Path, target: Path) -> None:
            seen["source"] = Path(source)
            seen["compiled"] = _load_yaml_file(Path(source))

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, self._source())
            self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_source=compile_source,
                    validate_blueprint=lambda target: [],
                ),
            )
        self.assertEqual(Path(seen["source"]).name, "CAMPAIGN_SOURCE.yaml")
        compiled = seen["compiled"]
        self.assertEqual(compiled["schema"], self.ci.CAMPAIGN_SOURCE_SCHEMA)

    def test_campaign_source_v2_does_not_pass_through_activation_compiler(self) -> None:
        def explode(intent: Path, repo_root: Path) -> dict:
            raise AssertionError("campaign-source.v2 was rebuilt by the activation compiler")

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, self._source())
            self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_activation=explode,
                    plan_window=explode,
                    compile_source=lambda source, target: None,
                    validate_blueprint=lambda target: [],
                ),
            )

    def test_seed_view_projects_the_repository_from_targets(self) -> None:
        """The runner and the compiler must bind the same repository."""
        module = _load("campaign_input_seed_view", PE_ROOT / "scripts/campaign_input.py")
        source = self._source()
        source["targets"] = [
            {"id": "TARGET-001", "repository_id": "Quantum-L9/Cursor-Governance"},
            {"id": "TARGET-002", "kind": "program_control", "repository_id": None},
        ]
        source.setdefault("metadata", {})["intended_host"] = "Quantum-L9/Cursor-Governance"
        seed = module.seed_view(source)
        self.assertEqual(seed["target"]["repository_id"], "Quantum-L9/Cursor-Governance")

    def test_seed_view_refuses_a_source_that_names_two_repositories(self) -> None:
        module = _load("campaign_input_seed_view_conflict", PE_ROOT / "scripts/campaign_input.py")
        source = self._source()
        source["targets"] = [{"id": "TARGET-001", "repository_id": "Quantum-L9/Cursor-Governance"}]
        source.setdefault("program", {})["target_repository_id"] = "Quantum-L9/l9-ci-core"
        with self.assertRaises(Exception) as ctx:
            module.seed_view(source)
        self.assertIn("l9-ci-core", str(ctx.exception))

    def test_rich_campaign_source_preserves_task_validations_and_dependencies(self) -> None:
        """The whole point of the direct route: rich semantics survive intake."""
        source = self._source()
        source["tasks"][1]["validation"] = [{"command": "git status --short"}]
        source["tasks"][1]["depends_on"] = ["TASK-001"]
        source["tasks"][0]["paths"] = {"writable": ["docs/program-execution/marker.md"]}
        source["dependency_edges"] = [{"from": "TASK-001", "to": "TASK-002"}]
        landed: dict[str, object] = {}

        def compile_source(source_path: Path, target: Path) -> None:
            landed["doc"] = _load_yaml_file(Path(source_path))

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, source)
            self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_source=compile_source,
                    validate_blueprint=lambda target: [],
                ),
            )
        doc = landed["doc"]
        task2 = next(item for item in doc["tasks"] if item["id"] == "TASK-002")
        self.assertEqual(task2["validation"], [{"command": "git status --short"}])
        self.assertEqual(task2["depends_on"], ["TASK-001"])
        self.assertEqual(doc["dependency_edges"], [{"from": "TASK-001", "to": "TASK-002"}])
        task1 = next(item for item in doc["tasks"] if item["id"] == "TASK-001")
        self.assertEqual(task1["paths"], {"writable": ["docs/program-execution/marker.md"]})

    def test_direct_campaign_source_without_plan_status_defaults_to_ready(self) -> None:
        """plan_status is optional in the schema; omission must not refuse the seal."""
        source = self._source()
        source.pop("plan_status", None)
        program = source.get("program")
        if isinstance(program, dict):
            program.pop("plan_status", None)
        landed: dict[str, object] = {}

        def compile_source(source_path: Path, target: Path) -> None:
            landed["compiled"] = _load_yaml_file(Path(source_path))

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, source)
            report = self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_source=compile_source,
                    validate_blueprint=lambda target: [],
                ),
            )
        self.assertIn("blueprint", report.stages_completed)
        compiled = landed.get("compiled")
        self.assertIsNotNone(compiled, msg="compile_source was never invoked")
        self.assertEqual(compiled["schema"], self.ci.CAMPAIGN_SOURCE_SCHEMA)
        # The runtime derives an effective Ready; it must not rewrite the source.
        self.assertNotIn("plan_status", compiled)
        self.assertNotIn("plan_status", compiled["program"])

    def test_direct_campaign_source_explicit_conditionally_ready_still_routes(self) -> None:
        source = self._source()
        source["plan_status"] = "ConditionallyReady"
        landed: dict[str, object] = {}

        def compile_source(source_path: Path, target: Path) -> None:
            landed["compiled"] = _load_yaml_file(Path(source_path))

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, source)
            self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_source=compile_source,
                    validate_blueprint=lambda target: [],
                ),
            )
        compiled = landed.get("compiled")
        self.assertIsNotNone(compiled, msg="compile_source was never invoked")
        self.assertEqual(compiled["plan_status"], "ConditionallyReady")

    def test_direct_campaign_source_explicit_blocked_still_refuses_seal(self) -> None:
        """Omission defaults to Ready; an explicit non-ready state never does."""
        for declared in ("Blocked", "Partial", "Failed"):
            with self.subTest(plan_status=declared):
                source = self._source()
                source["plan_status"] = declared
                invoked: list[Path] = []

                def compile_source(source_path: Path, target: Path) -> None:
                    invoked.append(Path(source_path))

                with tempfile.TemporaryDirectory() as raw:
                    root = _host_repo(Path(raw))
                    path = root / "CAMPAIGN_SOURCE.yaml"
                    _dump(path, source)
                    with self.assertRaises(self.mod.CampaignError) as ctx:
                        self.mod.run_campaign(
                            path,
                            until="blueprint",
                            primary=Path(raw) / "primary",
                            repo_root=root,
                            l9_root=Path(raw) / "l9",
                            hooks=self.mod.Hooks(
                                context7_stack=_stack_ok,
                                compile_source=compile_source,
                                validate_blueprint=lambda target: [],
                            ),
                        )
                self.assertIn("refuse seal", str(ctx.exception))
                self.assertEqual(invoked, [], msg="compile_source ran on a refused seal")

    def test_direct_campaign_source_malformed_plan_status_is_refused_before_isolation(
        self,
    ) -> None:
        """A declared-but-malformed status is a source defect, not a default.

        Source preflight now runs before isolation, so an empty or null
        `plan_status` is refused as a schema violation rather than reaching the
        seal check. Either way it never becomes Ready — and now nothing is
        created before it is caught.
        """
        for declared in ("", None):
            with self.subTest(plan_status=declared):
                source = self._source()
                source["plan_status"] = declared
                git_calls: list[object] = []
                compiled: list[object] = []

                with tempfile.TemporaryDirectory() as raw:
                    root = _host_repo(Path(raw))
                    l9 = Path(raw) / "l9"
                    path = root / "CAMPAIGN_SOURCE.yaml"
                    _dump(path, source)
                    with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                        self.mod.run_campaign(
                            path,
                            until="blueprint",
                            primary=Path(raw) / "primary",
                            repo_root=root,
                            l9_root=l9,
                            hooks=self.mod.Hooks(
                                context7_stack=_stack_ok,
                                git=lambda *a, **k: git_calls.append(a) or "",
                                compile_source=lambda source, target: compiled.append(source),
                                validate_blueprint=lambda target: [],
                            ),
                        )
                    payload = ctx.exception.to_dict()
                    self.assertTrue(payload["nothing_executed"])
                    self.assertFalse(payload["workspace_created"])
                    self.assertEqual(payload["tasks_started"], 0)
                    self.assertIn("plan_status", payload["reason"])
                    self.assertEqual(git_calls, [], msg="isolation ran on a refused source")
                    self.assertEqual(compiled, [], msg="compile ran on a refused source")
                    self.assertFalse(l9.exists(), msg="rejection created runtime state")

    # --- source preflight: deterministic defects die before isolation ------

    def _refuse_before_isolation(self, source: dict) -> dict:
        """Run a bad source through the front door; prove nothing was created."""
        git_calls: list[object] = []
        compiled: list[object] = []
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            l9 = Path(raw) / "l9"
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, source)

            # 1. campaign-check-input refuses, and runs no stage.
            self.assertEqual(self.mod.main(["--check-input", str(path)]), 2)

            # 2. run_campaign refuses at the same boundary.
            with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
                self.mod.run_campaign(
                    path,
                    until="blueprint",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        git=lambda *a, **k: git_calls.append(a) or "",
                        compile_source=lambda source, target: compiled.append(source),
                        validate_blueprint=lambda target: [],
                    ),
                )
            payload = ctx.exception.to_dict()
            self.assertTrue(payload["nothing_executed"])
            self.assertFalse(payload["workspace_created"])
            self.assertEqual(payload["tasks_started"], 0)
            self.assertEqual(git_calls, [], msg="isolate ran on a refused source")
            self.assertEqual(compiled, [], msg="compile ran on a refused source")
            self.assertFalse(l9.exists(), msg="refused source created runtime state")
        return payload

    def test_illegal_task_and_gate_ids_fail_check_input_before_execution(self) -> None:
        """The v3 failure: TASK-001A classified SUPPORTED, then died at template validation."""
        source = self._source()
        source["tasks"][0]["id"] = "TASK-001A"
        payload = self._refuse_before_isolation(source)
        self.assertIn("TASK-001A", payload["reason"])

    def test_illegal_gate_id_fails_check_input_before_execution(self) -> None:
        source = self._source()
        gates = source.get("gates") or []
        if not gates:
            self.skipTest("fixture declares no gates")
        gates[0]["id"] = "GATE-001A"
        payload = self._refuse_before_isolation(source)
        self.assertIn("GATE-001A", payload["reason"])

    def test_mutating_task_without_writable_scope_fails_check_input(self) -> None:
        source = self._source()
        task = next(
            item
            for item in source["tasks"]
            if (item.get("authorization_ceiling") or {}).get("local_write")
            and item.get("execution_kind") != "program_control"
        )
        task["paths"] = []
        task.pop("outputs", None)
        payload = self._refuse_before_isolation(source)
        self.assertIn(task["id"], payload["reason"])
        self.assertIn("local_write", payload["reason"])

    def test_composed_validation_command_fails_before_isolation(self) -> None:
        """Reproduces the v3 permission-render failure at the correct boundary."""
        source = self._source()
        task = source["tasks"][0]
        task["validation"] = [
            {
                "id": "VAL-001",
                "method": "command",
                "command_or_inspection": "grep -q x a.py && grep -q x b.py",
            }
        ]
        payload = self._refuse_before_isolation(source)
        self.assertIn("VAL-001", payload["reason"])

    def test_valid_source_still_passes_check_input_and_reaches_blueprint(self) -> None:
        """The preflight must not be so strict that a good campaign stops compiling."""
        source = self._source()
        landed: dict[str, object] = {}

        def compile_source(source_path: Path, target: Path) -> None:
            landed["doc"] = _load_yaml_file(Path(source_path))

        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            path = root / "CAMPAIGN_SOURCE.yaml"
            _dump(path, source)
            self.assertEqual(self.mod.main(["--check-input", str(path)]), 0)
            report = self.mod.run_campaign(
                path,
                until="blueprint",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    compile_source=compile_source,
                    validate_blueprint=lambda target: [],
                ),
            )
        self.assertIn("blueprint", report.stages_completed)
        doc = landed.get("doc")
        self.assertIsNotNone(doc, msg="compile_source was never invoked")
        # Explicit writable scope survives intake verbatim.
        task = next(item for item in doc["tasks"] if item["id"] == "TASK-001")
        self.assertEqual(task["paths"], ["docs/program-execution/demo/baseline.md"])

    def test_check_input_reports_route_and_runs_no_stage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "CAMPAIGN_SOURCE.yaml"
            _dump(path, self._source())
            self.assertEqual(self.mod.main(["--check-input", str(path)]), 0)
            intent = Path(raw) / "intent-v1.yaml"
            _dump(intent, INTENT_V1)
            # Compile ingress is live. Campaign execute of intent.v1 still
            # refuse_publication / classify reject; --check-input does not.
            self.assertEqual(self.mod.main(["--check-input", str(intent)]), 0)

    def test_cli_rejection_is_terminal_and_explains_itself(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            bad = root / "intent-v1.yaml"
            _dump(bad, INTENT_V1)
            buffer = io.StringIO()
            with contextlib.redirect_stderr(buffer):
                code = self.mod.main(
                    [
                        "--intent",
                        str(bad),
                        "--repo-root",
                        str(root),
                        "--l9-root",
                        str(Path(raw) / "l9"),
                    ]
                )
            self.assertEqual(code, 2)
            printed = buffer.getvalue()
            self.assertIn("PE_CAMPAIGN_INPUT_REJECTED", printed)
            self.assertIn("nothing_executed: true", printed)


def _load_yaml_file(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
