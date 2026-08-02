from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))


def redact(value: Any) -> Any:
    sensitive = {
        "token",
        "secret",
        "password",
        "authorization",
        "api_key",
        "private_key",
    }
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if key.lower() in sensitive else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main() -> int:
    raise SystemExit(
        "dead_letter CLI disabled (Sonar S8707); use PipelineStateStore dead-letter APIs"
    )


if __name__ == "__main__":
    raise SystemExit(main())
