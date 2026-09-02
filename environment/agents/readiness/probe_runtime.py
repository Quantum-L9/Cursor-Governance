#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from environment.agents.readiness.compose import execution_ready  # noqa: E402


def _cursor_deployment_ready(root: Path) -> bool:
    from environment.agents.deployment.receipts import (
        DeploymentNotReady,
        require_cursor_deployment_ready,
    )

    try:
        require_cursor_deployment_ready(root, root)
    except (DeploymentNotReady, OSError, ValueError):
        return False
    return True


def main() -> int:
    dims = {
        "IDENTITY_READY": (ROOT / "environment/agents/agent_registry.yaml").is_file(),
        "PROGRAM_EXECUTION_READY": (ROOT / "environment/program-execution").is_dir(),
        "AUTONOMY_READY": True,
        "DEPLOYMENT_READY": _cursor_deployment_ready(ROOT),
        "RESULT_INGRESS_READY": (ROOT / "environment/agents/results/gateway.py").is_file(),
        "DATA_CAPTURE_READY": (
            ROOT / "environment/agents/generated-data/ingress/ingest.py"
        ).is_file(),
        "DATA_DELIVERY_READY": True,
    }
    report = execution_ready(dims)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "EXECUTION_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
