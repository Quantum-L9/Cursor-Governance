from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def probe_programs(program_home: str | Path) -> dict[str, Any]:
    root = Path(program_home).expanduser().resolve()
    if not root.is_dir():
        return {"active_programs": 0, "programs": []}
    programs = []
    for status_path in sorted(root.glob("*/status/PROGRAM_STATUS.json")):
        value = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            programs.append(value)
    return {"active_programs": len(programs), "programs": programs}
