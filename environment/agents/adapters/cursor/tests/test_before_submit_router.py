"""Cursor beforeSubmitPrompt hook contract (VSP phase 6).

Runs the real hook as a subprocess with an injected receipt state root:
  * input fields: conversation_id, generation_id, workspace_roots, prompt
  * stdout is exactly {"continue": true}
  * every event writes routed | no_route | disabled | degraded
  * no additional_context, no global ~/.cursor/l9/skill-route.json
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[3]
HOOK = ROOT / "ops" / "hooks" / "before_submit_skill_router.py"
INSTALLED_NAME = "before-submit-skill-router.py"

sys.path.insert(0, str(ROOT))
from ops.skill_routing import receipt as rc  # noqa: E402
from ops.skill_routing import session_locator as loc  # noqa: E402


def _key(conversation: str) -> str:
    return hashlib.sha256(conversation.encode()).hexdigest()[:32]


class HookHarness(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.state = self.home / "routes"
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "L9_GOVERNANCE_DIR": str(ROOT),
                "L9_PROACTIVE_SKILLS": "true",
                "L9_SKILL_USAGE_LOGGING": "true",
                loc.STATE_ROOT_ENV: str(self.state),
            }
        )
        self.env.pop(loc.CONVERSATION_ENV, None)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, payload: dict | str, hook: Path = HOOK, **env_extra: str):
        env = dict(self.env)
        env.update(env_extra)
        proc = subprocess.run(
            [sys.executable, str(hook)],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, proc.stdout)
        self.assertEqual(json.loads(lines[0]), {"continue": True})
        return proc

    def receipt(self, conversation: str) -> dict:
        path = self.state / _key(conversation) / "current.json"
        self.assertTrue(path.is_file(), f"no receipt at {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def payload(self, prompt: str, conversation: str = "conv-A", generation: str = "gen-1"):
        return {
            "hook_event_name": "beforeSubmitPrompt",
            "conversation_id": conversation,
            "generation_id": generation,
            "workspace_roots": [str(ROOT)],
            "prompt": prompt,
            "attachments": [],
        }


class ContractTests(HookHarness):
    def test_routed_receipt_with_exact_materialized_resources(self) -> None:
        self.run_hook(
            self.payload("Audit this unfamiliar repository architecture and map the flows.")
        )
        receipt = self.receipt("conv-A")
        self.assertEqual(receipt["status"], "routed")
        self.assertEqual(receipt["schema"], rc.RECEIPT_SCHEMA)
        decision = receipt["decision"]
        self.assertEqual(decision["primary"]["name"], "l9-code-analysis")
        primary_md = Path(decision["primary"]["skill_md"])
        self.assertTrue(primary_md.is_file())
        self.assertEqual(primary_md, (ROOT / "skills" / "l9-code-analysis" / "SKILL.md").resolve())
        self.assertLessEqual(len(decision["supporting"]), 2)
        for item in decision["supporting"]:
            self.assertTrue(Path(item["skill_md"]).is_file())
        self.assertNotIn("prompt", receipt)
        self.assertIn("prompt_sha256", receipt)
        self.assertFalse((self.home / ".cursor" / "l9" / "skill-route.json").exists())
        # Receipt validates against the live registry generation.
        registry = json.loads((ROOT / "ops" / "generated" / "skill-registry.json").read_text())
        rc.read_receipt(
            "conv-A",
            state_root=self.state,
            generation_id=registry["generation_id"],
            workspace_roots=[str(ROOT.resolve())],
        )

    def test_no_route_overwrites_previous_route(self) -> None:
        self.run_hook(
            self.payload("Audit this unfamiliar repository architecture and map the flows.")
        )
        self.assertEqual(self.receipt("conv-A")["status"], "routed")
        self.run_hook(self.payload("Fix this typo."))
        receipt = self.receipt("conv-A")
        self.assertEqual(receipt["status"], "no_route")
        self.assertNotIn("decision", receipt)

    def test_empty_prompt_writes_no_route(self) -> None:
        self.run_hook(self.payload("   "))
        self.assertEqual(self.receipt("conv-A")["status"], "no_route")

    def test_disabled_overwrites_routed(self) -> None:
        self.run_hook(
            self.payload("Audit this unfamiliar repository architecture and map the flows.")
        )
        self.run_hook(
            self.payload("Audit this unfamiliar repository architecture"),
            L9_PROACTIVE_SKILLS="false",
        )
        self.assertEqual(self.receipt("conv-A")["status"], "disabled")

    def test_degraded_on_corrupt_registry(self) -> None:
        broken = self.home / "gov"
        (broken / "ops" / "generated").mkdir(parents=True)
        shutil.copytree(ROOT / "ops" / "skill_routing", broken / "ops" / "skill_routing")
        (broken / "ops" / "generated" / "skill-registry.json").write_text(
            "{corrupt", encoding="utf-8"
        )
        self.run_hook(
            self.payload("Audit this unfamiliar repository architecture and map the flows.")
        )
        self.assertEqual(self.receipt("conv-A")["status"], "routed")
        proc = self.run_hook(
            self.payload("Audit this unfamiliar repository architecture and map the flows."),
            L9_GOVERNANCE_DIR=str(broken),
        )
        self.assertIn("degraded", proc.stderr)
        receipt = self.receipt("conv-A")
        self.assertEqual(receipt["status"], "degraded")
        self.assertNotIn("decision", receipt)

    def test_two_conversations_have_separate_receipts(self) -> None:
        self.run_hook(
            self.payload(
                "Audit this unfamiliar repository architecture and map the flows.", "conv-A"
            )
        )
        self.run_hook(self.payload("Write an ADR for this architecture decision", "conv-B"))
        a = self.receipt("conv-A")
        b = self.receipt("conv-B")
        self.assertEqual(a["decision"]["primary"]["name"], "l9-code-analysis")
        self.assertEqual(b["decision"]["primary"]["name"], "l9-architecture-decision-records")
        self.assertNotEqual(a["conversation_key"], b["conversation_key"])

    def test_missing_conversation_id_fails_open_without_receipt(self) -> None:
        proc = self.run_hook({"prompt": "Audit this unfamiliar repository architecture"})
        self.assertIn("conversation_id", proc.stderr)
        self.assertFalse(self.state.exists() and any(self.state.iterdir()))

    def test_malformed_payload_fails_open(self) -> None:
        self.run_hook("not json at all")
        self.run_hook("")

    def test_explicit_hint_route_keeps_source(self) -> None:
        self.run_hook(self.payload("Run e2e and clear the e2e blockers in this repo"))
        receipt = self.receipt("conv-A")
        self.assertEqual(receipt["status"], "routed")
        self.assertEqual(receipt["decision"]["source"], "explicit_hint")
        self.assertEqual(receipt["decision"]["primary"]["invocation"], "explicit_only")

    def test_installed_name_runs_from_outside_repo(self) -> None:
        installed = self.home / ".cursor" / "hooks" / INSTALLED_NAME
        installed.parent.mkdir(parents=True)
        os.symlink(HOOK, installed)
        self.run_hook(self.payload("plan this before coding"), hook=installed)
        self.assertEqual(self.receipt("conv-A")["decision"]["primary"]["name"], "l9-plan-simple")

    def test_hook_source_has_no_forbidden_dependencies(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        for forbidden in (
            "additional_context",
            "skill-route.json",
            "write_text(",
            "urllib",
            "socket",
            "requests",
        ):
            self.assertNotIn(forbidden, text.replace("no additional_context", ""))


if __name__ == "__main__":
    unittest.main()
