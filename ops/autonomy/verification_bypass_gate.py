#!/usr/bin/env python3
"""Deny commands that skip local commit verification.

`git commit --no-verify` was forbidden in eight skill files and allowed by every
gate. Prose cannot deny a command; only a hook process returning a deny decision
can. This module is that decision, and
``ops/config/commit-verification-contract.json`` is the single declaration it
reads — the same file the session briefing and the conformance suite read, so
the rule an agent is told cannot drift from the rule that is enforced.

Placement matters. ``git`` is exempt from the *workflow* plane of
``local_execution_gate`` (publish path, L4 phase, worktree isolation) — see
``git_execution_exemption`` — so a check placed there would never run. This is
called from the same position as ``git_guardrails.command_requires_human``:
before the exemption, on every shell command.

It is a separate plane from ``git_guardrails`` on purpose. That contract decides
from effect, sensitivity, recoverability, and blast radius — a taxonomy about
*destroying work*. Skipping a hook destroys nothing; it removes a check. Forcing
it into the destructive taxonomy would corrupt both contracts, so this one
answers a different question: was the verification that governs this commit
actually run?

Human/ops breakglass is declared in the contract (``L9_VERIFY_BYPASS_AUTHORIZED``)
and requires a stated reason. An agent must not set it for itself: exporting it
in the same turn as the commit is the bypass one level up.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    segment_head,
    segment_words,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)

CONTRACT_ID = "l9-commit-verification-integrity"
CONTRACT_PATH = _HERE.parents[1] / "ops" / "config" / "commit-verification-contract.json"

#: Heads that can mutate a file when handed a path under the hook directory.
#: Deliberately not a catch-all: ``cat``/``ls`` over the same path is inspection
#: and stays allowed, which is what makes this check safe to leave on.
_HOOK_MUTATOR_HEADS = frozenset(
    {"rm", "mv", "cp", "chmod", "truncate", "ln", "install", "tee", "dd", "shred", "unlink"}
)

_HOOK_DIR_TOKEN = ".git/hooks"


class ContractError(RuntimeError):
    """The declaration could not be read or is not shaped as declared."""


@lru_cache(maxsize=4)
def _load_cached(target: str) -> dict[str, Any]:
    path = Path(target)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"{path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path}: top level is not an object")
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        raise ContractError(f"{path}: 'forms' must be a non-empty list")
    for form in forms:
        if not isinstance(form, dict) or not form.get("id") or not form.get("detector"):
            raise ContractError(f"{path}: every form needs an 'id' and a 'detector'")
    breakglass = data.get("breakglass")
    if not isinstance(breakglass, dict) or not breakglass.get("env"):
        raise ContractError(f"{path}: 'breakglass.env' is required")
    if not data.get("remedy"):
        raise ContractError(f"{path}: 'remedy' is required — a denial must name the way forward")
    return data


def load_contract(path: str | None = None) -> dict[str, Any]:
    """Parse and shape-check the declaration. Cached; raises ContractError.

    Resolved through ``CONTRACT_PATH`` at call time rather than import time so a
    test can repoint it.
    """
    return _load_cached(str(path) if path else str(CONTRACT_PATH))


load_contract.cache_clear = _load_cached.cache_clear  # type: ignore[attr-defined]


def briefing_lines(contract: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Lines the session briefing must carry, so the told rule is the real one."""
    data = contract or load_contract()
    return tuple(str(line) for line in data.get("briefing_lines", ()))


def _authorized(contract: dict[str, Any], env: Mapping[str, str] | None = None) -> bool:
    """True when a human has set the breakglass with a real reason."""
    source: Mapping[str, str] = os.environ if env is None else env
    breakglass = contract["breakglass"]
    reason = str(source.get(str(breakglass["env"]), "")).strip()
    if not reason:
        return False
    if not breakglass.get("requires_reason", True):
        return True
    rejected = {str(item).lower() for item in breakglass.get("rejected_reasons", ())}
    return reason.lower() not in rejected


