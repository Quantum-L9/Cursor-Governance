from __future__ import annotations

from workflows.dags.intelligence_harvest.state import HarvestState


def route_after_render_output(state: HarvestState) -> str:
    status = str(state.get("status") or "")
    if status in ["PASS", "PARTIAL", "BLOCKED", "FAIL"]:
        return status
    if state.get("errors"):
        return "FAIL" if "FAIL" in ["PASS", "PARTIAL", "BLOCKED", "FAIL"] else "FAIL"
    if state.get("blocked"):
        return "BLOCKED" if "BLOCKED" in ["PASS", "PARTIAL", "BLOCKED", "FAIL"] else "FAIL"
    if state.get("unknowns"):
        return "PARTIAL" if "PARTIAL" in ["PASS", "PARTIAL", "BLOCKED", "FAIL"] else "PASS"
    return "PASS"
