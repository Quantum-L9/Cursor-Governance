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


def _default_lock_digest() -> str:
    value = os.environ.get("L9_PROGRAM_LOCK_DIGEST")
    if value:
        return value
    return hashlib.sha256(b"program-execution-adapter-probe").hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=_default_runtime())
    parser.add_argument(
        "--program-lock-digest",
        default=_default_lock_digest(),
    )
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
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
                program_lock_digest=args.program_lock_digest,
            )
        )
        receipts.append(receipt.to_dict())
    status_counts: dict[str, int] = {}
    for receipt in receipts:
        status = str(receipt["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    payload = {
        "schema": "program-execution-adapter.probe-report.v1",
        "status": "PASS",
        "runtime_root": str(runtime),
        "status_counts": status_counts,
        "receipts": receipts,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
