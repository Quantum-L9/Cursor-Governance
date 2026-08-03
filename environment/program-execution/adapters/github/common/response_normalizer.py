from __future__ import annotations

import json
from typing import Any


def parse_json(value: str) -> Any:
    if not value.strip():
        return None
    return json.loads(value)
