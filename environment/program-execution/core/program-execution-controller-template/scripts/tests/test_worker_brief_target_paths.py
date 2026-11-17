"""A worker brief may name any target-repository path, including kernel-like names.

The brief is built only from typed Rendered Contract fields, so it never
carries kernel markdown. A former filename substring lint refused any brief
whose text contained AUDIT.md, PLAN.md, VALIDATION.md and similar names. It
matched ordinary target files (every Quantum-L9/.github release record has a
RELEASE_VALIDATION.md) and blocked those campaigns at render-contract. This
proves such a task renders.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, run_cli

TARGET_PATHS = (
    "docs/semantic-foundation/v3.44.0/RELEASE_VALIDATION.md",
    "docs/PLAN.md",
    "RELEASE.md",
)


class WorkerBriefTargetPathTests(unittest.TestCase):
    def test_kernel_like_target_paths_render_into_the_brief(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            objective = "Write " + ", ".join(TARGET_PATHS)
            _, repo, workspace = bootstrap_repo(temp, task_overrides={"objective": objective})
            draft = temp / "TASK-001.draft.json"
            run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(draft),
            )
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(draft),
                "--actor",
                "operator",
            )
            try:
                run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
                run_cli("prepare", "TASK-001", "--workspace", str(workspace))
                rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
                brief = Path(rendered["contract"]).with_name("TASK-001.WORKER_BRIEF.md")
                text = brief.read_text(encoding="utf-8")
            finally:
                cleanup_worktree(repo, workspace)
            for path in TARGET_PATHS:
                self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
