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
