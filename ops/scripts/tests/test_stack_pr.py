from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "stack_pr.py"


class StackPrTests(unittest.TestCase):
    def test_base_from_stack_never_main(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            stack = Path(raw) / "STACK.json"
            stack.write_text(
                json.dumps(
                    {
                        "schema": "l9.program-execution.pr-stack.v1",
                        "stack": [
                            {
                                "task_id": "TASK-001",
                                "branch": "pec/w0/task-001",
                                "pr_base": "campaign/demo-activate-v1",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "base", "--stack", str(stack)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "campaign/demo-activate-v1")
            self.assertNotIn("main", result.stdout)

    def test_missing_stack_refuses_default_branch(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "base"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("STACK.json required", result.stderr)


if __name__ == "__main__":
    unittest.main()


def _load_stack_pr():
    """Import stack_pr.py by path — ops/scripts is not an importable package."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("stack_pr_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OpenPrsIsRepoScopedTests(unittest.TestCase):
    """`stack_pr.py order` used a cross-repo search endpoint and could not run.

    A session gateway bound to its configured repositories answers
    `search/issues` with 403 and names the remedy: "Use repository-scoped
    endpoints (repos/{owner}/{repo}/...)". These tests pin the endpoint AND the
    two wrong-answer defects the 403 was hiding.
    """

    def setUp(self) -> None:
        self.mod = _load_stack_pr()
        self.calls: list[tuple] = []

    def _stub(self, payload):
        def fake_gh(*args):
            self.calls.append(args)
            return payload

        self.mod._gh = fake_gh

    def test_endpoint_is_repo_scoped_never_search(self) -> None:
        self._stub([])
        self.mod.open_prs("owner/repo", "")
        endpoint = self.calls[0][0]
        self.assertTrue(
            endpoint.startswith("repos/owner/repo/pulls"),
            f"must call a repo-scoped pulls endpoint, got {endpoint!r}",
        )
        self.assertNotIn("search/", endpoint, "cross-repo search 403s on a session gateway")

    def test_two_or_more_prs_return_a_list_with_head_and_base(self) -> None:
        """Both masked defects at once.

        The old projection read `.head.label` off search/issues items, whose PR
        representation carries no head/base at all, and emitted NDJSON that
        `_gh` could not parse past one result — after which callers iterated a
        string. Ordering reads exactly `number`, `head` and `base`.
        """
        self._stub(
            [
                {
                    "number": 2,
                    "title": "b",
                    "head": "o:feat/b",
                    "base": "o:feat/a",
                    "ref": "feat/b",
                },
                {"number": 1, "title": "a", "head": "o:feat/a", "base": "o:main", "ref": "feat/a"},
            ]
        )
        prs = self.mod.open_prs("owner/repo", "")
        self.assertIsInstance(prs, list)
        self.assertEqual(2, len(prs))
        for pr in prs:
            self.assertIsInstance(pr, dict)
            self.assertIsNotNone(pr["head"], "head must be populated, not null")
            self.assertIsNotNone(pr["base"], "base must be populated, not null")
        self.assertEqual("o:feat/a", prs[0]["base"])

    def test_prefix_filters_on_head_ref(self) -> None:
        self._stub(
            [
                {
                    "number": 2,
                    "title": "b",
                    "head": "o:agent/x",
                    "base": "o:main",
                    "ref": "agent/x",
                },
                {
                    "number": 1,
                    "title": "a",
                    "head": "o:claude/y",
                    "base": "o:main",
                    "ref": "claude/y",
                },
            ]
        )
        prs = self.mod.open_prs("owner/repo", "claude/")
        self.assertEqual([1], [pr["number"] for pr in prs])
        self.assertNotIn("ref", prs[0], "internal ref field must not leak to callers")

    def test_full_page_is_reported_not_silently_truncated(self) -> None:
        page = self.mod._PULLS_PAGE
        self._stub(
            [
                {"number": n, "title": "t", "head": "o:h", "base": "o:main", "ref": "h"}
                for n in range(page)
            ]
        )
        import io
        from contextlib import redirect_stderr

        err = io.StringIO()
        with redirect_stderr(err):
            self.mod.open_prs("owner/repo", "")
        self.assertIn("truncated", err.getvalue())
