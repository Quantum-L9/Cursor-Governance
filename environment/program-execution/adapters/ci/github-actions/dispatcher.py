from __future__ import annotations

import datetime as dt
from typing import Any


def dispatch_ref(contract: dict[str, Any]) -> str:
    """The branch or tag the workflow is dispatched on.

    GitHub's workflow_dispatch API accepts a branch or tag name only; a commit
    SHA is rejected, so `candidate_sha` cannot be the `--ref`. The contract
    names the ref; `candidate_sha` is proven afterwards against the run's
    `headSha` (the `candidate_sha_exact` gate).
    """
    ref = contract.get("ref") or contract.get("branch")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            "GitHub Actions dispatch requires a branch or tag `ref` in the contract; "
            "a commit SHA is not a dispatchable reference"
        )
    return ref.strip()


def dispatch_workflow(transport, contract: dict[str, Any]) -> dict[str, Any]:
    repository = str(contract["repository"])
    workflow = str(contract["workflow"])
    ref = dispatch_ref(contract)
    argv = ["workflow", "run", workflow, "--repo", repository, "--ref", ref]
    for key, value in sorted((contract.get("workflow_inputs") or {}).items()):
        argv.extend(["-f", f"{key}={value}"])
    dispatched_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    result = transport.run(argv)
    if result.exit_code != 0:
        raise RuntimeError(result.stderr or "workflow dispatch failed")
    return {
        "repository": repository,
        "workflow": workflow,
        "ref": ref,
        "candidate_sha": str(contract["candidate_sha"]),
        "dispatched_at": dispatched_at,
    }
