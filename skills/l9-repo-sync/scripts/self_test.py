#!/usr/bin/env python3
"""Fixture self-test: /ff parks unique work and never deletes it."""

from __future__ import annotations

import json
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
    # The fixtures assume `git init --bare` yields HEAD -> refs/heads/main; on a
    # host where init.defaultBranch is unset git uses master, the bare remote's
    # HEAD dangles, and clones land on an unborn branch instead of main.
    merged["GIT_CONFIG_COUNT"] = "2"
    merged["GIT_CONFIG_KEY_0"] = "init.defaultBranch"
    merged["GIT_CONFIG_VALUE_0"] = "main"
    merged["GIT_CONFIG_KEY_1"] = "core.excludesFile"
    merged["GIT_CONFIG_VALUE_1"] = ""
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
        (clone / ".env.local").write_text(
            "DEEPSEEK_API_KEY=sk-TEST-KEEP-NOT-REAL\n", encoding="utf-8"
        )
        (clone / ".claude").mkdir()
        (clone / ".claude" / "settings.local.json").write_text("{}\n", encoding="utf-8")
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
        if (clone / ".env.local").read_text(
            encoding="utf-8"
        ) != "DEEPSEEK_API_KEY=sk-TEST-KEEP-NOT-REAL\n":
            return _fail(".env.local was removed or changed")
        if (clone / ".claude" / "settings.local.json").read_text(encoding="utf-8") != "{}\n":
            return _fail(".claude/settings.local.json was removed or changed")
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


def test_origin_tracked_env_local_does_not_clobber() -> int:
    """If origin starts tracking .env.local, /ff must not move or overwrite the local copy."""
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
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        other = Path(tmp) / "other"
        run(["git", "clone", str(remote), str(other)])
        git(other, "config", "user.email", "test@example.com")
        git(other, "config", "user.name", "Test")
        (other / "tracked.txt").write_text("v2\n", encoding="utf-8")
        (other / ".env.local").write_text(
            "DEEPSEEK_API_KEY=sk-ORIGIN-SHOULD-NOT-WIN\n", encoding="utf-8"
        )
        git(other, "add", "tracked.txt", ".env.local")
        git(other, "commit", "-m", "origin tracks env.local")
        git(other, "push")

        (clone / ".env.local").write_text(
            "DEEPSEEK_API_KEY=sk-TEST-KEEP-NOT-REAL\n", encoding="utf-8"
        )
        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
                file=sys.stderr,
            )
            return 1
        if (clone / ".env.local").read_text(
            encoding="utf-8"
        ) != "DEEPSEEK_API_KEY=sk-TEST-KEEP-NOT-REAL\n":
            return _fail("local .env.local was clobbered by origin")
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "v2\n":
            return _fail("did not catch up tracked.txt")
    return 0


