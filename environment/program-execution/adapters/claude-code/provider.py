from __future__ import annotations

import os
import shutil
from pathlib import Path

from peer_execution.imports import load_module
from peer_execution.provider import (
    CanonicalExecutionRequest,
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)
from peer_execution.subprocess_runner import run_argv


class ClaudeCodeProvider:
    provider_id = "claude-code-direct"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.repository_root = Path(repository_root).resolve()

    def probe(self, context) -> ProviderProbe:
        executable = shutil.which("claude")
        required = [
            self.repository_root / "autonomy/adapters/claude_code/adapter.py",
            self.repository_root / "autonomy/adapters/conformance.py",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        metadata = self._provider_metadata()
        if executable is None:
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason="claude executable is absent",
                evidence=(
                    {"type": "executable", "path": None},
                    {"type": "path_probe", "missing": missing},
                    {"type": "provider_metadata", **metadata},
                ),
                observed_capabilities=("inspect", "local_write", "artifact_production"),
            )
        return ProviderProbe(
            status="PASS" if not missing else "BLOCKED",
            blocked_reason=(
                None if not missing else "root-autonomy Claude Code provider is unavailable"
            ),
            evidence=(
                {"type": "executable", "path": executable},
                {"type": "path_probe", "missing": missing},
                {"type": "provider_metadata", **metadata},
            ),
            observed_capabilities=("inspect", "local_write", "artifact_production"),
        )

    @staticmethod
    def _provider_metadata() -> dict[str, object]:
        model = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CLAUDE_MODEL")
        return {
            "provider_surface": "claude-code-cli",
            "backend_mode": (
                "custom_anthropic_compatible"
                if os.environ.get("ANTHROPIC_BASE_URL")
                else "anthropic_default"
            ),
            "model_hint": model,
        }

    def invoke(self, request: CanonicalExecutionRequest) -> ProviderInvocation:
        permission_profile = dict(request.permission_profile)
        renderer = load_module(
            Path(__file__).with_name("permission_renderer.py"),
            "pes_claude_permission_renderer",
        )
        permissions = renderer.render_permissions(
            permission_profile,
            request.rendered_contract,
        )
        argv = [
            "claude",
            "-p",
            request.worker_instruction,
            "--output-format",
            "json",
            "--max-turns",
            str(int(request.inference_budget.get("max_turns") or 12)),
            "--allowedTools",
            ",".join(permissions["allowed"]),
            "--disallowedTools",
            ",".join(permissions["denied"]),
        ]
        result = run_argv(
            argv,
            cwd=Path(request.worktree_ref).resolve(),
            timeout_seconds=int(request.timeout_budget.get("dispatch_seconds") or 1800),
            environment={
                "L9_AUTONOMY_REQUIRED": "1",
                "L9_PROGRAM_LOCK_DIGEST": request.program_lock_digest,
            },
        )
        parser = load_module(
            Path(__file__).with_name("stream_parser.py"),
            "pes_claude_stream_parser",
        )
        parse_error: str | None = None
        try:
            host = parser.parse_claude_json(result.stdout)
        except (TypeError, ValueError) as exc:
            host = {"is_error": True}
            parse_error = type(exc).__name__
        payload = host.get("result_payload")
        if not isinstance(payload, dict):
            payload = {}
        status = "PASS" if result.exit_code == 0 and not host.get("is_error") else "FAIL"
        usage = host.get("usage") if isinstance(host.get("usage"), dict) else {}
        # #region agent log
        try:
            import json as _json
            import time as _time

            _raw_result = host.get("result")
            _err_obj = (
                {
                    "type": "claude_code_error",
                    "exit_code": result.exit_code,
                    "stderr_digest": result.stderr_digest,
                    "parse_error": parse_error,
                }
                if status != "PASS"
                else None
            )
            with open(
                "/Users/macm2/Cursor-Governance/Cursor-Governance/.cursor/debug-65906b.log",
                "a",
                encoding="utf-8",
            ) as _dbg:
                _dbg.write(
                    _json.dumps(
                        {
                            "sessionId": "65906b",
                            "runId": "pre-fix",
                            "hypothesisId": "A",
                            "location": "adapters/claude-code/provider.py:invoke",
                            "message": "claude-code-direct invoke host result",
                            "data": {
                                "exit_code": result.exit_code,
                                "timed_out": result.timed_out,
                                "status": status,
                                "max_turns_requested": int(
                                    request.inference_budget.get("max_turns") or 12
                                ),
                                "num_turns": host.get("num_turns"),
                                "is_error": host.get("is_error"),
                                "subtype": host.get("subtype"),
                                "host_keys": sorted(host.keys()),
                                "result_type": type(_raw_result).__name__,
                                "result_is_str": isinstance(_raw_result, str),
                                "result_preview": (
                                    _raw_result[:400]
                                    if isinstance(_raw_result, str)
                                    else None
                                ),
                                "payload_keys": sorted(payload.keys()),
                                "changed_files_len": (
                                    len(payload.get("changed_files") or [])
                                    if isinstance(payload.get("changed_files"), list)
                                    else None
                                ),
                                "parse_error": parse_error,
                                "stderr_len": len(result.stderr or ""),
                                "stdout_len": len(result.stdout or ""),
                                "stderr_empty": not (result.stderr or "").strip(),
                                "stderr_preview": (
                                    (result.stderr or "")[-500:]
                                    .replace("sk-", "sk-REDACTED")
                                ),
                                "persisted_error_keys": (
                                    sorted(_err_obj.keys()) if _err_obj else []
                                ),
                                "allowed_tools": permissions.get("allowed"),
                                "denied_tools": permissions.get("denied"),
                            },
                            "timestamp": int(_time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        provider_result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status=status,
            structured_payload=payload,
            raw_output_digest=result.stdout_digest,
            provider_metadata=self._provider_metadata(),
            usage=usage,
            session_or_run_id=(
                str(host.get("session_id")) if host.get("session_id") is not None else None
            ),
            observed_capabilities=("inspect", "local_write", "artifact_production"),
            errors=(
                ()
                if status == "PASS"
                else (
                    {
                        "type": "claude_code_error",
                        "exit_code": result.exit_code,
                        "stderr_digest": result.stderr_digest,
                        "parse_error": parse_error,
                    },
                )
            ),
            transport_evidence_refs=(result.to_evidence(),),
        )
        return ProviderInvocation(
            status=status,
            evidence=(
                {
                    "type": "claude_code_execution",
                    "stdout_digest": result.stdout_digest,
                    "stderr_digest": result.stderr_digest,
                    "num_turns": host.get("num_turns"),
                },
            ),
            result=provider_result,
        )

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(
            status="BLOCKED",
            state=state,
            evidence=({"type": "poll_not_applicable", "execution_id": request.execution_id},),
        )

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(
            status="UNSUPPORTED",
            state=state,
            evidence=({"type": "cancellation_unsupported", "execution_id": request.execution_id},),
        )


PROVIDER_CLASS = ClaudeCodeProvider
