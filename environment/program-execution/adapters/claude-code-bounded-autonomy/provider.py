from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class ClaudeCodeBoundedAutonomyAdapter(BaseExecutionAdapter):
    adapter_id = "claude-code-bounded-autonomy"
    capabilities = ("inspect", "local_write", "artifact_production")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        bridge_module = load_module(
            self.repository_root
            / "environment/program-execution/integrations/claude-code-bounded-autonomy"
            / "bridge.py",
            "pes_claude_bounded_bridge",
        )
        self.bridge = bridge_module.ClaudeBoundedAutonomyBridge(self.repository_root)

    def _probe_status(self, context):
        result = self.bridge.probe()
        reason = None if result["status"] == "PASS" else "runtime unavailable"
        return result["status"], reason, [result]

    def _dispatch_record(self, record: dict[str, Any]):
        mapper = load_module(
            self.repository_root
            / "environment/program-execution/integrations/claude-code-bounded-autonomy"
            / "campaign_mapper.py",
            "pes_claude_campaign_mapper",
        )
        campaign = mapper.map_campaign(record["contract"], record["dispatch_id"])
        target_repo = Path(
            str(record["contract"].get("worktree") or self.repository_root)
        ).resolve()
        state_root = target_repo / ".l9/autonomy/claude-code"
        campaign_dir = Path(self.runtime.root) / "bounded-campaigns"
        campaign_dir.mkdir(parents=True, exist_ok=True)
        campaign_path = campaign_dir / f"{record['dispatch_id']}.json"
        campaign_path.write_text(
            json.dumps(campaign, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = self.bridge.initialize(campaign_path, state_root)
        record["bounded_campaign"] = result
        record["bounded_state_root"] = str(state_root)
        return "RUNNING", [
            {
                "type": "bounded_autonomy_campaign",
                "campaign_id": result.get("campaign_id"),
                "state_root": str(state_root),
            }
        ]
