"""Governance must not leave the wiring it injects as dirt in a consumer.

The Claude adapter's reconcilers materialize real files inside every workspace
they touch: `.claude/settings.json` and the two `CONSUMER_HOOK_FILES` hooks.
The installer's exclude list deliberately omitted them as "committable consumer
wiring" — right for a repo that commits them, wrong for the repo that does not,
where they sit as `??` after every session and land in any inventory that
enumerates the working tree.

Tracked-ness is the ownership signal, exactly as
`reconcile_claude_settings.settings_is_git_tracked` already defines it: a
tracked file is repo content and is left alone; an untracked one was injected
here and is governance's to contain. So the exclusion is conditional — an
unconditional one would force `git add -f` on a consumer that legitimately
commits its wiring.

These tests run the real installer against throwaway repositories and assert
the observable effect (`git status`), not the text of the glob list.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
RECONCILER = ROOT / "ops" / "scripts" / "reconcile_claude_settings.py"
GOV_PY = ROOT / ".venv" / "bin" / "python3"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def _workspace(tmp_path: Path, *, commit_wiring: bool) -> Path:
    repo = tmp_path / ("tracked" if commit_wiring else "untracked")
    (repo / ".claude" / "hooks").mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    # Only the SessionStart bootstrap hook is projected; the fail-open
    # merge_gate_wrap.py consumer copy was retired (gates dispatch through the
    # launcher, INV-1), so it is no longer an injected artifact here.
    (repo / ".claude" / "hooks" / "session_start_claude_governance.sh").write_text(
        "#!/bin/sh\n", encoding="utf-8"
    )
    _git(repo, "add", "README.md")
    if commit_wiring:
        _git(repo, "add", "-f", ".claude/settings.json", ".claude/hooks")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return repo


def _install(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALL), "--governance", str(ROOT), "--workspace", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_reconciler_publishes_the_files_it_writes() -> None:
    """The installer reads this list instead of restating it in shell."""
    out = subprocess.run(
        [str(GOV_PY), str(RECONCILER), "--print-workspace-artifacts"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert ".claude/settings.json" in out
    assert any(item.startswith(".claude/hooks/") for item in out)


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; installer cannot run")
def test_injected_wiring_leaves_no_dirt(tmp_path: Path) -> None:
    """A consumer that never committed the wiring ends the session clean."""
    repo = _workspace(tmp_path, commit_wiring=False)
    assert _git(repo, "status", "--porcelain").stdout.strip(), "fixture should start dirty"

    _install(repo)

    assert _git(repo, "status", "--porcelain").stdout.strip() == ""


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; installer cannot run")
def test_committed_wiring_is_left_alone(tmp_path: Path) -> None:
    """Repo content stays visible: no exclusion, so edits still show up."""
    repo = _workspace(tmp_path, commit_wiring=True)

    _install(repo)

    exclude = repo / ".git" / "info" / "exclude"
    body = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    assert ".claude/settings.json" not in body.splitlines()

    (repo / ".claude" / "settings.json").write_text('{"edited": true}\n', encoding="utf-8")
    assert ".claude/settings.json" in _git(repo, "status", "--porcelain").stdout


# --- F-548-007 / F-548-008: projection is ownership-aware ------------------------
#
# The reconciler is driven directly here (not through the installer) so the
# properties are isolated: tracked hook bytes survive projection while drift is
# reported; an untracked managed hook converges; a retired projection is pruned
# when untracked and preserved-with-report when tracked.

HOOK_SRC = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
SESSION_HOOK = "session_start_claude_governance.sh"
RETIRED_HOOK = "merge_gate_wrap.py"


def _reconcile(repo: Path, *extra: str) -> dict:
    import json

    proc = subprocess.run(
        [
            str(GOV_PY),
            str(RECONCILER),
            "--root",
            str(ROOT),
            "--workspace",
            str(repo),
            "--skip-user",
            "--skip-gov",
            "--json",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # `--check` exits 1 whenever drift is reported; that is the report, not a crash.
    assert proc.returncode in ((0, 1) if "--check" in extra else (0,)), proc.stderr + proc.stdout
    return json.loads(proc.stdout)["workspace"]


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; reconciler cannot run")
def test_tracked_consumer_hook_survives_projection_byte_for_byte(tmp_path: Path) -> None:
    """A git-tracked, divergent SessionStart hook is repo-owned: reported, never overwritten."""
    repo = _workspace(tmp_path, commit_wiring=True)
    divergent = b"#!/bin/sh\n# branch-local in-flight edit\n"
    hook = repo / ".claude" / "hooks" / SESSION_HOOK
    hook.write_bytes(divergent)
    _git(repo, "add", "-f", f".claude/hooks/{SESSION_HOOK}")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "edit hook")

    result = _reconcile(repo)

    assert hook.read_bytes() == divergent, "projection overwrote a tracked consumer hook"
    assert any(item == f"tracked-hook-drift:{hook}" for item in result["drift"]), result
    assert str(hook) in result["preserved_tracked_hooks"]
    assert str(hook) not in result["wrote"]
    # --check reports the same drift without writing either.
    check = _reconcile(repo, "--check")
    assert any(item == f"tracked-hook-drift:{hook}" for item in check["drift"])
    assert hook.read_bytes() == divergent


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; reconciler cannot run")
def test_untracked_managed_hook_still_converges_to_ssot(tmp_path: Path) -> None:
    repo = _workspace(tmp_path, commit_wiring=False)
    hook = repo / ".claude" / "hooks" / SESSION_HOOK
    assert hook.read_bytes() != (HOOK_SRC / SESSION_HOOK).read_bytes()

    result = _reconcile(repo)

    assert hook.read_bytes() == (HOOK_SRC / SESSION_HOOK).read_bytes()
    assert str(hook) in result["wrote"]
    assert not any(item.startswith("tracked-hook-drift:") for item in result["drift"])


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; reconciler cannot run")
def test_explicit_migration_switch_resyncs_a_tracked_hook(tmp_path: Path) -> None:
    repo = _workspace(tmp_path, commit_wiring=True)
    hook = repo / ".claude" / "hooks" / SESSION_HOOK
    result = _reconcile(repo, "--overwrite-tracked-hooks")
    assert hook.read_bytes() == (HOOK_SRC / SESSION_HOOK).read_bytes()
    assert str(hook) in result["wrote"]


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; reconciler cannot run")
def test_untracked_retired_projection_is_pruned(tmp_path: Path) -> None:
    """A previously managed merge_gate_wrap.py left behind untracked is removed."""
    repo = _workspace(tmp_path, commit_wiring=False)
    orphan = repo / ".claude" / "hooks" / RETIRED_HOOK
    orphan.write_text("# stale fail-open projection\n", encoding="utf-8")

    check = _reconcile(repo, "--check")
    assert f"retired-hook-present:{orphan}" in check["drift"]
    assert orphan.is_file(), "--check must not delete"

    result = _reconcile(repo)
    assert not orphan.exists()
    assert str(orphan) in result["removed"]
    # What remains under .claude/ is exactly the current managed set; the
    # exclusion of that set from `git status` is the installer's job (above).
    remaining = sorted(q.name for q in (repo / ".claude" / "hooks").iterdir())
    assert remaining == [SESSION_HOOK]


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; reconciler cannot run")
def test_tracked_file_at_a_retired_path_is_preserved_and_reported(tmp_path: Path) -> None:
    repo = _workspace(tmp_path, commit_wiring=True)
    owned = repo / ".claude" / "hooks" / RETIRED_HOOK
    body = "# the repository's own file at the retired name\n"
    owned.write_text(body, encoding="utf-8")
    _git(repo, "add", "-f", f".claude/hooks/{RETIRED_HOOK}")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "own it")

    result = _reconcile(repo)

    assert owned.read_text(encoding="utf-8") == body
    assert f"retired-hook-tracked:{owned}" in result["drift"]
    assert result["removed"] == []
