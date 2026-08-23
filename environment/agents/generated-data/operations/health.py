from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from module_loader import PriorWaveModuleLoader
from receipts import ProcessingReceiptChain
from state_store import PipelineStateStore

HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
UNHEALTHY = "UNHEALTHY"
MISCONFIGURED = "MISCONFIGURED"


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    message: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
        }


def run_health(
    *,
    repository_root: str | Path,
    database_path: str | Path,
    live: bool,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    store = PipelineStateStore(database_path)
    checks: list[HealthCheck] = []
    generated_data = root / "environment" / "agents" / "generated-data"
    required = [
        generated_data / "law" / "SUBAGENT_GENERATED_DATA_LAW.md",
        generated_data / "runtime" / "packet_validator.py",
        generated_data / "adapters" / "graphiti_memory.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    checks.append(
        HealthCheck(
            "required_files",
            HEALTHY if not missing else MISCONFIGURED,
            "Required files present" if not missing else "Required files missing",
            {"missing": missing},
        )
    )
    loader_errors = PriorWaveModuleLoader(root).validate_required_symbols()
    checks.append(
        HealthCheck(
            "prior_wave_imports",
            HEALTHY if not loader_errors else UNHEALTHY,
            "Prior-wave symbols load" if not loader_errors else "Prior-wave import failures",
            {"errors": loader_errors},
        )
    )
    status = store.pipeline_status()
    checks.append(
        HealthCheck(
            "state_store",
            HEALTHY,
            "SQLite state store available",
            status,
        )
    )
    chain = ProcessingReceiptChain(store)
    chain_errors: dict[str, list[str]] = {}
    with store.connect() as connection:
        job_rows = list(connection.execute("SELECT job_id FROM processing_jobs"))
    for row in job_rows:
        errors = chain.verify_job_chain(row["job_id"])
        if errors:
            chain_errors[row["job_id"]] = errors
    checks.append(
        HealthCheck(
            "receipt_integrity",
            HEALTHY if not chain_errors else UNHEALTHY,
            "Receipt chains valid" if not chain_errors else "Receipt chain failures",
            {"errors": chain_errors},
        )
    )
    transport_configured = any(
        os.environ.get(name)
        for name in (
            "L9_SGD_GRAPHITI_INGEST_COMMAND",
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "L9_SGD_GRAPHITI_HYDRATE_COMMAND",
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
        )
    )
    checks.append(
        HealthCheck(
            "live_transport_configuration",
            (HEALTHY if transport_configured else DEGRADED),
            (
                "At least one live Graphiti operation configured"
                if transport_configured
                else "Only local/outbox operation is configured"
            ),
            {},
        )
    )
    if live:
        for variable in (
            "L9_SGD_GRAPHITI_INGEST_COMMAND",
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "L9_SGD_GRAPHITI_HYDRATE_COMMAND",
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
        ):
            raw = os.environ.get(variable, "").strip()
            if not raw:
                checks.append(
                    HealthCheck(
                        f"live:{variable}",
                        MISCONFIGURED,
                        f"{variable} is not configured",
                        {},
                    )
                )
                continue
            command = shlex.split(raw)
            available = bool(command) and (
                Path(command[0]).exists() or __import__("shutil").which(command[0]) is not None
            )
            checks.append(
                HealthCheck(
                    f"live:{variable}",
                    HEALTHY if available else UNHEALTHY,
                    "Command executable available"
                    if available
                    else "Command executable unavailable",
                    {"command": command},
                )
            )
    rank = {
        HEALTHY: 0,
        DEGRADED: 1,
        UNHEALTHY: 2,
        MISCONFIGURED: 3,
    }
    overall = max(
        (check.status for check in checks),
        key=lambda item: rank[item],
        default=HEALTHY,
    )
    return {
        "status": overall,
        "checks": [check.to_dict() for check in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check generated-data pipeline health.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    database = args.database or root / ".l9" / "subagent-generated-data" / "pipeline.sqlite3"
    result = run_health(
        repository_root=root,
        database_path=database,
        live=args.live,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Status: {result['status']}")
        for check in result["checks"]:
            print(f"- {check['status']}: {check['name']} — {check['message']}")
    return {
        HEALTHY: 0,
        DEGRADED: 1,
        UNHEALTHY: 2,
        MISCONFIGURED: 3,
    }[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
