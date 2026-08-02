from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta

from autonomy.claim_lease import LeaseConflict, LeaseStore


class LeaseStoreTests(unittest.TestCase):
    def test_conflict_renew_and_expiry_reclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LeaseStore(tmp)
            now = datetime(2026, 8, 1, tzinfo=UTC)
            first = store.acquire(
                campaign_id="c",
                action_id="a",
                holder_agent_id="claude-code",
                ttl=timedelta(hours=1),
                now=now,
            )
            self.assertEqual(first.holder_agent_id, "claude-code")
            with self.assertRaises(LeaseConflict):
                store.acquire(
                    campaign_id="c",
                    action_id="a",
                    holder_agent_id="codex",
                    ttl=timedelta(hours=1),
                    now=now + timedelta(minutes=1),
                )
            renewed = store.renew(
                campaign_id="c",
                action_id="a",
                holder_agent_id="claude-code",
                ttl=timedelta(hours=2),
                now=now + timedelta(minutes=30),
            )
            self.assertGreater(renewed.expires_at, first.expires_at)
            reclaimed = store.acquire(
                campaign_id="c",
                action_id="a",
                holder_agent_id="codex",
                ttl=timedelta(hours=1),
                now=now + timedelta(hours=3),
            )
            self.assertEqual(reclaimed.holder_agent_id, "codex")

    def test_ttl_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LeaseStore(tmp)
            with self.assertRaises(ValueError):
                store.acquire(
                    campaign_id="c",
                    action_id="a",
                    holder_agent_id="claude-code",
                    ttl=timedelta(hours=25),
                )


if __name__ == "__main__":
    unittest.main()
