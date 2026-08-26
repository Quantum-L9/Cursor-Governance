"""The one grammar for a peer-executable validation command.

This law used to live privately inside the Claude permission renderer, which
meant the renderer was the only layer that knew what a valid command was. Every
upstream layer — the campaign-source compiler, launchability inference — could
emit a command the renderer would later refuse, and the refusal arrived at
provider dispatch: after isolation, compile, bootstrap and arm.

`ls -1 'a' 'b' >/dev/null` is the exact shape that cost a campaign run. It was
synthesized by launchability, survived compile and admission, and died at the
permission ceiling because `>` composes two shell operations.

So the grammar moves here and the renderer becomes a consumer. Nothing about
the ceiling is relaxed in the move: the same operators, substitutions, inline
interpreters and git subcommands are rejected, for the same reasons. What
changes is *when* a producer finds out.
"""

from __future__ import annotations

import shlex
from pathlib import Path

_SHELL_OPERATORS = frozenset({";", "&&", "||", "|", "&", ">", ">>", "<", "<<", "<<<"})
_INLINE_SHELLS = frozenset({"bash", "dash", "fish", "sh", "zsh"})
_INLINE_INTERPRETERS = frozenset({"node", "perl", "python", "python3", "ruby"})
_GIT_PREFIX_FLAGS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_GIT_PREFIX_ASSIGNMENTS = ("--git-dir=", "--work-tree=", "--namespace=")

# Read-only git subcommands a worker may run to prove its own work. A command
# that writes the index, the worktree or a remote is not validation.
SAFE_GIT_VALIDATION_COMMANDS = frozenset(
    {
        "cat-file",
        "check-ignore",
        "describe",
        "diff",
        "for-each-ref",
        "grep",
        "log",
        "ls-files",
        "merge-base",
        "rev-parse",
        "show",
        "status",
    }
)


class ValidationCommandError(ValueError):
    """A command no peer permission ceiling will admit.

    Raised by producers and consumers alike, so the diagnostic reads the same
    whether it surfaced at source preflight or at permission rendering.
    """


def _shell_tokens(value: str) -> tuple[str, ...]:
    lexer = shlex.shlex(value, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return tuple(lexer)
    except ValueError as exc:
        raise ValidationCommandError(
            f"validation command is not valid shell syntax: {value!r}"
        ) from exc


def _executable_index(tokens: tuple[str, ...]) -> int:
    index = 0
    if tokens and Path(tokens[0]).name == "env":
        index = 1
        while index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("-"):
            index += 1
    return index


def _git_subcommand(tokens: tuple[str, ...], executable_index: int) -> str | None:
    index = executable_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token in _GIT_PREFIX_FLAGS:
            index += 2
            continue
        if token.startswith(_GIT_PREFIX_ASSIGNMENTS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def validate_validation_command(command: str) -> str:
    """Return the command unchanged, or raise ValidationCommandError.

    Returning the input is deliberate: callers embed the result directly
    (`Bash(<command>)`), so a validator that silently rewrote its input would
    grant a permission for a command nobody wrote.
    """
    value = command.strip()
    if not value:
        raise ValidationCommandError("validation command must not be empty")
    if any(char in value for char in ("\x00", "\r", "\n")):
        raise ValidationCommandError("validation command must be a single shell line")
    if "$(" in value or "`" in value:
        raise ValidationCommandError("validation command must not use shell command substitution")
    tokens = _shell_tokens(value)
    if not tokens:
        raise ValidationCommandError("validation command must contain an executable")
    if any(token in _SHELL_OPERATORS for token in tokens):
        raise ValidationCommandError(
            "validation command must not compose multiple shell operations"
        )

    executable_index = _executable_index(tokens)
    if executable_index >= len(tokens):
        raise ValidationCommandError("validation command must contain an executable")
    executable = Path(tokens[executable_index]).name
    tail = tokens[executable_index + 1 :]
    if executable == "gh":
        raise ValidationCommandError(
            "validation command conflicts with the peer permission ceiling"
        )
    if executable in _INLINE_SHELLS and "-c" in tail:
        raise ValidationCommandError("validation command must not execute an inline shell program")
    if executable in _INLINE_INTERPRETERS and any(flag in tail for flag in ("-c", "-e")):
        raise ValidationCommandError("validation command must not execute inline code")
    if executable == "git":
        subcommand = _git_subcommand(tokens, executable_index)
        if subcommand not in SAFE_GIT_VALIDATION_COMMANDS:
            raise ValidationCommandError(
                "validation git command is not in the read-only validation allowlist: " + value
            )
    return value


def validation_command_error(command: str) -> str | None:
    """The rejection reason, or None when the command is admissible.

    For producers that report many findings rather than raising on the first.
    """
    try:
        validate_validation_command(command)
    except ValidationCommandError as exc:
        return str(exc)
    return None
