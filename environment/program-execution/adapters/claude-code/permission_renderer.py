from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def render_permissions(contract: Mapping[str, Any]) -> dict[str, list[str]]:
    actions = set(contract.get("requested_actions") or [])
    allowed = ["Read", "Grep", "Glob", "Bash(git status:*)", "Bash(git diff:*)"]
    if "local_write" in actions:
        allowed.extend(["Edit", "Write", "Bash(git add:*)", "Bash(git commit:*)"])
    denied = [
        "Bash(git push:*)",
        "Bash(git reset --hard:*)",
        "Bash(git clean -fd:*)",
        "Bash(gh:*)",
        "mcp__github__*",
    ]
    return {"allowed": allowed, "denied": denied}
