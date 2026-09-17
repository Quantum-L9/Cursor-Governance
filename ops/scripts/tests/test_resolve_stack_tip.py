"""Unit tests for the fail-closed stack-tip resolver (plan T1)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from resolve_stack_tip import (  # noqa: E402
    OpenPR,
    TipError,
    resolve_from_prs,
    resolve_stack_tip,
)


def _pr(number: int, head: str, base: str, sha: str = "") -> OpenPR:
    return OpenPR(number=number, head=head, base=base, sha=sha or f"{number:040d}")


class ResolveFromPrsTests(unittest.TestCase):
    def test_no_open_prs_selects_default_ref(self) -> None:
        result = resolve_from_prs([], default_ref="origin/main")
        self.assertEqual(result.ref, "origin/main")
        self.assertEqual(result.reason, "no_open_prs")

    def test_unique_chain_selects_tip_not_root(self) -> None:
        prs = [
            _pr(240, "feat/a", "main", "aa" * 20),
            _pr(241, "feat/b", "feat/a", "bb" * 20),
            _pr(242, "feat/stack-safe-merge", "feat/b", "cc" * 20),
        ]
        result = resolve_from_prs(prs, default_ref="origin/main")
        self.assertEqual(result.ref, "feat/stack-safe-merge")
        self.assertEqual(result.sha, "cc" * 20)
        self.assertEqual(result.reason, "unique_chain_tip")
        # Root first, tip last: the composer excludes each of these from a
        # child's story, and the publish lib fetches the ones above the tip.
        self.assertEqual(result.chain, ("feat/a", "feat/b", "feat/stack-safe-merge"))

    def test_no_open_prs_has_an_empty_chain(self) -> None:
        self.assertEqual(resolve_from_prs([], default_ref="origin/main").chain, ())

    # -- the branch's own open PR decides ------------------------------------

    def test_own_open_pr_base_wins_over_the_chain_tip(self) -> None:
        """A second `make pr` on the stack root must not resolve its own child."""
        prs = [
            _pr(600, "feat/root", "main", "aa" * 20),
            _pr(601, "feat/child", "feat/root", "bb" * 20),
        ]
        result = resolve_from_prs(prs, default_ref="origin/main", branch="feat/root")
        self.assertEqual(result.reason, "open_pr_base")
        self.assertEqual(result.ref, "origin/main")
        self.assertEqual(result.chain, ())

    def test_own_open_pr_survives_a_sibling_opened_mid_run(self) -> None:
        """PR #602: #603 appeared against main; #602's base was never in question."""
        prs = [
            _pr(600, "feat/root", "main", "aa" * 20),
            _pr(601, "feat/mid", "feat/root", "bb" * 20),
            _pr(602, "feat/leaf", "feat/mid", "cc" * 20),
            _pr(603, "agent/other", "main", "dd" * 20),
        ]
        with self.assertRaises(TipError):
            resolve_from_prs(prs, default_ref="origin/main")
        result = resolve_from_prs(prs, default_ref="origin/main", branch="feat/leaf")
        self.assertEqual(result.reason, "open_pr_base")
        self.assertEqual(result.ref, "feat/mid")
        self.assertEqual(result.sha, "bb" * 20)
        # Walked upward from the base, root first — the sibling is not on it.
        self.assertEqual(result.chain, ("feat/root", "feat/mid"))

    def test_own_open_pr_chain_stops_at_a_merged_ancestor(self) -> None:
        prs = [_pr(602, "feat/leaf", "feat/mid", "cc" * 20)]
        result = resolve_from_prs(prs, default_ref="origin/main", branch="feat/leaf")
        self.assertEqual(result.ref, "feat/mid")
        self.assertEqual(result.sha, "")
        self.assertEqual(result.chain, ("feat/mid",))

    def test_branch_without_an_open_pr_still_walks_the_chain(self) -> None:
        prs = [
            _pr(600, "feat/root", "main", "aa" * 20),
            _pr(601, "feat/child", "feat/root", "bb" * 20),
        ]
        result = resolve_from_prs(prs, default_ref="origin/main", branch="feat/new")
        self.assertEqual(result.reason, "unique_chain_tip")
        self.assertEqual(result.ref, "feat/child")

    def test_sibling_roots_targeting_main_exit(self) -> None:
        prs = [
            _pr(10, "feat/one", "main"),
            _pr(11, "feat/two", "main"),
        ]
        with self.assertRaises(TipError) as ctx:
            resolve_from_prs(prs, default_ref="origin/main")
        self.assertIn("sibling", str(ctx.exception))
        self.assertIn("feat/one", str(ctx.exception))
        self.assertIn("feat/two", str(ctx.exception))

    def test_sibling_fork_mid_chain_exit(self) -> None:
        prs = [
            _pr(1, "feat/base", "main"),
            _pr(2, "feat/left", "feat/base"),
            _pr(3, "feat/right", "feat/base"),
        ]
        with self.assertRaises(TipError) as ctx:
            resolve_from_prs(prs, default_ref="origin/main")
        self.assertIn("fork at feat/base", str(ctx.exception))

    def test_single_open_pr_targeting_main_is_the_tip(self) -> None:
        result = resolve_from_prs(
            [_pr(242, "feat/stack-safe-merge", "main", "ee" * 20)],
            default_ref="origin/main",
        )
        self.assertEqual(result.ref, "feat/stack-safe-merge")
        self.assertEqual(result.sha, "ee" * 20)
        self.assertEqual(result.reason, "unique_chain_tip")

    def test_origin_main_base_is_treated_as_main(self) -> None:
        result = resolve_from_prs(
            [_pr(7, "feat/only", "origin/main", "dd" * 20)],
            default_ref="origin/main",
        )
        self.assertEqual(result.ref, "feat/only")


