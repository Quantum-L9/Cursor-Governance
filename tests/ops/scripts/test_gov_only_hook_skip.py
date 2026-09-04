"""A governance-local hook must be skipped where its entry cannot resolve.

`gh-package-deps-preflight` is declared in the governance `.pre-commit-config.yaml`
with `entry: python3 ops/scripts/validate_gh_package_deps.py` — a path relative
to whichever tree pre-commit runs in. `run_pr_precommit.sh` deliberately names
the GOVERNANCE config as its authority while running with the CONSUMER workspace
as cwd, so in a consumer that entry resolves to
`<consumer>/ops/scripts/validate_gh_package_deps.py`, which does not exist:

    can't open file '/home/user/seo-bot/ops/scripts/validate_gh_package_deps.py'

The hook dies on a missing file rather than on anything it checked, and `make pr`
fails for a consumer repository on a finding that was never made. Observed in
Quantum-L9/SEO-Bot on a `package.json` edit that added test-group scripts, which
is all it takes to trip the hook's `files:` guard.

The guard is not a defence. It decides WHETHER the hook runs; the entry path
decides whether it CAN. `_GOV_ONLY_SKIP` is the existing mechanism for exactly
this class — its comment already recorded the identical signature for
`validate_commit_verification_contract.py` — and the list was empty.

These tests assert the EFFECT (the hook is absent from the SKIP pre-commit
actually receives in a consumer, present in governance), not the text of a
variable, so a refactor that keeps the name and loses the behavior still fails.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"

GOV_ONLY_HOOK = "gh-package-deps-preflight"


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _consumer_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / "package.json").write_text('{"name": "consumer"}\n', encoding="utf-8")
    git_in(repo, "add", "package.json")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    return repo


def _stub_precommit(tmp_path: Path) -> Path:
    """A `pre-commit` that reports the SKIP it was handed and exits clean."""
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    stub = bin_dir / "pre-commit"
    stub.write_text('#!/usr/bin/env bash\necho "SKIP=${SKIP:-}"\nexit 0\n', encoding="utf-8")
    stub.chmod(0o755)
    return bin_dir


def _effective_skips(tmp_path: Path, workspace: Path) -> list[str]:
    changed = tmp_path / "changed.txt"
    changed.write_text("package.json\n", encoding="utf-8")
    bin_dir = _stub_precommit(tmp_path)
    proc = subprocess.run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(workspace)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "WS": str(workspace),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(changed),
            "PR_PRECOMMIT_STAGE": "readers",
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        },
    )
    assert "SKIP=" in proc.stdout, proc.stdout + proc.stderr
    return [
        hook
        for line in proc.stdout.splitlines()
        if line.startswith("SKIP=")
        for hook in line.removeprefix("SKIP=").split(",")
        if hook
    ]


def test_hook_is_skipped_in_a_consumer_workspace(tmp_path: Path) -> None:
    """The regression. Without this the hook runs and dies on a missing file."""
    assert GOV_ONLY_HOOK in _effective_skips(tmp_path, _consumer_repo(tmp_path))


def test_hook_still_runs_in_the_governance_workspace(tmp_path: Path) -> None:
    """A skip everywhere would be a deleted check. Here the entry resolves."""
    assert GOV_ONLY_HOOK not in _effective_skips(tmp_path, ROOT)


def test_the_hook_entry_is_a_governance_tree_path() -> None:
    """Why the skip is needed, asserted rather than asserted-in-a-comment.

    If the entry ever becomes absolute or otherwise workspace-independent, the
    skip is dead weight and this test says so by failing.
    """
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert f"- id: {GOV_ONLY_HOOK}" in config
    assert "entry: python3 ops/scripts/validate_gh_package_deps.py" in config
    assert (ROOT / "ops" / "scripts" / "validate_gh_package_deps.py").is_file()
