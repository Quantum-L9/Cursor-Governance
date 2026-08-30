"""SP-01..SP-11 for ops/scripts/session_end_dirt_close.py."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import repo_hygiene  # noqa: E402
import session_end_dirt_close as dirt  # noqa: E402


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        env=merged,
    )
    return proc.stdout.strip()


def commit(root: Path, name: str, body: str = "x") -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")
    git(root, "add", "--", name)
    git(root, "commit", "-m", f"add {name}")


def sha256_text(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    upstream = tmp_path / "upstream.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(upstream)], check=True)
    root = tmp_path / "work"
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "remote", "add", "origin", str(upstream))
    commit(root, "base.txt", "base")
    commit(root, "landed.txt", "already on main")
    commit(root, "environment/generated/llm-rules/sample.md", "generated")
    git(root, "push", "-u", "origin", "main")
    return root


def _empty_blob_index(root: Path) -> str:
    path = root.parent / "empty-blobs.json"
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    return str(path)


def apply(root: Path, **kwargs: object) -> dict:
    payload = kwargs.pop("payload", {})
    assert isinstance(payload, dict)
    os.environ.setdefault("L9_DIRT_CLOSE_QUIET_SECONDS", "0")
    blob = kwargs.pop("blob_index_path", None)
    if blob is None:
        blob = _empty_blob_index(root)
    return dirt.run(
        root,
        apply=True,
        payload=payload,
        baseline="origin/main",
        blob_index_path=str(blob or ""),
        pr_heads=list(kwargs.pop("pr_heads", []) or []),
    )


def status(root: Path, **kwargs: object) -> dict:
    blob = kwargs.pop("blob_index_path", None)
    if blob is None:
        blob = _empty_blob_index(root)
    return dirt.run(
        root,
        apply=False,
        payload={},
        baseline="origin/main",
        blob_index_path=str(blob or ""),
        pr_heads=list(kwargs.pop("pr_heads", []) or []),
    )


def porcelain(root: Path) -> list[str]:
    return [rel for _st, rel in dirt.porcelain_rels(root)]


def test_sp01_unique_parks_and_cleans(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/work")
    (repo / "tracked.txt").write_text("modified unique", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "track")
    (repo / "tracked.txt").write_text("modified unique now", encoding="utf-8")
    (repo / "unique_untracked.md").write_text("only here", encoding="utf-8")

    result = apply(repo)
    st = result["status"]
    assert st["dirty_unique"] == 0
    assert st["skipped"] == ""
    assert "tracked.txt" not in porcelain(repo)
    assert "unique_untracked.md" not in porcelain(repo)
    assert dirt.ref_exists(repo, dirt.DIRT_SHELF_REF)
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "tracked.txt")
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "unique_untracked.md")


def test_sp02_baseline_blob_not_parked(repo: Path) -> None:
    git(repo, "rm", "--cached", "landed.txt")
    (repo / "landed.txt").write_text("already on main", encoding="utf-8")
    (repo / "novel.md").write_text("brand new", encoding="utf-8")

    result = apply(repo)
    st = result["status"]
    assert "landed.txt" in st["already_landed"]
    assert not dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "landed.txt")
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "novel.md")
    assert "landed.txt" not in porcelain(repo)
    assert "novel.md" not in porcelain(repo)


def test_sp03_secrets_left_and_never_indexed(repo: Path) -> None:
    secret_dir = repo / "WIP" / "Legal Defense"
    secret_dir.mkdir(parents=True)
    (secret_dir / "x").write_text("sensitive", encoding="utf-8")
    (repo / "WIP").mkdir(exist_ok=True)
    cred = repo / "WIP" / "bot-credentials.json"
    cred.write_text("{}", encoding="utf-8")
    (repo / "keep.md").write_text("novel", encoding="utf-8")

    result = apply(repo)
    st = result["status"]
    assert "WIP/Legal Defense/x" in st["left_in_tree"]
    assert "WIP/bot-credentials.json" in st["left_in_tree"]
    assert (secret_dir / "x").is_file()
    assert cred.is_file()
    assert not dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "WIP/Legal Defense/x")
    assert not dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "WIP/bot-credentials.json")


def test_sp04_second_apply_no_new_commit(repo: Path) -> None:
    (repo / "once.md").write_text("unique", encoding="utf-8")
    first = apply(repo)
    tip = dirt.ref_sha(repo, dirt.DIRT_SHELF_REF)
    second = apply(repo)
    assert dirt.ref_sha(repo, dirt.DIRT_SHELF_REF) == tip
    assert second["shelf_commit"] in {"", "unchanged"}
    assert first["status"]["dirty_unique"] == 0
    assert second["status"]["dirty_unique"] == 0


def test_sp05_aborted_and_background_skip(repo: Path) -> None:
    (repo / "stay.md").write_text("should stay", encoding="utf-8")
    aborted = apply(repo, payload={"reason": "aborted"})
    assert aborted["skip"].startswith("sessionEnd reason=")
    assert (repo / "stay.md").is_file()
    assert not dirt.ref_exists(repo, dirt.DIRT_SHELF_REF)

    bg = apply(repo, payload={"reason": "completed", "is_background_agent": True})
    assert bg["skip"] == "background agent session"
    assert (repo / "stay.md").is_file()


def test_sp06_quiet_window_skips(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "fresh.md").write_text("new", encoding="utf-8")
    monkeypatch.setenv("L9_DIRT_CLOSE_QUIET_SECONDS", "600")
    result = apply(repo, payload={"reason": "completed"})
    assert "quiet window" in result["skip"]
    assert (repo / "fresh.md").is_file()


def test_sp07_lock_skips(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "locked.md").write_text("new", encoding="utf-8")
    ident = dirt.lock_id(repo)
    lock = Path.home() / ".cursor" / f"l9-repo-write.{ident}.lock.d"
    lock.mkdir(parents=True, exist_ok=True)
    (lock / "owner").write_text("1 1 /tmp test\n", encoding="utf-8")
    try:
        monkeypatch.setenv("L9_DIRT_CLOSE_QUIET_SECONDS", "0")
        result = apply(repo, payload={"reason": "completed"})
        assert result["skip"] == "repo-write lock held"
        assert (repo / "locked.md").is_file()
    finally:
        (lock / "owner").unlink(missing_ok=True)
        lock.rmdir()


def test_sp08_generated_restored_not_parked(repo: Path) -> None:
    gen = repo / "environment" / "generated" / "llm-rules" / "sample.md"
    gen.write_text("dirty generated", encoding="utf-8")
    result = apply(repo)
    assert "environment/generated/llm-rules/sample.md" in result["status"]["already_landed"]
    assert gen.read_text(encoding="utf-8") == "generated"
    assert not dirt.path_on_rev(
        repo, dirt.DIRT_SHELF_REF, "environment/generated/llm-rules/sample.md"
    )


def test_sp09_open_pr_blob_removed_not_parked(repo: Path, tmp_path: Path) -> None:
    body = "same as the PR"
    (repo / "pr_copy.md").write_text(body, encoding="utf-8")
    index = tmp_path / "blobs.json"
    index.write_text(json.dumps({"pr_copy.md": [sha256_text(body)]}), encoding="utf-8")
    result = apply(repo, blob_index_path=index)
    assert "pr_copy.md" in result["status"]["already_landed"]
    assert not (repo / "pr_copy.md").exists()
    assert not dirt.ref_exists(repo, dirt.DIRT_SHELF_REF) or not dirt.path_on_rev(
        repo, dirt.DIRT_SHELF_REF, "pr_copy.md"
    )


def test_sp10_absorbed_shelf_pruned(repo: Path) -> None:
    (repo / "temp_novel.md").write_text("will land", encoding="utf-8")
    first = apply(repo)
    assert dirt.ref_exists(repo, dirt.DIRT_SHELF_REF)
    tip = first["status"]["novel_parked"]
    assert "temp_novel.md" in tip
    git(repo, "show", f"{dirt.DIRT_SHELF_REF}:temp_novel.md")
    (repo / "temp_novel.md").write_text("will land", encoding="utf-8")
    git(repo, "add", "--", "temp_novel.md")
    git(repo, "commit", "-m", "land novel")
    git(repo, "push", "origin", "main")
    second = apply(repo)
    assert not dirt.ref_exists(repo, dirt.DIRT_SHELF_REF)
    assert second["status"]["absorbed_pruned"]
    assert second["status"]["novel_parked"] == []
    assert "temp_novel.md" not in second["status"]["dirty_files"]


def test_sp11_status_zero_on_landed_pile(repo: Path) -> None:
    for i in range(49):
        commit(repo, f"copy{i}.txt", f"body-{i}")
    git(repo, "push", "origin", "main")
    cached = [f"copy{i}.txt" for i in range(49)] + ["landed.txt"]
    git(repo, "rm", "--cached", "--", *cached)

    before = status(repo)
    assert before["dirty_unique"] == 0
    assert len(before["already_landed"]) == 50
    after = apply(repo)
    assert after["status"]["dirty_unique"] == 0
    assert "landed.txt" not in porcelain(repo)
    for i in range(49):
        assert f"copy{i}.txt" not in porcelain(repo)


def test_dirt_shelf_is_protected_from_hygiene(repo: Path) -> None:
    (repo / "keep_me.md").write_text("novel", encoding="utf-8")
    apply(repo)
    assert dirt.ref_exists(repo, dirt.DIRT_SHELF_REF)
    report = repo_hygiene.build_report(repo_hygiene.Git(repo), max_stash_age=24)
    shelf = next(b for b in report.branches if b.name == "l9/dirt-shelf")
    assert shelf.status == "protected"
    assert shelf.action == "keep"


def test_error_reason_skips(repo: Path) -> None:
    (repo / "x.md").write_text("n", encoding="utf-8")
    result = apply(repo, payload={"reason": "error"})
    assert result["skip"] == "sessionEnd reason=error"
    assert (repo / "x.md").is_file()


def test_rolling_shelf_keeps_earlier_parks(repo: Path) -> None:
    (repo / "first.md").write_text("one", encoding="utf-8")
    apply(repo)
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "first.md")
    (repo / "second.md").write_text("two", encoding="utf-8")
    apply(repo)
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "first.md")
    assert dirt.path_on_rev(repo, dirt.DIRT_SHELF_REF, "second.md")


def test_staged_head_absent_is_unstaged(repo: Path) -> None:
    (repo / "staged.md").write_text("only index", encoding="utf-8")
    git(repo, "add", "--", "staged.md")
    result = apply(repo)
    assert result["status"]["dirty_unique"] == 0
    assert "staged.md" not in porcelain(repo)
    ls = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--", "staged.md"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert ls.stdout.strip() == ""


def test_park_failure_does_not_delete_worktree(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "keep.md").write_text("unique", encoding="utf-8")

    def boom(root: Path, rels: list[str]) -> tuple[str, str]:
        return dirt.DIRT_SHELF_REF, "update-ref-failed:denied"

    monkeypatch.setattr(dirt, "park_novel", boom)
    result = apply(repo)
    assert (repo / "keep.md").is_file()
    assert "keep.md" in result["status"]["dirty_files"]


def test_hook_uses_ssot_script_only() -> None:
    text = (REPO / "ops" / "hooks" / "session_end_repo_hygiene.sh").read_text(encoding="utf-8")
    assert 'DIRT_CLOSE="$GLOBAL_COMMANDS/ops/scripts/session_end_dirt_close.py"' in text
    assert 'DIRT_CLOSE="$WS/ops/scripts/session_end_dirt_close.py"' not in text
