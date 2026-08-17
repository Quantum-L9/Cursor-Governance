"""Merge-driver tests for generated artifacts (PR_OVERLAP_GUARDRAIL_V1).

Two branches each regenerate ops/generated/skill-registry.json from different
trees. Without the driver the merge must conflict; with merge=l9-generated
registered + attributed the merge must self-resolve as keep-ours and write the
regen-required marker. Runnable as unittest or pytest.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

DRIVER = Path(__file__).resolve().parents[1] / "git_merge_driver_generated.sh"
GENERATED = "ops/generated/skill-registry.json"
BASE_CONTENT = '{"skills": []}\n'
OURS_CONTENT = '{"skills": ["ours"]}\n'
THEIRS_CONTENT = '{"skills": ["theirs"]}\n'


def _run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = {
        "GIT_AUTHOR_NAME": "Tester",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "Tester",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, check=False)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed ({' '.join(args)}): {result.stdout}\n{result.stderr}")
    return result


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], path)
    _run(["git", "config", "user.name", "Tester"], path)
    _run(["git", "config", "user.email", "t@example.com"], path)


def _write_commit(repo: Path, rel: str, content: str, message: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _run(["git", "add", rel], repo)
    _run(["git", "commit", "-q", "-m", message], repo)


class MergeDriverGeneratedTests(unittest.TestCase):
    def _make_two_branch_repo(self) -> tuple[Path, Path]:
        """Repo with base commit; A/B branches each diverge the same generated file."""
        raw = tempfile.mkdtemp(prefix="l9-merge-driver-")
        repo = Path(raw)
        _init_repo(repo)
        _write_commit(repo, GENERATED, BASE_CONTENT, "base")
        _run(["git", "branch", "ours"], repo)
        _run(["git", "branch", "theirs"], repo)
        # theirs: different regeneration from a different tree
        _run(["git", "checkout", "-q", "theirs"], repo)
        _write_commit(repo, GENERATED, THEIRS_CONTENT, "theirs regen")
        # ours
        _run(["git", "checkout", "-q", "ours"], repo)
        _write_commit(repo, GENERATED, OURS_CONTENT, "ours regen")
        return repo, Path(raw)

    def test_plain_merge_conflicts_without_driver(self) -> None:
        repo, raw = self._make_two_branch_repo()
        result = _run(["git", "merge", "theirs"], repo, check=False)
        self.assertNotEqual(result.returncode, 0, "plain merge should conflict without the driver")
        self.assertIn("CONFLICT", result.stdout + result.stderr)

    def test_merge_self_resolves_with_driver_and_attributes(self) -> None:
        repo, raw = self._make_two_branch_repo()
        # Register the driver in this clone and attribute the generated path.
        _run(
            ["git", "config", "merge.l9-generated.driver", f"bash {DRIVER} %O %A %B %P"],
            repo,
        )
        _run(["git", "config", "merge.l9-generated.name", "l9 generated test driver"], repo)
        attrs = repo / ".gitattributes"
        attrs.write_text(f"{GENERATED} merge=l9-generated\n", encoding="utf-8")
        _run(["git", "add", ".gitattributes"], repo)
        _run(["git", "commit", "-q", "-m", "attributes"], repo)

        result = _run(["git", "merge", "theirs"], repo, check=False)
        self.assertEqual(
            result.returncode, 0, f"driver merge should succeed: {result.stdout}\n{result.stderr}"
        )
        self.assertEqual(
            (repo / GENERATED).read_text(encoding="utf-8"),
            OURS_CONTENT,
            "keep-ours: merged file must equal our version",
        )
        marker = repo / ".l9" / "pr" / "regen-required.txt"
        self.assertTrue(marker.is_file(), "regen-required marker must be written")
        self.assertIn(GENERATED, marker.read_text(encoding="utf-8").splitlines())

    def test_driver_direct_invocation_keeps_ours_and_marks(self) -> None:
        raw = tempfile.mkdtemp(prefix="l9-merge-driver-direct-")
        repo = Path(raw)
        _init_repo(repo)
        _write_commit(repo, "seed.txt", "seed\n", "seed")
        ours = repo / "ours.tmp"
        ours.write_text("ours-content\n", encoding="utf-8")
        result = _run(
            [
                "bash",
                str(DRIVER),
                str(repo / "base.tmp"),
                str(ours),
                str(repo / "theirs.tmp"),
                GENERATED,
            ],
            repo,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            ours.read_text(encoding="utf-8"), "ours-content\n", "driver must never edit content"
        )
        marker = repo / ".l9" / "pr" / "regen-required.txt"
        self.assertIn(GENERATED, marker.read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
