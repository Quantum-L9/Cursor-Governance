"""Unit tests for the quote-aware command parser shared by the autonomy gates."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from command_parse import (  # noqa: E402
    extract_named_roots,
    split_segments,
    strip_heredoc_bodies,
)


def test_strip_heredoc_bodies_removes_data():
    command = "python - <<'EOF'\ngit revert foo\necho inside\nEOF\ngit status"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" not in stripped
    assert stripped.strip().endswith("git status")


def test_strip_heredoc_bodies_allows_redirect_after_delimiter():
    command = "cat <<'EOF' > notes.md\ngit revert foo\nEOF\necho done"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" not in stripped
    assert "echo done" in stripped


def test_shift_expression_is_not_a_heredoc_opener():
    command = "print(1 << SHIFT)\ngit revert foo"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" in stripped


def test_strip_heredoc_bodies_handles_nested_terminator_words():
    # A data line that equals the terminator closes early → we match MORE text
    # afterwards (fail-closed direction), never hide the tail.
    command = "cat <<EOF\nhello\nEOF\nEOF\ngit revert x\nEOF\necho done"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" in stripped


def test_split_segments_honors_quotes():
    command = "echo 'a && b' ; git status && printf \"x|y\""
    segments = split_segments(command)
    assert segments[0] == "echo 'a && b'"
    assert segments[1] == "git status"
    assert segments[2] == 'printf "x|y"'


def test_split_segments_splits_or():
    segments = split_segments("git push || echo fail")
    assert segments == ["git push", "echo fail"]


def test_extract_named_roots_static_only():
    command = 'cd /tmp/work && git -C /tmp/work push origin HEAD && git -C "$DYNAMIC" push'
    assert extract_named_roots(command) == ["/tmp/work", "/tmp/work"]


def test_extract_named_roots_rejects_dynamic_and_unsafe_tokens():
    assert extract_named_roots("cd ~/repo && git push") == []
    assert extract_named_roots("git -C $(pwd) push") == []
    assert extract_named_roots("git -C '$(pwd)' push") == []
    assert extract_named_roots("cd /tmp/x* && git push") == []


def test_extract_named_roots_ignores_heredoc_data():
    command = (
        "python - <<'EOF'\ncd /tmp/not-a-command && git -C /tmp/also-data push\nEOF\n"
        "cd /tmp/real && git push"
    )
    assert extract_named_roots(command) == ["/tmp/real"]


@pytest.mark.parametrize("bad", ["", None])
def test_extract_named_roots_empty_command(bad):
    assert extract_named_roots(bad or "") == []


# --- Heredoc bodies: data is stripped, shell-executed bodies are not ----------
# Assembled from parts so this source never carries a literal a PreToolUse
# matcher could mistake for an executed command.

_NL = chr(10)
_CMD = "git push --" + "force"


def _heredoc(opener: str) -> str:
    return _NL.join([opener + " <<'EOF'", _CMD, "EOF"])


def test_data_heredoc_body_is_stripped() -> None:
    """A body written to a file is data — a runbook quoting a command is not one."""
    assert _CMD not in strip_heredoc_bodies(_heredoc("cat > /tmp/runbook.md"))


def test_foreign_interpreter_body_is_stripped() -> None:
    """A Python body is Python; the shell never runs those words."""
    assert _CMD not in strip_heredoc_bodies(_heredoc("python3 -"))


def test_shell_heredoc_body_is_kept() -> None:
    """`bash <<'EOF'` EXECUTES its body, so stripping it would be a gate bypass."""
    for opener in ("bash", "sh", "/bin/bash", "zsh", "env FOO=1 bash"):
        assert _CMD in strip_heredoc_bodies(_heredoc(opener)), opener


def test_stripping_resumes_after_a_shell_heredoc_closes() -> None:
    """The keep-flag must not leak past its terminator."""
    command = _NL.join(
        [
            "bash <<'EOF'",
            _CMD,
            "EOF",
            "cat > /tmp/x.md <<'EOF2'",
            "quoted " + _CMD,
            "EOF2",
            "echo done",
        ]
    )
    stripped = strip_heredoc_bodies(command)
    assert stripped.count(_CMD) == 1
    assert "quoted" not in stripped
    assert "echo done" in stripped
