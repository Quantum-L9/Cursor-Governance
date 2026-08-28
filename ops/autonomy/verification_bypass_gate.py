#!/usr/bin/env python3
"""Deny a shell command that suppresses verification rather than passing it.

This repository installs **no** git commit hook. ``pre-commit install`` is
forbidden (``validate_claude_env.check_session_deps_installs_no_git_hook``,
``ops/scripts/run_pr_precommit.sh``): the catalog runs from ``make pr-check`` /
``make pr``, which apply the surface-aware SKIP list a raw hook would not.

That design has a sharp edge. An agent that has learned "commits run hooks"
elsewhere reaches for ``--no-verify`` or ``-c core.hooksPath=/dev/null`` out of
habit. Here those tokens suppress nothing — there is no hook — so the command
succeeds and *looks* like a bypass that worked. Nothing in the tree contradicted
it, and prose in a rule file cannot: a rule is read after the fact, a gate
answers at the moment of the call.

So this plane is not about protecting a hook. It is about the intent: on a
repository with no commit hook, the only reason to type a hook-bypass token is
to get past verification, and there is no legitimate case to preserve. Deny it,
and say where verification actually lives.

Policy SSOT: ``ops/config/verification-bypass-policy.json`` — one machine-readable
file this gate and its tests both read, so the token list is never restated in
prose that can drift from the enforcement.

Runs in ``local_execution_gate.evaluate`` BEFORE the git/gh workflow exemption,
alongside ``git_guardrails``: a git command is exempt from *workflow* denials,
never from this one.

Human authorization (human / ops only — never agent self-issued):
  L9_VERIFICATION_BYPASS_AUTHORIZED=<reason>
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import split_segments, strip_heredoc_bodies  # noqa: E402

POLICY_PATH = _HERE.parent / "config" / "verification-bypass-policy.json"

#: A bare truthy value is not a reason; mirrors ``git_guardrails.human_authorized``.
_EMPTY_REASONS = frozenset({"1", "0", "y", "yes", "no", "true", "false", "ok"})


@lru_cache(maxsize=1)
def policy() -> dict:
    """Load the JSON policy. A missing or malformed policy fails CLOSED.

    An unreadable policy means the gate cannot tell a bypass from a normal
    command. Returning an empty policy would silently allow every bypass, so the
    loader raises and the caller's fail-closed path denies instead.
    """
    with POLICY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not data.get("bypass_flags"):
        raise ValueError(f"malformed verification-bypass policy: {POLICY_PATH}")
    return data


def human_authorized(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    spec = policy()
    reason = str(env.get(spec["authorization_env"], "")).strip()
    if not reason or reason.lower() in _EMPTY_REASONS:
        return False
    return len(reason) >= int(spec.get("authorization_min_reason_chars", 8))


def _guarded_command(words: list[str]) -> str | None:
    """Return the guarded ``git <subcommand>`` this segment runs, else None.

    Skips git's global options so ``git -c core.hooksPath=x commit`` still
    resolves to ``git commit``.
    """
    spec = policy()
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith("-"):
        index += 1  # leading VAR=value assignments
    if index >= len(words) or Path(words[index]).name != "git":
        return None
    index += 1
    takes_arg = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
    while index < len(words) and words[index].startswith("-"):
        if words[index] in takes_arg:
            index += 2
        else:
            index += 1
    if index >= len(words):
        return None
    candidate = f"git {words[index]}"
    return candidate if candidate in spec["guarded_commands"] else None


def _reason(what: str, detail: str) -> str:
    spec = policy()
    return (
        f"L9 verification-bypass gate: {what} — {detail}\n"
        "This repository installs NO git commit hook by design; the token suppresses "
        "nothing, so typing it is intent to bypass verification.\n"
        f"Verification runs at: {spec['verification_path']}.\n"
        "Run the command without the token. If verification is what you want to "
        f"satisfy, run `make pr-check`. Human override: {spec['authorization_env']}=<reason>."
    )


def command_bypasses_verification(command: str) -> str | None:
    """Return a deny reason when ``command`` suppresses verification, else None."""
    if not command or not command.strip():
        return None
    try:
        spec = policy()
    except (OSError, ValueError, json.JSONDecodeError) as exc:  # fail closed
        return (
            "L9 verification-bypass gate: policy unreadable "
            f"({POLICY_PATH.name}: {exc}); refusing to classify — fail closed"
        )
    if human_authorized():
        return None

    flags = set(spec["bypass_flags"])
    flag_exempt = set(spec.get("bypass_flag_exempt_commands", ()))
    config_keys = tuple(spec["bypass_config_keys"])
    env_names = set(spec["bypass_env_assignments"])

    for segment in split_segments(strip_heredoc_bodies(command)):
        try:
            words = shlex.split(segment)
        except ValueError:
            continue
        if not words:
            continue

        # Inline env assignments that disable hooks, on any command in the segment.
        for word in words:
            if "=" not in word or word.startswith("-"):
                break
            if word.split("=", 1)[0] in env_names:
                return _reason(
                    f"`{word.split('=', 1)[0]}=` disables or narrows hook execution",
                    f"in `{segment.strip()[:120]}`",
                )

        guarded = _guarded_command(words)
        if guarded is None:
            continue

        for word in words:
            key = word.split("=", 1)[0]
            if key in ("-c", "--config") or word.startswith("-c"):
                continue
            if any(word.startswith(f"{cfg}=") or word == cfg for cfg in config_keys):
                return _reason(f"`{key}` redirects git away from its hooks", f"on `{guarded}`")

        if guarded not in flag_exempt:
            for word in words[1:]:
                if word in flags:
                    return _reason(f"`{word}` skips hook execution", f"on `{guarded}`")
    return None


def main(argv: list[str] | None = None) -> int:
    """CLI: classify a command string. Exit 2 when it would be denied."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: verification_bypass_gate.py <command ...>", file=sys.stderr)
        return 64
    reason = command_bypasses_verification(" ".join(args))
    if reason:
        print(reason, file=sys.stderr)
        return 2
    print("ALLOW: no verification bypass detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
