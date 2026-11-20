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
Entrypoint: commands/planner.md. Everything is delegated to ops/autonomy/projection_mode.py;
read the bound callables from MODE (MODE.evaluate, MODE.request, MODE.release, ...).

Commands: on | off | status. Exit codes: 0 ACTIVE or OFF, 3 BLOCKED, 1 REJECTED or STALE.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import projection_mode  # noqa: E402

MODE = projection_mode.ProjectionMode("planner")

if __name__ == "__main__":
    sys.exit(MODE.main())
