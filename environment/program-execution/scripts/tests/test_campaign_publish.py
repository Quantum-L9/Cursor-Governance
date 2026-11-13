"""campaign_publish: the one way a finished campaign leaves the machine.

PROGRAM_EXECUTION_MAKE_PR_FINISH_V1. Each refusal below is a state in which
the governance SSOT `make pr` must not be reached; each is asserted on the
spawned argv, not on a hook that would absorb any argv.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
MODULE = PE_ROOT / "scripts" / "campaign_publish.py"
AUTHORITY = {
    "merge": "forbidden",
    "push": "via_make_pr_only",
    "pull_request": "via_make_pr_only",
    "publication": {
        "route": "make_pr_ssot",
        "raw_push": "forbidden",
        "raw_pull_request": "forbidden",
    },
}


def _load():
    spec = importlib.util.spec_from_file_location("campaign_publish_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


publish = _load()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


class Fixture:
    """A target with a bare origin, a campaign branch in its own worktree, a Blueprint."""

    def __init__(self, root: Path, *, ahead: bool = True) -> None:
        self.root = root
        origin = root / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True
        )
        self.target = root / "target"
        self.target.mkdir()
        _git(self.target, "init", "-b", "main")
        _git(self.target, "config", "user.email", "t@example.com")
        _git(self.target, "config", "user.name", "T")
        (self.target / "README.md").write_text("x\n", encoding="utf-8")
        _git(self.target, "add", "README.md")
        _git(self.target, "commit", "-m", "base")
        _git(self.target, "remote", "add", "origin", str(origin))
        _git(self.target, "push", "-q", "origin", "main")
        _git(self.target, "fetch", "-q", "origin")
        self.workspace = root / "integration"
        _git(self.target, "worktree", "add", "-q", "-b", "campaign/demo", str(self.workspace))
        if ahead:
            (self.workspace / "work.txt").write_text("verified\n", encoding="utf-8")
            _git(self.workspace, "add", "work.txt")
            _git(self.workspace, "commit", "-m", "pec: work")
        self.pec = root / "pec"
        (self.pec / "runtime").mkdir(parents=True)
        self.blueprint = root / "blueprint"
        self.blueprint.mkdir()
        (self.blueprint / "PROGRAM.yaml").write_text(
            yaml.safe_dump(
                {
                    "program": {
                        "id": "demo",
                        "name": "Demo program",
                        "objective": "Prove the finish.",
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.blueprint / "TASK_CARDS.yaml").write_text(
            yaml.safe_dump({"tasks": [{"id": "TASK-001", "title": "Do the work"}]}),
            encoding="utf-8",
        )
        self.ssot = root / "ssot"
        for marker in publish.SSOT_MARKERS:
            (self.ssot / marker).parent.mkdir(parents=True, exist_ok=True)
            (self.ssot / marker).touch()
        self.calls: list[list[str]] = []
        self.make_result = 0
        self.write_summary = True

    def spawn(self, argv, *, timeout, cwd=None, env=None):
        argv = [str(part) for part in argv]
        if argv[0] == "git":
            return subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env, check=False
            )
        self.calls.append(argv)
        if argv[0] == "make":
            assert env is not None and env["PR_REMEDIATE"] == "0"
            if self.write_summary:
                summary = self.workspace / ".l9" / "pr" / "pr-summary.json"
                summary.parent.mkdir(parents=True, exist_ok=True)
                summary.write_text(
                    json.dumps(
                        {
                            "number": 7,
                            "url": "https://x/pull/7",
                            "repo": "o/r",
                            "source": "github_api",
                        }
                    ),
                    encoding="utf-8",
                )
            return subprocess.CompletedProcess(argv, self.make_result, "make out", "make err")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def run(self, authority=AUTHORITY):
        return publish.publish_campaign(
            pec_workspace=self.pec,
            campaign_id="demo",
            target=self.target,
            blueprint=self.blueprint,
            base_ref="origin/main",
            authority=authority,
            spawn=self.spawn,
            environ={"L9_GOVERNANCE_DIR": str(self.ssot), "PATH": "/usr/bin:/bin"},
        )

    def makes(self) -> list[list[str]]:
        return [call for call in self.calls if call[0] == "make"]


class CampaignPublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _refused(self, fixture: Fixture, code: str, **kwargs) -> None:
        with self.assertRaises(publish.PublicationError) as caught:
            fixture.run(**kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_publishes_the_verified_head_once_through_the_ssot(self) -> None:
        fixture = Fixture(self.root)
        record = fixture.run()
        self.assertEqual(
            fixture.makes(),
            [
                [
                    "make",
                    "-C",
                    str(fixture.ssot.resolve()),
                    "pr",
                    f"WS={fixture.workspace.resolve()}",
                ]
            ],
        )
        self.assertEqual(record["number"], 7)
        self.assertEqual(record["head_branch"], "campaign/demo")
        self.assertEqual(record["head_sha"], _git(fixture.workspace, "rev-parse", "HEAD"))
        intent = json.loads((fixture.workspace / ".l9/pr/pr-intent.json").read_text())
        self.assertEqual(intent["title"], "[demo] Demo program")
        self.assertEqual(intent["head"], record["head_sha"])
        self.assertIn("TASK-001 Do the work", intent["reviewer_focus"])
        # Idempotent per head: a second finish does not run make pr again.
        fixture.run()
        self.assertEqual(len(fixture.makes()), 1)

    def test_route_other_than_ssot_make_pr_is_refused(self) -> None:
        fixture = Fixture(self.root)
        self._refused(
            fixture,
            "PUBLICATION_ROUTE_UNDECLARED",
            authority={**AUTHORITY, "publication": {"route": "raw_push"}},
        )
        self._refused(
            fixture,
            "PUBLICATION_AUTHORITY_WIDENED",
            authority={**AUTHORITY, "merge": "via_make_pr_only"},
        )
        self.assertEqual(fixture.calls, [])

    def test_missing_ssot_is_refused(self) -> None:
        fixture = Fixture(self.root)
        (fixture.ssot / "ops/scripts/compose_pr_body.py").unlink()
        self._refused(fixture, "GOVERNANCE_SSOT_UNAVAILABLE")
        self.assertEqual(fixture.makes(), [])

    def test_dirty_integration_tree_is_refused(self) -> None:
        fixture = Fixture(self.root)
        (fixture.workspace / "work.txt").write_text("unverified\n", encoding="utf-8")
        self._refused(fixture, "INTEGRATION_TREE_DIRTY")
        self.assertEqual(fixture.makes(), [])

    def test_nothing_ahead_of_base_is_refused(self) -> None:
        fixture = Fixture(self.root, ahead=False)
        self._refused(fixture, "NOTHING_TO_PUBLISH")
        self.assertEqual(fixture.makes(), [])

    def test_failed_make_pr_is_a_failure_with_its_log(self) -> None:
        fixture = Fixture(self.root)
        fixture.make_result = 2
        self._refused(fixture, "MAKE_PR_FAILED")
        log = (fixture.pec / "runtime" / "publication.log").read_text(encoding="utf-8")
        self.assertIn("exit=2", log)
        self.assertIn("make err", log)
        self.assertFalse((fixture.pec / "runtime" / "PUBLICATION.json").exists())

    def test_unreported_publication_is_a_failure(self) -> None:
        fixture = Fixture(self.root)
        fixture.write_summary = False
        self._refused(fixture, "PUBLICATION_UNREPORTED")


if __name__ == "__main__":
    unittest.main()
