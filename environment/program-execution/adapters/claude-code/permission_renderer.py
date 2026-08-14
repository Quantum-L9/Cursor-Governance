from __future__ import annotations

import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_SHELL_OPERATORS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<", "<<<"}
_SAFE_GIT_VALIDATION_COMMANDS = {
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


def _shell_tokens(value: str) -> tuple[str, ...]:
    lexer = shlex.shlex(value, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return tuple(lexer)
    except ValueError as exc:
        raise ValueError(f"validation command is not valid shell syntax: {value!r}") from exc


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
        if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _validated_command(command: str) -> str:
    value = command.strip()
    if not value:
        raise ValueError("validation command must not be empty")
    if any(char in value for char in ("\x00", "\r", "\n")):
        raise ValueError("validation command must be a single shell line")
    if "$(" in value or "`" in value:
        raise ValueError("validation command must not use shell command substitution")
    tokens = _shell_tokens(value)
    if not tokens:
        raise ValueError("validation command must contain an executable")
    if any(token in _SHELL_OPERATORS for token in tokens):
        raise ValueError("validation command must not compose multiple shell operations")

    executable_index = _executable_index(tokens)
    if executable_index >= len(tokens):
        raise ValueError("validation command must contain an executable")
    executable = Path(tokens[executable_index]).name
    tail = tokens[executable_index + 1 :]
    if executable == "gh":
        raise ValueError("validation command conflicts with the peer permission ceiling")
    if executable in {"bash", "dash", "fish", "sh", "zsh"} and "-c" in tail:
        raise ValueError("validation command must not execute an inline shell program")
    if executable in {"node", "perl", "python", "python3", "ruby"} and any(
        flag in tail for flag in ("-c", "-e")
    ):
        raise ValueError("validation command must not execute inline code")
    if executable == "git":
        subcommand = _git_subcommand(tokens, executable_index)
        if subcommand not in _SAFE_GIT_VALIDATION_COMMANDS:
            raise ValueError(
                "validation git command is not in the read-only validation allowlist: " + value
            )
    return value


def render_permissions(
    profile: Mapping[str, Any],
    rendered_contract: Mapping[str, Any],
) -> dict[str, list[str]]:
    allowed_actions = set(profile.get("allowed_actions") or [])
    denied_actions = set(profile.get("denied_actions") or [])
    allowed: list[str] = []
    if "inspect" in allowed_actions:
        allowed.extend(
            [
                "Read",
                "Grep",
                "Glob",
                "Bash(git status:*)",
                "Bash(git diff:*)",
            ]
        )
    if "local_write" in allowed_actions:
        allowed.extend(["Edit", "Write"])
    for command in rendered_contract.get("validation_commands") or []:
        if not isinstance(command, str):
            raise ValueError("validation commands must be strings")
        allowed.append(f"Bash({_validated_command(command)})")
    denied = [
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(git reset --hard:*)",
        "Bash(git clean -fd:*)",
        "Bash(gh:*)",
        "mcp__github__*",
    ]
    if "push" in denied_actions or "push" not in allowed_actions:
        denied.append("Bash(git push:*)")
    return {"allowed": sorted(set(allowed)), "denied": sorted(set(denied))}
