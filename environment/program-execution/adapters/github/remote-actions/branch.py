from __future__ import annotations

from typing import Any


def create_branch(transport, repository: str, branch: str, base_sha: str) -> dict[str, Any]:
    return transport.api(
        f"repos/{repository}/git/refs",
        method="POST",
        fields={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )
