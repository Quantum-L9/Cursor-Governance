"""A worker receives the bound projection only when its task contract asks for it.

Every campaign is still bound to its execution projection at bootstrap
(CANONICAL_LAW PROGRAM_EXECUTION_MANUAL_STAGE_V1 item 6), and the binding is
re-verified on every dispatch. What changed is the hand-off: the projection's
views used to be pasted whole into every worker prompt, costing turns and
tokens on tasks that never use them. A task now opts in with
`projection_context: true`; otherwise its worker gets the contract alone.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_campaign_projection_opt_in", SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load_runner()
PROJECTION = {"schema": "l9.peer-execution.projection-context.v1", "views": [{"path": "v"}]}


class _FrontDoor(SimpleNamespace):
    SAFE_BEFORE_DISPATCH = "SAFE_BEFORE_DISPATCH"

    class RetryReceiptUnrecorded(Exception):
        pass

    def __init__(self) -> None:
        super().__init__(requests=[])

    def PeerExecutionRequest(self, **fields):  # noqa: N802 - mirrors the real dataclass
        return SimpleNamespace(**fields)

    def execute(self, request):
        self.requests.append(request)
        return {"status": "PASS", "dispatch_id": "d-1"}


def _dispatch(contract: dict) -> tuple[SimpleNamespace, list[int]]:
    front_door = _FrontDoor()
    verified: list[int] = []

    def _bound(_workspace):
        verified.append(1)
        return dict(PROJECTION)

    with (
        patch.object(RUNNER, "_peer_pipeline", lambda: front_door),
        patch.object(RUNNER, "bound_projection_context", _bound),
        patch.object(RUNNER, "_peer_identity", lambda: ("claude-code", "claude-code-cli", None)),
        patch.object(RUNNER, "_live_controller_attempt", lambda *_: None),
    ):
        RUNNER._run_peer_execution(Path("/nonexistent"), contract, autonomy_authority={})
    return front_door.requests[0], verified


class ProjectionOptInTests(unittest.TestCase):
    def test_a_contract_without_the_flag_gets_no_projection(self) -> None:
        request, verified = _dispatch({"task_id": "TASK-001"})
        self.assertIsNone(request.projection)
        self.assertEqual(verified, [1], "the binding is still verified on every dispatch")

    def test_a_false_flag_gets_no_projection(self) -> None:
        request, _ = _dispatch({"task_id": "TASK-001", "projection_context": False})
        self.assertIsNone(request.projection)

    def test_an_opted_in_contract_gets_the_bound_projection(self) -> None:
        request, _ = _dispatch({"task_id": "TASK-001", "projection_context": True})
        self.assertEqual(request.projection, PROJECTION)

    def test_a_truthy_non_boolean_does_not_opt_in(self) -> None:
        request, _ = _dispatch({"task_id": "TASK-001", "projection_context": "yes"})
        self.assertIsNone(request.projection)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
