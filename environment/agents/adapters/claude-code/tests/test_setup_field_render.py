"""The Setup script field text is rendered deterministically and fits the field.

The field on claude.ai/code takes at most 100 lines of at most 200 bytes. A
hand-condensed paste drifted from the stub (2026-11-20: the stored field was a
condensed 2026-11-20.2 while the repository stub was 2026-11-20.3), so the field
text is rendered from the stub, checked in beside SETUP_SCRIPT.md, and is the only
thing a human pastes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ADAPTER = Path(__file__).resolve().parents[1]
REPO = ADAPTER.parents[3]
sys.path.insert(0, str(ADAPTER))

import verify_account_env as vae  # noqa: E402

FIELD = REPO / vae.SETUP_FIELD_REL


def _commands(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and not line.startswith("#!")
    ]


def test_render_strips_only_comments_and_blank_lines() -> None:
    stub = (
        "#!/usr/bin/env bash\n# L9-PASTE-BEGIN marker\n\nset -uo pipefail\n"
        "  # indented comment\nfoo() { echo 'a # not a comment'; }  # trailing kept\n"
        "\n   \nexit 0\n# L9-PASTE-END\n"
    )
    out = vae.render_setup_field(stub)
    assert out == (
        "#!/usr/bin/env bash\nset -uo pipefail\n"
        "foo() { echo 'a # not a comment'; }  # trailing kept\nexit 0\n"
    )
    assert _commands(out) == _commands(stub)
    assert vae.render_setup_field(stub) == out  # deterministic


@pytest.mark.parametrize(
    ("stub", "problem"),
    [
        ("#!/usr/bin/env bash\n" + "true\n" * 101, r"102 lines > 100"),
        ("#!/usr/bin/env bash\necho " + "x" * 200 + "\n", r"lines over 200 bytes: \[2\]"),
        ("#!/usr/bin/env bash\necho `date`\n", "backtick"),
        ("#!/usr/bin/env bash\necho DEGRADED\n", "DEGRADED"),
        ("#!/usr/bin/env bash\nl9-materialize-governance\n", "materialize"),
        ("#!/usr/bin/env bash\nl9_install_child_bootstrap\n", "l9_install_child_bootstrap"),
        ("#!/usr/bin/env bash\ncat <<EOF\n# kept\nEOF\n", "heredoc"),
    ],
)
def test_render_fails_closed(stub: str, problem: str) -> None:
    with pytest.raises(vae.SetupFieldError, match=problem):
        vae.render_setup_field(stub)


def test_checked_in_field_equals_a_fresh_render() -> None:
    assert FIELD.read_text(encoding="utf-8") == vae.render_setup_field(), (
        f"{vae.SETUP_FIELD_REL} is stale: run verify_account_env.py --emit-fields"
    )


def test_checked_in_field_fits_the_account_field() -> None:
    text = FIELD.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= vae.SETUP_FIELD_MAX_LINES
    assert all(len(line.encode("utf-8")) <= vae.SETUP_FIELD_MAX_LINE_BYTES for line in lines)
    assert "`" not in text
    assert lines[0] == "#!/usr/bin/env bash"


def test_checked_in_field_carries_no_second_bootstrap_path() -> None:
    text = FIELD.read_text(encoding="utf-8")
    for word in ("DEGRADED", "materialize", "child-only", "l9_install_child_bootstrap"):
        assert word.lower() not in text.lower(), word


def test_checked_in_field_keeps_every_stub_command() -> None:
    text = FIELD.read_text(encoding="utf-8")
    assert _commands(text) == _commands(vae.STUB.read_text(encoding="utf-8"))
    assert f'L9_STUB_REVISION="{vae.stub_revision_expected()}"' in text


def test_paste_docs_name_the_rendered_file_as_the_only_paste() -> None:
    setup = (REPO / "docs" / "account-fields" / "SETUP_SCRIPT.md").read_text(encoding="utf-8")
    index = (REPO / "docs" / "ACCOUNT_FIELDS.md").read_text(encoding="utf-8")
    assert "Paste exactly one thing: [`SETUP_FIELD.txt`](SETUP_FIELD.txt)" in setup
    assert "docs/account-fields/SETUP_FIELD.txt` — the only thing to paste" in index


# --- The 2026-11-20.4 move: every stub step now runs from web/setup.sh ---------

#: The last stub revision that ran every step itself, kept verbatim as evidence.
PRE_MOVE_STUB = ADAPTER / "tests" / "fixtures" / "setup.bootstrap.2026-11-20.3.sh"
STEPS = ADAPTER / "web" / "setup.bootstrap_steps.sh"
SETUP = ADAPTER / "web" / "setup.sh"


def _cmd_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _body(lines: list[str], header: str) -> list[str]:
    """The lines of shell function `header` up to its closing lone brace."""
    start = lines.index(header) + 1
    return lines[start : lines.index("}", start)]


def test_every_moved_stub_step_runs_from_setup_in_the_same_order() -> None:
    """Old stub == new stub + moved steps, line for line, in the original order.

    The reconstruction interleaves the new stub with the two hook bodies at the
    points where the old stub ran them: the prelude right after GOV_DIR is pinned,
    the epilogue right after the hand-off returns. The only lines allowed to
    differ are the revision bump and the scaffolding the move needs (the function
    headers, the prelude re-pinning GOV_DIR/GOV_BRANCH it used to inherit, the
    epilogue receiving SETUP_RC as its argument, and the stub's final exit).
    """
    old = _cmd_lines(PRE_MOVE_STUB)
    stub = _cmd_lines(vae.STUB)
    steps = _cmd_lines(STEPS)
    prelude = _body(steps, "l9_bootstrap_prelude() {")
    epilogue = _body(steps, "l9_bootstrap_epilogue() {")
    assert prelude[:2] == [
        'GOV_DIR="$HOME/.cursor-governance"',
        'GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"',
    ]
    assert epilogue[0] == 'SETUP_RC="$1"'
    assert stub[-1] == 'exit "$SETUP_RC"'

    pin = stub.index('GOV_DIR="$HOME/.cursor-governance"')
    handoff = stub.index("SETUP_RC=$?")
    rebuilt = stub[: pin + 1] + prelude[2:] + stub[pin + 1 : handoff + 1] + epilogue[1:]
    rebuilt = [line for line in rebuilt if line != "export L9_STUB_REVISION"]
    revision = 'L9_STUB_REVISION="2026-11-20.4"'
    rebuilt[rebuilt.index(revision)] = 'L9_STUB_REVISION="2026-11-20.3"'
    assert rebuilt == old
    # The helpers the moved steps call print exactly what the stub's did.
    assert steps[:2] == old[old.index('L9_STUB_REVISION="2026-11-20.3"') + 1 :][:2]


def test_setup_runs_the_prelude_first_and_the_epilogue_on_exit() -> None:
    text = SETUP.read_text(encoding="utf-8")
    hook = text.index(
        'if [ "${L9_GOVERNANCE_BOOTSTRAPPED:-}" = "1" ]; then\n  _L9_BOOTSTRAP_STEPS='
    )
    assert hook < text.index("if ! have gh; then")  # before setup.sh's own first step
    block = text[hook : text.index("\nfi\n", hook)]
    assert block.index("l9_bootstrap_prelude") < block.index(
        "trap 'l9_bootstrap_epilogue \"$?\"' EXIT"
    )


def _run_steps(tmp_path: Path, exit_code: int) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / "claude.env"
    env_file.write_text("")
    script = (
        "set -uo pipefail\n"
        f". {STEPS}\n"
        "l9_bootstrap_prelude\n"
        "trap 'l9_bootstrap_epilogue \"$?\"' EXIT\n"
        'printf "VARS:%s|%s|%s|%s|%s\\n" "${SONAR_TOKEN-unset}" "${AWS_ACCESS_KEY_ID-unset}" '
        '"${L9_MEMORY_HTTP_URL-unset}" "$L9_GOVERNANCE_SURFACE" "$L9_GOVERNANCE_DIR"\n'
        f"exit {exit_code}\n"
    )
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "CLAUDE_ENV_FILE": str(env_file),
        "L9_STUB_REVISION": "2026-11-20.4",
        "SONAR_TOKEN": "leaked",
        "AWS_ACCESS_KEY_ID": "proxy-injected",
        "L9_MEMORY_HTTP_URL": "http://retired",
        "L9_GOVERNANCE_SURFACE": "claude-code-web",
        "L9_GOVERNANCE_DIR": "$HOME/.cursor-governance",
    }
    return subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("exit_code", [0, 3])
def test_moved_steps_have_the_stub_environment_effects(tmp_path: Path, exit_code: int) -> None:
    result = _run_steps(tmp_path, exit_code)
    assert result.returncode == exit_code, result.stderr
    gov = f"{tmp_path}/.cursor-governance"
    vars_line = next(line for line in result.stdout.splitlines() if line.startswith("VARS:"))
    assert vars_line == f"VARS:unset|proxy-injected|unset|claude-code|{gov}"
    assert "AWS_ACCESS_KEY_ID holds the platform proxy sentinel" in result.stdout
    assert "UNEXPANDED $HOME" in result.stderr
    durable = (tmp_path / ".l9" / "cloud-session.env").read_text(encoding="utf-8")
    assert "export L9_STUB_REVISION=2026-11-20.4" in durable
    assert f"export L9_GOVERNANCE_DIR={gov}" in durable
    assert "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN" in durable
    assert (tmp_path / "claude.env").read_text(encoding="utf-8") == durable
    if exit_code:
        assert "cloud bootstrap FAILED — web/setup.sh exited 3" in result.stderr
        assert "cloud bootstrap complete" not in result.stdout
    else:
        assert "cloud bootstrap complete — governance at " in result.stdout
