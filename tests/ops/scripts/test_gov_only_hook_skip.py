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

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"

GOV_ONLY_HOOK = "gh-package-deps-preflight"

#: Locality is declared once, per hook, in the contract the runner reads. The
#: tests derive from the same declaration, so a hook added to the catalog with
#: a governance-tree entry is covered here without anyone remembering to list
#: it (`cursor-skill-projection` and `no-hardcoded-paths` were missed exactly
#: that way while this file hardcoded three ids).
CONTRACT = json.loads(
    (ROOT / "ops" / "config" / "precommit-hook-contract.json").read_text(encoding="utf-8")
)["hooks"]


def _corpus_skip() -> set[str]:
    script = (SCRIPTS / "run_pr_precommit.sh").read_text(encoding="utf-8")
    line = next(x for x in script.splitlines() if x.startswith('_CORPUS_SKIP="'))
    return set(line.split('"', 2)[1].split(","))


def _configured_entries() -> dict[str, str]:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    return {
        str(hook["id"]): str(hook.get("entry", ""))
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
    }


def _governance_tree_path(entry: str) -> str | None:
    return next((tok for tok in entry.split() if "/" in tok and (ROOT / tok).is_file()), None)


GOVERNANCE_LOCAL = sorted(h for h, e in CONTRACT.items() if e.get("locality") == "governance")

#: hook id -> the governance-tree script its `entry:` resolves against, for the
#: governance-local hooks the corpus skip does not already remove. `max-velocity`
#: is the harder case: no `files:` guard and `pass_filenames: false`, so it fires
#: on every consumer `make pr` rather than only on a matching path.
GOV_ONLY_HOOKS = {
    hook: path
    for hook in GOVERNANCE_LOCAL
    if hook not in _corpus_skip()
    and (path := _governance_tree_path(_configured_entries().get(hook, "")))
}

#: A hook whose entry is NOT a governance-tree path. It must keep running in a
#: consumer, otherwise the skip has quietly become "gate nothing".
CONSUMER_APPLICABLE_HOOK = "check-merge-conflict"


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


def _precommit_observer(tmp_path: Path) -> Path:
    """Observe the runner invocation without overriding its locked PATH order."""
    observer = tmp_path / "precommit-observer.sh"
    observer.write_text(
        'pre-commit() { echo "SKIP=${SKIP:-}"; echo "PATH=$PATH"; }\n',
        encoding="utf-8",
    )
    return observer


def _effective_skips(tmp_path: Path, workspace: Path, stage: str = "readers") -> list[str]:
    changed = tmp_path / "changed.txt"
    changed.write_text("package.json\n", encoding="utf-8")
    observer = _precommit_observer(tmp_path)
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
            "PR_PRECOMMIT_STAGE": stage,
            "PR_PRECOMMIT_DEFER_DIRTY_STOP": "1",
            "BASH_ENV": str(observer),
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


@pytest.mark.parametrize("hook", GOVERNANCE_LOCAL)
def test_hook_is_skipped_in_a_consumer_workspace(tmp_path: Path, hook: str) -> None:
    """The regression. Without this the hook runs and dies on a missing file."""
    assert hook in _effective_skips(tmp_path, _consumer_repo(tmp_path))


@pytest.mark.parametrize("hook", sorted(GOV_ONLY_HOOKS))
def test_hook_still_runs_in_the_governance_workspace(tmp_path: Path, hook: str) -> None:
    """A skip everywhere would be a deleted check. Here the entry resolves."""
    assert hook not in _effective_skips(tmp_path, ROOT)


def test_governance_hooks_resolve_python3_to_locked_venv(tmp_path: Path) -> None:
    """Cursor-Governance#567: host python3 must not win over `.venv/bin`."""
    locked_python3 = ROOT / ".venv" / "bin" / "python3"
    assert locked_python3.is_file(), (
        f"locked interpreter missing at {locked_python3} (run: make venv)"
    )
    changed = tmp_path / "changed.txt"
    changed.write_text("package.json\n", encoding="utf-8")
    observer = _precommit_observer(tmp_path)
    proc = subprocess.run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(ROOT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "WS": str(ROOT),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(changed),
            "PR_PRECOMMIT_STAGE": "readers",
            "BASH_ENV": str(observer),
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    path_lines = [line for line in proc.stdout.splitlines() if line.startswith("PATH=")]
    assert path_lines, (
        "stub pre-commit did not emit PATH=; stdout/stderr:\n" + proc.stdout + proc.stderr
    )
    first = path_lines[0].removeprefix("PATH=").split(":", 1)[0]
    assert first == str(ROOT / ".venv" / "bin")


def test_a_consumer_applicable_hook_is_not_skipped(tmp_path: Path) -> None:
    """The skip is narrow. Widening it into "gate nothing" fails here.

    `check-merge-conflict` has no governance-tree entry, so it can and must
    still run against a consumer workspace.
    """
    assert CONSUMER_APPLICABLE_HOOK not in _effective_skips(tmp_path, _consumer_repo(tmp_path))


@pytest.mark.parametrize(("hook", "entry"), sorted(GOV_ONLY_HOOKS.items()))
def test_the_hook_entry_is_a_governance_tree_path(hook: str, entry: str) -> None:
    """Why the skip is needed, asserted rather than asserted-in-a-comment.

    If an entry ever becomes absolute or otherwise workspace-independent, the
    skip is dead weight for that hook and this test says so by failing.
    """
    assert entry in _configured_entries()[hook]
    assert (ROOT / entry).is_file()


def test_every_hook_declares_its_locality() -> None:
    assert set(CONTRACT) == set(_configured_entries())
    assert {e.get("locality") for e in CONTRACT.values()} <= {"governance", "any"}
    assert all("locality" in e for e in CONTRACT.values())


def test_newly_found_governance_local_hooks_are_declared() -> None:
    """The two hooks the hand-kept list missed are governance-local."""
    for hook in ("cursor-skill-projection", "no-hardcoded-paths"):
        assert CONTRACT[hook]["locality"] == "governance"
        assert hook in GOV_ONLY_HOOKS


def test_each_hook_runs_in_exactly_one_pass(tmp_path: Path) -> None:
    """The runner promises each hook id runs at most once per invocation.

    A hook in neither the reader nor the writer list was skipped by neither
    pass, so `cursor-skill-projection`, `max-velocity` and `adr-identity` ran
    twice in the governance workspace. Pass membership now comes from each
    hook's declared mode; every non-corpus hook runs in exactly one pass.
    """
    (tmp_path / "r").mkdir()
    (tmp_path / "w").mkdir()
    readers = set(_effective_skips(tmp_path / "r", ROOT, "readers"))
    writers = set(_effective_skips(tmp_path / "w", ROOT, "writers"))
    corpus = _corpus_skip()
    for hook in _configured_entries():
        passes = int(hook not in readers) + int(hook not in writers)
        assert passes == (0 if hook in corpus else 1), (hook, passes)


def test_max_velocity_has_no_files_guard() -> None:
    """`max-velocity` fires on every consumer publish, which is why it is listed.

    A `files:` guard would not make the skip unnecessary (the entry path still
    could not resolve), but its absence is why this one broke the documented
    consumer path on *any* nonempty change rather than only a matching one.
    """
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    block = config.split("- id: max-velocity", 1)[1].split("- id: ", 1)[0]
    assert "pass_filenames: false" in block
    assert "files:" not in block
