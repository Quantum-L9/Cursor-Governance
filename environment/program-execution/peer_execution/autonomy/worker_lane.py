"""Isolated Git worktree execution lanes without shell interpolation."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class GitWorktreeLane:
    """Create, execute inside, and remove one isolated Git worktree."""

    def __init__(
        self,
        *,
        repo: Path | str,
        lane_root: Path | str,
        campaign_id: str,
        action_id: str,
    ) -> None:
        self.repo = Path(repo).resolve()
        self.lane_root = Path(lane_root).resolve()
        for value, label in ((campaign_id, "campaign_id"), (action_id, "action_id")):
            if not SAFE_ID.fullmatch(value):
                raise ValueError(f"unsafe {label}: {value!r}")
        self.path = self.lane_root / campaign_id / action_id

    def _git(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        return CommandResult(tuple(["git", *args]), result.returncode, result.stdout, result.stderr)

    def create(self, *, ref: str = "HEAD", branch: str | None = None) -> Path:
        if not (self.repo / ".git").exists():
            raise ValueError(f"not a Git repository: {self.repo}")
        if self.path.exists():
            raise FileExistsError(f"lane already exists: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        args = ["worktree", "add"]
        if branch:
            if not SAFE_ID.fullmatch(branch.replace("/", "-")):
                raise ValueError(f"unsafe branch name: {branch!r}")
            args.extend(["-b", branch])
        else:
            args.append("--detach")
        args.extend([str(self.path), ref])
        result = self._git(args)
        if result.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {result.stderr.strip()}")
        script = Path(__file__).resolve().parents[4] / "ops/scripts/ensure_workspace_wired.sh"
        if script.is_file():
            env = os.environ.copy()
            env["L9_WIRE_LINKS_ONLY"] = "1"
            subprocess.run(
                ["bash", str(script), str(self.path)],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
        self._wire_consumer_links()
        return self.path

    def _wire_consumer_links(self) -> None:
        """Always write the three consumer links. CI has no ~/.cursor-governance,
        so ensure_workspace_wired.sh no-ops; dangling symlinks still satisfy make pr.
        """
        gc = Path.home() / ".cursor-governance"
        plans = Path.home() / ".cursor" / "plans"
        commands = self.path / ".cursor-commands"
        if not commands.exists() and not commands.is_symlink():
            commands.symlink_to(gc)
        gov = self.path / ".cursor" / "governance"
        gov.mkdir(parents=True, exist_ok=True)
        law_link = gov / "CANONICAL_LAW.md"
        if not law_link.exists() and not law_link.is_symlink():
            law_link.symlink_to(gc / "CANONICAL_LAW.md")
        plans_link = self.path / ".cursor" / "plans"
        if not plans_link.exists() and not plans_link.is_symlink():
            plans_link.symlink_to(plans)

    def run(self, argv: Sequence[str], *, timeout: int = 900) -> CommandResult:
        if not self.path.is_dir():
            raise RuntimeError("lane must be created before execution")
        if not argv:
            raise ValueError("argv must not be empty")
        result = subprocess.run(
            list(argv),
            cwd=self.path,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(tuple(argv), result.returncode, result.stdout, result.stderr)

    def remove(self, *, force: bool = False) -> None:
        if not self.path.exists():
            return
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(self.path))
        result = self._git(args)
        if result.returncode != 0:
            raise RuntimeError(f"git worktree remove failed: {result.stderr.strip()}")
        campaign_dir = self.path.parent
        if campaign_dir.exists() and not any(campaign_dir.iterdir()):
            campaign_dir.rmdir()

    def emergency_cleanup_unregistered(self) -> None:
        """Remove a path only after Git no longer recognizes it as a worktree."""

        if self.path.exists():
            result = self._git(["worktree", "list", "--porcelain"])
            if str(self.path) in result.stdout:
                raise RuntimeError("refusing filesystem cleanup of a registered worktree")
            shutil.rmtree(self.path)
