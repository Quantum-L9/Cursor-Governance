from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
GOV_ROOT = PE_ROOT.parents[1]
FENCE = re.compile(r"```(?:bash|sh|shell)\n(.*?)```", re.S)
FORBIDDEN_IN_FENCE = (
    "compile_campaign_source.py",
    "compile_activation_files.py",
    "accept_blueprint.py",
    "collect_evidence.py",
    "pec.py bootstrap",
    "pec.py claim",
    "pec.py reconcile",
    "program-execution intent",
    "--admission-draft",
    "continue L4",
)
AGENT_SURFACES = (
    GOV_ROOT / "skills/l9-pe-campaign-activate/SKILL.md",
    GOV_ROOT / "skills/l9-pe-campaign-activate/references/pipeline.md",
    GOV_ROOT / "skills/l9-pe-campaign-activate/references/merge-authority.md",
    GOV_ROOT / "skills/l9-plan/references/executable-plan.pe-autonomy.template.md",
    GOV_ROOT
    / "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md",
    PE_ROOT / "README.md",
    PE_ROOT / "ARCHITECTURE.md",
)


class CampaignTunnelAirtightTests(unittest.TestCase):
    def test_agent_surfaces_have_no_inner_command_fences(self) -> None:
        leaks: list[str] = []
        for path in AGENT_SURFACES:
            self.assertTrue(path.is_file(), f"missing agent surface {path}")
            text = path.read_text(encoding="utf-8")
            for block in FENCE.findall(text):
                for token in FORBIDDEN_IN_FENCE:
                    if token in block:
                        leaks.append(f"{path.relative_to(GOV_ROOT)} fence has {token}")
        self.assertEqual(leaks, [])

    def test_agent_surfaces_name_the_only_front_door(self) -> None:
        for path in AGENT_SURFACES:
            text = path.read_text(encoding="utf-8")
            self.assertRegex(
                text,
                r"make(?:\s+-C\s+\"\$HOME/\.cursor-governance\")?\s+campaign INTENT=",
                f"{path.name} must name the live front door",
            )

    def test_pec_mutation_refuses_without_tunnel_env(self) -> None:
        pec = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
        env = os.environ.copy()
        env.pop("L9_CAMPAIGN_TUNNEL", None)
        env.pop("L9_ALLOW_PEC_DIRECT", None)
        completed = subprocess.run(
            [
                sys.executable,
                str(pec),
                "claim",
                "TASK-001",
                "--workspace",
                "/tmp/l9-unused-campaign-workspace",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("not a live campaign front door", payload["error"])
        self.assertIn("campaign INTENT=", payload["error"])

    def test_pec_status_stays_inspectable_without_tunnel_env(self) -> None:
        pec = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
        env = os.environ.copy()
        env.pop("L9_CAMPAIGN_TUNNEL", None)
        env.pop("L9_ALLOW_PEC_DIRECT", None)
        completed = subprocess.run(
            [
                sys.executable,
                str(pec),
                "status",
                "--workspace",
                "/tmp/l9-unused-campaign-workspace",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        payload = json.loads(completed.stdout)
        self.assertNotIn("not a live campaign front door", payload.get("error", ""))

    def test_campaign_tunnel_env_is_enough_for_pec_mutation(self) -> None:
        pec = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
        env = os.environ.copy()
        env.pop("L9_ALLOW_PEC_DIRECT", None)
        env["L9_CAMPAIGN_TUNNEL"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(pec),
                "claim",
                "TASK-001",
                "--workspace",
                "/tmp/l9-unused-campaign-workspace",
                "--holder",
                "worker",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertNotIn("not a live campaign front door", payload["error"])
        self.assertIn("not bootstrapped", payload["error"])


if __name__ == "__main__":
    unittest.main()
