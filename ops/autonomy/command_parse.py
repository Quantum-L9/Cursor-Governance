"""Quote-aware Bash command-string parsing shared by the autonomy gates.

Design constraints (fail-closed):

- Heredoc bodies are DATA, not commands — they are stripped before matching.
  Terminators are tracked with a stack and matched line-start/exact; a data
  line that merely looks like a terminator closes the body early, which means
  we match MORE of the remaining text (the safe direction).
- Quoted spans are NEVER stripped. Stripping them would hide real commands
  passed to wrappers (``bash -c 'git push …'``) — a fail-open hole. Segment
  splitting honors quote state instead.
- Only static named paths are extracted (``git -C <path>`` / ``cd <path>``);
  tokens containing substitutions or glob characters are ignored so dynamic
  targets can never widen a gate.
"""

from __future__ import annotations

import re

_HEREDOC_OPEN_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1\s*$")
_SEPARATOR_PAIRS = ("&&", "||")
_SEPARATOR_SINGLES = ";|"


def strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc bodies; keeps the line that opens the heredoc."""
    lines = command.splitlines()
    out: list[str] = []
    terminators: list[str] = []
    for line in lines:
        if terminators:
            if line.strip() == terminators[-1]:
                terminators.pop()
            continue
        out.append(line)
        match = _HEREDOC_OPEN_RE.search(line)
        if match:
            terminators.append(match.group(2))
    return "\n".join(out)


def split_segments(command: str) -> list[str]:
    """Split on ``&&`` ``||`` ``;`` ``|`` newline, honoring single/double quotes."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        ch = command[index]
        if quote is not None:
            buf.append(ch)
            if ch == quote and (index == 0 or command[index - 1] != "\\"):
                quote = None
            index += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            index += 1
            continue
        pair = command[index : index + 2]
        if pair in _SEPARATOR_PAIRS:
            if buf:
                segments.append("".join(buf))
                buf = []
            index += 2
            continue
        if ch in _SEPARATOR_SINGLES or ch == "\n":
            if buf:
                segments.append("".join(buf))
                buf = []
            index += 1
            continue
        buf.append(ch)
        index += 1
    if buf:
        segments.append("".join(buf))
    return [segment.strip() for segment in segments if segment.strip()]


def _dequote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    return token


def segment_words(segment: str) -> list[str]:
    """Word-split a segment honoring quotes (no glob/expansion semantics)."""
    import shlex

    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def segment_head(segment: str) -> str | None:
    """First command word of a segment, skipping env-assignment prefixes."""
    words = segment_words(segment)
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    return words[index] if index < len(words) else None


_WRAPPERS = ("bash", "sh", "zsh", "sudo", "xargs")


def wrapper_subcommands(segment: str, *, _depth: int = 0) -> list[str]:
    """Nested command strings carried by wrapper invocations (``bash -c '…'``).

    Quotes are preserved on the returned strings — callers must never strip
    them before matching. Depth-limited to avoid pathological nesting.
    """
    if _depth >= 3:
        return []
    words = segment_words(segment)
    if not words or words[0] not in _WRAPPERS:
        return []
    found: list[str] = []
    for index, word in enumerate(words):
        if word in ("-c", "--command") and index + 1 < len(words):
            found.append(words[index + 1])
    if words[0] == "xargs" and len(words) > 1:
        # xargs <cmd...> — everything after xargs is the wrapped command
        found.append(" ".join(words[1:]))
    nested: list[str] = []
    for sub in found:
        nested.append(sub)
        nested.extend(wrapper_subcommands(sub, _depth=_depth + 1))
    return nested


#: Executables whose ``-C <path>`` names the directory the command runs in.
#: ``make -C`` means what ``git -C`` means, and a publish invoked that way must
#: be judged against that checkout's receipt, not the session's.
_DASH_C_EXECUTABLES = frozenset({"git", "make"})


def extract_named_roots(command: str) -> list[str]:
    """Static repo paths named by ``git -C``/``make -C <path>`` or ``cd <path>``.

    Fail-closed: tokens containing ``$``, backticks, ``(``/``)``, wildcards,
    braces, or ``~`` are ignored (dynamic targets never widen a gate).
    Heredoc bodies are stripped first — data inside them is not a command.
    """
    roots: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        tokens = segment.split()
        for index, token in enumerate(tokens):
            head = token.rstrip(";")
            candidate: str | None = None
            if (
                head in _DASH_C_EXECUTABLES
                and index + 2 < len(tokens)
                and tokens[index + 1] == "-C"
            ):
                candidate = tokens[index + 2]
            elif head == "cd" and index + 1 < len(tokens):
                candidate = tokens[index + 1]
            if candidate is None:
                continue
            candidate = _dequote(candidate)
            if not candidate or any(ch in candidate for ch in "$`()*?[]{}~"):
                continue
            roots.append(candidate)
    return roots
