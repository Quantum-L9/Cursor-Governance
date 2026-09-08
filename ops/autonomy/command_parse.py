"""Quote-aware Bash command-string parsing shared by the autonomy gates.

Design constraints (fail-closed):

- Heredoc bodies are DATA, not commands — they are stripped before matching.
  Terminators are tracked with a stack and matched line-start/exact; a data
  line that merely looks like a terminator closes the body early, which means
  we match MORE of the remaining text (the safe direction).
- Quoted spans are NEVER stripped. Stripping them would hide real commands
  passed to wrappers (``bash -c 'git push …'``) — a fail-open hole. Segment
  splitting honors quote state instead.
- Only static named paths are extracted (``git -C <path>`` / ``cd <path>`` /
  make ``WS=``); tokens containing substitutions or glob characters are
  ignored so dynamic targets can never widen a gate.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

# Opener only — no repeating optional-quantifier group. CodeQL 410/412 flagged
# both `\S+` and `[^\s>|&;]+` after `[0-9]?>>?` inside `*`: `>a>a…` / `!0>`
# have exponentially many decompositions. Redirects after the delimiter are
# checked in Python so the engine never backtracks.
_HEREDOC_OPEN_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_REDIRECT_OP_RE = re.compile(r"[0-9]?>>?")
_SEPARATOR_PAIRS = ("&&", "||")
_SEPARATOR_SINGLES = ";|"


_SEPARATOR_STARTS = (*_SEPARATOR_PAIRS, *_SEPARATOR_SINGLES)


def _remainder_is_redirects(rest: str) -> bool:
    """True when REST is only whitespace, redirect clauses, or a separator tail.

    A heredoc opener may be followed on the SAME line by redirects (`> file`,
    `2>err`) and by the start of the next command — `git commit -F - <<'MSG' &&
    git log` is ordinary Bash, and the body still begins on the following line.
    Only redirects were accepted before, so that form was not recognised as an
    opener at all and its body was never stripped.

    The consequence was a false DENY, not a false allow. The unstripped body
    reached ``split_segments``, which splits on ``&&`` regardless of where the
    text came from, so prose in a commit message could yield a fragment whose
    first word is ``git``. A message quoting ``cd <clone> && git checkout
    <branch>`` produced the phantom segment ``git checkout <branch>` was
    denied.``, and ``worktree_isolation_gate`` refused the commit as a branch
    switch on a dirty tree — describing a command that was never run. It needed
    a dirty tree to fire, so it presented as intermittent.
    """
    tokens = rest.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        # `&& git log`, `; echo`, `| tee` — the heredoc body is still the next
        # line; this token begins a sibling command, which stays on the opener
        # line and is segmented normally.
        if token.startswith(_SEPARATOR_STARTS):
            return True
        if _REDIRECT_OP_RE.fullmatch(token):
            if index + 1 >= len(tokens):
                return False
            index += 2
            continue
        glued = _REDIRECT_OP_RE.match(token)
        if glued is not None and glued.end() < len(token):
            index += 1
            continue
        return False
    return True


def _heredoc_delimiter(line: str) -> str | None:
    """Return the terminator word when LINE opens a heredoc, else None."""
    match = _HEREDOC_OPEN_RE.search(line)
    if match is None:
        return None
    if not _remainder_is_redirects(line[match.end() :]):
        return None
    return match.group(2)


def strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc bodies; keeps the line that opens the heredoc.

    A terminator is only honoured when a matching closing line actually
    follows. Skipping to end-of-input on an opener that never closes is the
    fail-OPEN direction — every later line would go unscanned — and widening
    which lines count as openers (see ``_remainder_is_redirects``) would
    otherwise widen that blindness too. Unclosed openers are therefore left in
    place and matched as text, consistent with this module's rule that an
    early-closing body makes us match MORE of the remaining text, never less.
    """
    lines = command.splitlines()
    out: list[str] = []
    terminators: list[str] = []
    for position, line in enumerate(lines):
        if terminators:
            if line.strip() == terminators[-1]:
                terminators.pop()
            continue
        out.append(line)
        delimiter = _heredoc_delimiter(line)
        if delimiter is not None and any(
            later.strip() == delimiter for later in lines[position + 1 :]
        ):
            terminators.append(delimiter)
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


#: Executables whose ``-C <path>`` names a directory. For ``git`` that is the
#: repo. For ``make`` it is the makefile directory — the workspace a goal
#: acts on is ``WS=`` (Makefile ``WS ?= $(CURDIR)``). When ``WS=`` is present
#: it is the named root and ``make -C`` is not.
_DASH_C_EXECUTABLES = frozenset({"git", "make"})

ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MAKE_WORKSPACE_VARS = frozenset({"WS", "L9_L4_WORKSPACE"})
_MAKE_OPTS_WITH_ARG = frozenset(
    {"-C", "-f", "-j", "-l", "-o", "-W", "--directory", "--file", "--makefile", "--jobs"}
)


def _assignment_value(token: str, keys: frozenset[str]) -> str | None:
    if not ENV_ASSIGN_RE.match(token):
        return None
    key, _, value = token.partition("=")
    if key not in keys:
        return None
    cleaned = _dequote(value.strip())
    return cleaned or None


def make_workspace_raw(segment: str) -> str | None:
    """Last ``WS=`` / ``L9_L4_WORKSPACE=`` on a make segment, or None."""
    tokens = segment_words(segment)
    index = 0
    found: str | None = None
    while index < len(tokens) and ENV_ASSIGN_RE.match(tokens[index]):
        raw = _assignment_value(tokens[index], MAKE_WORKSPACE_VARS)
        if raw is not None:
            found = raw
        index += 1
    if index >= len(tokens) or PurePosixPath(tokens[index]).name != "make":
        return None
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token in _MAKE_OPTS_WITH_ARG:
            index += 2
            continue
        raw = _assignment_value(token, MAKE_WORKSPACE_VARS)
        if raw is not None:
            found = raw
        index += 1
    return found


def extract_named_roots(command: str) -> list[str]:
    """Static repo paths named by ``git -C``, make ``WS=`` / ``make -C``, or ``cd``.

    A make ``WS=`` / ``L9_L4_WORKSPACE=`` is the workspace the Makefile acts
    on. ``make -C`` is only used when those are absent (CURDIR after ``-C``).

    Fail-closed: tokens containing ``$``, backticks, ``(``/``)``, wildcards,
    braces, or ``~`` are ignored (dynamic targets never widen a gate).
    Heredoc bodies are stripped first — data inside them is not a command.
    """
    roots: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        make_ws = make_workspace_raw(segment)
        skip_make_dash_c = False
        if make_ws and not any(ch in make_ws for ch in "$`()*?[]{}~"):
            roots.append(make_ws)
            skip_make_dash_c = True
        tokens = segment_words(segment)
        for index, token in enumerate(tokens):
            head = token.rstrip(";")
            candidate: str | None = None
            if (
                head in _DASH_C_EXECUTABLES
                and index + 2 < len(tokens)
                and tokens[index + 1] == "-C"
            ):
                if skip_make_dash_c and head == "make":
                    continue
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
