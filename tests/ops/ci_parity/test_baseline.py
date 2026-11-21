"""PR gate blocks only on what the change introduces (operator decision 2026-11-21).

`changed-files` and `whole-tree` lanes re-scan the merge-base snapshot and match
findings by fingerprint; a finding present at the merge-base is a WARN, never a
block. An unresolvable base, a failed base scan, or a lane that did not finish
fails closed (exit 3): unknown never passes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import findings as fnd  # noqa: E402
import manifest  # noqa: E402
import run  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        + ["-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _scan_bad(ctx: run.Context, lane: object, binary: Path, files: list[str]) -> list:
    """Stand-in scanner: every line containing BAD is an error. A `whole-tree`
    lane scans every *.txt in the snapshot; the others scan the files given."""
    root = ctx.scan_dir
    if getattr(lane, "extra", {}).get("scope") == "whole-tree":
        targets = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.txt"))
    else:
        targets = files
    out = []
    for rel in targets:
        for number, line in enumerate((root / rel).read_text().splitlines(), 1):
            if "BAD" in line:
                out.append(fnd.Finding("fake", "bad", "error", rel, number, "bad pattern"))
    return out


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    binary = tmp_path / "fake-tool"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    (tmp_path / "inst").mkdir()
    (tmp_path / "inst" / "state.json").write_text(
        json.dumps({"fake": {"version": "1", "path": str(binary)}})
    )
    yml = tmp_path / "tools.yaml"
    yml.write_text(
        "schema: l9.ci-parity.tools.v1\n"
        f"install_root: {tmp_path / 'inst'}\n"
        f"bin_dir: {tmp_path / 'bin'}\n"
        f"cache_root: {tmp_path / 'cache'}\n"
        "tools:\n  fake:\n    version: '1'\n    method: release_binary\n"
        "    url: https://example.invalid/fake\n    sha256: '" + "0" * 64 + "'\n"
        "    binary: fake\n    version_cmd: [--version]\n    expect: '1'\n"
        "lanes:\n"
        "  biome:\n    tool: fake\n    tier: fast\n    globs: ['*.txt']\n"
        "    block: [error]\n    scope: changed-files\n    weight: 1\n"
        "  semgrep-l9:\n    tool: fake\n    tier: heavy\n    globs: ['*.txt']\n"
        "    block: [error]\n    scope: whole-tree\n    weight: 1\n"
    )
    monkeypatch.setitem(run.LANES, "biome", _scan_bad)
    monkeypatch.setitem(run.LANES, "semgrep-l9", _scan_bad)
    monkeypatch.delenv("PR_BASE", raising=False)
    monkeypatch.delenv("L9_CI_PARITY_BASE", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "a.txt").write_text("one\nBAD legacy\nthree\n")
    (repo / "other.txt").write_text("BAD elsewhere\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    return {"loaded": manifest.load(yml), "repo": repo, "base": _git(repo, "rev-parse", "HEAD")}


def _gate(world: dict, lanes: str) -> int:
    return run.mode_gate(world["loaded"], world["repo"], "HEAD", world["base"], lanes.split(","))


def _receipt(world: dict, lane: str) -> dict:
    cache = run.cache_dir(world["loaded"], run.repo_slug(world["repo"]))
    (path,) = (cache / "receipts").glob(f"*/{lane}.json")
    return json.loads(path.read_text())


@pytest.mark.parametrize("lane", ["biome", "semgrep-l9"])
def test_a_new_finding_blocks(world: dict, lane: str, capsys: pytest.CaptureFixture[str]) -> None:
    repo = world["repo"]
    (repo / "a.txt").write_text("one\nBAD legacy\nthree\nBAD introduced\n")
    _git(repo, "commit", "-q", "-am", "introduce")
    assert _gate(world, lane) == run.EXIT_BLOCK
    out = capsys.readouterr().out
    assert "BLOCK a.txt:4" in out
    assert "BLOCK a.txt:2" not in out and "WARN  pre-existing a.txt:2" in out
    record = _receipt(world, lane)
    assert record["new"] == 1 and record["baseline"] == "merge-base"
    assert record["preexisting"] == (2 if lane == "semgrep-l9" else 1)


@pytest.mark.parametrize("lane", ["biome", "semgrep-l9"])
def test_a_finding_only_pre_existing_warns_and_passes(
    world: dict, lane: str, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = world["repo"]
    # The legacy finding moves down two lines: same code, same file.
    (repo / "a.txt").write_text("zero\nhalf\none\nBAD legacy\nthree\n")
    _git(repo, "commit", "-q", "-am", "touch the file")
    assert _gate(world, lane) == 0
    out = capsys.readouterr().out
    assert "BLOCK" not in out
    assert "WARN  pre-existing a.txt:4" in out
    assert "pre-existing finding(s)" in out  # the per-lane count line
    record = _receipt(world, lane)
    assert record["status"] == "pass" and record["new"] == 0 and record["preexisting"] >= 1
    assert [f["path"] for f in record["preexisting_blocking"]].count("a.txt") == 1


def test_an_unresolvable_base_blocks(world: dict, capsys: pytest.CaptureFixture[str]) -> None:
    code = run.mode_gate(world["loaded"], world["repo"], "HEAD", "no-such-base", ["biome"])
    assert code == run.EXIT_INCOMPLETE
    assert "BLOCK cannot-evaluate" in capsys.readouterr().out


def test_an_incomplete_head_scan_blocks(
    world: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unfinished(ctx: run.Context, lane: object, binary: Path, files: list[str]) -> list:
        ctx.notices.append("fake: gate incomplete — no report")
        return []

    monkeypatch.setitem(run.LANES, "biome", unfinished)
    repo = world["repo"]
    (repo / "a.txt").write_text("one\nBAD legacy\nthree\nfine\n")
    _git(repo, "commit", "-q", "-am", "clean change")
    assert _gate(world, "biome") == run.EXIT_INCOMPLETE
    assert "INCOMPLETE" in capsys.readouterr().out
    assert _receipt(world, "biome")["incomplete"] is True


def test_a_failed_base_scan_blocks(
    world: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def base_fails(ctx: run.Context, lane: object, binary: Path, files: list[str]) -> list:
        if ctx.sha == world["base"]:
            ctx.notices.append("fake: base scan crashed")
            return []
        return _scan_bad(ctx, lane, binary, files)

    monkeypatch.setitem(run.LANES, "biome", base_fails)
    repo = world["repo"]
    (repo / "a.txt").write_text("zero\none\nBAD legacy\nthree\n")
    _git(repo, "commit", "-q", "-am", "move legacy")
    # The legacy finding cannot be shown pre-existing, so it stays new and blocks.
    assert _gate(world, "biome") == run.EXIT_BLOCK
    out = capsys.readouterr().out
    assert "BLOCK a.txt:3" in out
    assert "baseline unavailable" in out and "INCOMPLETE" in out
    record = _receipt(world, "biome")
    assert record["baseline"] == "unavailable" and record["incomplete"] is True
    assert not run.receipt_reusable(world["loaded"], world["loaded"].lanes["biome"], record)


def test_a_renamed_file_keeps_its_pre_existing_finding(world: dict) -> None:
    repo = world["repo"]
    _git(repo, "mv", "a.txt", "renamed.txt")
    _git(repo, "commit", "-q", "-m", "rename")
    assert _gate(world, "biome") == 0
    record = _receipt(world, "biome")
    assert record["new"] == 0 and record["preexisting"] == 1


def test_a_finding_moved_to_another_file_counts_as_new(world: dict) -> None:
    """Known fingerprint limit, erring toward blocking: the fingerprint carries
    the path (as Semgrep's match_based_id does), so code moved into another file
    is a new finding there even though the same text existed elsewhere."""
    repo = world["repo"]
    (repo / "a.txt").write_text("one\nthree\n")
    (repo / "moved.txt").write_text("BAD legacy\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "move a line across files")
    assert _gate(world, "biome") == run.EXIT_BLOCK


def test_a_repeat_of_a_pre_existing_finding_is_new(world: dict) -> None:
    repo = world["repo"]
    (repo / "a.txt").write_text("one\nBAD legacy\nthree\nBAD legacy\n")
    _git(repo, "commit", "-q", "-am", "duplicate")
    assert _gate(world, "biome") == run.EXIT_BLOCK
    record = _receipt(world, "biome")
    assert record["new"] == 1 and record["preexisting"] == 1


def test_a_core_refusal_is_never_pre_existing(tmp_path: Path) -> None:
    refusal = run.CoreRefusal("resolve-consumer-metadata", "product_kind invalid").finding()
    new, pre = fnd.split_new([refusal], tmp_path, [refusal], tmp_path, {})
    assert new == [refusal] and pre == []


def test_parse_renames_reads_name_status_rows() -> None:
    rows = "R100\told/a.py\tnew/a.py\nM\tkeep.py\nR087\tx.ts\ty.ts\n"
    assert fnd.parse_renames(rows) == {"new/a.py": "old/a.py", "y.ts": "x.ts"}
