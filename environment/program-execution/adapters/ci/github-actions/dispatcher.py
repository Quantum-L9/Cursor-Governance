from __future__ import annotations

from typing import Any


def dispatch_workflow(transport, contract: dict[str, Any]) -> dict[str, Any]:
    repository = str(contract["repository"])
    workflow = str(contract["workflow"])
    ref = str(contract["candidate_sha"])
    argv = ["workflow", "run", workflow, "--repo", repository, "--ref", ref]
    for key, value in sorted((contract.get("workflow_inputs") or {}).items()):
        argv.extend(["-f", f"{key}={value}"])
    result = transport.run(argv)
    if result.exit_code != 0:
        raise RuntimeError(result.stderr or "workflow dispatch failed")
    return {"repository": repository, "workflow": workflow, "ref": ref}
