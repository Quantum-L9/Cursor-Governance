# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/deployment/tests/test_deployment.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Patch B deployment tests: idempotency, collisions, shadows, receipts."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from environment.agents.deployment import receipts as receipt_lib  # noqa: E402
from environment.agents.deployment import reconcile as reconcile_mod  # noqa: E402
from environment.agents.deployment import validate as validate_lib  # noqa: E402
from environment.agents.deployment.renderers import cursor as cursor_renderer  # noqa: E402


class DeploymentReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.home = self.root / "home"
        self.workspace = self.root / "workspace"
        self.runtime = self.root / "l9runtime"
        self.agents_dir = self.home / ".cursor" / "agents"
        self.workspace.mkdir(parents=True)
        self.home.mkdir(parents=True)
        self.runtime.mkdir(parents=True)
        self.agents_dir.mkdir(parents=True)
        self._prev_runtime = os.environ.get("L9_RUNTIME_ROOT")
        os.environ["L9_RUNTIME_ROOT"] = str(self.runtime)

    def tearDown(self) -> None:
        if self._prev_runtime is None:
            os.environ.pop("L9_RUNTIME_ROOT", None)
        else:
            os.environ["L9_RUNTIME_ROOT"] = self._prev_runtime
        self._tmpdir.cleanup()

    def _reconcile(self, **kwargs):
        return reconcile_mod.reconcile(
            surface="cursor",
            repo_root=REPO_ROOT,
            workspace=self.workspace,
            agents_dir=self.agents_dir,
            home=self.home,
            **kwargs,
        )

    def test_renders_five_managed_roles(self) -> None:
        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_READY)
        for filename in cursor_renderer.ROLE_FILENAMES.values():
            path = self.agents_dir / filename
            self.assertTrue(path.is_file(), filename)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(cursor_renderer.is_managed(text), filename)
            self.assertIn("name:", text.split("---", 2)[1])
            self.assertIn("model: inherit", text)
            # Cursor-supported frontmatter only — no custom L9 keys in YAML header.
            header = text.split("---", 2)[1]
            for forbidden in ("managed", "source_digest", "role_schema", "renderer_version"):
                self.assertNotIn(f"{forbidden}:", header)
            prov = cursor_renderer.parse_managed_provenance(text)
            assert prov is not None
            self.assertEqual(prov["managed"], "true")
            self.assertIn(prov["role"], cursor_renderer.ROLE_FILENAMES)

    def test_idempotency(self) -> None:
        first = self._reconcile()
        second = self._reconcile()
        self.assertEqual(first["status"], validate_lib.STATUS_READY)
        self.assertEqual(second["status"], validate_lib.STATUS_READY)
        self.assertEqual(first["rendered_digests"], second["rendered_digests"])
        for filename in cursor_renderer.ROLE_FILENAMES.values():
            text = (self.agents_dir / filename).read_text(encoding="utf-8")
            self.assertEqual(
                cursor_renderer.content_digest(text), first["rendered_digests"][filename]
            )
        # Second pass should not rewrite — only unchanged_managed / preserve ops.
        ops = {a["op"] for a in second["actions"]}
        self.assertIn("unchanged_managed", ops)
        self.assertNotIn("create_managed", ops)
        self.assertNotIn("replace_stale_managed", ops)

    def test_managed_collision_not_overwritten(self) -> None:
        collision = self.agents_dir / "l9-recon.md"
        original = "---\nname: l9-recon\ndescription: user owned\n---\n\nuser agent\n"
        collision.write_text(original, encoding="utf-8")

        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_BLOCKED)
        self.assertEqual(collision.read_text(encoding="utf-8"), original)
        reasons = {c.get("reason") for c in result["collisions"]}
        self.assertIn("unmanaged_name_collision", reasons)
        self.assertTrue(
            any(
                b.get("reason") == "unmanaged_name_collision"
                for b in result["validation"]["blocked"]
            )
        )

    def test_project_shadow_blocks(self) -> None:
        self._reconcile()
        project_agents = self.workspace / ".cursor" / "agents"
        project_agents.mkdir(parents=True)
        shadow = project_agents / "l9-recon.md"
        shadow.write_text(
            "---\nname: l9-recon\ndescription: project override\n---\n\nshadow\n",
            encoding="utf-8",
        )

        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_BLOCKED)
        blocked = result["validation"]["blocked"]
        self.assertTrue(
            any(b.get("reason") == "project_shadow_blocks_managed_role" for b in blocked),
            blocked,
        )
        # Global managed file remains intact.
        global_text = (self.agents_dir / "l9-recon.md").read_text(encoding="utf-8")
        self.assertTrue(cursor_renderer.is_managed(global_text))

    def test_project_shadow_matching_managed_is_ready(self) -> None:
        first = self._reconcile()
        self.assertEqual(first["status"], validate_lib.STATUS_READY)
        project_agents = self.workspace / ".cursor" / "agents"
        project_agents.mkdir(parents=True)
        expected = (self.agents_dir / "l9-recon.md").read_text(encoding="utf-8")
        (project_agents / "l9-recon.md").write_text(expected, encoding="utf-8")

        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_READY)
        shadows = result["validation"]["shadow_checks"]
        self.assertTrue(any(s.get("filename") == "l9-recon.md" and s.get("ok") for s in shadows))

    def test_non_l9_preservation_and_obsolete_managed_removal(self) -> None:
        user_agent = self.agents_dir / "my-custom-agent.md"
        user_agent.write_text(
            "---\nname: my-custom-agent\ndescription: personal\n---\n\nkeep me\n",
            encoding="utf-8",
        )
        obsolete = self.agents_dir / "l9-obsolete.md"
        obsolete.write_text(
            cursor_renderer.render_role(
                "recon",
                {
                    "autonomy_role": "recon",
                    "cursor_subagent_type": "explore",
                    "mutation": False,
                    "default_background": True,
                    "result_kind": "ReconReport",
                    "generated_data_role": "recon",
                    "responsibilities": ["x"],
                    "prohibited": ["y"],
                },
                source_rel="environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml",
                role_schema="l9.cursor-subagents.roles.v1",
                source_digest="deadbeef",
            ).replace("l9-recon", "l9-obsolete", 1),
            encoding="utf-8",
        )
        # Ensure obsolete still parses as managed after name tweak in body only —
        # keep provenance role as recon so marker remains valid.
        self.assertTrue(cursor_renderer.is_managed(obsolete.read_text(encoding="utf-8")))

        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_READY)
        self.assertTrue(user_agent.is_file())
        self.assertEqual(
            user_agent.read_text(encoding="utf-8"),
            "---\nname: my-custom-agent\ndescription: personal\n---\n\nkeep me\n",
        )
        self.assertFalse(obsolete.exists())
        ops = {a["op"] for a in result["actions"]}
        self.assertIn("preserve_unmanaged", ops)
        self.assertIn("remove_obsolete_managed", ops)

    def test_receipt_verification(self) -> None:
        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_READY)
        self.assertIsNotNone(result["receipt_path"])
        path = Path(result["receipt_path"]).resolve()
        self.assertTrue(path.is_file())
        expected_path = (
            self.runtime / "agents" / "deployments" / "cursor" / f"{result['workspace_id']}.json"
        ).resolve()
        self.assertEqual(path, expected_path)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["schema"], receipt_lib.RECEIPT_SCHEMA)
        self.assertTrue(receipt_lib.verify_receipt_digest(loaded))
        self.assertEqual(loaded["status"], validate_lib.STATUS_READY)
        self.assertEqual(loaded["surface"], "cursor")
        self.assertEqual(loaded["source_manifest_digest"], result["source_manifest_digest"])
        self.assertEqual(len(loaded["rendered_digests"]), 5)
        self.assertIn("effective_definition_checks", loaded)
        self.assertIn("shadow_checks", loaded)
        self.assertIn("observed_at", loaded)
        self.assertIn("governance_sha", loaded)

    def test_replace_stale_managed(self) -> None:
        stale = self.agents_dir / "l9-test.md"
        stale.write_text(
            cursor_renderer.render_role(
                "test",
                {
                    "autonomy_role": "executor",
                    "cursor_subagent_type": "generalPurpose",
                    "mutation": "bounded",
                    "default_background": True,
                    "result_kind": "TestReport",
                    "generated_data_role": "executor",
                    "responsibilities": ["old"],
                    "prohibited": ["old"],
                },
                source_rel="environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml",
                role_schema="l9.cursor-subagents.roles.v1",
                source_digest="0000000000000000000000000000000000000000000000000000000000000000",
            ),
            encoding="utf-8",
        )
        result = self._reconcile()
        self.assertEqual(result["status"], validate_lib.STATUS_READY)
        self.assertTrue(any(a["op"] == "replace_stale_managed" for a in result["actions"]))
        text = stale.read_text(encoding="utf-8")
        prov = cursor_renderer.parse_managed_provenance(text)
        assert prov is not None
        self.assertEqual(prov["source_digest"], result["source_manifest_digest"])

    def test_unsupported_surface_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reconcile_mod.reconcile(
                surface="claude-code",
                repo_root=REPO_ROOT,
                workspace=self.workspace,
                agents_dir=self.agents_dir,
            )

    def test_require_ready_after_reconcile(self) -> None:
        self._reconcile()
        loaded = receipt_lib.require_cursor_deployment_ready(self.workspace, REPO_ROOT)
        self.assertEqual(loaded["status"], validate_lib.STATUS_READY)

    def test_require_ready_missing_receipt(self) -> None:
        with self.assertRaises(receipt_lib.DeploymentNotReady):
            receipt_lib.require_cursor_deployment_ready(self.workspace, REPO_ROOT)

    def test_require_ready_blocked_status(self) -> None:
        self._reconcile()
        workspace_id = receipt_lib.workspace_id_for(self.workspace)
        loaded = receipt_lib.read_deployment_receipt(
            surface="cursor", workspace_id=workspace_id
        )
        assert loaded is not None
        loaded["status"] = validate_lib.STATUS_BLOCKED
        receipt_lib.write_deployment_receipt(
            loaded, surface="cursor", workspace_id=workspace_id
        )
        with self.assertRaises(receipt_lib.DeploymentNotReady) as ctx:
            receipt_lib.require_cursor_deployment_ready(self.workspace, REPO_ROOT)
        self.assertIn("BLOCKED", str(ctx.exception))

    def test_require_ready_stale_digest(self) -> None:
        self._reconcile()
        workspace_id = receipt_lib.workspace_id_for(self.workspace)
        loaded = receipt_lib.read_deployment_receipt(
            surface="cursor", workspace_id=workspace_id
        )
        assert loaded is not None
        loaded["source_manifest_digest"] = "0" * 64
        receipt_lib.write_deployment_receipt(
            loaded, surface="cursor", workspace_id=workspace_id
        )
        with self.assertRaises(receipt_lib.DeploymentNotReady) as ctx:
            receipt_lib.require_cursor_deployment_ready(self.workspace, REPO_ROOT)
        self.assertIn("stale", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
