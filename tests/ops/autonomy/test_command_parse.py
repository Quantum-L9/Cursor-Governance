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
    command = "python - <<'EOF'\ncd /tmp/not-a-command && git -C /tmp/also-data push\nEOF\ncd /tmp/real && git push"
    assert extract_named_roots(command) == ["/tmp/real"]


@pytest.mark.parametrize("bad", ["", None])
def test_extract_named_roots_empty_command(bad):
    assert extract_named_roots(bad or "") == []
