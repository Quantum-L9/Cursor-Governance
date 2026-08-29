from __future__ import annotations

from typing import TypedDict


class HarvestState(TypedDict, total=False):
    status: str
    unknowns: list[str]
    errors: list[str]
    ran: list[str]
    blocked: bool
