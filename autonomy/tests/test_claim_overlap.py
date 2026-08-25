"""Canonical resource-key overlap semantics (PHASE-6 part A).

One overlap rule, three enforcement points: the transactional ClaimRegistry,
the Scheduler admission prefilter, and the graph linter all call the same
primitive. These tests pin the mandated semantics:

- same exact path conflicts
- parent scope and child file conflict
- overlapping glob scopes conflict
- disjoint sibling files do not conflict
- opaque identical keys conflict
- opaque different keys do not conflict
- ambiguous mutation scope fails closed to the broader conflict
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomy.errors import PolicyViolation
from autonomy.runtime.claims import (
    ClaimRegistry,
    claim_scopes_conflict,
    resource_keys_overlap,
)
from autonomy.runtime.store import RuntimeStore


def _write_conflict(key_a: str, key_b: str) -> bool:
    return claim_scopes_conflict(
        key=key_a,
        mode="write",
        exclusive=True,
        other_key=key_b,
        other_mode="write",
        other_exclusive=True,
    )


class ResourceKeyOverlapTest(unittest.TestCase):
    def test_same_exact_path_conflicts(self) -> None:
        self.assertTrue(_write_conflict("docs/report.md", "docs/report.md"))
        self.assertTrue(_write_conflict("path:docs/report.md", "docs/report.md"))

    def test_parent_scope_and_child_file_conflict(self) -> None:
        self.assertTrue(_write_conflict("src", "src/module.py"))
        self.assertTrue(_write_conflict("src/**", "src/module.py"))
        self.assertTrue(_write_conflict("src/pkg/deep.py", "src"))

    def test_overlapping_glob_scope_conflicts(self) -> None:
        self.assertTrue(_write_conflict("src/**", "src/*.py"))
        self.assertTrue(_write_conflict("**", "docs/report.md"))
        self.assertTrue(_write_conflict("src/*/handlers.py", "src/api/handlers.py"))

    def test_disjoint_sibling_files_do_not_conflict(self) -> None:
        self.assertFalse(_write_conflict("docs/a.md", "docs/b.md"))
        self.assertFalse(_write_conflict("src/**", "docs/**"))
        self.assertFalse(resource_keys_overlap("src/a.py", "src/b.py"))

    def test_opaque_identical_key_conflicts(self) -> None:
        self.assertTrue(_write_conflict("target-lineage:TARGET-001", "target-lineage:TARGET-001"))
        self.assertTrue(_write_conflict("repository:declared", "repository:declared"))

    def test_opaque_different_key_does_not_conflict(self) -> None:
        self.assertFalse(_write_conflict("target-lineage:TARGET-001", "target-lineage:TARGET-002"))
        self.assertFalse(resource_keys_overlap("repository:declared", "target-lineage:TARGET-001"))

    def test_ambiguous_mutation_scope_fails_closed(self) -> None:
        # Absolute, escaping, and empty scopes cannot be parsed as repository
        # content; they must collide with every path-scoped write.
        self.assertTrue(_write_conflict("path:", "docs/a.md"))
        self.assertTrue(_write_conflict("/etc/passwd", "docs/a.md"))
        self.assertTrue(_write_conflict("../outside", "docs/a.md"))

    def test_read_read_same_scope_does_not_conflict(self) -> None:
        self.assertFalse(
            claim_scopes_conflict(
                key="docs/a.md",
                mode="read",
                exclusive=False,
                other_key="docs",
                other_mode="read",
                other_exclusive=False,
            )
        )


class RegistryOverlapTest(unittest.TestCase):
    """The transactional registry rejects overlapping scopes, not just equal keys."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = RuntimeStore(Path(self._tmp.name) / "runtime.sqlite3")
        self.registry = ClaimRegistry(self.store)

    def _hold(self, key: str, *, action: str = "action-a") -> None:
        with self.store.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO campaigns (
                    campaign_id, graph_id, state, base_sha, campaign_json,
                    graph_json, created_at, updated_at
                ) VALUES ('camp-1', 'graph-1', 'EXECUTING', 'aaaaaaaa', '{}',
                          '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO actions (
                    campaign_id, action_id, role, kind, status, mutation,
                    resource_class, priority_weight, critical_depth,
                    action_json, created_at, updated_at
                ) VALUES ('camp-1', ?, 'executor', 'work', 'LEASED', 1,
                          'repository_mutation', 1.0, 1, '{}',
                          '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
                """,
                (action,),
            )
            connection.execute(
                """
                INSERT INTO leases (
                    lease_id, campaign_id, graph_id, action_id, agent_id, role,
                    capability_id, base_sha, status, issued_at, expires_at,
                    last_heartbeat_at, metadata_json
                ) VALUES (?, 'camp-1', 'graph-1', ?, 'agent-a', 'executor',
                          ?, 'aaaaaaaa', 'ACTIVE', '2026-01-01T00:00:00Z',
                          '2026-01-01T01:00:00Z', '2026-01-01T00:00:00Z', '{}')
                """,
                (f"lease-{action}", action, f"cap-{action}"),
            )
            self.registry.create_claims(
                connection,
                lease_id=f"lease-{action}",
                campaign_id="camp-1",
                action_id=action,
                claims=[{"key": key, "mode": "write"}],
            )

    def _assert_denied(self, key: str) -> None:
        with self.store.transaction() as connection:
            with self.assertRaises(PolicyViolation):
                self.registry.assert_available(
                    connection,
                    campaign_id="camp-1",
                    claims=[{"key": key, "mode": "write"}],
                )

    def _assert_allowed(self, key: str) -> None:
        with self.store.transaction() as connection:
            self.registry.assert_available(
                connection,
                campaign_id="camp-1",
                claims=[{"key": key, "mode": "write"}],
            )

    def test_parent_scope_blocks_child_file(self) -> None:
        self._hold("src/**")
        self._assert_denied("src/module.py")

    def test_child_file_blocks_parent_scope(self) -> None:
        self._hold("src/module.py")
        self._assert_denied("src")

    def test_disjoint_scopes_admit_concurrently(self) -> None:
        self._hold("src/**")
        self._assert_allowed("docs/**")

    def test_exact_opaque_key_still_blocks(self) -> None:
        self._hold("repository:declared")
        self._assert_denied("repository:declared")


if __name__ == "__main__":
    unittest.main()
