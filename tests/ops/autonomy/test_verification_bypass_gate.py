"""Conformance suite for the commit-verification plane.

The point of these tests is not that the module has functions. It is that the
rule an agent is *told* and the rule that is *enforced* are the same object:
every form in the declaration is proven to deny, the briefing is proven to carry
the declaration's own lines, and the tracked tree is proven to contain no
command that the gate would refuse.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from verification_bypass_gate import (  # noqa: E402
    CONTRACT_PATH,
    ContractError,
    briefing_lines,
    command_bypasses_verification,
    load_contract,
    verification_status,
)

CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
HOOK_FILE = ".git/hooks/pre-commit"

#: One command per declared form id. Parametrised from the declaration itself,
#: so adding a form without a proof here fails `test_every_form_is_exercised`.
DENIED: dict[str, str] = {
    "git-commit-no-verify": 'git commit --no-verify -m "x"',
    "git-push-no-verify": "git push --no-verify origin HEAD",
    "git-hookspath-override": 'git -c core.hooksPath=/dev/null commit -m "x"',
    "git-config-hookspath": "git config core.hooksPath /dev/null",
    "hook-suppressing-env": 'SKIP=ruff git commit -m "x"',
    "pre-commit-uninstall": "pre-commit uninstall",
    "hook-file-mutation": f"rm -f {HOOK_FILE}",
}

ALLOWED = [
    'git commit -m "ordinary commit"',
    "git commit --amend --no-edit",
    "git push origin HEAD",
    "git push -n origin HEAD",  # -n is --dry-run on push, read-only
    'git commit -m "-n"',  # the message is "-n", not a bypass
    'git commit -F msg.txt -m "x"',
    "git status --porcelain",
    "SKIP=ruff pre-commit run --all-files",  # how run_pr_precommit.sh narrows the gate
    f"cat {HOOK_FILE}",
    "ls .git/hooks",
    "echo 'git commit --no-verify'",  # data, not a command
]


@pytest.mark.parametrize("form_id,command", sorted(DENIED.items()))
def test_declared_form_is_denied(form_id: str, command: str) -> None:
    reason = command_bypasses_verification(command, env={})
    assert reason, f"form {form_id} declared but not enforced: {command!r}"
    assert form_id in reason or "could not be evaluated" not in reason


def test_every_form_is_exercised() -> None:
    """A form added to the declaration with no proof here is a silent gap."""
    declared = {form["id"] for form in CONTRACT["forms"]}
    assert declared == set(DENIED), f"unproven forms: {declared ^ set(DENIED)}"


@pytest.mark.parametrize("command", ALLOWED)
def test_ordinary_work_is_untouched(command: str) -> None:
    assert command_bypasses_verification(command, env={}) is None, command


def test_bypass_hidden_in_a_wrapper_is_caught() -> None:
    assert command_bypasses_verification('bash -c "git commit --no-verify -m x"', env={})


def test_bypass_in_a_later_segment_is_caught() -> None:
    assert command_bypasses_verification("git add -A && git commit --no-verify -m x", env={})


def test_heredoc_body_is_data_not_command() -> None:
    command = "cat > note.md <<'EOF'\ngit commit --no-verify\nEOF"
    assert command_bypasses_verification(command, env={}) is None


def test_breakglass_needs_a_real_reason() -> None:
    command = 'git commit --no-verify -m "x"'
    env_name = CONTRACT["breakglass"]["env"]
    assert command_bypasses_verification(command, env={env_name: "1"})
    assert command_bypasses_verification(command, env={env_name: ""})
    assert command_bypasses_verification(command, env={env_name: "yes"}), (
        "a bare affirmative is not a stated reason"
    )
    assert (
        command_bypasses_verification(
            command, env={env_name: "operator ib: hook shim broken by upstream, tracked in #412"}
        )
        is None
    )


def test_unreadable_declaration_fails_closed_over_governed_commands(tmp_path, monkeypatch) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("verification_bypass_gate.CONTRACT_PATH", broken)
    load_contract.cache_clear()
    try:
        assert command_bypasses_verification('git commit -m "x"', env={})
        assert command_bypasses_verification("ls -la", env={}) is None
    finally:
        load_contract.cache_clear()


def test_contract_shape_is_validated() -> None:
    load_contract.cache_clear()
    try:
        assert load_contract()["contract_id"]
    finally:
        load_contract.cache_clear()
    with pytest.raises(ContractError):
        load_contract(str(ROOT / "ops" / "config" / "does-not-exist.json"))


def test_briefing_lines_are_non_empty() -> None:
    lines = briefing_lines()
    assert lines and all(line.strip() for line in lines)


def test_status_never_prescribes_installing_a_commit_hook() -> None:
    """The correction that matters most.

    A governed L9 workspace has NO commit hook by design: a raw hook runs the
    catalog without run_pr_precommit.sh's surface-aware SKIP list, so
    symlinks-check rejects every commit on a non-cursor surface.
    `pre-commit install` is forbidden (validate_claude_env.py asserts it, and
    run_pr_precommit.sh says so in as many words). An earlier version of this
    reporter told the agent to run it — advice that would have broken every
    commit on this surface. No status output may prescribe it again.
    """
    for candidate in (ROOT, ROOT / "does-not-exist"):
        text = json.dumps(verification_status(candidate)).lower()
        index = text.find("pre-commit install")
        while index != -1:
            # Every mention must be negated. Checking only for the substring
            # would flag the prohibition itself, so the lead-in is what decides.
            lead = text[max(0, index - 48) : index]
            assert any(marker in lead for marker in ("not ", "never", "forbid", "n't")), (
                f"unnegated 'pre-commit install' in status for {candidate}: ...{lead}"
            )
            index = text.find("pre-commit install", index + 1)


def test_governed_workspace_reports_absent_hook_as_by_design() -> None:
    """`armed: false` here is correct, not a deficiency to be repaired."""
    status = verification_status(ROOT)
    assert status["armed"] is False
    assert status["by_design"] is True
    assert status["model"] == "governed_gate"
    assert "make pr-check" in status["reason"]


def test_status_reports_an_armed_checkout(tmp_path) -> None:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    shim = repo / ".git" / "hooks" / "pre-commit"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    shim.chmod(0o755)
    assert verification_status(repo)["armed"] is True


def test_status_on_a_non_repository_is_not_a_crash(tmp_path) -> None:
    assert verification_status(tmp_path)["armed"] is False


def test_contract_does_not_teach_a_commit_time_only_model() -> None:
    """The remedy must name the gate this repo actually runs."""
    blob = json.dumps(CONTRACT)
    assert "make pr-check" in blob
    assert "run `pre-commit install`" not in blob


@pytest.mark.parametrize(
    "command",
    [
        'GIT_CONFIG_GLOBAL=/dev/null git commit -m "x"',
        "GIT_CONFIG_SYSTEM=/dev/null git push origin HEAD",
    ],
)
def test_config_suppressing_env_is_denied(command: str) -> None:
    """Neutralising the config that carries core.hooksPath names no bypass."""
    assert command_bypasses_verification(command, env={})


def test_config_env_on_a_read_only_command_is_untouched() -> None:
    assert command_bypasses_verification("GIT_CONFIG_GLOBAL=/dev/null git status", env={}) is None
