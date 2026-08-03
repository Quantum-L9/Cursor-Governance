from __future__ import annotations

from typing import Any


def create_draft(transport, contract: dict[str, Any]) -> dict[str, Any]:
    result = transport.run(
        [
            "pr",
            "create",
            "--repo",
            str(contract["repository"]),
            "--base",
            str(contract["base_branch"]),
            "--head",
            str(contract["head_branch"]),
            "--title",
            str(contract["title"]),
            "--body",
            str(contract.get("body") or ""),
            "--draft",
        ]
    )
    if result.exit_code != 0:
        raise RuntimeError(result.stderr or "draft PR creation failed")
    return {"url": result.stdout.strip()}


def update_draft(transport, contract: dict[str, Any]) -> dict[str, Any]:
    argv = [
        "pr",
        "edit",
        str(contract["pull_request"]),
        "--repo",
        str(contract["repository"]),
    ]
    if "title" in contract:
        argv.extend(["--title", str(contract["title"])])
    if "body" in contract:
        argv.extend(["--body", str(contract["body"])])
    result = transport.run(argv)
    if result.exit_code != 0:
        raise RuntimeError(result.stderr or "draft PR update failed")
    return {"pull_request": contract["pull_request"], "updated": True}
