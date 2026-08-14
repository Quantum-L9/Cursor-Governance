from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autonomy.bootstrap import compile_context
from autonomy.state_store import StateStore

from autonomy.models import ActionRuntime, ActionSpec, CampaignState, ResourceLock


class BootstrapTests(unittest.TestCase):
    def test_compiles_active_campaign_and_next_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = StateStore(workspace / ".l9" / "autonomy")
            state = CampaignState(
                "campaign",
                "Parallel inspection",
                {
                    "a": ActionSpec(
                        action_id="a",
                        objective="A",
                        resources=(ResourceLock("service:github", "read"),),
                    ),
                    "b": ActionSpec(
                        action_id="b",
                        objective="B",
                        resources=(ResourceLock("service:github", "read"),),
                    ),
                },
                {"a": ActionRuntime(), "b": ActionRuntime()},
            )
            store.save(state)
            env = {
                "L9_AUTONOMY_ENABLED": "true",
                "L9_AUTONOMY_STATE_DIR": ".l9/autonomy",
                "L9_AUTONOMY_MAX_PARALLEL": "4",
                "L9_AUTONOMY_MAX_MUTATION_LANES": "2",
            }
            with patch.dict(os.environ, env, clear=False):
                context = compile_context(workspace)
            self.assertEqual(context["campaign_id"], "campaign")
            self.assertEqual(context["next_action_set"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
