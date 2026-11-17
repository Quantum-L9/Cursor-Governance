#!/usr/bin/env python3
"""Planner mode — opt-in, session-bound binding of the strategic-planning projections.

Binds the six required domain projections of l9.domain-consumer-binding/strategic-planner@1
(strategic-value, architecture, signals, governance, evidence-provenance,
capabilities-dependencies; Quantum-L9/.github v3.36.0, ADR-033) plus the Plan Keeper context
role projection l9.projection/strategic-planning-context@2 (v3.35.0, ADR-032), read-only. A
sibling of architect mode and CTO mode; it drives skills/l9-strategic-plan and never confers
Strategic Authority over the Plan.

Contract: governance/planner-mode/MODE.yaml (`l9.cursor-governance.planner-mode/v1`).
State: <workspace>/.l9/planner-mode/session.json (`l9.planner-mode-session/v1`).
Entrypoint: commands/planner.md. The implementation is ops/autonomy/projection_mode.py.

Commands: on | off | status. Exit codes: 0 ACTIVE or OFF, 3 BLOCKED, 1 REJECTED or STALE.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from projection_mode import (  # noqa: E402
    ADMITTED,
    REPO,
    SESSION_ENVS,
    ContractError,
    ProjectionMode,
    resolve_session_id,
)

MODE = ProjectionMode("planner")
MODE_CONTRACT = MODE.contract
STATE_REL = MODE.state_rel
load_contract = MODE.load_contract
evaluate = MODE.evaluate
request = MODE.request
release = MODE.release
state_path = MODE.state_path
main = MODE.main

__all__ = [
    "ADMITTED",
    "MODE",
    "MODE_CONTRACT",
    "REPO",
    "SESSION_ENVS",
    "STATE_REL",
    "ContractError",
    "evaluate",
    "load_contract",
    "main",
    "release",
    "request",
    "resolve_session_id",
    "state_path",
]

if __name__ == "__main__":
    sys.exit(main())
