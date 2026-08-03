from __future__ import annotations

from pathlib import Path
from typing import Any


def download_declared(
    transport,
    contract: dict[str, Any],
    run_id: int,
    destination: Path,
) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    collected = []
    for name in contract.get("artifact_names") or []:
        result = transport.run(
            [
                "run",
                "download",
                str(run_id),
                "--repo",
                str(contract["repository"]),
                "--name",
                str(name),
                "--dir",
                str(destination / str(name)),
            ],
            timeout_seconds=300,
        )
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or f"artifact download failed: {name}")
        collected.append(str(destination / str(name)))
    return collected
