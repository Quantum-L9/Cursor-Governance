#!/usr/bin/env python3
"""Fixture self-test: /ff parks unique work and never deletes it."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FF = ROOT / "scripts" / "ff.sh"


_HOST_LEAKS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GITHUB_ACTIONS",
    "GITHUB_EVENT_PATH",
    "GITHUB_WORKSPACE",
    "GOVERNANCE_GITHUB_BRANCH",
    "CURSOR_GOVERNANCE_DIR",
)


def run(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = dict(os.environ)
    for key in _HOST_LEAKS:
        merged.pop(key, None)
    if env:
        merged.update(env)
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, env=merged
    )


def git(repo: Path, *args: str) -> None:
    proc = run(["git", "-C", str(repo), *args])
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")


def _init_clone(path: Path) -> None:
    run(["git", "init", str(path)])
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def test_behind_with_colliding_and_hold() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        clone = Path(tmp) / "clone"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(clone)])
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Test")
        (clone / "tracked.txt").write_text("v1\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "base")
        git(clone, "branch", "-M", "main")
        git(clone, "push", "-u", "origin", "main")
        # A fresh bare repo points HEAD at the host's init.defaultBranch
        # (often master); a second clone would then check out nothing and
        # push its "ahead" commit to the wrong branch, silently voiding the
        # behind-origin premise of this scenario.
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        other = Path(tmp) / "other"
        run(["git", "clone", str(remote), str(other)])
        git(other, "config", "user.email", "test@example.com")
        git(other, "config", "user.name", "Test")
        (other / "tracked.txt").write_text("v2\n", encoding="utf-8")
        (other / "landed.md").write_text("now tracked on main\n", encoding="utf-8")
        git(other, "add", "tracked.txt", "landed.md")
        git(other, "commit", "-m", "ahead")
        git(other, "push")

        (clone / ".venv").mkdir()
        (clone / ".venv" / "pyvenv.cfg").write_text("home = /tmp\n", encoding="utf-8")
        (clone / "notes.untracked").write_text("keep me\n", encoding="utf-8")
        (clone / "landed.md").write_text("local untracked copy\n", encoding="utf-8")
        (clone / "tracked.txt").write_text("local-dirty\n", encoding="utf-8")

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}", file=sys.stderr
            )
            return 1
        if not (clone / ".venv" / "pyvenv.cfg").is_file():
            return _fail(".venv was removed")
        if (clone / "notes.untracked").read_text(encoding="utf-8") != "keep me\n":
            return _fail("untracked file lost or changed")
        landed = (clone / "landed.md").read_text(encoding="utf-8")
        if landed != "now tracked on main\n":
            return _fail(
                "landed.md was not caught up from origin/main got="
                + repr(landed)
                + " stdout="
                + repr(proc.stdout)
            )
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "v2\n":
            return _fail("did not catch up tracked.txt")
        if "local-dirty" in (clone / "tracked.txt").read_text(encoding="utf-8"):
            return _fail("unique dirty was left in the worktree instead of parked")
        if "class=unique" not in proc.stdout:
            return _fail("did not classify unique dirty tracked")
        refs = run(
            [
                "git",
                "-C",
                str(clone),
                "for-each-ref",
                "--format=%(refname)",
                "refs/l9/preserved/ff-dirty/",
            ]
        )
        if not refs.stdout.strip():
            return _fail("dirty-tracked was not parked")
    return 0


def test_non_overlapping_dirty_still_parks() -> int:
    """origin changes A; clone dirties B. Triple-dot would miss B; reset --keep must still run."""
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        clone = Path(tmp) / "clone"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(clone)])
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Test")
        (clone / "a.txt").write_text("a1\n", encoding="utf-8")
        (clone / "b.txt").write_text("b1\n", encoding="utf-8")
        git(clone, "add", "a.txt", "b.txt")
        git(clone, "commit", "-m", "base")
        git(clone, "branch", "-M", "main")
        git(clone, "push", "-u", "origin", "main")
        # Same defaultBranch pitfall as above: pin the bare remote's HEAD so
        # the second clone lands on main and its push really advances it.
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        other = Path(tmp) / "other"
        run(["git", "clone", str(remote), str(other)])
        git(other, "config", "user.email", "test@example.com")
        git(other, "config", "user.name", "Test")
        (other / "a.txt").write_text("a2\n", encoding="utf-8")
        git(other, "add", "a.txt")
        git(other, "commit", "-m", "change a only")
        git(other, "push")

        (clone / "b.txt").write_text("b-local-unique\n", encoding="utf-8")
        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}", file=sys.stderr
            )
            return 1
        if (clone / "a.txt").read_text(encoding="utf-8") != "a2\n":
            return _fail("did not catch up a.txt")
        if (clone / "b.txt").read_text(encoding="utf-8") != "b1\n":
            return _fail("b.txt should be origin/HEAD after park+restore+keep")
        if "class=unique" not in proc.stdout:
            return _fail("unique b.txt dirt was not classified")
        hold_hits = list(home.joinpath(".cursor/l9-ff-hold").rglob("b.txt"))
        if not any(p.read_text(encoding="utf-8") == "b-local-unique\n" for p in hold_hits):
            return _fail("unique b.txt bytes were not copied to l9-ff-hold")
    return 0


def test_already_at_tip_leaves_dirty() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        clone = Path(tmp) / "clone"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(clone)])
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Test")
        (clone / "tracked.txt").write_text("tip\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "base")
        git(clone, "branch", "-M", "main")
        git(clone, "push", "-u", "origin", "main")
        (clone / "tracked.txt").write_text("unique-at-tip\n", encoding="utf-8")
        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}", file=sys.stderr
            )
            return 1
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "unique-at-tip\n":
            return _fail("already-at-tip dirty unique work was discarded")
        if "leave_at_tip" not in proc.stdout:
            return _fail("already-at-tip dirt was not classified leave_at_tip")
    return 0


def test_unrelated_history_with_dirty() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        clone = Path(tmp) / "clone"
        run(["git", "init", "--bare", str(remote)])

        seed = Path(tmp) / "seed"
        _init_clone(seed)
        (seed / "tracked.txt").write_text("origin\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "origin base")
        git(seed, "branch", "-M", "main")
        git(seed, "remote", "add", "origin", str(remote))
        git(seed, "push", "-u", "origin", "main")

        _init_clone(clone)
        (clone / "tracked.txt").write_text("other-history\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "unrelated")
        git(clone, "branch", "-M", "main")
        git(clone, "remote", "add", "origin", str(remote))
        git(clone, "fetch", "origin")
        (clone / "tracked.txt").write_text("local-unique-unrelated\n", encoding="utf-8")
        (clone / ".venv").mkdir()
        (clone / ".venv" / "pyvenv.cfg").write_text("home = /tmp\n", encoding="utf-8")
        (clone / "notes.untracked").write_text("keep\n", encoding="utf-8")

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}", file=sys.stderr
            )
            return 1
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "origin\n":
            return _fail("unrelated-history clone did not land on origin/main content")
        if (clone / "notes.untracked").read_text(encoding="utf-8") != "keep\n":
            return _fail("untracked lost on unrelated-history catch-up")
        if not (clone / ".venv" / "pyvenv.cfg").is_file():
            return _fail(".venv removed on unrelated-history catch-up")
        hold_hits = list(home.joinpath(".cursor/l9-ff-hold").rglob("tracked.txt"))
        if not any(p.read_text(encoding="utf-8") == "local-unique-unrelated\n" for p in hold_hits):
            return _fail("unrelated-history unique dirt was not held")
    return 0


def main() -> int:
    struct = run([sys.executable, str(ROOT / "scripts" / "validate_pack_structure.py")])
    if struct.returncode != 0:
        print(struct.stderr or struct.stdout, file=sys.stderr)
        return 1

    for name, fn in (
        ("behind_colliding", test_behind_with_colliding_and_hold),
        ("non_overlapping_dirty", test_non_overlapping_dirty_still_parks),
        ("already_at_tip", test_already_at_tip_leaves_dirty),
        ("unrelated_history", test_unrelated_history_with_dirty),
    ):
        rc = fn()
        if rc != 0:
            print(f"FAIL: {name}", file=sys.stderr)
            return rc

    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
