"""A whole-catalog pytest run belongs to CI, not to a chat turn.

`make pr-check` is the designed local gate: precommit once, plus pytest targets
selected from the changed set. A hand-picked directory list is how a CI-only
failure gets missed — the swallowed-failure ratchet lives in `ops/scripts/tests/`
while the neighbouring `tests/ops/scripts/` looks like the obvious place, and a
ten-minute repo-wide run is the wrong way to close that gap.

Only unscoped runs are denied. Targeted runs are the fast half of the loop and
must stay allowed, so the false-positive cases below matter as much as the
denials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from local_execution_gate import (  # noqa: E402
    FULL_PYTEST_OVERRIDE_ENV,
    command_runs_unscoped_pytest,
)

UNSCOPED = [
    # The exact command a ten-minute run took in-session before it was stopped.
    (
        'TESTING=true PYTHONPATH="$PWD" .venv/bin/python -m pytest . '
        + "--ignore=environment/program-execution/peer_execution/autonomy "
        + "-n auto -q --timeout=300"
    ),
    "pytest",
    "python -m pytest",
    "python3 -m pytest",
    ".venv/bin/python -m pytest .",
    "pytest ./",
    "cd /repo && pytest . -q",
    "make test",
    "make pr-full",
    "PR_BASE=origin/main make -C /gov test",
]

SCOPED_OR_UNRELATED = [
    ".venv/bin/python -m pytest ops/scripts/tests/test_bootstrap_invariants.py -q",
    (
        "PYTHONPATH=environment/program-execution .venv/bin/python -m pytest "
        + "environment/program-execution/tests/hardening -q"
    ),
    ".venv/bin/python -m pytest tests/ops/scripts/ -q -p no:cacheprovider",
    ".venv/bin/python -m pytest a.py b.py -n auto -q",
    "make pr-check",
    "PR_REMEDIATE=0 make pr",
    "git status --porcelain",
    "ruff check ops/scripts/select_pr_pytest_paths.py",
    # pytest's own tmp_path lives under /tmp/pytest-of-<user>/pytest-<n>/. Naming
    # one of those directories in an unrelated command is not an invocation.
    "cd /tmp/pytest-of-runner/pytest-0/test_named_root0/stacked && make pr",
    "make -C /tmp/pytest-of-runner/pytest-0/test_named_root0/stacked pr",
    "ls /home/runner/pytest-cache",
]

WRAPPED_UNSCOPED = [
    "uv run pytest",
    "uv run --frozen pytest .",
    "env pytest",
    "time .venv/bin/python -m pytest .",
]


@pytest.mark.parametrize("command", UNSCOPED)
def test_unscoped_catalog_run_is_denied(command: str) -> None:
    reason = command_runs_unscoped_pytest(command)
    assert reason, f"should have been denied: {command}"


@pytest.mark.parametrize("command", SCOPED_OR_UNRELATED)
def test_targeted_and_unrelated_commands_are_allowed(command: str) -> None:
    reason = command_runs_unscoped_pytest(command)
    assert reason is None, f"false positive on: {command} -> {reason}"


@pytest.mark.parametrize("command", WRAPPED_UNSCOPED)
def test_wrappers_do_not_hide_a_catalog_run(command: str) -> None:
    """`uv run` / `env` / `time` pass the command through — so does the gate."""

    assert command_runs_unscoped_pytest(command), f"should have been denied: {command}"


def test_options_are_not_mistaken_for_targets() -> None:
    """`-n auto` and `-p no:cacheprovider` consume their value, not a target.

    Without this, `pytest -n auto` would read `auto` as a positional target and
    the run would look scoped when it collects the entire tree.
    """

    assert command_runs_unscoped_pytest("pytest -n auto -q") is not None
    assert command_runs_unscoped_pytest("pytest -p no:cacheprovider") is not None
    assert command_runs_unscoped_pytest("pytest -k something -q") is not None
    assert command_runs_unscoped_pytest("pytest -n auto tests/x.py") is None


def test_heredoc_body_is_data_not_a_command() -> None:
    """Prose that mentions the command must not trip the gate."""

    command = "cat <<'EOF' > notes.md\nWe should not run pytest . here\nEOF"
    assert command_runs_unscoped_pytest(command) is None


def test_deny_reason_names_the_replacement_command() -> None:
    """A deny that does not say what to run instead just costs another turn."""

    reason = command_runs_unscoped_pytest("pytest .")
    assert reason is not None
    from local_execution_gate import _full_pytest_deny_reason

    text = _full_pytest_deny_reason(reason)
    assert "make pr-check" in text
    assert FULL_PYTEST_OVERRIDE_ENV in text
