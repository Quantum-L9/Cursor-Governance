"""Tests for local_execution_gate.effective_root.

Cursor's beforeShellExecution reports the project root, not the shell cwd, so a
command that cd's into a linked worktree was being judged against the wrong
checkout -- wrong branch, wrong L4 receipt. Rule 49 requires per-agent
worktrees, so that made publishing from a worktree impossible.

The resolution must not become an escape hatch: only a worktree of the same
repository may redirect the gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from l4_local import authorize_release, begin  # noqa: E402
from local_execution_gate import cursor_shell_verdict, effective_root, evaluate  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def make_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    (path / "f.txt").write_text("x", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-m", "init")
    return path


@pytest.fixture
def main_repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "main")


@pytest.fixture
def linked_worktree(main_repo: Path, tmp_path: Path) -> Path:
    wt = tmp_path / "wt"
    git(main_repo, "worktree", "add", "-b", "feat/x", str(wt))
    return wt


def test_cd_into_linked_worktree_redirects(main_repo: Path, linked_worktree: Path) -> None:
    command = f'cd "{linked_worktree}" && make pr'
    assert effective_root(command, main_repo) == linked_worktree.resolve()


def test_cd_into_unrelated_repo_does_not_redirect(main_repo: Path, tmp_path: Path) -> None:
    """A different repository must not be able to steer the gate away."""
    other = make_repo(tmp_path / "other")
    assert effective_root(f'cd "{other}" && git push', main_repo) == main_repo


def test_cd_into_non_repo_does_not_redirect(main_repo: Path, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert effective_root(f'cd "{plain}" && git push', main_repo) == main_repo


def test_no_leading_cd_keeps_root(main_repo: Path) -> None:
    assert effective_root("make pr", main_repo) == main_repo


def test_cd_later_in_command_is_ignored(main_repo: Path, linked_worktree: Path) -> None:
    """Only a leading cd sets the shell's starting directory for the command."""
    command = f'make pr && cd "{linked_worktree}"'
    assert effective_root(command, main_repo) == main_repo


def test_relative_cd_to_a_missing_directory_is_ignored(main_repo: Path) -> None:
    assert effective_root("cd subdir && git push", main_repo) == main_repo


def test_missing_directory_is_ignored(main_repo: Path, tmp_path: Path) -> None:
    assert effective_root(f'cd "{tmp_path / "nope"}" && git push', main_repo) == main_repo


def test_unquoted_and_env_expanded_paths_resolve(
    main_repo: Path, linked_worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        effective_root(f"cd {linked_worktree} && make pr", main_repo) == linked_worktree.resolve()
    )
    monkeypatch.setenv("WT", str(linked_worktree))
    assert effective_root("cd $WT && make pr", main_repo) == linked_worktree.resolve()


def test_subdirectory_of_worktree_resolves_to_its_toplevel(
    main_repo: Path, linked_worktree: Path
) -> None:
    sub = linked_worktree / "nested"
    sub.mkdir()
    assert effective_root(f'cd "{sub}" && make pr', main_repo) == linked_worktree.resolve()


# --- Container root: the reported project dir is not a repository at all -----
#
# The case above is "project root is repo A, cd into a worktree of repo A".
# A cloud session reports a *container root* holding many clones side by side
# which is itself no repository (`/home/user`). _common_dir() returns None
# there, so the same-repository comparison could never succeed and the gate
# resolved the L4 receipt under a path that cannot hold one -- making
# publication from a worktree impossible, the exact outcome this function
# exists to prevent.
#
# With no repository context at the root there is nothing to be steered away
# FROM, so a cd into a real work tree is the only signal available. This
# relaxes nothing about authorization: the receipt must still exist at the
# resolved root and bind the head SHA.


@pytest.fixture
def container_root(tmp_path: Path) -> Path:
    """A plain directory holding checkouts, like a cloud session's project dir."""
    root = tmp_path / "container"
    root.mkdir()
    return root


def test_cd_into_a_repo_redirects_when_root_is_not_a_repo(
    container_root: Path, main_repo: Path
) -> None:
    assert effective_root(f'cd "{main_repo}" && make pr', container_root) == main_repo.resolve()


def test_cd_into_a_linked_worktree_redirects_when_root_is_not_a_repo(
    container_root: Path, linked_worktree: Path
) -> None:
    """The live case: container root, worktree holding the release receipt."""
    command = f'cd "{linked_worktree}" && PR_REMEDIATE=0 make pr'
    assert effective_root(command, container_root) == linked_worktree.resolve()


def test_non_repo_root_without_a_leading_cd_is_unchanged(container_root: Path) -> None:
    assert effective_root("make pr", container_root) == container_root


