"""run.py as a state machine: gate verdicts, receipt reuse, isolation, concurrency."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import manifest  # noqa: E402
import run  # noqa: E402

# A stand-in shellcheck: reports every line containing BAD as an error and
# counts its invocations, so receipt reuse is observable.
FAKE_SHELLCHECK = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_COUNT"], "a") as fh:
    fh.write("x\\n")
comments = []
for path in [a for a in sys.argv[1:] if not a.startswith("-")]:
    for n, line in enumerate(open(path), 1):
        if "BAD" in line:
            comments.append(
                {"file": path, "line": n, "level": "error", "code": 1000, "message": "bad"}
            )
print(json.dumps({"comments": comments}))
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    fake = tmp_path / "fake-shellcheck"
    fake.write_text(FAKE_SHELLCHECK)
    fake.chmod(0o755)
    count = tmp_path / "count"
    count.write_text("")
    monkeypatch.setenv("FAKE_COUNT", str(count))
    (tmp_path / "inst").mkdir()
    (tmp_path / "inst" / "state.json").write_text(
        json.dumps({"shellcheck": {"version": "1", "path": str(fake)}})
    )
    yml = tmp_path / "tools.yaml"
    yml.write_text(
        "schema: l9.ci-parity.tools.v1\n"
        f"install_root: {tmp_path / 'inst'}\n"
        f"bin_dir: {tmp_path / 'bin'}\n"
        f"cache_root: {tmp_path / 'cache'}\n"
        "tools:\n  shellcheck:\n    version: '1'\n    method: release_binary\n"
        "    url: https://example.invalid/sc\n    sha256: '" + "0" * 64 + "'\n"
        "    binary: shellcheck\n    version_cmd: [--version]\n    expect: '1'\n"
        "lanes:\n  shellcheck:\n    tool: shellcheck\n    tier: fast\n    globs: ['*.sh']\n"
        "    block: [error]\n    weight: 1\n"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "a.sh").write_text("BAD legacy\nok\n")
    _git(repo, "add", "a.sh")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    return {"loaded": manifest.load(yml), "repo": repo, "base": base, "count": count}


def _calls(world: dict) -> int:
    return len(world["count"].read_text().splitlines())


def test_gate_blocks_only_a_new_finding_on_a_changed_line(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nBAD new\n")
    _git(repo, "commit", "-q", "-am", "add bad")
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 2
    out = capsys.readouterr().out
    assert "BLOCK a.sh:3" in out and "a.sh:1" not in out


def test_pre_existing_debt_never_blocks(world: dict) -> None:
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nfine\n")
    _git(repo, "commit", "-q", "-am", "clean change")
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 0


def test_receipt_is_reused_and_the_worktree_is_never_touched(world: dict) -> None:
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nBAD new\n")
    _git(repo, "commit", "-q", "-am", "add bad")
    (repo / "wip.txt").write_text("uncommitted edit in progress\n")
    before = _git(repo, "status", "--porcelain")
    assert run.mode_commit(world["loaded"], repo, "HEAD", world["base"], background=False) == 0
    first = _calls(world)
    assert first == 1
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 2
    assert _calls(world) == first  # push gate reused the commit-time receipt
    assert _git(repo, "status", "--porcelain") == before


def test_a_shallow_workspace_snapshot_sees_later_commits(world: dict, tmp_path: Path) -> None:
    """The snapshot of a shallow workspace must not freeze at its first commit.

    git ignores --shared/--local for a shallow source, so the cached clone is a
    copy with no alternates. Observed on a hosted (shallow) checkout: the first
    ci-parity run built the snapshot, and every run after the next commit failed
    `checkout --detach <sha>` with "reference is not a tree" (exit 128).
    """
    workspace = tmp_path / "shallow-ws"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{world['repo']}", str(workspace)],
        check=True,
        capture_output=True,
    )
    assert _git(workspace, "rev-parse", "--is-shallow-repository") == "true"
    cache = tmp_path / "snapcache"
    first = _git(workspace, "rev-parse", "HEAD")
    run.ensure_snapshot(workspace, cache, first)

    (workspace / "a.sh").write_text("ok\n")
    _git(workspace, "commit", "-q", "-am", "later commit")
    later = _git(workspace, "rev-parse", "HEAD")
    clone = run.ensure_snapshot(workspace, cache, later)
    assert _git(clone, "rev-parse", "HEAD") == later
    assert (clone / "a.sh").read_text() == "ok\n"


def test_fixing_the_finding_clears_the_gate(world: dict) -> None:
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nBAD new\n")
    _git(repo, "commit", "-q", "-am", "add bad")
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 2
    (repo / "a.sh").write_text("BAD legacy\nok\nfixed\n")
    _git(repo, "commit", "-q", "-am", "fix")
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 0


def test_absent_tool_is_a_skip_not_a_block(world: dict, capsys: pytest.CaptureFixture[str]) -> None:
    world["loaded"].state_path.write_text("{}")
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nBAD new\n")
    _git(repo, "commit", "-q", "-am", "add bad")
    assert run.mode_gate(world["loaded"], repo, "HEAD", world["base"]) == 0
    assert "not installed" in capsys.readouterr().out


def test_file_mode_reports_only_the_edited_lines(
    world: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = world["repo"]
    (repo / "a.sh").write_text("BAD legacy\nok\nBAD edited\n")
    assert run.mode_file(world["loaded"], [str(repo / "a.sh")]) == 0
    out = capsys.readouterr().out
    assert "a.sh:3" in out and "a.sh:1" not in out


def test_weighted_semaphore_never_exceeds_capacity() -> None:
    sem = run.WeightedSemaphore(3)
    peak = [0]
    lock = threading.Lock()

    def work(weight: int) -> None:
        taken = sem.acquire(weight)
        with lock:
            peak[0] = max(peak[0], sem.used)
        time.sleep(0.02)
        sem.release(taken)

    threads = [threading.Thread(target=work, args=(w,)) for w in (1, 2, 3, 1, 2, 5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak[0] <= 3 and sem.used == 0


def test_a_newer_commit_cancels_the_older_run(tmp_path: Path) -> None:
    proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
    (tmp_path / "inflight.json").write_text(
        json.dumps({"sha": "old", "pid": proc.pid, "pgid": proc.pid})
    )
    run.cancel_older(tmp_path, "new")
    assert proc.wait(timeout=5) == -signal.SIGTERM


def test_same_commit_is_not_cancelled(tmp_path: Path) -> None:
    proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        (tmp_path / "inflight.json").write_text(
            json.dumps({"sha": "same", "pid": proc.pid, "pgid": proc.pid})
        )
        run.cancel_older(tmp_path, "same")
        time.sleep(0.2)
        assert proc.poll() is None
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait()


def test_kill_switch_disables_every_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("L9_CI_PARITY", "0")
    assert run.main(["--gate", "HEAD"]) == 0
    assert "disabled" in capsys.readouterr().out


def test_missing_base_is_cannot_evaluate_not_the_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "f.txt").write_text("one\n")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "one")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("two\n")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "two")
    head = _git(repo, "rev-parse", "HEAD")
    parent = _git(repo, "rev-parse", "HEAD^")
    monkeypatch.delenv("PR_BASE", raising=False)
    monkeypatch.delenv("L9_CI_PARITY_BASE", raising=False)
    assert run.resolve_base(repo, head, "does-not-exist") is None
    assert run.resolve_base(repo, head, "does-not-exist") != parent
    assert run.resolve_base(repo, head, first) == first
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True,
        capture_output=True,
    )
    shallow_head = _git(shallow, "rev-parse", "HEAD")
    assert run.resolve_base(shallow, shallow_head, "does-not-exist") is None
    loaded = manifest.load()
    assert run.mode_gate(loaded, repo, head, "does-not-exist") == 0
    assert "cannot-evaluate" in capsys.readouterr().out


def test_manifest_bytes_change_the_runner_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    original = run._runner_digest()
    real = Path.read_bytes

    def wrapped(self: Path, *args: object, **kwargs: object) -> bytes:
        data = real(self, *args, **kwargs)
        if self.name == "manifest.py":
            return data + b"\n# semantic\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", wrapped)
    changed = run._runner_digest()
    assert changed != original
    lane = manifest.load().lanes["codeql"]
    tool = manifest.load().tools[lane.tool]
    assert run.lane_digest(lane, tool)
