"""Replan semantic revision projection conformance (TASK-004).

Proves the canonical projection seam accounts for every registered peer under
one semantic revision digest, that unsupported peers fail closed explicitly,
and that partial semantic revision activation is impossible.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from peer_execution.replan_projection import (
    applicable_peers,
    build_semantic_revision,
    project_to_peers,
    verify_projection,
)

sys.dont_write_bytecode = True  # keep PE tree free of compiled debris

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent.parent
BINDINGS_PATH = REPO_ROOT / "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
CONTRACT = ROOT / "core/shared/REPLAN_CONTRACT.yaml"
SCHEMA = ROOT / "core/shared/schemas/replan-revision.schema.json"

ACTOR = "controller"
SEMANTIC_KWARGS = {
    "replan_revision_id": "rev-1",
    "plan_revision": "plan-rev-0+rev-1",
    "activated_at": "2026-08-14T22:00:00+00:00",
    "actor": ACTOR,
}


class ReplanProjectionTests(unittest.TestCase):
    def test_semantic_revision_is_digest_bound(self) -> None:
        semantic = build_semantic_revision(CONTRACT, SCHEMA, **SEMANTIC_KWARGS)
        self.assertEqual(semantic["schema"], "program-execution.replan.semantic-revision.v1")
        self.assertEqual(semantic["contract_digest"], _sha256(CONTRACT))
        self.assertEqual(semantic["revision_schema_digest"], _sha256(SCHEMA))
        self.assertIn("sha256:", semantic["semantic_revision_digest"])
        # Mutating any identity field changes the revision digest.
        rebuilt = build_semantic_revision(
            CONTRACT, SCHEMA, **dict(SEMANTIC_KWARGS, replan_revision_id="rev-2")
        )
        self.assertNotEqual(
            rebuilt["semantic_revision_digest"], semantic["semantic_revision_digest"]
        )

    def test_every_registered_peer_is_accounted_for(self) -> None:
        semantic = build_semantic_revision(CONTRACT, SCHEMA, **SEMANTIC_KWARGS)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            accounting = project_to_peers(
                REPO_ROOT, workspace, semantic_revision=semantic, actor=ACTOR
            )
            self.assertEqual(accounting["status"], "ACTIVE")
            digests = {record["semantic_revision_digest"] for record in accounting["records"]}
            self.assertEqual(len(digests), 1)
            self.assertIn(semantic["semantic_revision_digest"], digests)
            self.assertTrue(
                (workspace / "runtime/projection/replan-semantic-revision.json").is_file()
            )
            self.assertTrue((workspace / "runtime/projection/peer-accounting.json").is_file())
            verification = verify_projection(REPO_ROOT, workspace)
            self.assertEqual(verification["status"], "ACTIVE")

    def test_unsupported_peer_fails_closed_and_blocks_activation(self) -> None:
        bindings = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
        peers = dict(bindings["peers"])
        peers["legacy-bot"] = {"agent_ref": "legacy-bot"}  # no execution bindings
        peers = dict(peers)
        doc = dict(bindings, peers=peers)
        semantic = build_semantic_revision(CONTRACT, SCHEMA, **SEMANTIC_KWARGS)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            with mock.patch(
                "peer_execution.replan_projection.load_peer_bindings", return_value=doc
            ):
                accounting = project_to_peers(
                    REPO_ROOT, workspace, semantic_revision=semantic, actor=ACTOR
                )
            self.assertEqual(accounting["status"], "BLOCKED")
            legacy = next(r for r in accounting["records"] if r["peer_id"] == "legacy-bot")
            self.assertEqual(legacy["capability"], "unsupported")
            self.assertTrue(legacy["fail_closed"])

    def test_partial_activation_is_detected_on_verification(self) -> None:
        semantic = build_semantic_revision(CONTRACT, SCHEMA, **SEMANTIC_KWARGS)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            project_to_peers(REPO_ROOT, workspace, semantic_revision=semantic, actor=ACTOR)
            bindings = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
            peers = dict(bindings["peers"])
            # A newly registered peer with no accounting yet must block promotion.
            peers["new-peer"] = dict(peers["cursor"], agent_ref="new-peer")
            doc = dict(bindings, peers=peers)
            with mock.patch(
                "peer_execution.replan_projection.load_peer_bindings", return_value=doc
            ):
                verification = verify_projection(REPO_ROOT, workspace)
            self.assertEqual(verification["status"], "BLOCKED")
            self.assertIn("missing peer accounting: new-peer", verification["reason"])

    def test_applicable_peer_set_matches_registry(self) -> None:
        bindings = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
        peers = applicable_peers(bindings)
        declared = set(bindings["peers"])
        self.assertEqual(set(peers), declared)
        for spec in peers.values():
            self.assertEqual(spec["capability"], "supported")
            self.assertFalse(spec["fail_closed"])


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
