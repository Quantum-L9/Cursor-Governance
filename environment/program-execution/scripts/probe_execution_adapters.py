from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from adapters.common.models import ProbeContext
from peer_execution.imports import load_module, pe_script

_provider_loader = pe_script("provider_loader")
instantiate = _provider_loader.instantiate
load_registry = _provider_loader.load_registry
repository_root = _provider_loader.repository_root


def _default_runtime() -> Path:
    # `environment/agents/runtime_paths.py` owns the program runtime root
    # (`L9_PROGRAM_HOME`, else `$L9_RUNTIME_ROOT/programs`). Restating that
    # resolution here had already drifted: it ignored `L9_RUNTIME_ROOT`.
    runtime_paths = load_module(
        repository_root() / "environment" / "agents" / "runtime_paths.py",
        "pe_agent_runtime_paths",
    )
    return (runtime_paths.program_runtime_root() / "_adapter-probe").resolve()


#: The inventory probe runs with no program. Its receipts bind to this named
#: sentinel, land only under the `_adapter-probe` runtime root, and are labelled
#: `inventory_sentinel` in the report; the routing gate refuses a capability
#: receipt whose digest is not the live Program Lock, so they can never admit a
#: dispatch.
INVENTORY_PROBE_LOCK_DIGEST = (
    "sha256:" + hashlib.sha256(b"program-execution-adapter-probe:inventory-sentinel").hexdigest()
)
INVENTORY_RUNTIME_DIRNAME = "_adapter-probe"


def _lock_binding(digest: str | None) -> tuple[str, str]:
    """(digest, binding_kind): a real lock from the operator, else the sentinel."""
    value = digest or os.environ.get("L9_PROGRAM_LOCK_DIGEST")
    if value:
        return value, "program_lock"
    return INVENTORY_PROBE_LOCK_DIGEST, "inventory_sentinel"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=_default_runtime())
    parser.add_argument(
        "--program-lock-digest",
        default=None,
        help="bind receipts to this Program Lock; omitted = inventory sentinel",
    )
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
    digest, binding_kind = _lock_binding(args.program_lock_digest)
    if binding_kind == "inventory_sentinel" and runtime.name != INVENTORY_RUNTIME_DIRNAME:
        parser.error(
            f"sentinel-bound receipts may only be written under a {INVENTORY_RUNTIME_DIRNAME!r} "
            f"runtime root, not {runtime}; pass --program-lock-digest for a program runtime"
        )
    receipts = []
    for entry in load_registry().get("adapters") or []:
        if entry.get("status") == "non_routable":
            continue
        adapter_id = str(entry["adapter_id"])
        adapter = instantiate(adapter_id, runtime)
        receipt = adapter.probe(
            ProbeContext(
                repository_root=str(repository_root()),
                runtime_root=str(runtime),
                program_lock_digest=digest,
            )
        )
        receipts.append(receipt.to_dict())
    status_counts: dict[str, int] = {}
    for receipt in receipts:
        status = str(receipt["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    payload = {
        "schema": "program-execution-adapter.probe-report.v1",
        # The report is the inventory; it is not a PASS unless every routable
        # adapter answered PASS or an honest BLOCKED. A FAIL receipt is a FAIL.
        "status": "FAIL" if status_counts.get("FAIL") else "PASS",
        "runtime_root": str(runtime),
        "program_lock_digest": digest,
        "program_lock_binding": binding_kind,
        "status_counts": status_counts,
        "receipts": receipts,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