def test_feature_branch_switches_to_main() -> int:
    """Off-main clone: switch to main, keep the feature ref, park feature dirt."""
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
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        other = Path(tmp) / "other"
        run(["git", "clone", str(remote), str(other)])
        git(other, "config", "user.email", "test@example.com")
        git(other, "config", "user.name", "Test")
        (other / "tracked.txt").write_text("v2\n", encoding="utf-8")
        git(other, "add", "tracked.txt")
        git(other, "commit", "-m", "origin ahead")
        git(other, "push")

        git(clone, "checkout", "-b", "feat/unique")
        (clone / "feature.txt").write_text("only-on-feature\n", encoding="utf-8")
        git(clone, "add", "feature.txt")
        git(clone, "commit", "-m", "unique feature commit")
        feature_sha = run(["git", "-C", str(clone), "rev-parse", "HEAD"]).stdout.strip()
        (clone / "tracked.txt").write_text("feature-dirty\n", encoding="utf-8")
        (clone / ".venv").mkdir()
        (clone / ".venv" / "pyvenv.cfg").write_text("home = /tmp\n", encoding="utf-8")
        (clone / "notes.untracked").write_text("keep me\n", encoding="utf-8")

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
                file=sys.stderr,
            )
            return 1
        branch = run(["git", "-C", str(clone), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        if branch != "main":
            return _fail(f"expected HEAD on main, got {branch}")
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "v2\n":
            return _fail("did not catch up tracked.txt from origin/main")
        if (clone / "feature.txt").is_file():
            return _fail("feature-only tracked file leaked onto main")
        still = run(["git", "-C", str(clone), "rev-parse", "feat/unique"]).stdout.strip()
        if still != feature_sha:
            return _fail("feature branch tip moved; unique commits must stay")
        if "step 0 switched feat/unique -> main" not in proc.stdout:
            return _fail("missing step 0 switch log")
        if "feature-dirty" in (clone / "tracked.txt").read_text(encoding="utf-8"):
            return _fail("feature dirty was left on main")
        hold_hits = list(home.joinpath(".cursor/l9-ff-hold").rglob("tracked.txt"))
        if not any(p.read_text(encoding="utf-8") == "feature-dirty\n" for p in hold_hits):
            return _fail("feature dirty bytes were not copied to l9-ff-hold")
        if (clone / "notes.untracked").read_text(encoding="utf-8") != "keep me\n":
            return _fail("untracked file lost across switch")
        if not (clone / ".venv" / "pyvenv.cfg").is_file():
            return _fail(".venv was removed")
        preserve = run(
            [
                "git",
                "-C",
                str(clone),
                "for-each-ref",
                "--format=%(refname)",
                "refs/l9/preserved/ff/",
            ]
        )
        if preserve.stdout.strip():
            return _fail("must not park feature commits as l9/ff-preserve-*")
    return 0


def _force_shallow(repo: Path) -> None:
    """Mark a local clone shallow. ``git clone --depth`` is a no-op on file://."""
    git_dir = Path(run(["git", "-C", str(repo), "rev-parse", "--git-dir"]).stdout.strip())
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    head = run(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    (git_dir / "shallow").write_text(f"{head}\n", encoding="utf-8")


def _preserve_refs(clone: Path) -> str:
    return run(
        [
            "git",
            "-C",
            str(clone),
            "for-each-ref",
            "--format=%(refname)",
            "refs/l9/preserved/ff/",
        ]
    ).stdout.strip()


def test_shallow_behind_never_preserves() -> int:
    """SHA-unequal shallow clone must not create l9/ff-preserve-* from rev-list."""
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        seed = Path(tmp) / "seed"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(seed)])
        git(seed, "config", "user.email", "test@example.com")
        git(seed, "config", "user.name", "Test")
        (seed / "tracked.txt").write_text("c0\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "c0")
        git(seed, "branch", "-M", "main")
        (seed / "tracked.txt").write_text("c1\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "c1")
        git(seed, "push", "-u", "origin", "main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        shallow = Path(tmp) / "shallow"
        run(["git", "clone", str(remote), str(shallow)])
        git(shallow, "config", "user.email", "test@example.com")
        git(shallow, "config", "user.name", "Test")
        _force_shallow(shallow)
        shallow_flag = run(
            ["git", "-C", str(shallow), "rev-parse", "--is-shallow-repository"]
        ).stdout.strip()
        if shallow_flag != "true":
            return _fail(f"fixture clone is not shallow, got {shallow_flag!r}")

        (seed / "tracked.txt").write_text("c2\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "c2")
        git(seed, "push")

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(shallow), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
                file=sys.stderr,
            )
            return 1
        if (shallow / "tracked.txt").read_text(encoding="utf-8") != "c2\n":
            return _fail("shallow clone did not catch up via reset --keep")
        if _preserve_refs(shallow):
            return _fail("shallow unequal must not write l9/ff-preserve-* from rev-list")
        if "skip rev-list preserve" not in proc.stdout:
            return _fail("missing shallow SHA-unequal log")
    return 0


def test_shallow_at_tip_leaves_dirty() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        seed = Path(tmp) / "seed"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(seed)])
        git(seed, "config", "user.email", "test@example.com")
        git(seed, "config", "user.name", "Test")
        (seed / "tracked.txt").write_text("base\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "base")
        git(seed, "branch", "-M", "main")
        (seed / "tracked.txt").write_text("tip\n", encoding="utf-8")
        git(seed, "add", "tracked.txt")
        git(seed, "commit", "-m", "tip")
        git(seed, "push", "-u", "origin", "main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        shallow = Path(tmp) / "shallow"
        run(["git", "clone", str(remote), str(shallow)])
        git(shallow, "config", "user.email", "test@example.com")
        git(shallow, "config", "user.name", "Test")
        _force_shallow(shallow)
        if (
            run(["git", "-C", str(shallow), "rev-parse", "--is-shallow-repository"]).stdout.strip()
            != "true"
        ):
            return _fail("at-tip fixture clone is not shallow")
        (shallow / "tracked.txt").write_text("unique-shallow-tip\n", encoding="utf-8")

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(shallow), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
                file=sys.stderr,
            )
            return 1
        if (shallow / "tracked.txt").read_text(encoding="utf-8") != "unique-shallow-tip\n":
            return _fail("SHA-equal shallow at-tip discarded dirty work")
        if _preserve_refs(shallow):
            return _fail("SHA-equal shallow must not preserve")
        if "leave_at_tip" not in proc.stdout:
            return _fail("SHA-equal shallow dirt was not leave_at_tip")
    return 0


def test_full_history_unique_tip_preserves() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        remote = Path(tmp) / "remote.git"
        clone = Path(tmp) / "clone"
        run(["git", "init", "--bare", str(remote)])
        run(["git", "clone", str(remote), str(clone)])
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Test")
        (clone / "tracked.txt").write_text("origin\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "base")
        git(clone, "branch", "-M", "main")
        git(clone, "push", "-u", "origin", "main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

        (clone / "extra.txt").write_text("unique-on-main\n", encoding="utf-8")
        git(clone, "add", "extra.txt")
        git(clone, "commit", "-m", "unique main commit")
        unique_sha = run(["git", "-C", str(clone), "rev-parse", "HEAD"]).stdout.strip()

        home = Path(tmp) / "home"
        home.mkdir()
        proc = run(
            ["bash", str(FF)],
            env={"CURSOR_GOVERNANCE_DIR": str(clone), "HOME": str(home)},
        )
        if proc.returncode != 0:
            print(
                f"FAIL: ff.sh rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}",
                file=sys.stderr,
            )
            return 1
        if not _preserve_refs(clone):
            return _fail("full-history unique tip must write l9/ff-preserve-*")
        parked = run(
            [
                "git",
                "-C",
                str(clone),
                "for-each-ref",
                "--format=%(objectname)",
                "refs/l9/preserved/ff/",
            ]
        ).stdout.strip()
        if unique_sha not in parked:
            return _fail("preserve ref must point at the unique tip")
        if (clone / "tracked.txt").read_text(encoding="utf-8") != "origin\n":
            return _fail("reset --keep did not return main to origin")
        if (clone / "extra.txt").is_file():
            return _fail("unique file must leave main after preserve+reset")
    return 0


def _ff_shelf() -> Path:
    return ROOT / "scripts" / "ff_shelf.py"


def test_ff_shelf_list_and_rsync_argv() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        _init_clone(clone)
        (clone / "tracked.txt").write_text("t\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "base")
        (clone / "WIP").mkdir()
        (clone / "WIP" / "note.md").write_text("wip leftover\n", encoding="utf-8")
        (clone / "docs" / "plans").mkdir(parents=True)
        (clone / "docs" / "plans" / "left.md").write_text("plan leftover\n", encoding="utf-8")
        (clone / "root-queue.md").write_text("not corpus leftover\n", encoding="utf-8")
        shelf = Path(tmp) / "shelf"
        proc = run(
            [
                sys.executable,
                str(_ff_shelf()),
                "--clone",
                str(clone),
                "--dry-run",
                "--stamp",
                "20260905T000000Z",
                "--shelf-worktree",
                str(shelf),
                "--author",
                "tester",
            ]
        )
        if proc.returncode != 0:
            return _fail(f"ff_shelf dry-run failed: {proc.stderr or proc.stdout}")
        data = json.loads(proc.stdout)
        list_path = Path(data["list_path"])
        if list_path.resolve() != (clone / ".l9" / "ff-shelf-untracked.txt").resolve():
            return _fail(f"list must land under clone .l9/, got {list_path}")
        if not list_path.is_file():
            return _fail("list file was not written")
        listed = list_path.read_text(encoding="utf-8").splitlines()
        if "WIP/note.md" not in listed or "docs/plans/left.md" not in listed:
            return _fail(f"missing leftover paths: {listed}")
        if "root-queue.md" in listed:
            return _fail("root queue file must not be shelved")
        rsync = data["rsync"]
        joined = " ".join(rsync)
        if "<(" in joined:
            return _fail("rsync must not use process substitution")
        files_from = next((a for a in rsync if a.startswith("--files-from=")), "")
        if files_from != f"--files-from={list_path}":
            return _fail(f"files-from must be the in-clone list, got {files_from}")
        if files_from.startswith("--files-from=/tmp/") and "/.l9/" not in files_from:
            return _fail("files-from must not be a /tmp path")
        add = data["add"]
        if "--pathspec-from-file=" + str(list_path) not in add:
            return _fail("add must use --pathspec-from-file alone")
        if "commit" in add or "status" in add or "&&" in " ".join(add):
            return _fail("add command must not also commit or status")
    return 0


def test_ff_shelf_append_not_restamp() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        _init_clone(clone)
        (clone / "tracked.txt").write_text("t\n", encoding="utf-8")
        git(clone, "add", "tracked.txt")
        git(clone, "commit", "-m", "base")
        (clone / "docs" / "plans").mkdir(parents=True)
        (clone / "docs" / "plans" / "left.md").write_text("plan leftover\n", encoding="utf-8")
        prs = [
            {
                "number": 1,
                "headRefName": "feat/ff-shelf-old",
                "author": {"login": "tester"},
                "updatedAt": "2026-09-01T00:00:00Z",
            },
            {
                "number": 2,
                "headRefName": "feat/ff-shelf-newer",
                "author": {"login": "tester"},
                "updatedAt": "2026-09-05T00:00:00Z",
            },
            {
                "number": 3,
                "headRefName": "feat/ff-shelf-other",
                "author": {"login": "someone-else"},
                "updatedAt": "2026-09-06T00:00:00Z",
            },
        ]
        pr_path = Path(tmp) / "prs.json"
        pr_path.write_text(json.dumps(prs), encoding="utf-8")
        proc = run(
            [
                sys.executable,
                str(_ff_shelf()),
                "--clone",
                str(clone),
                "--dry-run",
                "--stamp",
                "20260905T999999Z",
                "--author",
                "tester",
                "--open-shelf-prs",
                str(pr_path),
            ]
        )
        if proc.returncode != 0:
            return _fail(f"ff_shelf append dry-run failed: {proc.stderr or proc.stdout}")
        data = json.loads(proc.stdout)
        if data.get("action") != "append":
            return _fail(f"expected append, got {data.get('action')}")
        if data.get("branch") != "feat/ff-shelf-newer":
            return _fail(f"must append newest same-author shelf PR, got {data.get('branch')}")
        if data.get("branch") == "feat/ff-shelf-20260905T999999Z":
            return _fail("must not cut a second stamp")
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
        ("keep_env_local", test_origin_tracked_env_local_does_not_clobber),
        ("feature_branch_switch", test_feature_branch_switches_to_main),
        ("shallow_behind", test_shallow_behind_never_preserves),
        ("shallow_at_tip", test_shallow_at_tip_leaves_dirty),
        ("full_history_unique", test_full_history_unique_tip_preserves),
        ("ff_shelf_rsync", test_ff_shelf_list_and_rsync_argv),
        ("ff_shelf_append", test_ff_shelf_append_not_restamp),
    ):
        rc = fn()
        if rc != 0:
            print(f"FAIL: {name}", file=sys.stderr)
            return rc

    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
