#!/usr/bin/env python3
"""Architect mode — opt-in, session-bound binding of the architecture and strategic-planning
domain projections.

Binds seven admitted Quantum-L9/.github domain projections (v3.36.0, ADR-033): the required
set of l9.domain-consumer-binding/gar@1 (architecture, governance, evidence-provenance,
contracts-conformance, capabilities-dependencies) plus what
l9.domain-consumer-binding/strategic-planner@1 adds (strategic-value, signals). It is not the
default operating plane and it replaces invoking /l9-global-architect for architectural
context.

Contract: governance/architect-mode/MODE.yaml (`l9.cursor-governance.architect-mode/v1`).
State: <workspace>/.l9/architect-mode/session.json (`l9.architect-mode-session/v1`).
Entrypoint: commands/architect.md. The implementation is ops/autonomy/projection_mode.py.

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

MODE = ProjectionMode("architect")
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