class ResolveStackTipRepoTests(unittest.TestCase):
    def _repo(self) -> tuple[Path, str]:
        raw = tempfile.mkdtemp()
        repo = Path(raw)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=repo, check=True, capture_output=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "branch", "origin/main", sha],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                "https://github.com/Quantum-L9/Cursor-Governance.git",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo, sha

    def test_empty_list_resolves_default_sha(self) -> None:
        repo, sha = self._repo()
        result = resolve_stack_tip(repo, default_ref="main", prs=[])
        self.assertEqual(result.ref, "main")
        self.assertEqual(result.sha, sha)
        self.assertEqual(result.reason, "no_open_prs")

    def test_own_open_pr_on_main_resolves_the_default_sha(self) -> None:
        repo, sha = self._repo()
        prs = [
            _pr(600, "main-root", "main", "aa" * 20),
            _pr(601, "feat/child", "main-root", "bb" * 20),
        ]
        result = resolve_stack_tip(repo, default_ref="main", prs=prs, branch="main-root")
        self.assertEqual(result.reason, "open_pr_base")
        self.assertEqual(result.ref, "main")
        self.assertEqual(result.sha, sha)

    def test_branch_defaults_to_the_checked_out_one(self) -> None:
        repo, _sha = self._repo()
        subprocess.run(["git", "checkout", "-q", "-b", "feat/leaf"], cwd=repo, check=True)
        prs = [
            _pr(600, "feat/root", "main", "aa" * 20),
            _pr(602, "feat/leaf", "feat/root", "cc" * 20),
            _pr(603, "agent/other", "main", "dd" * 20),
        ]
        result = resolve_stack_tip(repo, default_ref="main", prs=prs)
        self.assertEqual((result.reason, result.ref), ("open_pr_base", "feat/root"))
        # agent_worktree_start.sh passes --branch "" : a new task starts from
        # the board's tip, not from the launching checkout's own PR base.
        del prs[2]
        fresh = resolve_stack_tip(repo, default_ref="main", prs=prs, branch="")
        self.assertEqual((fresh.reason, fresh.ref), ("unique_chain_tip", "feat/leaf"))

    def test_gh_failure_is_fail_closed(self) -> None:
        repo, _sha = self._repo()

        def boom(_slug: str) -> list[OpenPR] | None:
            return None

        with self.assertRaises(TipError) as ctx:
            resolve_stack_tip(repo, list_prs=boom)
        self.assertIn("could not enumerate open PRs", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