def test_non_repo_root_cd_into_non_repo_is_unchanged(container_root: Path, tmp_path: Path) -> None:
    """Only a real work tree may redirect; a plain directory must not."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert effective_root(f'cd "{plain}" && make pr', container_root) == container_root


def test_repo_root_still_refuses_an_unrelated_repo(main_repo: Path, tmp_path: Path) -> None:
    """Regression guard: the same-repository rule is untouched when root IS a repo.

    The container-root branch must not become a way to reach an unrelated
    repository from a session whose project dir is a real checkout.
    """
    other = make_repo(tmp_path / "other")
    assert effective_root(f'cd "{other}" && make pr', main_repo) == main_repo


def test_make_ws_redirects_to_another_repo(main_repo: Path, tmp_path: Path) -> None:
    """Governance makefile contract: WS= is the target, even across repos."""
    other = make_repo(tmp_path / "other")
    command = f'PR_REMEDIATE=0 make -C "{main_repo}" pr WS="{other}"'
    assert effective_root(command, main_repo) == other.resolve()


def test_make_ws_env_prefix_redirects(main_repo: Path, tmp_path: Path) -> None:
    other = make_repo(tmp_path / "other")
    command = f'WS="{other}" PR_REMEDIATE=0 make pr'
    assert effective_root(command, main_repo) == other.resolve()


def test_make_directory_naming_the_root_keeps_root(main_repo: Path) -> None:
    assert effective_root(f'make -C "{main_repo}" pr', main_repo) == main_repo


def test_invalid_ws_is_ignored(main_repo: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    command = f"make pr WS={missing}"
    assert effective_root(command, main_repo) == main_repo


def test_make_ws_does_not_expand_env(
    main_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = make_repo(tmp_path / "other")
    monkeypatch.setenv("WS_TARGET", str(other))
    assert effective_root("make pr WS=$WS_TARGET", main_repo) == main_repo


def test_cd_unrelated_still_refused_when_ws_absent(main_repo: Path, tmp_path: Path) -> None:
    other = make_repo(tmp_path / "other")
    assert effective_root(f'cd "{other}" && make pr', main_repo) == main_repo


def test_evaluate_uses_ws_receipt_not_session_root(
    main_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A governance-checkout session may publish a consumer that holds the receipt."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    consumer = make_repo(tmp_path / "consumer")
    git(consumer, "checkout", "-b", "feat/ws")
    begin(consumer, contract_id="ws")
    authorize_release(consumer)
    command = f'PR_REMEDIATE=0 make -C "{main_repo}" pr WS="{consumer}"'
    assert evaluate("Bash", {"command": command}, root=main_repo) is None
    assert evaluate("Bash", {"command": "PR_REMEDIATE=0 make pr"}, root=main_repo) is not None


def test_cursor_verdict_allows_ws_when_session_root_has_no_receipt(
    main_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    consumer = make_repo(tmp_path / "consumer")
    git(consumer, "checkout", "-b", "feat/ws")
    begin(consumer, contract_id="ws")
    authorize_release(consumer)
    event = {
        "command": f'PR_REMEDIATE=0 make -C "{main_repo}" pr WS="{consumer}"',
        "cwd": str(main_repo),
        "workspace_roots": [str(main_repo)],
    }
    import json

    permission, message = cursor_shell_verdict(json.dumps(event))
    assert permission == "allow", message


# --- The Claude entry point must use this resolution too ---------------------
#
# effective_root() was wired into main_cursor_shell() only. main_claude()
# passed workspace_from_event(event) straight to evaluate(), so on the Claude
# surface the leading-cd resolution never ran at all and a worktree could never
# publish -- the whole reason this function exists, unreached for one surface.


def test_claude_entrypoint_resolves_the_leading_cd(
    monkeypatch: pytest.MonkeyPatch, main_repo: Path, linked_worktree: Path
) -> None:
    import io
    import json

    import local_execution_gate as gate

    seen: dict[str, Path] = {}

    def fake_evaluate(tool_name, tool_input, *, root=None):  # noqa: ANN001, ANN202
        seen["root"] = root
        return None

    monkeypatch.setattr(gate, "evaluate", fake_evaluate)
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: main_repo)
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": f'cd "{linked_worktree}" && PR_REMEDIATE=0 make pr'},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))

    assert gate.main_claude() == 0
    assert seen["root"] == linked_worktree.resolve()


# --- ...and so must the guardrail pre-check that answers BEFORE evaluate -----
#
# main_claude() asks _guardrail_from_payload() first, so that the git/gh
# workflow exemption cannot wave a destructive command through before any
# policy runs. Answering first is only safe while both planes answer about the
# same checkout. The pre-check resolved workspace_from_event() directly and
# skipped effective_root(), so the test above passed while the real surface
# still denied: on a cloud container the reported workspace is /home/user,
# which holds many clones and is itself no repository, so LiveProbe ran
# `git -C /home/user status --porcelain`, got exit 128, and any command whose
# classification consults the dirty set failed closed on I017 -- before the
# corrected root existed.
#
# `git checkout -b` never consults the dirty set (a new branch off HEAD
# clobbers nothing) and stayed allowed, which made the breakage look
# intermittent instead of total.


def test_guardrail_precheck_resolves_the_leading_cd(
    monkeypatch: pytest.MonkeyPatch, main_repo: Path, linked_worktree: Path
) -> None:
    import local_execution_gate as gate

    seen: dict[str, Path | None] = {}

    def fake_requires_human(command: str, *, root: Path | None = None) -> str | None:  # noqa: ARG001
        seen["root"] = root
        return None

    monkeypatch.setattr(gate, "command_requires_human", fake_requires_human)
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: main_repo)  # noqa: ARG005
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f'cd "{linked_worktree}" && git checkout other-branch'},
        }
    )

    assert gate._guardrail_from_payload(payload) is None
    assert seen["root"] == linked_worktree.resolve(), (
        "the guardrail plane must judge the checkout the command runs in, "
        "not the reported project root"
    )


def test_guardrail_precheck_survives_a_container_root_that_is_no_repository(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A non-repository workspace must not deny every dirty-set command.

    This is the cloud multi-repo shape: /home/user holds clones side by side.
    A command that cd's into a real clone is judged there; one that names no
    checkout still fails closed, because the gate genuinely cannot tell which
    repository it would touch.
    """
    import local_execution_gate as gate

    container = tmp_path / "container"
    container.mkdir()
    clone = make_repo(container / "clone")
    git(clone, "branch", "feature")
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: container)  # noqa: ARG005

    def verdict(command: str) -> str | None:
        return gate._guardrail_from_payload(
            json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        )

    assert verdict(f"cd {clone} && git checkout feature") is None
    denied = verdict("git checkout feature")
    assert denied is not None and "I017" in denied


