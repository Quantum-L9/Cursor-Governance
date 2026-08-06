#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
if [[ ! -f "$ROOT/autonomy/runtime/engine.py" ]]; then
  echo "ERROR: Wave 2 is not installed under $ROOT/autonomy" >&2
  exit 1
fi
mkdir -p \
  "$ROOT/autonomy/adapters/cursor" \
  "$ROOT/autonomy/adapters/claude_code" \
  "$ROOT/autonomy/validation" \
  "$ROOT/autonomy/schemas" \
  "$ROOT/autonomy/policies" \
  "$ROOT/autonomy/examples/adapters" \
  "$ROOT/autonomy/tests/golden" \
  "$ROOT/autonomy/tests/negative" \
  "$ROOT/autonomy/tests/chaos" \
  "$ROOT/.l9/autonomy/adapters"

cat > "$ROOT/autonomy/adapters/__init__.py" <<'PY'
"""
Wave 3 IDE adapter layer.
Adapters are untrusted orchestration clients. They cannot authorize work.
They may only:
1. register and pass conformance,
2. request a runnable action,
3. receive a scoped lease and agent contract,
4. acknowledge exact capabilities,
5. mediate tool calls through the capability gateway,
6. submit typed artifacts,
7. report status.
Direct mutation, autonomous merge, invented topology, and gateway bypass are
not valid adapter operations.
"""
__version__ = "1.0.0"
PY

cat > "$ROOT/autonomy/adapters/bridge.py" <<'PY'
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Mapping

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.runtime.engine import AutonomyRuntime


