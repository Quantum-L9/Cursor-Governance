"""Convert a validated contract into Claude tool permissions.

The renderer stays the authority for *how* an admissible command becomes a
`Bash(...)` grant. It is no longer the only layer that knows *what* is
admissible: that grammar is `peer_execution.validation_command`, shared with
the campaign-source compiler and launchability so a producer cannot emit a
command this ceiling would later refuse.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from peer_execution.validation_command import validate_validation_command


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
        allowed.append(f"Bash({validate_validation_command(command)})")
    # Workers may not mint a candidate commit. candidate_sha on the worker
    # receipt is JSON null; the controller records worktree HEAD after the
    # attempt. Do not grant git add/commit to "fix" that identity.
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