def _env_prefix(words: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split leading ``VAR=value`` assignments from the command words."""
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    return list(words[:index]), list(words[index:])


def _git_parts(words: Sequence[str]) -> tuple[list[str], str | None, list[str]] | None:
    """``(global_opts, subcommand, args)`` for a git invocation, else None.

    ``_git_subcommand`` in ``git_guardrails`` discards the global options; the
    ``-c core.hooksPath=…`` form lives entirely inside them, so this keeps them.
    """
    _, rest = _env_prefix(words)
    if not rest or PurePosixPath(rest[0]).name != "git":
        return None
    index = 1
    globals_: list[str] = []
    while index < len(rest):
        word = rest[index]
        if word in {"-C", "--git-dir", "--work-tree", "--namespace", "-c", "--config-env"}:
            globals_.extend(rest[index + 1 : index + 2])
            index += 2
            continue
        if word.startswith("-"):
            globals_.append(word)
            index += 1
            continue
        break
    if index >= len(rest):
        return globals_, None, []
    return globals_, rest[index], list(rest[index + 1 :])


def _flag_present(
    args: Sequence[str],
    long_flags: Sequence[str],
    short_flags: Sequence[str],
    value_flags: Sequence[str],
) -> bool:
    """Scan args for a bypass flag, skipping values of value-taking flags.

    The value skip is the whole reason this is not a regex: in
    ``git commit -m -n`` the ``-n`` is the commit message, not a bypass, and a
    gate that denies that is a gate someone turns off.
    """
    long_set = set(long_flags)
    short_set = {item.lstrip("-") for item in short_flags if item.strip("-")}
    value_set = set(value_flags)
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            return False
        if arg in value_set:
            index += 2
            continue
        base = arg.split("=", 1)[0]
        if base in long_set:
            return True
        if short_set and arg.startswith("-") and not arg.startswith("--"):
            # A short cluster (-nm) carries every letter in it.
            if short_set.intersection(arg[1:]):
                return True
        index += 1
    return False


def _redirect_targets(segment: str) -> list[str]:
    """Tokens a ``>``/``>>`` redirect writes into."""
    targets: list[str] = []
    tokens = segment.replace(">>", " > ").replace(">", " > ").split()
    for index, token in enumerate(tokens):
        if token == ">" and index + 1 < len(tokens):
            targets.append(tokens[index + 1].strip("\"'"))
    return targets


def _match_form(
    contract: dict[str, Any], form: dict[str, Any], segment: str, words: Sequence[str]
) -> bool:
    """True when this segment exhibits this declared bypass form."""
    detector = form["detector"]
    git = _git_parts(words)

    if detector == "git_flag":
        if git is None:
            return False
        _globals, sub, args = git
        if sub != form.get("subcommand"):
            return False
        value_flags = contract.get("git_value_flags", {}).get(str(sub), [])
        return _flag_present(args, form.get("flags", ()), form.get("short_flags", ()), value_flags)

    if detector == "git_global_config":
        if git is None:
            return False
        globals_, _sub, _args = git
        keys = {str(key).lower() for key in form.get("keys", ())}
        return any(token.split("=", 1)[0].strip().lower() in keys for token in globals_)

    if detector == "git_subcommand_args":
        if git is None:
            return False
        _globals, sub, args = git
        if sub != form.get("subcommand"):
            return False
        wanted = {str(item).lower() for item in form.get("match_args", ())}
        return any(arg.split("=", 1)[0].strip().lower() in wanted for arg in args)

    if detector == "env_prefix":
        if git is None:
            return False
        _globals, sub, _args = git
        if sub not in set(form.get("applies_to_subcommands", ())):
            return False
        assigns, _rest = _env_prefix(words)
        names = {str(name).upper() for name in form.get("vars", ())}
        return any(item.split("=", 1)[0].upper() in names for item in assigns)

    if detector == "argv":
        _assigns, rest = _env_prefix(words)
        if not rest or PurePosixPath(rest[0]).name != str(form.get("head")):
            return False
        return all(str(item) in rest[1:] for item in form.get("args", ()))

    if detector == "hook_path_write":
        _assigns, rest = _env_prefix(words)
        head = PurePosixPath(rest[0]).name if rest else ""
        touches = [word for word in rest[1:] if _HOOK_DIR_TOKEN in word]
        if head in _HOOK_MUTATOR_HEADS and touches:
            return True
        if (
            head in {"sed", "perl"}
            and touches
            and any(word.startswith("-i") or word == "--in-place" for word in rest[1:])
        ):
            return True
        return any(_HOOK_DIR_TOKEN in target for target in _redirect_targets(segment))

    return False


def _deny_reason(contract: dict[str, Any], form: dict[str, Any]) -> str:
    breakglass = contract["breakglass"]
    return (
        f"verification bypass ({CONTRACT_ID}): `{form['label']}` "
        f"{form['why']}. {contract['remedy']} "
        f"Declared in ops/config/commit-verification-contract.json (form `{form['id']}`); "
        "denied by ops/autonomy/verification_bypass_gate.py. "
        f"Human/ops override: {breakglass['env']}=<reason>."
    )


def _unreadable_contract_verdict(command: str, exc: BaseException) -> str | None:
    """Fail closed, but only over the commands this plane governs."""
    lowered = command.lower()
    governs = _HOOK_DIR_TOKEN in lowered or any(
        token in lowered for token in ("git commit", "git push", "pre-commit")
    )
    if not governs:
        return None
    return (
        f"verification bypass ({CONTRACT_ID}): the declaration could not be "
        f"evaluated ({type(exc).__name__}: {exc}), so commit verification cannot "
        "be proven to have run and this fails closed. Repair "
        "ops/config/commit-verification-contract.json."
    )


def command_bypasses_verification(
    command: str, *, env: Mapping[str, str] | None = None
) -> str | None:
    """Deny reason when this command skips commit verification, else None.

    Never raises. A declaration that cannot be read fails closed for exactly the
    commands it governs (git commit/push, pre-commit, hook-directory writes) and
    stays silent for everything else: a typo in one JSON file must not brick a
    session, but it must not silently retire the gate either.
    """
    if not command or not command.strip():
        return None
    try:
        contract = load_contract()
    except ContractError as exc:
        return _unreadable_contract_verdict(command, exc)
    if _authorized(contract, env):
        return None
    try:
        segments: list[str] = []
        for segment in split_segments(strip_heredoc_bodies(command)):
            segments.append(segment)
            segments.extend(wrapper_subcommands(segment))
        for segment in segments:
            if segment_head(segment) is None:
                continue
            words = segment_words(segment)
            if not words:
                continue
            for form in contract["forms"]:
                if _match_form(contract, form, segment, words):
                    return _deny_reason(contract, form)
    except Exception as exc:  # noqa: BLE001 - gate boundary: never fail open
        print(
            f"verification_bypass_gate: evaluation failed ({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )
        return _unreadable_contract_verdict(command, exc)
    return None


__all__ = [
    "CONTRACT_ID",
    "CONTRACT_PATH",
    "ContractError",
    "briefing_lines",
    "command_bypasses_verification",
    "load_contract",
]