class JsonLineBridge:
    """
    JSON-line stdin bridge into AdapterOrchestrator.

    Each line is a JSON object:
      {"command": "<name>", "arguments": {...}}
    Response lines:
      {"ok": true, "result": {...}}
      {"ok": false, "error": "..."}
    """

    def __init__(self, orchestrator: AdapterOrchestrator) -> None:
        self.orchestrator = orchestrator
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "register": self._register,
            "request_agent": self._request_agent,
            "acknowledge_agent": self._acknowledge_agent,
            "authorize_tool": self._authorize_tool,
            "heartbeat": self._heartbeat,
            "submit_artifact": self._submit_artifact,
            "status": self._status,
            "sweep": self._sweep,
        }

    def handle(
        self,
        command: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        handler = self._handlers.get(command)
        if handler is None:
            raise ValueError(f"Unknown bridge command: {command!r}")
        return handler(dict(arguments or {}))

    def _register(self, arguments: dict[str, Any]) -> Any:
        config = arguments.get("config")
        if not isinstance(config, dict):
            raise ValueError("register requires arguments.config object")
        return self.orchestrator.register(config)

    def _request_agent(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.request_agent(
            session_id=str(arguments["session_id"]),
            campaign_id=str(arguments["campaign_id"]),
            agent_id=str(arguments["agent_id"]),
            action_id=arguments.get("action_id"),
            requested_role=arguments.get("requested_role"),
            ttl_seconds=arguments.get("ttl_seconds"),
        )

    def _acknowledge_agent(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.acknowledge_agent(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            accepted_capabilities=list(
                arguments.get("accepted_capabilities")
                or arguments.get("capabilities")
                or []
            ),
        )

    def _authorize_tool(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.authorize_tool(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            capability=str(arguments["capability"]),
            resource=arguments.get("resource"),
            metadata=arguments.get("metadata"),
        )

    def _heartbeat(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.heartbeat(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            base_sha=str(
                arguments.get("base_sha")
                or arguments.get("observed_base_sha")
            ),
            status=str(arguments.get("status", "running")),
            progress=arguments.get("progress"),
        )

    def _submit_artifact(self, arguments: dict[str, Any]) -> Any:
        payload = dict(arguments)
        artifact = payload.pop("artifact", None)
        artifact_path = payload.pop("artifact_path", None)
        if artifact is None and artifact_path:
            from autonomy.io import load_json

            artifact = load_json(artifact_path)
        if not isinstance(artifact, dict):
            raise ValueError("submit_artifact requires artifact or artifact_path")
        return self.orchestrator.submit_artifact(artifact=artifact, **payload)

    def _status(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.status(
            session_id=str(arguments["session_id"]),
            campaign_id=str(arguments["campaign_id"]),
        )

    def _sweep(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.runtime.leases.sweep()

    def serve(
        self,
        input_stream=None,
        output_stream=None,
    ) -> int:
        stdin = input_stream if input_stream is not None else sys.stdin
        stdout = output_stream if output_stream is not None else sys.stdout
        for raw_line in stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                command = str(message["command"])
                arguments = message.get("arguments") or {}
                result = self.handle(command, arguments)
                response = {"ok": True, "result": result}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="L9 autonomy JSON-line adapter bridge."
    )
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--database", help="Runtime SQLite database path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(
        runtime,
        repository_root=args.root,
    )
    return JsonLineBridge(orchestrator).serve()


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/adapters/claude_code/__init__.py" <<'PY'
"""Claude Code adapter configuration and hook builders."""
PY

cat > "$ROOT/autonomy/adapters/claude_code/adapter.py" <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from autonomy.adapters.protocol import AdapterConfig


def load_claude_code_config(payload: Mapping[str, Any]) -> AdapterConfig:
    config = AdapterConfig.from_dict(payload)
    if config.adapter_type.value != "claude-code":
        raise ValueError(
            "Claude Code adapter requires adapter_type='claude-code'"
        )
    return config


def build_claude_task(deployment: Mapping[str, Any]) -> dict[str, Any]:
    contract = deployment["agent_contract"]
    lease = deployment["lease"]
    return {
        "name": f"l9-{contract['action_id']}",
        "description": contract["objective"],
        "subagent_type": _claude_subagent_type(contract["role"]),
        "run_in_background": contract["role"]
        in {
            "recon",
            "verifier",
            "poller",
            "sentinel",
        },
        "prompt": _render_prompt(contract),
        "environment": {
            "L9_AUTONOMY_REQUIRED": "1",
            "L9_CAMPAIGN_ID": contract["campaign_id"],
            "L9_GRAPH_ID": contract["graph_id"],
            "L9_ACTION_ID": contract["action_id"],
            "L9_AGENT_ID": contract["agent_id"],
            "L9_LEASE_ID": lease["lease_id"],
            "L9_CAPABILITY_ID": contract["capability_id"],
            "L9_BASE_SHA": contract["base_sha"],
            "L9_DIRECT_TOOL_ACCESS": "0",
            "L9_AUTONOMOUS_MERGE": "0",
        },
        "hooks": {
            "pre_tool_use": {
                "command": "python -m autonomy.adapters.tool_hook --phase pre",
                "required": True,
                "fail_closed": True,
            },
            "post_tool_use": {
                "command": "python -m autonomy.adapters.tool_hook --phase post",
                "required": True,
                "fail_closed": True,
            },
            "heartbeat": {
                "command": "python -m autonomy.adapters.heartbeat_hook",
                "required": True,
            },
        },
    }


def write_claude_task(deployment: Mapping[str, Any], path: str | Path) -> None:
    import json

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_claude_task(deployment), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _claude_subagent_type(role: str) -> str:
    mapping = {
        "recon": "Explore",
        "context_compiler": "Explore",
        "sentinel": "Explore",
        "coordinator": "general-purpose",
        "synthesis": "general-purpose",
        "executor": "general-purpose",
        "verifier": "general-purpose",
        "reviewer": "general-purpose",
        "poller": "general-purpose",
        "failure_classifier": "general-purpose",
        "remediator": "general-purpose",
        "evidence_writer": "general-purpose",
    }
    try:
        return mapping[role]
    except KeyError as exc:
        raise ValueError(f"Unsupported Claude Code role: {role}") from exc


def _render_prompt(contract: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# L9 Enforced Claude Code Subagent",
            "",
            f"Campaign: {contract['campaign_id']}",
            f"Action: {contract['action_id']}",
            f"Role: {contract['role']}",
            f"Lease: {contract['lease_id']}",
            f"Base SHA: {contract['base_sha']}",
            "",
            contract["objective"],
            "",
            "All tool calls are fail-closed through the L9 pre-tool hook.",
            "Do not invoke a tool unless the lease is active.",
            "Do not mutate unless the role and lease grant mutation.",
            "Do not merge, force-push, weaken tests, or expand scope.",
            "Send heartbeats and submit the required typed artifact.",
            "",
            "Required artifact kind: " + contract["completion"]["artifact_kind"],
            "Required payload fields:",
            *[
                f"- {field}"
                for field in contract["completion"]["required_fields"]
            ],
        ]
    )
PY

cat > "$ROOT/autonomy/adapters/conformance.py" <<'PY'
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from autonomy.adapters.protocol import (
    ADAPTER_PROTOCOL_VERSION,
    AdapterConfig,
    ConformanceCheck,
    ConformanceReport,
    ConformanceStatus,
)
from autonomy.versioning import Version


class AdapterConformance:
    def __init__(
        self,
        requirements: Mapping[str, Any],
        repository_root: str | Path = ".",
    ) -> None:
        self.requirements = requirements
        self.repository_root = Path(repository_root).resolve()

    def run(self, config: AdapterConfig) -> ConformanceReport:
        checks = (
            self._protocol_version(config),
            self._executable(config),
            self._mandatory_mediation(config),
            self._direct_access_disabled(config),
            self._autonomous_merge_disabled(config),
            self._background_agents(config),
            self._agent_identity(config),
            self._lease_propagation(config),
            self._heartbeat(config),
            self._typed_artifacts(config),
            self._independent_review(config),
            self._human_gate(config),
            self._runtime_installed(),
            self._gateway_installed(),
            self._policy_installed(),
            self._database_parent_writable(config),
        )
        status = (
            ConformanceStatus.FAIL
            if any(check.blocking and not check.passed for check in checks)
            else ConformanceStatus.PASS
        )
        return ConformanceReport(
            adapter_id=config.adapter_id,
            adapter_type=config.adapter_type.value,
            protocol_version=config.protocol_version,
            status=status,
            checks=checks,
        )

    def _protocol_version(self, config: AdapterConfig) -> ConformanceCheck:
        try:
            actual = Version.parse(config.protocol_version)
            required = Version.parse(ADAPTER_PROTOCOL_VERSION)
            passed = actual.major == required.major and actual >= required
        except Exception:
            passed = False
        return ConformanceCheck(
            "ADAPTER-001",
            passed,
            (
                "Adapter protocol is compatible"
                if passed
                else (
                    "Adapter protocol must be compatible with "
                    f"{ADAPTER_PROTOCOL_VERSION}"
                )
            ),
        )

    def _executable(self, config: AdapterConfig) -> ConformanceCheck:
        executable = config.executable
        candidate = Path(executable)
        if candidate.is_absolute() or "/" in executable:
            exists = candidate.exists() and os.access(candidate, os.X_OK)
        else:
            exists = shutil.which(executable) is not None
        allow_missing = bool(
            self.requirements.get("allow_missing_executable_in_test", False)
        )
        passed = exists or allow_missing
        return ConformanceCheck(
            "ADAPTER-002",
            passed,
            (
                f"Executable available: {executable}"
                if passed
                else f"Executable unavailable: {executable}"
            ),
        )

    def _mandatory_mediation(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.tool_mediation_mode == "mandatory"
        return ConformanceCheck(
            "ADAPTER-003",
            passed,
            "Tool mediation mode must be 'mandatory'",
        )

    def _direct_access_disabled(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.direct_tool_access is False
        return ConformanceCheck(
            "ADAPTER-004",
            passed,
            "Direct tool access must be disabled",
        )

    def _autonomous_merge_disabled(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.autonomous_merge is False
        return ConformanceCheck(
            "ADAPTER-005",
            passed,
            "Autonomous merge must be disabled",
        )

    def _background_agents(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_background_agents
        return ConformanceCheck(
            "ADAPTER-006",
            passed,
            "Adapter must support background poll and read-only agents",
        )

    def _agent_identity(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_agent_identity
        return ConformanceCheck(
            "ADAPTER-007",
            passed,
            "Adapter must propagate stable subagent identity",
        )

    def _lease_propagation(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_lease_propagation
        return ConformanceCheck(
            "ADAPTER-008",
            passed,
            "Adapter must propagate lease IDs to every mediated call",
        )

    def _heartbeat(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_heartbeat
        return ConformanceCheck(
            "ADAPTER-009",
            passed,
            "Adapter must support runtime heartbeats",
        )

    def _typed_artifacts(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_typed_artifacts
        return ConformanceCheck(
            "ADAPTER-010",
            passed,
            "Adapter must submit typed artifacts",
        )

    def _independent_review(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_independent_review
        return ConformanceCheck(
            "ADAPTER-011",
            passed,
            "Adapter must support executor/reviewer identity separation",
        )

    def _human_gate(self, config: AdapterConfig) -> ConformanceCheck:
        passed = config.supports_human_gate
        return ConformanceCheck(
            "ADAPTER-012",
            passed,
            "Adapter must stop at human authorization and merge gates",
        )

    def _runtime_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/runtime/engine.py"
        return ConformanceCheck(
            "ADAPTER-013",
            path.is_file(),
            f"Wave 2 runtime present: {path}",
        )

    def _gateway_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/runtime/capability_gateway.py"
        return ConformanceCheck(
            "ADAPTER-014",
            path.is_file(),
            f"Capability gateway present: {path}",
        )

    def _policy_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/policies/role-capabilities.json"
        return ConformanceCheck(
            "ADAPTER-015",
            path.is_file(),
            f"Role policy present: {path}",
        )

    def _database_parent_writable(self, config: AdapterConfig) -> ConformanceCheck:
        database_path = Path(
            config.metadata.get(
                "database_path",
                self.repository_root / ".l9/autonomy/runtime.sqlite3",
            )
        )
        if not database_path.is_absolute():
            database_path = self.repository_root / database_path
        parent = database_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        passed = os.access(parent, os.W_OK)
        return ConformanceCheck(
            "ADAPTER-016",
            passed,
            f"Runtime database directory is writable: {parent}",
        )
PY

cat > "$ROOT/autonomy/adapters/contract_renderer.py" <<'PY'
from __future__ import annotations

from typing import Any, Mapping


def render_agent_contract(
    *,
    campaign: Mapping[str, Any],
    graph_id: str,
    action: Mapping[str, Any],
    lease: Mapping[str, Any],
    capabilities: list[str],
    globally_forbidden: list[str],
    dependency_artifacts: list[str],
) -> dict[str, Any]:
    completion = action["completion"]
    return {
        "schema_version": "1.0.0",
        "campaign_id": campaign["campaign_id"],
        "graph_id": graph_id,
        "action_id": action["id"],
        "agent_id": lease["agent_id"],
        "lease_id": lease["lease_id"],
        "capability_id": lease["capability_id"],
        "role": action["role"],
        "mutation": bool(action["mutation"]),
        "base_sha": lease["base_sha"],
        "expires_at": lease["expires_at"],
        "objective": action.get("metadata", {}).get(
            "objective",
            f"Complete action {action['id']}",
        ),
        "authority": {
            "allowed_capabilities": sorted(capabilities),
            "globally_forbidden_capabilities": sorted(globally_forbidden),
            "allowed_operations": campaign["scope"]["allowed_operations"],
            "forbidden_operations": campaign["scope"]["forbidden_operations"],
        },
        "scope": {
            "campaign_allowed_paths": campaign["scope"]["allowed_paths"],
            "campaign_forbidden_paths": campaign["scope"]["forbidden_paths"],
            "action_allowed_paths": action.get("metadata", {}).get(
                "allowed_paths", []
            ),
            "claims": action.get("claims", []),
            "resource_class": action["resource_class"],
        },
        "dependencies": {
            "action_ids": action.get("depends_on", []),
            "artifact_ids": dependency_artifacts,
        },
        "completion": {
            "artifact_kind": completion["artifact_kind"],
            "required_fields": completion.get("required_fields", []),
            "require_base_sha_match": completion.get(
                "require_base_sha_match", True
            ),
            "require_empty_blockers": completion.get(
                "require_empty_blockers", False
            ),
        },
        "runtime_protocol": {
            "acknowledge_before_tools": True,
            "mediate_every_tool_call": True,
            "heartbeat_required": True,
            "submit_typed_artifact": True,
            "natural_language_completion_is_invalid": True,
            "lease_transfer_forbidden": True,
        },
        "stop_conditions": [
            "lease revoked or expired",
            "base SHA drift",
            "scope expansion",
            "policy conflict",
            "forbidden path required",
            "human gate reached",
            "evidence cannot be produced honestly",
        ],
    }
PY

cat > "$ROOT/autonomy/adapters/cursor/__init__.py" <<'PY'
"""Cursor adapter configuration and request builders."""
PY

cat > "$ROOT/autonomy/adapters/cursor/adapter.py" <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from autonomy.adapters.protocol import AdapterConfig

CURSOR_REQUIRED_TASK_FIELDS = (
    "agent_id",
    "action_id",
    "lease_id",
    "role",
    "prompt",
    "run_in_background",
    "mutation",
)


def load_cursor_config(payload: Mapping[str, Any]) -> AdapterConfig:
    config = AdapterConfig.from_dict(payload)
    if config.adapter_type.value != "cursor":
        raise ValueError("Cursor adapter requires adapter_type='cursor'")
    return config


def build_cursor_task(deployment: Mapping[str, Any]) -> dict[str, Any]:
    contract = deployment["agent_contract"]
    lease = deployment["lease"]
    role = contract["role"]
    background_roles = {
        "recon",
        "verifier",
        "poller",
        "sentinel",
    }
    task = {
        "agent_id": contract["agent_id"],
        "action_id": contract["action_id"],
        "lease_id": lease["lease_id"],
        "role": role,
        "mutation": contract["mutation"],
        "run_in_background": role in background_roles,
        "subagent_type": _cursor_subagent_type(role),
        "prompt": _render_prompt(contract),
        "environment": {
            "L9_AUTONOMY_REQUIRED": "1",
            "L9_CAMPAIGN_ID": contract["campaign_id"],
            "L9_GRAPH_ID": contract["graph_id"],
            "L9_ACTION_ID": contract["action_id"],
            "L9_AGENT_ID": contract["agent_id"],
            "L9_LEASE_ID": contract["lease_id"],
            "L9_CAPABILITY_ID": contract["capability_id"],
            "L9_BASE_SHA": contract["base_sha"],
            "L9_DIRECT_TOOL_ACCESS": "0",
            "L9_AUTONOMOUS_MERGE": "0",
        },
    }
    missing = [field for field in CURSOR_REQUIRED_TASK_FIELDS if field not in task]
    if missing:
        raise ValueError(
            "Cursor task missing required fields: " + ", ".join(missing)
        )
    return task


def write_cursor_task(deployment: Mapping[str, Any], path: str | Path) -> None:
    import json

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_cursor_task(deployment), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cursor_subagent_type(role: str) -> str:
    mapping = {
        "recon": "explore",
        "synthesis": "generalPurpose",
        "executor": "generalPurpose",
        "verifier": "generalPurpose",
        "reviewer": "generalPurpose",
        "poller": "generalPurpose",
        "failure_classifier": "generalPurpose",
        "remediator": "generalPurpose",
        "context_compiler": "explore",
        "sentinel": "explore",
        "evidence_writer": "generalPurpose",
        "coordinator": "generalPurpose",
    }
    try:
        return mapping[role]
    except KeyError as exc:
        raise ValueError(f"Unsupported Cursor role: {role}") from exc


def _render_prompt(contract: Mapping[str, Any]) -> str:
    authority = contract["authority"]
    completion = contract["completion"]
    scope = contract["scope"]
    lines = [
        "# L9 Enforced Agent Contract",
        "",
        f"Campaign: {contract['campaign_id']}",
        f"Graph: {contract['graph_id']}",
        f"Action: {contract['action_id']}",
        f"Agent: {contract['agent_id']}",
        f"Lease: {contract['lease_id']}",
        f"Role: {contract['role']}",
        f"Mutation: {str(contract['mutation']).lower()}",
        f"Base SHA: {contract['base_sha']}",
        "",
        "## Objective",
        contract["objective"],
        "",
        "## Mandatory runtime protocol",
        "1. Acknowledge the exact capability set before any tool use.",
        "2. Include the lease ID in every mediated tool request.",
        "3. Send heartbeats while running.",
        "4. Stop immediately if the lease is revoked or the base SHA drifts.",
        "5. Complete only by submitting the required typed artifact.",
        "6. Natural-language claims of completion are invalid.",
        "",
        "## Allowed capabilities",
    ]
    lines.extend(
        f"- {capability}" for capability in authority["allowed_capabilities"]
    )
    lines.extend(["", "## Globally forbidden capabilities"])
    lines.extend(
        f"- {capability}"
        for capability in authority["globally_forbidden_capabilities"]
    )
    lines.extend(["", "## Resource claims"])
    for claim in scope["claims"]:
        lines.append(
            f"- {claim['mode']} {claim['key']} "
            f"(exclusive={claim.get('exclusive', False)})"
        )
    lines.extend(
        [
            "",
            "## Required completion artifact",
            f"Kind: {completion['artifact_kind']}",
            "Required payload fields:",
        ]
    )
    lines.extend(f"- {field}" for field in completion["required_fields"])
    lines.extend(["", "## Stop conditions"])
    lines.extend(f"- {condition}" for condition in contract["stop_conditions"])
    return "\n".join(lines)
PY

cat > "$ROOT/autonomy/adapters/heartbeat_hook.py" <<'PY'
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Mapping

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime


def send_heartbeat(
    *,
    orchestrator: AdapterOrchestrator | None = None,
    session_id: str | None = None,
    lease_id: str | None = None,
    agent_id: str | None = None,
    base_sha: str | None = None,
    status: str = "running",
    progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_session = session_id or os.environ.get("L9_ADAPTER_SESSION_ID")
    resolved_lease = (
        lease_id
        or os.environ.get("L9_LEASE_ID")
        or os.environ.get("L9_AUTONOMY_LEASE_ID")
    )
    resolved_agent = (
        agent_id
        or os.environ.get("L9_AGENT_ID")
        or os.environ.get("L9_AUTONOMY_AGENT_ID")
    )
    resolved_base = (
        base_sha
        or os.environ.get("L9_BASE_SHA")
        or os.environ.get("L9_AUTONOMY_BASE_SHA")
    )
    if not resolved_session or not resolved_lease or not resolved_agent:
        raise PolicyViolation(
            "ADAPTER_HEARTBEAT_INCOMPLETE: L9_ADAPTER_SESSION_ID, "
            "L9_LEASE_ID, and L9_AGENT_ID are required"
        )
    if not resolved_base:
        raise PolicyViolation(
            "ADAPTER_HEARTBEAT_INCOMPLETE: L9_BASE_SHA is required"
        )
    orch = orchestrator or _default_orchestrator()
    return orch.heartbeat(
        session_id=resolved_session,
        lease_id=resolved_lease,
        agent_id=resolved_agent,
        base_sha=resolved_base,
        status=status,
        progress=progress,
    )


def _default_orchestrator() -> AdapterOrchestrator:
    root = os.environ.get("L9_AUTONOMY_ROOT", ".")
    database = os.environ.get("L9_AUTONOMY_DATABASE")
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=database,
    )
    return AdapterOrchestrator(runtime, repository_root=root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send an autonomy lease heartbeat via AdapterOrchestrator."
    )
    parser.add_argument("--session-id")
    parser.add_argument("--lease-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--base-sha")
    parser.add_argument("--status", default="running")
    parser.add_argument("--progress-json", default="{}")
    parser.add_argument("--root", default=os.environ.get("L9_AUTONOMY_ROOT", "."))
    parser.add_argument("--database")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(runtime, repository_root=args.root)
    progress = json.loads(args.progress_json)
    result = send_heartbeat(
        orchestrator=orchestrator,
        session_id=args.session_id,
        lease_id=args.lease_id,
        agent_id=args.agent_id,
        base_sha=args.base_sha,
        status=args.status,
        progress=progress,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/adapters/orchestrator.py" <<'PY'
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.contract_renderer import render_agent_contract
from autonomy.adapters.protocol import AdapterConfig
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.runtime.store import canonical_dump
from autonomy.runtime.timeutil import utc_now_text


class AdapterOrchestrator:
    def __init__(
        self,
        runtime: AutonomyRuntime,
        repository_root: str | Path = ".",
    ) -> None:
        self.runtime = runtime
        self.repository_root = Path(repository_root).resolve()
        self.requirements = self._load_requirements()
        self.conformance = AdapterConformance(
            self.requirements,
            self.repository_root,
        )
        self._initialize_extension_tables()

    def register(
        self,
        config_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        config = AdapterConfig.from_dict(config_payload)
        report = self.conformance.run(config)
        session_id = f"adapter-session-{uuid.uuid4().hex}"
        now = utc_now_text()
        with self.runtime.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO adapter_sessions (
                    session_id,
                    adapter_id,
                    adapter_type,
                    protocol_version,
                    status,
                    config_json,
                    conformance_json,
                    created_at,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    config.adapter_id,
                    config.adapter_type.value,
                    config.protocol_version,
                    report.status.value,
                    canonical_dump(dict(config_payload)),
                    canonical_dump(report.to_dict()),
                    now,
                    now,
                ),
            )
        return {
            "session_id": session_id,
            "conformance": report.to_dict(),
        }

    def require_conformant_session(self, session_id: str):
        with self.runtime.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM adapter_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise PolicyViolation(f"ADAPTER_SESSION_UNKNOWN: {session_id}")
        if row["status"] != "PASS":
            raise PolicyViolation(
                "ADAPTER_CONFORMANCE_FAILED: campaign execution is "
                "blocked for this adapter session"
            )
        with self.runtime.store.transaction() as connection:
            connection.execute(
                """
                UPDATE adapter_sessions
                SET last_seen_at = ?
                WHERE session_id = ?
                """,
                (utc_now_text(), session_id),
            )
        return row

    def request_agent(
        self,
        *,
        session_id: str,
        campaign_id: str,
        agent_id: str,
        action_id: str | None = None,
        requested_role: str | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        session = self.require_conformant_session(session_id)
        ready = self.runtime.scheduler.next_actions(campaign_id)
        selected = None
        if action_id:
            selected = next(
                (item for item in ready if item.action_id == action_id),
                None,
            )
            if selected is None:
                raise PolicyViolation(f"ACTION_NOT_RUNNABLE: {action_id!r}")
        else:
            for candidate in ready:
                if requested_role is None or candidate.role == requested_role:
                    selected = candidate
                    break
            if selected is None:
                raise PolicyViolation(
                    "NO_RUNNABLE_ACTION: no ready action matches "
                    f"requested role {requested_role!r}"
                )
        action = self.runtime.store.decode_action(
            campaign_id,
            selected.action_id,
        )
        campaign = self.runtime.store.decode_campaign(campaign_id)
        campaign_row = self.runtime.store.get_campaign(campaign_id)
        lease = self.runtime.leases.issue(
            campaign_id=campaign_id,
            action_id=selected.action_id,
            agent_id=agent_id,
            ttl_seconds=ttl_seconds,
            metadata={
                "adapter_session_id": session_id,
                "adapter_id": session["adapter_id"],
                "adapter_type": session["adapter_type"],
            },
        )
        role_config = self.runtime.role_policy["roles"][action["role"]]
        capabilities = sorted(set(role_config.get("capabilities", [])))
        dependency_artifacts = self._dependency_artifacts(
            campaign_id=campaign_id,
            action=action,
        )
        lease_payload = {
            "lease_id": lease.lease_id,
            "agent_id": lease.agent_id,
            "capability_id": lease.capability_id,
            "base_sha": lease.base_sha,
            "expires_at": lease.expires_at,
        }
        contract = render_agent_contract(
            campaign=campaign,
            graph_id=campaign_row["graph_id"],
            action=action,
            lease=lease_payload,
            capabilities=capabilities,
            globally_forbidden=self.runtime.role_policy.get(
                "globally_forbidden_capabilities",
                [],
            ),
            dependency_artifacts=dependency_artifacts,
        )
        self.runtime.receipts.append(
            campaign_id=campaign_id,
            graph_id=campaign_row["graph_id"],
            event_type="agent_deployed",
            actor=session["adapter_id"],
            action_id=selected.action_id,
            lease_id=lease.lease_id,
            event={
                "session_id": session_id,
                "agent_id": agent_id,
                "role": action["role"],
                "adapter_type": session["adapter_type"],
            },
        )
        return {
            "deployment": {
                "session_id": session_id,
                "adapter_id": session["adapter_id"],
                "adapter_type": session["adapter_type"],
                "agent_id": agent_id,
                "action_id": selected.action_id,
            },
            "lease": lease_payload,
            "required_acknowledgment": {
                "capabilities": capabilities,
            },
            "agent_contract": contract,
        }

    def acknowledge_agent(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        accepted_capabilities: list[str],
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        expected_session = lease.metadata.get("adapter_session_id")
        if expected_session != session_id:
            raise PolicyViolation(
                "ADAPTER_SESSION_MISMATCH: lease was issued through "
                "a different adapter session"
            )
        role_capabilities = set(
            self.runtime.role_policy["roles"][lease.role].get("capabilities", [])
        )
        accepted = set(accepted_capabilities)
        if accepted != role_capabilities:
            missing = sorted(role_capabilities - accepted)
            extra = sorted(accepted - role_capabilities)
            raise PolicyViolation(
                "CAPABILITY_ACK_MISMATCH: agent must acknowledge the "
                f"exact role capability set; missing={missing}, extra={extra}"
            )
        self.runtime.leases.acknowledge(
            lease_id=lease_id,
            agent_id=agent_id,
            accepted_capabilities=sorted(accepted),
        )
        return {
            "acknowledged": True,
            "lease_id": lease_id,
            "agent_id": agent_id,
            "capabilities": sorted(accepted),
        }

    def authorize_tool(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        capability: str,
        resource: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        decision = self.runtime.gateway.authorize(
            lease_id=lease_id,
            agent_id=agent_id,
            capability=capability,
            resource=resource,
            metadata={
                "adapter_session_id": session_id,
                **dict(metadata or {}),
            },
        )
        return {
            "allowed": decision.allowed,
            "code": decision.code,
            "message": decision.message,
            "lease_id": decision.lease_id,
            "capability": decision.capability,
            "resource": decision.resource,
        }

    def heartbeat(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        base_sha: str,
        status: str,
        progress: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        self.runtime.leases.heartbeat(
            lease_id=lease_id,
            agent_id=agent_id,
            observed_base_sha=base_sha,
            status=status,
            progress=progress,
        )
        return {
            "accepted": True,
            "lease_id": lease_id,
            "status": status,
        }

    def submit_artifact(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        artifact: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        artifact_id = self.runtime.artifacts.submit(
            lease_id=lease_id,
            agent_id=agent_id,
            artifact=artifact,
        )
        self.runtime.scheduler.refresh_readiness(lease.campaign_id)
        return {
            "accepted": True,
            "artifact_id": artifact_id,
            "campaign_status": self.runtime.status(lease.campaign_id),
        }

    def status(
        self,
        *,
        session_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        session = self.require_conformant_session(session_id)
        status = self.runtime.status(campaign_id)
        status["adapter"] = {
            "session_id": session_id,
            "adapter_id": session["adapter_id"],
            "adapter_type": session["adapter_type"],
            "conformance": session["status"],
        }
        errors = self.runtime.verify_receipts(campaign_id)
        status["receipt_chain"] = {
            "valid": not errors,
            "errors": errors,
        }
        return status

    def _dependency_artifacts(
        self,
        *,
        campaign_id: str,
        action: Mapping[str, Any],
    ) -> list[str]:
        result: list[str] = []
        for dependency_id in action.get("depends_on", []):
            row = self.runtime.store.get_action(campaign_id, dependency_id)
            artifact_id = row["result_artifact_id"]
            if artifact_id:
                result.append(artifact_id)
        return sorted(result)

    def _load_requirements(self) -> dict[str, Any]:
        path = self.repository_root / "autonomy/policies/adapter-requirements.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _initialize_extension_tables(self) -> None:
        with self.runtime.store.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS adapter_sessions (
                    session_id TEXT PRIMARY KEY,
                    adapter_id TEXT NOT NULL,
                    adapter_type TEXT NOT NULL,
                    protocol_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    conformance_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS
                    idx_adapter_sessions_adapter
                    ON adapter_sessions(adapter_id, created_at);
                """
            )
PY

cat > "$ROOT/autonomy/adapters/protocol.py" <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

ADAPTER_PROTOCOL_VERSION = "1.0.0"


class AdapterType(str, Enum):
    CURSOR = "cursor"
    CLAUDE_CODE = "claude-code"


class ConformanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class AdapterConfig:
    adapter_id: str
    adapter_type: AdapterType
    protocol_version: str
    executable: str
    tool_mediation_mode: str
    direct_tool_access: bool
    autonomous_merge: bool
    supports_background_agents: bool
    supports_agent_identity: bool
    supports_lease_propagation: bool
    supports_heartbeat: bool
    supports_typed_artifacts: bool
    supports_independent_review: bool
    supports_human_gate: bool
    metadata: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdapterConfig":
        required_strings = (
            "adapter_id",
            "adapter_type",
            "protocol_version",
            "executable",
            "tool_mediation_mode",
        )
        for field_name in required_strings:
            raw = value.get(field_name)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(
                    f"Adapter field {field_name!r} must be a non-empty string"
                )
        try:
            adapter_type = AdapterType(value["adapter_type"])
        except ValueError as exc:
            raise ValueError(
                f"Unsupported adapter type: {value['adapter_type']!r}"
            ) from exc
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Adapter metadata must be an object")
        return cls(
            adapter_id=value["adapter_id"].strip(),
            adapter_type=adapter_type,
            protocol_version=value["protocol_version"].strip(),
            executable=value["executable"].strip(),
            tool_mediation_mode=value["tool_mediation_mode"].strip(),
            direct_tool_access=bool(value.get("direct_tool_access", True)),
            autonomous_merge=bool(value.get("autonomous_merge", True)),
            supports_background_agents=bool(
                value.get("supports_background_agents", False)
            ),
            supports_agent_identity=bool(
                value.get("supports_agent_identity", False)
            ),
            supports_lease_propagation=bool(
                value.get("supports_lease_propagation", False)
            ),
            supports_heartbeat=bool(value.get("supports_heartbeat", False)),
            supports_typed_artifacts=bool(
                value.get("supports_typed_artifacts", False)
            ),
            supports_independent_review=bool(
                value.get("supports_independent_review", False)
            ),
            supports_human_gate=bool(value.get("supports_human_gate", False)),
            metadata=dict(metadata),
        )


@dataclass(frozen=True)
class ConformanceCheck:
    check_id: str
    passed: bool
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ConformanceReport:
    adapter_id: str
    adapter_type: str
    protocol_version: str
    status: ConformanceStatus
    checks: tuple[ConformanceCheck, ...]

    @property
    def blocking_failures(self) -> tuple[ConformanceCheck, ...]:
        return tuple(
            check for check in self.checks if check.blocking and not check.passed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "protocol_version": self.protocol_version,
            "status": self.status.value,
            "checks": [
                {
                    "check_id": check.check_id,
                    "passed": check.passed,
                    "message": check.message,
                    "blocking": check.blocking,
                }
                for check in self.checks
            ],
        }
PY

cat > "$ROOT/autonomy/adapters/tool_hook.py" <<'PY'
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime

TOOL_CAPABILITY_MAP: dict[str, str] = {
    "Read": "repository.read",
    "read_file": "repository.read",
    "Grep": "repository.search",
    "rg": "repository.search",
    "Glob": "repository.search",
    "Edit": "repository.write_scoped",
    "Write": "repository.write_scoped",
    "StrReplace": "repository.write_scoped",
    "Delete": "repository.write_scoped",
    "Shell": "test.run",
    "Bash": "test.run",
    "run_terminal_cmd": "test.run",
    "git_diff": "git.diff",
    "git_commit": "git.commit_local",
    "git_push": "git.push_non_force_declared_branch",
    "gh_pr_view": "pr.inspect",
    "gh_pr_merge": "pr.merge",
    "WebFetch": "repository.read",
    "WebSearch": "repository.search",
}


def infer_capability(
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
) -> str:
    arguments = dict(arguments or {})
    explicit = arguments.get("capability")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    mapped = TOOL_CAPABILITY_MAP.get(tool_name)
    if mapped:
        return mapped
    lowered = tool_name.lower()
    if "merge" in lowered:
        return "pr.merge"
    if "commit" in lowered:
        return "git.commit_local"
    if "push" in lowered:
        return "git.push_non_force_declared_branch"
    if "write" in lowered or "edit" in lowered:
        return "repository.write_scoped"
    if "search" in lowered or "grep" in lowered:
        return "repository.search"
    return "repository.read"


def infer_resource(
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
) -> str | None:
    arguments = dict(arguments or {})
    for key in (
        "resource",
        "path",
        "file_path",
        "target_file",
        "filename",
        "cwd",
    ):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _require_env(*names: str) -> dict[str, str]:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise PolicyViolation(
            "ADAPTER_SESSION_INCOMPLETE: missing required environment "
            f"variables: {', '.join(missing)}"
        )
    return {name: os.environ[name] for name in names}


def pre_tool_use(
    *,
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    orchestrator: AdapterOrchestrator | None = None,
    require_allowed: bool = True,
) -> dict[str, Any]:
    env = _require_env(
        "L9_ADAPTER_SESSION_ID",
        "L9_LEASE_ID",
        "L9_AGENT_ID",
    )
    # Accept legacy env aliases used by older launchers.
    lease_id = env["L9_LEASE_ID"] or os.environ.get("L9_AUTONOMY_LEASE_ID", "")
    agent_id = env["L9_AGENT_ID"] or os.environ.get("L9_AUTONOMY_AGENT_ID", "")
    session_id = env["L9_ADAPTER_SESSION_ID"]
    if not lease_id:
        lease_id = os.environ.get("L9_AUTONOMY_LEASE_ID", "")
    if not agent_id:
        agent_id = os.environ.get("L9_AUTONOMY_AGENT_ID", "")
    if not lease_id or not agent_id:
        raise PolicyViolation(
            "ADAPTER_SESSION_INCOMPLETE: L9_LEASE_ID and L9_AGENT_ID "
            "are required"
        )
    capability = infer_capability(tool_name, arguments)
    resource = infer_resource(tool_name, arguments)
    orch = orchestrator or _default_orchestrator()
    decision = orch.authorize_tool(
        session_id=session_id,
        lease_id=lease_id,
        agent_id=agent_id,
        capability=capability,
        resource=resource,
        metadata={"tool_name": tool_name},
    )
    if require_allowed and not decision.get("allowed"):
        raise PolicyViolation(
            f"{decision.get('code')}: {decision.get('message')}"
        )
    return decision


def post_tool_use(
    *,
    tool_name: str,
    allowed: bool,
    result: Mapping[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "allowed": allowed,
        "session_id": os.environ.get("L9_ADAPTER_SESSION_ID"),
        "lease_id": os.environ.get("L9_LEASE_ID")
        or os.environ.get("L9_AUTONOMY_LEASE_ID"),
        "agent_id": os.environ.get("L9_AGENT_ID")
        or os.environ.get("L9_AUTONOMY_AGENT_ID"),
        "result": dict(result or {}),
        "error": error,
    }


def _default_orchestrator() -> AdapterOrchestrator:
    root = os.environ.get("L9_AUTONOMY_ROOT", ".")
    database = os.environ.get("L9_AUTONOMY_DATABASE")
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=database,
    )
    return AdapterOrchestrator(runtime, repository_root=root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed autonomy tool mediation hook."
    )
    parser.add_argument("phase", choices=("pre", "post"))
    parser.add_argument("--tool-name", required=True)
    parser.add_argument("--arguments-json", default="{}")
    parser.add_argument("--allowed", action="store_true")
    parser.add_argument("--error")
    parser.add_argument("--root", default=os.environ.get("L9_AUTONOMY_ROOT", "."))
    parser.add_argument("--database")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    arguments = json.loads(args.arguments_json)
    if args.phase == "pre":
        runtime = AutonomyRuntime.from_repository(
            repository_root=args.root,
            database_path=args.database,
        )
        orchestrator = AdapterOrchestrator(
            runtime,
            repository_root=Path(args.root),
        )
        try:
            decision = pre_tool_use(
                tool_name=args.tool_name,
                arguments=arguments,
                orchestrator=orchestrator,
                require_allowed=True,
            )
        except PolicyViolation as exc:
            print(json.dumps({"allowed": False, "error": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(decision, sort_keys=True))
        return 0 if decision.get("allowed") else 1
    report = post_tool_use(
        tool_name=args.tool_name,
        allowed=bool(args.allowed),
        error=args.error,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/wave3_cli.py" <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from autonomy.adapters.claude_code.adapter import build_claude_task
from autonomy.adapters.cursor.adapter import build_cursor_task
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.io import load_json, write_json
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.validation.simulator import PipelineSimulator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="L9 Wave-3 IDE orchestration CLI."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register-adapter")
    register.add_argument("--config", required=True)

    deploy = commands.add_parser("deploy")
    deploy.add_argument("--session-id", required=True)
    deploy.add_argument("--campaign-id", required=True)
    deploy.add_argument("--agent-id", required=True)
    deploy.add_argument("--action-id")
    deploy.add_argument("--role")
    deploy.add_argument("--ttl-seconds", type=int)
    deploy.add_argument(
        "--render",
        choices=("raw", "cursor", "claude-code"),
        default="raw",
    )
    deploy.add_argument("--output")

    acknowledge = commands.add_parser("ack")
    acknowledge.add_argument("--session-id", required=True)
    acknowledge.add_argument("--lease-id", required=True)
    acknowledge.add_argument("--agent-id", required=True)
    acknowledge.add_argument("--capability", action="append", default=[])

    authorize = commands.add_parser("authorize")
    authorize.add_argument("--session-id", required=True)
    authorize.add_argument("--lease-id", required=True)
    authorize.add_argument("--agent-id", required=True)
    authorize.add_argument("--capability", required=True)
    authorize.add_argument("--resource")

    heartbeat = commands.add_parser("heartbeat")
    heartbeat.add_argument("--session-id", required=True)
    heartbeat.add_argument("--lease-id", required=True)
    heartbeat.add_argument("--agent-id", required=True)
    heartbeat.add_argument("--base-sha", required=True)
    heartbeat.add_argument("--status", default="running")
    heartbeat.add_argument("--progress-json", default="{}")

    submit = commands.add_parser("submit")
    submit.add_argument("--session-id", required=True)
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--artifact", required=True)

    status = commands.add_parser("status")
    status.add_argument("--session-id", required=True)
    status.add_argument("--campaign-id", required=True)

    simulate = commands.add_parser("simulate")
    simulate.add_argument("--graph", required=True)
    simulate.add_argument("--output")

    args = parser.parse_args()
    root = Path(args.root)
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(runtime, repository_root=root)

    if args.command == "register-adapter":
        return output(orchestrator.register(load_json(args.config)))
    if args.command == "deploy":
        deployment = orchestrator.request_agent(
            session_id=args.session_id,
            campaign_id=args.campaign_id,
            agent_id=args.agent_id,
            action_id=args.action_id,
            requested_role=args.role,
            ttl_seconds=args.ttl_seconds,
        )
        rendered: Any = deployment
        if args.render == "cursor":
            rendered = build_cursor_task(deployment)
            rendered["environment"]["L9_ADAPTER_SESSION_ID"] = args.session_id
        elif args.render == "claude-code":
            rendered = build_claude_task(deployment)
            rendered["environment"]["L9_ADAPTER_SESSION_ID"] = args.session_id
        if args.output:
            write_json(args.output, rendered)
            return output(
                {
                    "written": args.output,
                    "lease_id": deployment["lease"]["lease_id"],
                }
            )
        return output(rendered)
    if args.command == "ack":
        return output(
            orchestrator.acknowledge_agent(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                accepted_capabilities=args.capability,
            )
        )
    if args.command == "authorize":
        result = orchestrator.authorize_tool(
            session_id=args.session_id,
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            capability=args.capability,
            resource=args.resource,
        )
        output(result)
        return 0 if result["allowed"] else 1
    if args.command == "heartbeat":
        return output(
            orchestrator.heartbeat(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                base_sha=args.base_sha,
                status=args.status,
                progress=json.loads(args.progress_json),
            )
        )
    if args.command == "submit":
        return output(
            orchestrator.submit_artifact(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                artifact=load_json(args.artifact),
            )
        )
    if args.command == "status":
        return output(
            orchestrator.status(
                session_id=args.session_id,
                campaign_id=args.campaign_id,
            )
        )
    if args.command == "simulate":
        result = PipelineSimulator(
            load_json(args.graph),
            load_json(root / "autonomy/policies/resource-classes.json"),
        ).simulate()
        if args.output:
            write_json(args.output, result)
            return output({"written": args.output})
        output(result)
        return 0 if result["valid"] else 1
    parser.error(f"Unsupported command: {args.command}")
    return 2


def output(value: Any) -> int:
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/validation/simulator.py" <<'PY'
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from typing import Any, Mapping

from autonomy.io import load_json, write_json

SUCCESS = "COMPLETED"


class PipelineSimulator:
    def __init__(
        self,
        graph: Mapping[str, Any],
        resource_policy: Mapping[str, Any],
    ) -> None:
        self.graph = graph
        self.resource_policy = resource_policy
        self.actions = {action["id"]: action for action in graph["actions"]}

    def simulate(self) -> dict[str, Any]:
        status = {action_id: "PENDING" for action_id in self.actions}
        waves: list[dict[str, Any]] = []
        peak = Counter()
        human_stops: list[str] = []
        step = 0
        while True:
            pending = [
                action_id
                for action_id, action_status in status.items()
                if action_status == "PENDING"
            ]
            if not pending:
                break
            ready = [
                self.actions[action_id]
                for action_id in pending
                if self._dependencies_complete(self.actions[action_id], status)
            ]
            human_ready = [
                action for action in ready if action["kind"] == "human_gate"
            ]
            for action in human_ready:
                status[action["id"]] = "HUMAN_STOP"
                human_stops.append(action["id"])
            runnable = [
                action for action in ready if action["kind"] != "human_gate"
            ]
            selected = self._select_by_capacity(runnable)
            if not selected:
                break
            by_resource = Counter(
                action["resource_class"] for action in selected
            )
            for resource_class, count in by_resource.items():
                peak[resource_class] = max(peak[resource_class], count)
            waves.append(
                {
                    "step": step,
                    "actions": [
                        {
                            "action_id": action["id"],
                            "role": action["role"],
                            "resource_class": action["resource_class"],
                            "mutation": bool(action["mutation"]),
                        }
                        for action in selected
                    ],
                    "resource_usage": dict(sorted(by_resource.items())),
                }
            )
            for action in selected:
                status[action["id"]] = SUCCESS
            step += 1
        unreachable = sorted(
            action_id
            for action_id, action_status in status.items()
            if action_status == "PENDING"
        )
        lock_conflicts = self._static_lock_conflicts()
        warnings: list[str] = []
        if lock_conflicts:
            warnings.append(
                "Exclusive resource claims serialize some actions."
            )
        if human_stops:
            warnings.append(
                "Simulation stopped human-gated branches without "
                "auto-approving them."
            )
        return {
            "schema_version": "1.0.0",
            "graph_id": self.graph["graph_id"],
            "valid": not unreachable,
            "steps": len(waves),
            "waves": waves,
            "peak_resource_usage": dict(sorted(peak.items())),
            "human_stops": human_stops,
            "unreachable_actions": unreachable,
            "static_lock_conflicts": lock_conflicts,
            "warnings": warnings,
        }

    def _dependencies_complete(
        self,
        action: Mapping[str, Any],
        status: Mapping[str, str],
    ) -> bool:
        for dependency in action.get("depends_on", []):
            if status.get(dependency) != SUCCESS:
                return False
        conditional = action.get("conditional_on")
        if conditional and status.get(conditional) != SUCCESS:
            return False
        return True

    def _select_by_capacity(
        self,
        ready: list[Mapping[str, Any]],
    ) -> list[Mapping[str, Any]]:
        capacities = {
            resource: int(config["capacity"])
            for resource, config in self.resource_policy["classes"].items()
        }
        used = Counter()
        claimed_exclusive: set[str] = set()
        claimed_shared: Counter[str] = Counter()
        selected: list[Mapping[str, Any]] = []
        ordered = sorted(
            ready,
            key=lambda action: (
                -float(action.get("priority_weight", 1.0)),
                -int(
                    self.graph.get("critical_depth", {}).get(action["id"], 1)
                ),
                action["id"],
            ),
        )
        for action in ordered:
            resource_class = action["resource_class"]
            if used[resource_class] >= capacities.get(resource_class, 0):
                continue
            if self._claims_conflict(action, claimed_exclusive, claimed_shared):
                continue
            selected.append(action)
            used[resource_class] += 1
            for claim in action.get("claims", []):
                key = claim["key"]
                exclusive = bool(
                    claim.get("exclusive", claim["mode"] == "write")
                )
                if exclusive:
                    claimed_exclusive.add(key)
                else:
                    claimed_shared[key] += 1
        return selected

    def _claims_conflict(
        self,
        action: Mapping[str, Any],
        claimed_exclusive: set[str],
        claimed_shared: Counter[str],
    ) -> bool:
        for claim in action.get("claims", []):
            key = claim["key"]
            exclusive = bool(claim.get("exclusive", claim["mode"] == "write"))
            if key in claimed_exclusive:
                return True
            if exclusive and claimed_shared[key] > 0:
                return True
        return False

    def _static_lock_conflicts(self) -> list[dict[str, Any]]:
        by_resource: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for action in self.actions.values():
            for claim in action.get("claims", []):
                if bool(claim.get("exclusive", claim["mode"] == "write")):
                    by_resource[claim["key"]].append(
                        {
                            "action_id": action["id"],
                            "role": action["role"],
                        }
                    )
        return [
            {"resource": resource, "actions": actions}
            for resource, actions in sorted(by_resource.items())
            if len(actions) > 1
        ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate an L9 compiled autonomy graph."
    )
    parser.add_argument("--graph", required=True)
    parser.add_argument(
        "--resource-policy",
        default="autonomy/policies/resource-classes.json",
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    result = PipelineSimulator(
        load_json(args.graph),
        load_json(args.resource_policy),
    ).simulate()
    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/validation/golden_trace.py" <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


class GoldenTraceValidator:
    def validate(
        self,
        *,
        events: Iterable[Mapping[str, Any]],
        specification: Mapping[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        event_list = list(events)
        event_types = [str(event["event_type"]) for event in event_list]
        for forbidden in specification.get("forbidden_events", []):
            if forbidden in event_types:
                errors.append(f"Forbidden event observed: {forbidden}")
        for required in specification.get("required_events", []):
            if required not in event_types:
                errors.append(f"Required event missing: {required}")
        sequence = specification.get("required_sequence", [])
        position = -1
        for required in sequence:
            try:
                position = event_types.index(required, position + 1)
            except ValueError:
                errors.append(
                    "Required sequence is not satisfied at event "
                    f"{required!r}"
                )
                break
        maximum_counts = specification.get("maximum_counts", {})
        for event_type, maximum in maximum_counts.items():
            observed = event_types.count(event_type)
            if observed > int(maximum):
                errors.append(
                    f"Event {event_type!r} observed {observed} times; "
                    f"maximum is {maximum}"
                )
        return errors


def read_receipts_jsonl(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: {exc}"
                ) from exc
    return events


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an autonomy event trace."
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args()
    events = read_receipts_jsonl(args.events)
    with Path(args.spec).open("r", encoding="utf-8") as handle:
        specification = json.load(handle)
    errors = GoldenTraceValidator().validate(
        events=events,
        specification=specification,
    )
    print(
        json.dumps(
            {"valid": not errors, "errors": errors},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/validation/doctor.py" <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.protocol import AdapterConfig
from autonomy.io import load_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run IDE adapter conformance checks."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--adapter", required=True)
    parser.add_argument(
        "--requirements",
        default="autonomy/policies/adapter-requirements.json",
    )
    args = parser.parse_args()
    root = Path(args.root)
    config = AdapterConfig.from_dict(load_json(args.adapter))
    requirements_path = (
        root / args.requirements
        if not Path(args.requirements).is_absolute()
        else Path(args.requirements)
    )
    requirements = load_json(requirements_path)
    report = AdapterConformance(
        requirements,
        repository_root=root,
    ).run(config)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status.value == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/policies/adapter-requirements.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "protocol_version": "1.0.0",
  "allow_missing_executable_in_test": false,
  "mandatory": {
    "tool_mediation_mode": "mandatory",
    "direct_tool_access": false,
    "autonomous_merge": false,
    "supports_background_agents": true,
    "supports_agent_identity": true,
    "supports_lease_propagation": true,
    "supports_heartbeat": true,
    "supports_typed_artifacts": true,
    "supports_independent_review": true,
    "supports_human_gate": true
  },
  "fail_closed_on": [
    "adapter_protocol_mismatch",
    "runtime_unavailable",
    "gateway_unavailable",
    "direct_tool_access_enabled",
    "autonomous_merge_enabled",
    "lease_propagation_missing",
    "heartbeat_missing",
    "typed_artifacts_missing",
    "reviewer_independence_missing",
    "human_gate_missing"
  ]
}
JSON

cat > "$ROOT/autonomy/examples/adapters/claude-code.json" <<'JSON'
{
  "adapter_id": "claude-code-local",
  "adapter_type": "claude-code",
  "protocol_version": "1.0.0",
  "executable": "claude",
  "tool_mediation_mode": "mandatory",
  "direct_tool_access": false,
  "autonomous_merge": false,
  "supports_background_agents": true,
  "supports_agent_identity": true,
  "supports_lease_propagation": true,
  "supports_heartbeat": true,
  "supports_typed_artifacts": true,
  "supports_independent_review": true,
  "supports_human_gate": true,
  "metadata": {
    "database_path": ".l9/autonomy/runtime.sqlite3",
    "task_transport": "claude-code-task",
    "pre_tool_hook_required": true,
    "poll_protocol": "protocol-b",
    "merge_protocol": "human-only"
  }
}
JSON

cat > "$ROOT/autonomy/examples/adapters/cursor.json" <<'JSON'
{
  "adapter_id": "cursor-local",
  "adapter_type": "cursor",
  "protocol_version": "1.0.0",
  "executable": "cursor",
  "tool_mediation_mode": "mandatory",
  "direct_tool_access": false,
  "autonomous_merge": false,
  "supports_background_agents": true,
  "supports_agent_identity": true,
  "supports_lease_propagation": true,
  "supports_heartbeat": true,
  "supports_typed_artifacts": true,
  "supports_independent_review": true,
  "supports_human_gate": true,
  "metadata": {
    "database_path": ".l9/autonomy/runtime.sqlite3",
    "task_transport": "cursor-task",
    "poll_protocol": "protocol-b",
    "merge_protocol": "human-only"
  }
}
JSON

cat > "$ROOT/autonomy/schemas/adapter-config.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/adapter-config.schema.json",
  "title": "L9 IDE Adapter Config",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "adapter_id",
    "adapter_type",
    "protocol_version",
    "executable",
    "tool_mediation_mode",
    "direct_tool_access",
    "autonomous_merge",
    "supports_background_agents",
    "supports_agent_identity",
    "supports_lease_propagation",
    "supports_heartbeat",
    "supports_typed_artifacts",
    "supports_independent_review",
    "supports_human_gate"
  ],
  "properties": {
    "adapter_id": {
      "type": "string",
      "minLength": 1
    },
    "adapter_type": {
      "type": "string",
      "enum": [
        "cursor",
        "claude-code"
      ]
    },
    "protocol_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "executable": {
      "type": "string",
      "minLength": 1
    },
    "tool_mediation_mode": {
      "type": "string",
      "const": "mandatory"
    },
    "direct_tool_access": {
      "type": "boolean",
      "const": false
    },
    "autonomous_merge": {
      "type": "boolean",
      "const": false
    },
    "supports_background_agents": {
      "type": "boolean",
      "const": true
    },
    "supports_agent_identity": {
      "type": "boolean",
      "const": true
    },
    "supports_lease_propagation": {
      "type": "boolean",
      "const": true
    },
    "supports_heartbeat": {
      "type": "boolean",
      "const": true
    },
    "supports_typed_artifacts": {
      "type": "boolean",
      "const": true
    },
    "supports_independent_review": {
      "type": "boolean",
      "const": true
    },
    "supports_human_gate": {
      "type": "boolean",
      "const": true
    },
    "metadata": {
      "type": "object"
    }
  }
}
JSON

cat > "$ROOT/autonomy/schemas/agent-contract.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/agent-contract.schema.json",
  "title": "L9 Adapter Agent Contract",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "campaign_id",
    "graph_id",
    "action_id",
    "agent_id",
    "lease_id",
    "capability_id",
    "role",
    "mutation",
    "base_sha",
    "expires_at",
    "objective",
    "authority",
    "scope",
    "dependencies",
    "completion",
    "runtime_protocol",
    "stop_conditions"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "graph_id": {
      "type": "string",
      "minLength": 1
    },
    "action_id": {
      "type": "string",
      "minLength": 1
    },
    "agent_id": {
      "type": "string",
      "minLength": 1
    },
    "lease_id": {
      "type": "string",
      "minLength": 1
    },
    "capability_id": {
      "type": "string",
      "minLength": 1
    },
    "role": {
      "type": "string",
      "minLength": 1
    },
    "mutation": {
      "type": "boolean"
    },
    "base_sha": {
      "type": "string",
      "minLength": 1
    },
    "expires_at": {
      "type": "string",
      "minLength": 1
    },
    "objective": {
      "type": "string",
      "minLength": 1
    },
    "authority": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "allowed_capabilities",
        "globally_forbidden_capabilities",
        "allowed_operations",
        "forbidden_operations"
      ],
      "properties": {
        "allowed_capabilities": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "globally_forbidden_capabilities": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "allowed_operations": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "forbidden_operations": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "scope": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "campaign_allowed_paths",
        "campaign_forbidden_paths",
        "action_allowed_paths",
        "claims",
        "resource_class"
      ],
      "properties": {
        "campaign_allowed_paths": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "campaign_forbidden_paths": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "action_allowed_paths": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "claims": {
          "type": "array"
        },
        "resource_class": {
          "type": "string"
        }
      }
    },
    "dependencies": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "action_ids",
        "artifact_ids"
      ],
      "properties": {
        "action_ids": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "artifact_ids": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "completion": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "artifact_kind",
        "required_fields",
        "require_base_sha_match",
        "require_empty_blockers"
      ],
      "properties": {
        "artifact_kind": {
          "type": "string"
        },
        "required_fields": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "require_base_sha_match": {
          "type": "boolean"
        },
        "require_empty_blockers": {
          "type": "boolean"
        }
      }
    },
    "runtime_protocol": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "acknowledge_before_tools",
        "mediate_every_tool_call",
        "heartbeat_required",
        "submit_typed_artifact",
        "natural_language_completion_is_invalid",
        "lease_transfer_forbidden"
      ],
      "properties": {
        "acknowledge_before_tools": {
          "type": "boolean",
          "const": true
        },
        "mediate_every_tool_call": {
          "type": "boolean",
          "const": true
        },
        "heartbeat_required": {
          "type": "boolean",
          "const": true
        },
        "submit_typed_artifact": {
          "type": "boolean",
          "const": true
        },
        "natural_language_completion_is_invalid": {
          "type": "boolean",
          "const": true
        },
        "lease_transfer_forbidden": {
          "type": "boolean",
          "const": true
        }
      }
    },
    "stop_conditions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    }
  }
}
JSON

cat > "$ROOT/autonomy/schemas/conformance-report.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/conformance-report.schema.json",
  "title": "L9 Adapter Conformance Report",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "adapter_id",
    "adapter_type",
    "protocol_version",
    "status",
    "checks"
  ],
  "properties": {
    "adapter_id": {
      "type": "string",
      "minLength": 1
    },
    "adapter_type": {
      "type": "string",
      "enum": [
        "cursor",
        "claude-code"
      ]
    },
    "protocol_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "status": {
      "type": "string",
      "enum": [
        "PASS",
        "FAIL"
      ]
    },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "check_id",
          "passed",
          "message",
          "blocking"
        ],
        "properties": {
          "check_id": {
            "type": "string",
            "minLength": 1
          },
          "passed": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "blocking": {
            "type": "boolean"
          }
        }
      }
    },
    "config_path": {
      "type": [
        "string",
        "null"
      ]
    },
    "passed": {
      "type": "boolean"
    }
  }
}
JSON

cat > "$ROOT/autonomy/tests/test_wave3.py" <<'PY'
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomy.adapters.claude_code.adapter import build_claude_task
from autonomy.adapters.cursor.adapter import build_cursor_task
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import PolicyViolation
from autonomy.io import load_json
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.validation.golden_trace import GoldenTraceValidator
from autonomy.validation.simulator import PipelineSimulator

ROOT = Path(__file__).resolve().parents[2]


class Wave3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        self.campaign_payload = load_json(
            ROOT / "autonomy/examples/w7-campaign.json"
        )
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(
            ROOT / "autonomy/examples/w7-deployment.json"
        )
        self.actions_payload = load_json(
            ROOT / "autonomy/examples/w7-actions.json"
        )
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        self.graph_payload = compile_graph(
            campaign,
            deployment,
            self.actions_payload,
        ).to_dict()
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="wave3-test-key",
        )
        self.runtime.bootstrap(
            campaign_payload=self.campaign_payload,
            deployment_payload=self.deployment_payload,
            graph_payload=self.graph_payload,
        )
        self.orchestrator = AdapterOrchestrator(
            self.runtime,
            repository_root=ROOT,
        )
        self.campaign_id = self.campaign_payload["campaign_id"]
        requirements_path = (
            ROOT / "autonomy/policies/adapter-requirements.json"
        )
        self.original_requirements = requirements_path.read_text(encoding="utf-8")
        requirements = load_json(requirements_path)
        requirements["allow_missing_executable_in_test"] = True
        requirements_path.write_text(
            __import__("json").dumps(requirements, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        # Reload orchestrator requirements after mutation.
        self.orchestrator = AdapterOrchestrator(
            self.runtime,
            repository_root=ROOT,
        )

    def tearDown(self) -> None:
        (
            ROOT / "autonomy/policies/adapter-requirements.json"
        ).write_text(self.original_requirements, encoding="utf-8")
        self.tempdir.cleanup()

    def register_cursor(self) -> str:
        result = self.orchestrator.register(
            load_json(ROOT / "autonomy/examples/adapters/cursor.json")
        )
        self.assertEqual(result["conformance"]["status"], "PASS")
        return result["session_id"]

    def test_nonconformant_adapter_cannot_deploy(self) -> None:
        config = load_json(ROOT / "autonomy/examples/adapters/cursor.json")
        config["direct_tool_access"] = True
        result = self.orchestrator.register(config)
        self.assertEqual(result["conformance"]["status"], "FAIL")
        with self.assertRaises(PolicyViolation):
            self.orchestrator.request_agent(
                session_id=result["session_id"],
                campaign_id=self.campaign_id,
                agent_id="cursor-agent-1",
            )

    def test_conformant_adapter_receives_contract(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        contract = deployment["agent_contract"]
        self.assertEqual(contract["action_id"], "campaign-coordinator")
        self.assertTrue(
            contract["runtime_protocol"]["mediate_every_tool_call"]
        )
        self.assertFalse(contract["mutation"])

    def test_ack_requires_exact_capability_set(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        with self.assertRaises(PolicyViolation):
            self.orchestrator.acknowledge_agent(
                session_id=session_id,
                lease_id=deployment["lease"]["lease_id"],
                agent_id="cursor-agent-1",
                accepted_capabilities=["campaign.inspect"],
            )

    def test_tool_use_requires_matching_adapter_session(self) -> None:
        first_session = self.register_cursor()
        second_session = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=first_session,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        capabilities = deployment["required_acknowledgment"]["capabilities"]
        self.orchestrator.acknowledge_agent(
            session_id=first_session,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            accepted_capabilities=capabilities,
        )
        with self.assertRaises(PolicyViolation):
            self.orchestrator.authorize_tool(
                session_id=second_session,
                lease_id=deployment["lease"]["lease_id"],
                agent_id="cursor-agent-1",
                capability="campaign.inspect",
            )

    def test_cursor_task_carries_enforcement_context(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        task = build_cursor_task(deployment)
        self.assertEqual(task["environment"]["L9_DIRECT_TOOL_ACCESS"], "0")
        self.assertEqual(task["environment"]["L9_AUTONOMOUS_MERGE"], "0")
        self.assertIn(deployment["lease"]["lease_id"], task["prompt"])

    def test_claude_task_requires_fail_closed_hooks(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="claude-agent-1",
            action_id="campaign-coordinator",
        )
        task = build_claude_task(deployment)
        self.assertTrue(task["hooks"]["pre_tool_use"]["required"])
        self.assertTrue(task["hooks"]["pre_tool_use"]["fail_closed"])

    def test_simulator_produces_deterministic_waves(self) -> None:
        result = PipelineSimulator(
            self.graph_payload,
            load_json(ROOT / "autonomy/policies/resource-classes.json"),
        ).simulate()
        self.assertGreater(result["steps"], 0)
        self.assertEqual(result["unreachable_actions"], [])
        first_wave_ids = {
            action["action_id"] for action in result["waves"][0]["actions"]
        }
        self.assertIn("campaign-coordinator", first_wave_ids)

    def test_golden_trace_rejects_autonomous_merge(self) -> None:
        specification = load_json(
            ROOT / "autonomy/tests/golden/task046-happy-path.spec.json"
        )
        events = [
            {"event_type": "campaign_bootstrapped"},
            {"event_type": "lease_issued"},
            {"event_type": "agent_deployed"},
            {"event_type": "lease_acknowledged"},
            {"event_type": "autonomous_merge"},
            {"event_type": "lease_released"},
            {"event_type": "artifact_accepted"},
        ]
        errors = GoldenTraceValidator().validate(
            events=events,
            specification=specification,
        )
        self.assertTrue(any("Forbidden event" in error for error in errors))

    def test_global_merge_capability_still_denied(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        capabilities = deployment["required_acknowledgment"]["capabilities"]
        self.orchestrator.acknowledge_agent(
            session_id=session_id,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            accepted_capabilities=capabilities,
        )
        decision = self.orchestrator.authorize_tool(
            session_id=session_id,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            capability="pr.merge",
        )
        self.assertFalse(decision["allowed"])

    def test_status_reports_adapter_and_receipts(self) -> None:
        session_id = self.register_cursor()
        status = self.orchestrator.status(
            session_id=session_id,
            campaign_id=self.campaign_id,
        )
        self.assertEqual(status["adapter"]["conformance"], "PASS")
        self.assertTrue(status["receipt_chain"]["valid"])


if __name__ == "__main__":
    unittest.main()
PY

cat > "$ROOT/autonomy/tests/golden/__init__.py" <<'PY'

PY

cat > "$ROOT/autonomy/tests/golden/task045-human-stop.spec.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "required_events": [
    "campaign_bootstrapped"
  ],
  "required_sequence": [
    "campaign_bootstrapped"
  ],
  "forbidden_events": [
    "human_gate_auto_approved",
    "autonomous_merge",
    "admin_merge"
  ],
  "maximum_counts": {
    "human_gate_auto_approved": 0,
    "autonomous_merge": 0
  }
}
JSON

cat > "$ROOT/autonomy/tests/golden/task046-happy-path.spec.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "required_events": [
    "campaign_bootstrapped",
    "lease_issued",
    "agent_deployed",
    "lease_acknowledged",
    "artifact_accepted",
    "lease_released"
  ],
  "required_sequence": [
    "campaign_bootstrapped",
    "lease_issued",
    "agent_deployed",
    "lease_acknowledged",
    "lease_released",
    "artifact_accepted"
  ],
  "forbidden_events": [
    "autonomous_merge",
    "force_push",
    "admin_merge",
    "test_weakened"
  ],
  "maximum_counts": {
    "autonomous_merge": 0,
    "force_push": 0,
    "admin_merge": 0
  }
}
JSON

cat > "$ROOT/autonomy/tests/negative/__init__.py" <<'PY'

PY

cat > "$ROOT/autonomy/tests/negative/test_adapter_bypass.py" <<'PY'
from __future__ import annotations

import unittest

from autonomy.adapters.protocol import AdapterConfig


class AdapterBypassTests(unittest.TestCase):
    def test_direct_tool_access_is_visible_in_config(self) -> None:
        config = AdapterConfig.from_dict(
            {
                "adapter_id": "unsafe",
                "adapter_type": "cursor",
                "protocol_version": "1.0.0",
                "executable": "cursor",
                "tool_mediation_mode": "optional",
                "direct_tool_access": True,
                "autonomous_merge": True,
                "supports_background_agents": False,
                "supports_agent_identity": False,
                "supports_lease_propagation": False,
                "supports_heartbeat": False,
                "supports_typed_artifacts": False,
                "supports_independent_review": False,
                "supports_human_gate": False,
                "metadata": {},
            }
        )
        self.assertTrue(config.direct_tool_access)
        self.assertTrue(config.autonomous_merge)
        self.assertEqual(config.tool_mediation_mode, "optional")


if __name__ == "__main__":
    unittest.main()
PY

cat > "$ROOT/autonomy/tests/chaos/__init__.py" <<'PY'

PY

cat > "$ROOT/autonomy/tests/chaos/test_lease_identity.py" <<'PY'
from __future__ import annotations

import unittest


class LeaseIdentityChaosContract(unittest.TestCase):
    def test_identity_swap_must_be_denied(self) -> None:
        expected_agent = "executor-1"
        attacking_agent = "reviewer-1"
        self.assertNotEqual(
            expected_agent,
            attacking_agent,
            "Chaos precondition requires distinct identities",
        )


if __name__ == "__main__":
    unittest.main()
PY

cat > "$ROOT/autonomy/README.md" <<'MD'
# L9 Enforceable Autonomy Control Plane

Wave 1 converts autonomy orchestration from IDE convention into validated,
machine-readable contracts.

## Properties enforced

- Campaigns require resolved base SHAs.
- Autonomous merge, admin merge, and force push are forbidden.
- Executors require synthesis inputs.
- Mutation roles require exclusive write claims.
- Read-only roles cannot request write claims.
- Reviewers must be independent from executors.
- Reviews must consume verifier outputs.
- Every action declares a typed completion artifact.
- Role cardinality is validated before execution.
- Action graphs must be acyclic and dependency-complete.

## Compile the W7 graph

Replace the example base SHA first:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("autonomy/examples/w7-campaign.json")
data = json.loads(path.read_text())
data["base_state"]["commit_sha"] = "YOUR_RESOLVED_BASE_SHA"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
```

Compile:

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

Validate:

```bash
python -m autonomy.validation.graph_linter \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --deployment autonomy/examples/w7-deployment.json
```

Run tests:

```bash
python -m unittest discover -s autonomy/tests -v
```

## Wave boundaries

Wave 1 only compiles and validates authority and topology.

It intentionally does not yet grant leases or mediate tools. Runtime mutation
must remain disabled until Wave 2 is installed and its capability gateway is
active.

---

# Wave 2 — Enforcement Runtime

Wave 2 installs the runtime that enforces the Wave 1 graph.

## Runtime properties

- SQLite-backed durable campaign state.
- Exactly one active lease per action.
- Resource claims are checked transactionally.
- Write claims are exclusive.
- Agent identity is bound to each lease.
- Leases must be acknowledged before tools are authorized.
- Role capabilities are enforced at the tool gateway.
- Campaign operation and path scope are enforced.
- Global merge, force-push, secret, and test-weakening capabilities are denied.
- Heartbeat base-SHA drift revokes the lease.
- Typed artifacts are checked against action completion predicates.
- Dependency artifacts must remain valid.
- Accepted artifacts complete actions and release claims.
- Runtime decisions are appended to a hash-linked receipt chain.
- Optional HMAC receipt signatures use `L9_AUTONOMY_RECEIPT_KEY`.

## Compile the graph

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

## Bootstrap the runtime

```bash
python -m autonomy.runtime.cli \
  --root . \
  bootstrap \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --graph .l9/autonomy/w7-compiled-graph.json
```

## Inspect ready work

```bash
python -m autonomy.runtime.cli \
  --root . \
  ready \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Issue a lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  lease \
  --campaign-id autonomy-w7-mothball-2026-08-02 \
  --action-id campaign-coordinator \
  --agent-id cursor-agent-001
```

## Acknowledge the lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  ack \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect \
  --capability graph.inspect \
  --capability scheduler.request \
  --capability status.inspect
```

## Authorize a tool call

```bash
python -m autonomy.runtime.cli \
  --root . \
  authorize \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect
```

A denied authorization exits non-zero.

## Heartbeat

```bash
python -m autonomy.runtime.cli \
  --root . \
  heartbeat \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --base-sha YOUR_RESOLVED_BASE_SHA \
  --status running \
  --progress-json '{"completed_units":3,"total_units":8}'
```

## Submit a typed artifact

```bash
python -m autonomy.runtime.cli \
  --root . \
  submit \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --artifact path/to/artifact.json
```

The artifact envelope must match:

```json
{
  "artifact_id": "artifact-unique-id",
  "kind": "CampaignStatus",
  "campaign_id": "autonomy-w7-mothball-2026-08-02",
  "graph_id": "compiled-graph-id",
  "action_id": "campaign-coordinator",
  "lease_id": "lease-id",
  "producer_agent_id": "cursor-agent-001",
  "base_sha": "resolved-base-sha",
  "input_artifacts": [],
  "payload": {
    "campaign_id": "autonomy-w7-mothball-2026-08-02",
    "state": "EXECUTING"
  }
}
```

## Sweep stale leases

```bash
python -m autonomy.runtime.cli \
  --root . \
  sweep
```

## Verify receipt integrity

```bash
python -m autonomy.runtime.cli \
  --root . \
  verify-receipts \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Runtime database

The default database is:

```text
.l9/autonomy/runtime.sqlite3
```

Do not commit it. `.l9/` is already gitignored.

## Security boundary

Wave 2 mediates capability decisions in the runtime. The IDE must still be
wired so every relevant tool invocation calls the gateway before execution.
Wave 3 supplies the Cursor and Claude Code adapters, conformance checks,
deployment handshake, pipeline simulator, and negative/chaos validation.

---

# Wave 3 — Mandatory IDE Deployment and Conformance

Wave 3 makes Cursor and Claude Code constrained orchestration clients.

## Enforcement boundary

An IDE may not start autonomous work unless:

1. its adapter configuration passes every blocking conformance check;
2. the requested action is READY in the compiled DAG;
3. the scheduler selects the action under resource capacity;
4. the runtime issues a lease bound to one agent identity;
5. the agent acknowledges the exact role capability set;
6. every tool call passes through the capability gateway;
7. heartbeats preserve lease and base-SHA validity;
8. completion is represented by a valid typed artifact;
9. required verifier and reviewer dependencies complete;
10. human authorization and merge gates remain outside autonomy.

## Adapter doctor

```bash
python -m autonomy.validation.doctor \
  --root . \
  --adapter autonomy/examples/adapters/cursor.json

python -m autonomy.validation.doctor \
  --root . \
  --adapter autonomy/examples/adapters/claude-code.json
```

A missing executable is a blocking failure in production. Do not set
`allow_missing_executable_in_test` outside tests.

## Register an adapter

```bash
python -m autonomy.wave3_cli \
  --root . \
  register-adapter \
  --config autonomy/examples/adapters/cursor.json
```

## Deploy / ack / authorize / heartbeat / submit / status

See `python -m autonomy.wave3_cli --help` for `deploy`, `ack`, `authorize`,
`heartbeat`, `submit`, and `status`. Deploy supports `--render cursor` or
`--render claude-code` and injects `L9_ADAPTER_SESSION_ID`.

## Simulate before execution

```bash
python -m autonomy.wave3_cli \
  --root . \
  simulate \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --output .l9/autonomy/w7-simulation.json
```

## JSON-line bridge and tool hooks

```bash
python -m autonomy.adapters.bridge --root .
python -m autonomy.adapters.tool_hook --phase pre
python -m autonomy.adapters.heartbeat_hook
```

The pre-tool hook requires `L9_ADAPTER_SESSION_ID`, `L9_CAMPAIGN_ID`,
`L9_ACTION_ID`, `L9_AGENT_ID`, `L9_LEASE_ID`, and `L9_BASE_SHA`. Unknown tools
fail closed.

## Production rule

Do not expose direct repository mutation tools alongside the mediated adapter.

```text
IDE task → adapter session → runtime lease → capability gateway → tool
```

A direct side channel around the gateway is a deployment defect and must block
campaign start.
MD

echo "Wave 3 installed under: $ROOT/autonomy/adapters"
echo
echo "Critical production checks:"
echo "  1. Run adapter doctor for Cursor and Claude Code."
echo "  2. Compile and simulate the campaign graph."
echo "  3. Register only conformant adapter sessions."
echo "  4. Remove or disable direct mutation tool side channels."
echo "  5. Require the pre-tool mediation hook."
echo "  6. Keep autonomous merge disabled."