# --- A second CLONE of the same repository ----------------------------------
#
# The same-repository test was `--git-common-dir` equality, which relates
# worktrees of one clone and nothing else. Two clones share no git directory,
# so this fleet's ordinary shape -- the SSOT at `~/.cursor-governance` plus a
# consumer checkout of the same repository elsewhere -- read as "unrelated".
# `cd ~/.cursor-governance && make pr` was therefore judged against the
# session's checkout: the wrong branch and the wrong L4 receipt, which is the
# failure this function exists to prevent, one clone further out.
#
# Clones are related by the remote they publish to. Authorization is unchanged:
# the receipt must still exist at the resolved root and bind its head SHA,
# which `test_publish_into_a_second_clone_without_a_receipt_is_denied` proves.

CANONICAL_SSH = "git@github.com:Quantum-L9/Cursor-Governance.git"
CANONICAL_HTTPS = "https://github.com/Quantum-L9/Cursor-Governance"


@pytest.fixture
def second_clone(main_repo: Path, tmp_path: Path) -> Path:
    """Another clone of `main_repo`, sharing an origin spelled differently."""
    clone = tmp_path / "clone2"
    subprocess.run(
        ["git", "clone", "--quiet", str(main_repo), str(clone)],
        check=True,
        capture_output=True,
    )
    git(clone, "config", "user.email", "t@example.com")
    git(clone, "config", "user.name", "t")
    git(main_repo, "remote", "add", "origin", CANONICAL_SSH)
    git(clone, "remote", "set-url", "origin", CANONICAL_HTTPS)
    return clone


def test_cd_into_a_second_clone_of_the_same_repository_redirects(
    main_repo: Path, second_clone: Path
) -> None:
    command = f'cd "{second_clone}" && PR_REMEDIATE=0 make pr'
    assert effective_root(command, main_repo) == second_clone.resolve()


def test_second_clone_match_survives_scp_and_https_spellings(
    main_repo: Path, second_clone: Path
) -> None:
    """One repository, four spellings; normalization must relate them all."""
    for spelling in (
        CANONICAL_SSH,
        CANONICAL_HTTPS,
        "https://github.com/Quantum-L9/Cursor-Governance.git",
        "ssh://git@github.com/Quantum-L9/Cursor-Governance.git",
    ):
        git(second_clone, "remote", "set-url", "origin", spelling)
        assert effective_root(f'cd "{second_clone}" && make pr', main_repo) == (
            second_clone.resolve()
        ), spelling


def test_cd_into_a_clone_with_a_different_origin_does_not_redirect(
    main_repo: Path, second_clone: Path
) -> None:
    """Shared history is not shared identity: a fork must not redirect."""
    git(second_clone, "remote", "set-url", "origin", "git@github.com:someone/fork.git")
    assert effective_root(f'cd "{second_clone}" && make pr', main_repo) == main_repo


