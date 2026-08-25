from __future__ import annotations

import unittest
from dataclasses import asdict

from autonomy.readiness import action_readiness

from autonomy.models import ActionRuntime, ActionSpec, CampaignState, ResourceLock


class SchedulerAuthoritySemanticsTests(unittest.TestCase):
    """RC-06: the scheduler carries no pseudo-authority.

    Mutation authority is the separately enforced Root Autonomy grant at
    dispatch time; an `authority_granted` flag on the action graph was never
    that grant and must not exist or gate readiness.
    """

    def _spec(self, raw_extra: dict | None = None) -> ActionSpec:
        raw = {
            "action_id": "fix-a",
            "objective": "Fix PR A",
            "resources": [{"key": "repo:quantum/a", "mode": "write"}],
            "mutation": True,
            **(raw_extra or {}),
        }
        return ActionSpec.from_dict(raw)

    def test_action_spec_has_no_authority_field(self) -> None:
        spec = self._spec()
        self.assertFalse(hasattr(spec, "authority_granted"))
        self.assertNotIn("authority_granted", asdict(spec))

    def test_legacy_authority_flag_never_gates_readiness(self) -> None:
        # A stale graph carrying the retired flag (even false) is not an
        # authority denial: readiness is dependency/precondition truth only.
        spec = self._spec({"authority_granted": False})
        state = CampaignState(
            campaign_id="campaign",
            objective="Converge",
            action_specs={"fix-a": spec},
            action_runtime={"fix-a": ActionRuntime()},
        )
        decision = action_readiness(state, "fix-a")
        self.assertTrue(decision.ready)
        self.assertNotEqual(decision.reason, "authority_not_granted")

    def test_preconditions_still_gate_readiness(self) -> None:
        spec = ActionSpec(
            action_id="fix-a",
            objective="Fix PR A",
            resources=(ResourceLock("repo:quantum/a", "write"),),
            mutation=True,
            preconditions_satisfied=False,
        )
        state = CampaignState(
            campaign_id="campaign",
            objective="Converge",
            action_specs={"fix-a": spec},
            action_runtime={"fix-a": ActionRuntime()},
        )
        decision = action_readiness(state, "fix-a")
        self.assertFalse(decision.ready)
        self.assertEqual(decision.reason, "preconditions_not_satisfied")


if __name__ == "__main__":
    unittest.main()
