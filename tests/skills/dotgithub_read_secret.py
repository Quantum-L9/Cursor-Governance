"""Shared contract for the one secret a pull-request workflow may hold.

Quantum-L9/.github is private (docs/DEGRADED_MODE_CONTRACT.md, 2026-11-16), and a
repository's GITHUB_TOKEN cannot read it. A pull-request workflow runs the
workflow file from the PR's own branch, so any secret there can be printed by
whoever pushes that branch. The only secret allowed is a read-only token scoped
to that repository, and only as the token of a non-persisted actions/checkout
of it, on a step with no env or run.
"""

from __future__ import annotations

import json
import re
from typing import Any

DOTGITHUB_READ_SECRET = "secrets.L9_GITHUB_READ_TOKEN"


def assert_only_dotgithub_read_secret(workflow: dict[str, Any], text: str) -> None:
    assert set(re.findall(r"secrets\.[A-Za-z0-9_]+", text)) <= {DOTGITHUB_READ_SECRET}
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if DOTGITHUB_READ_SECRET not in json.dumps(step):
                continue
            with_ = step.get("with") or {}
            assert str(step.get("uses", "")).startswith("actions/checkout@")
            assert with_.get("repository") == "Quantum-L9/.github"
            assert with_.get("token") == "${{ " + DOTGITHUB_READ_SECRET + " }}"
            assert with_.get("persist-credentials") is False
            assert set(step) <= {"name", "if", "uses", "with"}, "only the checkout sees it"