def test_cd_into_a_clone_is_refused_when_the_root_has_no_origin(
    main_repo: Path, tmp_path: Path
) -> None:
    """With no identity to compare, the gate must not infer a relationship."""
    clone = tmp_path / "anon"
    subprocess.run(
        ["git", "clone", "--quiet", str(main_repo), str(clone)],
        check=True,
        capture_output=True,
    )
    assert effective_root(f'cd "{clone}" && make pr', main_repo) == main_repo


def test_relative_cd_into_a_sibling_worktree_redirects(
    main_repo: Path, linked_worktree: Path
) -> None:
    """`cd ../wt` is how an agent moves between sibling checkouts."""
    relative = Path("..") / linked_worktree.name
    assert effective_root(f"cd {relative} && make pr", main_repo) == linked_worktree.resolve()


# --- `make -C` names the tree Make will act on ------------------------------
#
# This repository's Makefile defaults `WS ?= $(CURDIR)`, so `-C <dir>` selects
# the acted-on tree exactly as `WS=` does. The resolver only read `WS=`, so
# `make -C ~/.cursor-governance pr` was judged against the session's checkout.


def test_make_directory_redirects_to_another_repo(main_repo: Path, tmp_path: Path) -> None:
    other = make_repo(tmp_path / "other")
    command = f'PR_REMEDIATE=0 make -C "{other}" pr'
    assert effective_root(command, main_repo) == other.resolve()


def test_make_directory_accepts_every_spelling(main_repo: Path, tmp_path: Path) -> None:
    other = make_repo(tmp_path / "other")
    for command in (
        f'make -C "{other}" pr',
        f"make -C{other} pr",
        f'make --directory "{other}" pr',
        f'make --directory="{other}" pr',
        f'PR_REMEDIATE=0 make -C "{other}" pr',
    ):
        assert effective_root(command, main_repo) == other.resolve(), command


def test_make_directory_expands_a_leading_tilde(
    main_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shell expands `~` before make sees it, so the gate must too."""
    home = tmp_path / "home"
    home.mkdir()
    other = make_repo(home / "gov")
    monkeypatch.setenv("HOME", str(home))
    assert effective_root("make -C ~/gov pr", main_repo) == other.resolve()


def test_make_directory_does_not_expand_env(
    main_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = make_repo(tmp_path / "other")
    monkeypatch.setenv("GOV", str(other))
    assert effective_root("make -C $GOV pr", main_repo) == main_repo


def test_make_directory_wins_over_a_leading_cd(
    main_repo: Path, linked_worktree: Path, tmp_path: Path
) -> None:
    """Make acts on `-C`, whatever the shell's cwd is."""
    other = make_repo(tmp_path / "other")
    command = f'cd "{linked_worktree}" && make -C "{other}" pr'
    assert effective_root(command, main_repo) == other.resolve()


def test_ws_still_wins_over_make_directory(main_repo: Path, tmp_path: Path) -> None:
    """Makefile precedence: `WS ?= $(CURDIR)`, so an explicit WS= overrides -C."""
    other = make_repo(tmp_path / "other")
    directed = make_repo(tmp_path / "directed")
    command = f'make -C "{directed}" pr WS="{other}"'
    assert effective_root(command, main_repo) == other.resolve()


def test_a_bare_directory_is_not_reachable_by_make_directory(
    main_repo: Path, tmp_path: Path
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert effective_root(f'make -C "{plain}" pr', main_repo) == main_repo


# --- Resolution is not authorization ----------------------------------------


def test_publish_into_a_second_clone_without_a_receipt_is_denied(
    main_repo: Path, second_clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redirecting the gate must not import the session's release receipt.

    The session checkout holds a valid L4 release; the clone the command
    actually publishes from holds none, so the publication must be denied.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    git(main_repo, "checkout", "-q", "-b", "feat/session")
    begin(main_repo, contract_id="session")
    authorize_release(main_repo)

    event = {
        "command": f'cd "{second_clone}" && PR_REMEDIATE=0 make pr',
        "cwd": str(main_repo),
        "workspace_roots": [str(main_repo)],
    }
    permission, message = cursor_shell_verdict(json.dumps(event))
    assert permission == "deny", "the clone holds no release receipt"
    assert message

    allowed, _ = cursor_shell_verdict(
        json.dumps(
            {
                "command": "PR_REMEDIATE=0 make pr",
                "cwd": str(main_repo),
                "workspace_roots": [str(main_repo)],
            }
        )
    )
    assert allowed == "allow", "the authorized session checkout still publishes"
