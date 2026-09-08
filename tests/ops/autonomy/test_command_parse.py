"""Unit tests for the quote-aware command parser shared by the autonomy gates."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from command_parse import (  # noqa: E402
    extract_named_roots,
    make_workspace_raw,
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


def test_make_workspace_raw_leading_and_trailing():
    assert make_workspace_raw("WS=/tmp/wb make pr") == "/tmp/wb"
    assert make_workspace_raw("make -C /tmp/gov pr WS=/tmp/wb") == "/tmp/wb"
    assert make_workspace_raw("PR_REMEDIATE=0 make pr") is None
    assert make_workspace_raw("git -C /tmp/wb push") is None


def test_extract_named_roots_make_ws_beats_make_dash_c():
    """Governance makefile lives at -C; the target checkout is WS=."""
    command = "PR_REMEDIATE=0 make -C /tmp/gov pr WS=/tmp/wb"
    assert extract_named_roots(command) == ["/tmp/wb"]


def test_extract_named_roots_make_dash_c_when_ws_absent():
    assert extract_named_roots("make -C /tmp/gov pr") == ["/tmp/gov"]


def test_make_workspace_raw_quoted_path_with_spaces():
    assert make_workspace_raw('make pr WS="/tmp/Consumer Repo"') == "/tmp/Consumer Repo"
    assert make_workspace_raw('WS="/tmp/Consumer Repo" make pr') == "/tmp/Consumer Repo"


def test_extract_named_roots_quoted_ws_with_spaces():
    assert extract_named_roots('make pr WS="/tmp/Consumer Repo"') == ["/tmp/Consumer Repo"]


def test_heredoc_opener_may_be_followed_by_a_separator():
    """`cmd <<EOF && next` is ordinary Bash: the body still starts next line.

    Only redirects were accepted after the delimiter, so this form was not an
    opener at all and its body was never stripped. That leaked DATA into
    command matching: split_segments splits on `&&` wherever it appears, so
    prose in a commit message became a segment whose first word is `git`.
    """
    command = "git commit -F - <<'MSG' && git log --oneline -1\ngit revert foo\nMSG\necho done"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" not in stripped
    assert "git log --oneline -1" in stripped, "the sibling command shares the opener line"
    assert "echo done" in stripped


def test_heredoc_opener_accepts_redirects_then_separator():
    command = "cat <<'EOF' > notes.md && echo saved\ngit revert foo\nEOF\necho done"
    stripped = strip_heredoc_bodies(command)
    assert "git revert" not in stripped
    assert "echo saved" in stripped
    assert "echo done" in stripped


def test_quoted_shift_text_is_still_not_an_opener():
    """Widening the remainder rule must not make quoted text open a heredoc."""
    command = 'echo "a << EOF" && git status\ngit revert foo'
    stripped = strip_heredoc_bodies(command)
    assert "git revert" in stripped, "nothing was opened, so nothing may be hidden"


def test_unterminated_heredoc_does_not_hide_later_commands():
    """Fail-OPEN guard: an opener that never closes must not blind the scan.

    Skipping to end-of-input would leave every later line unmatched. Widening
    which lines count as openers would widen that blindness too, so a
    terminator is only honoured when a matching closing line actually follows.
    """
    command = "cat <<EOF && echo hi\nsome data\ngit revert HEAD~3"
    stripped = strip_heredoc_bodies(command)
    assert "git revert HEAD~3" in stripped
