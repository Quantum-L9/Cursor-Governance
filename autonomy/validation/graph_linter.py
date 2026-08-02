from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from autonomy.errors import GraphValidationError
from autonomy.models import (
    Action,
    DeploymentManifest,
    Role,
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    action_id: str | None = None

    def render(self) -> str:
        suffix = f" action={self.action_id}" if self.action_id else ""
        return f"{self.severity} {self.code}{suffix}: {self.message}"


class GraphLinter:
    def __init__(
        self,
        deployment: DeploymentManifest,
        role_policy: Mapping[str, Any],
        pipeline_policy: Mapping[str, Any],
    ) -> None:
        self.deployment = deployment
        self.role_policy = role_policy
        self.pipeline_policy = pipeline_policy

    def lint(self, compiled_graph: Mapping[str, Any]) -> list[Finding]:
        raw_actions = compiled_graph.get("actions")
        if not isinstance(raw_actions, list):
            raise GraphValidationError("Compiled graph actions must be a list")
        actions = [Action.from_dict(item) for item in raw_actions]
        findings: list[Finding] = []
        findings.extend(self._check_role_cardinality(actions))
        findings.extend(self._check_role_mutation(actions))
        findings.extend(self._check_executor_dependencies(actions))
        findings.extend(self._check_reviewer_independence(actions))
        findings.extend(self._check_verification_before_review(actions))
        findings.extend(self._check_human_merge_policy(actions))
        findings.extend(self._check_claim_modes(actions))
        findings.extend(self._check_completion_contracts(actions))
        return findings

    def assert_valid(self, compiled_graph: Mapping[str, Any]) -> None:
        findings = self.lint(compiled_graph)
        blocking = [finding for finding in findings if finding.severity == "ERROR"]
        if blocking:
            rendered = "\n".join(item.render() for item in blocking)
            raise GraphValidationError(f"Compiled graph failed validation:\n{rendered}")

    def _check_role_cardinality(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        counts = Counter(action.role for action in actions)
        findings: list[Finding] = []
        for role, configuration in self.deployment.required_roles.items():
            minimum = int(configuration.get("min", 0))
            maximum = int(configuration.get("max", minimum))
            count = counts[role]
            if count < minimum:
                findings.append(
                    Finding(
                        "PIPE-ROLE-MIN",
                        "ERROR",
                        f"Role {role.value!r} requires at least {minimum} "
                        f"actions but graph contains {count}",
                    )
                )
            if count > maximum:
                findings.append(
                    Finding(
                        "PIPE-ROLE-MAX",
                        "ERROR",
                        f"Role {role.value!r} allows at most {maximum} "
                        f"actions but graph contains {count}",
                    )
                )
        return findings

    def _check_role_mutation(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        policies = self.role_policy.get("roles", {})
        findings: list[Finding] = []
        for action in actions:
            role_config = policies.get(action.role.value)
            if not isinstance(role_config, Mapping):
                findings.append(
                    Finding(
                        "POLICY-ROLE-MISSING",
                        "ERROR",
                        f"No role capability policy exists for {action.role.value!r}",
                        action.id,
                    )
                )
                continue
            mutation_allowed = bool(role_config.get("mutation_allowed", False))
            if action.mutation and not mutation_allowed:
                findings.append(
                    Finding(
                        "PIPE-MUTATION-ROLE",
                        "ERROR",
                        f"Role {action.role.value!r} is not allowed to mutate",
                        action.id,
                    )
                )
        return findings

    def _check_executor_dependencies(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.EXECUTOR:
                continue
            missing = [
                dependency for dependency in action.depends_on if dependency not in action_by_id
            ]
            if missing:
                findings.append(
                    Finding(
                        "PIPE-DEP-MISSING",
                        "ERROR",
                        "Action depends on unknown action id(s): " + ", ".join(sorted(missing)),
                        action.id,
                    )
                )
                continue
            dependencies = [action_by_id[dependency] for dependency in action.depends_on]
            has_synthesis = any(dependency.role is Role.SYNTHESIS for dependency in dependencies)
            if not has_synthesis:
                findings.append(
                    Finding(
                        "PIPE-001",
                        "ERROR",
                        "Executor must depend directly on a synthesis action",
                        action.id,
                    )
                )
        return findings

    def _check_reviewer_independence(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.REVIEWER:
                continue
            missing = [source for source in action.independent_from if source not in action_by_id]
            if missing:
                findings.append(
                    Finding(
                        "PIPE-INDEP-MISSING",
                        "ERROR",
                        "independent_from references unknown action id(s): "
                        + ", ".join(sorted(missing)),
                        action.id,
                    )
                )
                continue
            executor_dependencies = {
                source
                for source in action.independent_from
                if action_by_id[source].role is Role.EXECUTOR
            }
            if not executor_dependencies:
                findings.append(
                    Finding(
                        "PIPE-004",
                        "ERROR",
                        "Reviewer must declare independence from at least one executor action",
                        action.id,
                    )
                )
            if action.mutation:
                findings.append(
                    Finding(
                        "PIPE-REVIEW-MUTATION",
                        "ERROR",
                        "Independent reviewer cannot mutate",
                        action.id,
                    )
                )
        return findings

    def _check_verification_before_review(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        action_by_id = {action.id: action for action in actions}
        findings: list[Finding] = []
        for action in action_by_id.values():
            if action.role is not Role.REVIEWER:
                continue
            missing = [
                dependency for dependency in action.depends_on if dependency not in action_by_id
            ]
            if missing:
                findings.append(
                    Finding(
                        "PIPE-DEP-MISSING",
                        "ERROR",
                        "Action depends on unknown action id(s): " + ", ".join(sorted(missing)),
                        action.id,
                    )
                )
                continue
            dependencies = [action_by_id[dependency] for dependency in action.depends_on]
            verifier_count = sum(dependency.role is Role.VERIFIER for dependency in dependencies)
            if verifier_count < 1:
                findings.append(
                    Finding(
                        "PIPE-005",
                        "ERROR",
                        "Reviewer must depend on at least one verifier",
                        action.id,
                    )
                )
        return findings

    def _check_human_merge_policy(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        for action in actions:
            forbidden = {
                "merge",
                "merge_pull_request",
                "admin_merge",
                "force_push",
            }
            raw_operations = action.metadata.get("operations", [])
            if raw_operations in (None, []):
                declared_operations: set[str] = set()
            elif not isinstance(raw_operations, list) or any(
                not isinstance(item, str) for item in raw_operations
            ):
                findings.append(
                    Finding(
                        "PIPE-OPS-TYPE",
                        "ERROR",
                        "metadata.operations must be a list of strings",
                        action.id,
                    )
                )
                continue
            else:
                declared_operations = set(raw_operations)
            unsafe = forbidden & declared_operations
            if unsafe:
                findings.append(
                    Finding(
                        "PIPE-008",
                        "ERROR",
                        "Action declares forbidden autonomous operations: "
                        + ", ".join(sorted(unsafe)),
                        action.id,
                    )
                )
        return findings

    def _check_claim_modes(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        for action in actions:
            write_claims = [claim for claim in action.claims if claim.mode == "write"]
            if action.mutation and not write_claims:
                findings.append(
                    Finding(
                        "PIPE-WRITE-CLAIM",
                        "ERROR",
                        "Mutation action requires at least one exclusive write claim",
                        action.id,
                    )
                )
            if not action.mutation and write_claims:
                findings.append(
                    Finding(
                        "PIPE-READONLY-WRITE-CLAIM",
                        "ERROR",
                        "Non-mutation action cannot request write claims",
                        action.id,
                    )
                )
        return findings

    def _check_completion_contracts(
        self,
        actions: Iterable[Action],
    ) -> list[Finding]:
        findings: list[Finding] = []
        expected_artifacts = {
            Role.RECON: "ReconReport",
            Role.SYNTHESIS: "ExecutionBrief",
            Role.EXECUTOR: "ExecutionResult",
            Role.VERIFIER: "VerificationReport",
            Role.REVIEWER: "ReviewVerdict",
            Role.POLLER: "PollReport",
            Role.FAILURE_CLASSIFIER: "RemediationBrief",
            Role.REMEDIATOR: "RemediationResult",
            Role.CONTEXT_COMPILER: "ContextPack",
            Role.SENTINEL: "SentinelReport",
            Role.EVIDENCE_WRITER: "EvidenceReceipt",
        }
        for action in actions:
            expected = expected_artifacts.get(action.role)
            if expected and action.completion.artifact_kind != expected:
                findings.append(
                    Finding(
                        "PIPE-ARTIFACT-KIND",
                        "ERROR",
                        f"Role {action.role.value!r} must produce "
                        f"{expected!r}, not "
                        f"{action.completion.artifact_kind!r}",
                        action.id,
                    )
                )
        return findings


def main() -> int:
    raise SystemExit("graph_linter file-path CLI is disabled; call lint_graph()")


if __name__ == "__main__":
    raise SystemExit(main())
