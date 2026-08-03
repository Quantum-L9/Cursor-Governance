from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def task_request(
    deployment: Mapping[str, Any],
    *,
    run_in_background: bool,
) -> dict[str, Any]:
    task = dict(deployment)
    task["run_in_background"] = run_in_background
    task["transport"] = "program_runtime_filesystem"
    return task
