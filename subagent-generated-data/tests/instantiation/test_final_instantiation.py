from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
ROOT = TEST_FILE.parents[3]
ORCHESTRATION = BASE / "orchestration"
RETRIEVAL = BASE / "retrieval"
INVALIDATION = BASE / "invalidation"
INTEGRATION = BASE / "integration"
for path in (
    ORCHESTRATION,
    RETRIEVAL,
    INVALIDATION,
    INTEGRATION,
):
    sys.path.insert(0, str(path))
from context_query import (
    ContextBudget,
    ContextCandidate,
    ContextQuery,
    StaticContextClient,
)
from context_selector import ContextSelector
from end_to_end_golden import run_golden
from repository_event_bridge import (
    normalize_relative_path,
    parse_name_status,
)
from reuse_recorder import ReuseRecorder
from state_store import PipelineStateStore


class FinalInstantiationTests(unittest.TestCase):
    def test_context_budget_is_enforced(self) -> None:
        query = ContextQuery(
            repository="r",
            repository_class="l9_python",
            campaign_id="c",
            action_id="a",
            agent_id="g",
            role="verifier",
            task_type="test",
            paths=("src/a.py",),
            base_sha="abc1234",
            visibility_ceiling="repository_local",
            budget=ContextBudget(
                max_items=1,
                max_characters=10,
            ),
        )
        candidates = [
            ContextCandidate(
                record_id="one",
                text="12345",
                score=1,
                confidence=1,
                state="active",
                authority_class="advisory",
                visibility="repository_local",
                repository="r",
                source_sha="abc1234",
                paths=("src/a.py",),
                task_types=("test",),
                roles=("verifier",),
                epistemic_status="observed",
                invalidated=False,
            ),
            ContextCandidate(
                record_id="two",
                text="67890",
                score=0.9,
                confidence=1,
                state="active",
                authority_class="advisory",
                visibility="repository_local",
                repository="r",
                source_sha="abc1234",
                paths=("src/a.py",),
                task_types=("test",),
                roles=("verifier",),
                epistemic_status="observed",
                invalidated=False,
            ),
        ]
        result = ContextSelector().select(
            query=query,
            result=StaticContextClient(candidates).query(query),
        )
        self.assertEqual(len(result.selected), 1)

    def test_contested_memory_is_excluded(self) -> None:
        query = ContextQuery(
            repository="r",
            repository_class="l9_python",
            campaign_id="c",
            action_id="a",
            agent_id="g",
            role="verifier",
            task_type="test",
            paths=(),
            base_sha="abc1234",
            visibility_ceiling="repository_local",
            budget=ContextBudget(),
        )
        candidate = ContextCandidate(
            record_id="contested",
            text="x",
            score=1,
            confidence=1,
            state="active",
            authority_class="advisory",
            visibility="repository_local",
            repository="r",
            source_sha="abc1234",
            paths=(),
            task_types=(),
            roles=(),
            epistemic_status="contested",
            invalidated=False,
        )
        result = ContextSelector().select(
            query=query,
            result=StaticContextClient([candidate]).query(query),
        )
        self.assertEqual(result.record_ids, ())

    def test_reuse_is_not_remote_before_finalization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = PipelineStateStore(Path(temp) / "pipeline.sqlite3")
            recorder = ReuseRecorder(store)
            selected = recorder.record_selection(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                payload={},
            )
            injected = recorder.record_injection(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                payload={},
            )
            self.assertFalse(selected.remote_dispatched)
            self.assertFalse(injected.remote_dispatched)

    def test_stale_reuse_creates_candidate_not_direct_action(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = PipelineStateStore(Path(temp) / "pipeline.sqlite3")
            result = ReuseRecorder(store).finalize_outcome(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                outcome="stale",
                correction_required=True,
                validity_confirmed=False,
                evidence={},
            )
            self.assertIsNotNone(result.invalidation_candidate)
            self.assertTrue(result.invalidation_candidate["requires_policy_approval"])

    def test_path_normalization_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            normalize_relative_path("../secret")
        with self.assertRaises(ValueError):
            normalize_relative_path("/absolute")
        self.assertEqual(
            normalize_relative_path("src/a.py"),
            "src/a.py",
        )

    def test_git_name_status_parsing(self) -> None:
        changes = parse_name_status("M\tsrc/a.py\nA\ttests/test_a.py\nR100\told.py\tnew.py\n")
        self.assertEqual(len(changes), 3)
        self.assertEqual(
            changes[2].change_kind,
            "renamed",
        )

    def test_mock_golden_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_golden(
                mode="mock",
                database=Path(temp) / "pipeline.sqlite3",
                repository_root=ROOT,
            )
        self.assertTrue(result["pipeline_passed"])
        self.assertTrue(result["retrieval_proven"])
        self.assertTrue(result["reuse_proven"])
        self.assertTrue(result["receipt_integrity_proven"])

    def test_outbox_does_not_claim_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_golden(
                mode="outbox",
                database=Path(temp) / "pipeline.sqlite3",
                repository_root=ROOT,
            )
        self.assertTrue(result["pipeline_passed"])
        self.assertFalse(result["destination_acceptance_proven"])
        self.assertFalse(result["full_compounding_loop_proven"])


if __name__ == "__main__":
    unittest.main()
