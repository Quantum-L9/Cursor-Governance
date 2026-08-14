from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomy.state_store import StateStore

from autonomy.models import ActionRuntime, ActionSpec, CampaignState


class StateStoreTests(unittest.TestCase):
    def test_round_trip_and_digest_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(tmp)
            state = CampaignState(
                "campaign-1",
                "Do the work",
                {"a": ActionSpec(action_id="a", objective="A")},
                {"a": ActionRuntime()},
            )
            path = store.save(state)
            loaded = store.load("campaign-1")
            self.assertEqual(loaded.state_digest, state.state_digest)
            self.assertEqual(loaded.objective, "Do the work")

            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["objective"] = "tampered"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                store.load("campaign-1")

    def test_checkpoint_persists_next_action_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            state = CampaignState(
                "campaign-2",
                "Checkpoint",
                {"a": ActionSpec(action_id="a", objective="A")},
                {"a": ActionRuntime()},
            )
            store.checkpoint(
                state,
                action_id="a",
                evidence={"exit_code": 0},
                next_action_set=["b", "c"],
            )
            loaded = store.load("campaign-2")
            self.assertEqual(loaded.checkpoints[0]["next_action_set"], ["b", "c"])


if __name__ == "__main__":
    unittest.main()
