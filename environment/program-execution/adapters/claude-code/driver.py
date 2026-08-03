from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module
from adapters.common.subprocess_runner import run_argv


class ClaudeCodeDirectAdapter(BaseExecutionAdapter):
    adapter_id = "claude-code-direct"
    capabilities = ("inspect", "local_write", "artifact_production")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()

    def _probe_status(self, context):
        executable = shutil.which("claude")
        autonomy = self.repository_root / "autonomy/adapters/conformance.py"
        missing = []
        if executable is None:
            missing.append("claude")
        if not autonomy.is_file():
            missing.append(str(autonomy))
        evidence = [
            {"type": "executable", "path": executable},
            {"type": "missing", "items": missing},
        ]
        return (
            "PASS" if not missing else "BLOCKED",
            None
            if not missing
            else "Claude executable or root-autonomy conformance is unavailable",
            evidence,
        )

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        permission_module = load_module(
            Path(__file__).with_name("permission_renderer.py"),
            "pes_claude_permission_renderer",
        )
        permissions = permission_module.render_permissions(contract)
        prompt = "\n".join(
            [
                "Execute this exact Program Execution Rendered Contract.",
                "Return only JSON containing candidate_sha, changed_files,",
                "validation_results, and residual_unknowns.",
                json.dumps(contract, indent=2, sort_keys=True),
            ]
        )
        argv = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--max-turns",
            str(int(contract.get("max_turns") or 24)),
            "--allowedTools",
            ",".join(permissions["allowed"]),
            "--disallowedTools",
            ",".join(permissions["denied"]),
        ]
        worktree = Path(str(contract.get("worktree") or self.repository_root)).resolve()
        result = run_argv(
            argv,
            cwd=worktree,
            timeout_seconds=int(contract.get("timeout_seconds") or 1800),
            environment={
                "L9_AUTONOMY_REQUIRED": "1",
                "L9_PROGRAM_LOCK_DIGEST": str(
                    contract.get("program_lock_digest") or contract.get("program_digest")
                ),
            },
        )
        parser = load_module(
            Path(__file__).with_name("stream_parser.py"),
            "pes_claude_stream_parser",
        )
        host = parser.parse_claude_json(result.stdout) if result.stdout else {"is_error": True}
        mapper = load_module(
            Path(__file__).with_name("receipt_mapper.py"),
            "pes_claude_receipt_mapper",
        )
        record["result"] = mapper.map_result(contract, host)
        record["command_evidence"] = result.to_evidence()
        status = "PASS" if result.exit_code == 0 and not host.get("is_error") else "FAIL"
        return status, [result.to_evidence()]
