from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from autonomy.errors import ContractError


class Role(StrEnum):
    COORDINATOR = "coordinator"
    RECON = "recon"
    SYNTHESIS = "synthesis"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    REVIEWER = "reviewer"
    POLLER = "poller"
    FAILURE_CLASSIFIER = "failure_classifier"
    REMEDIATOR = "remediator"
    CONTEXT_COMPILER = "context_compiler"
    SENTINEL = "sentinel"
    EVIDENCE_WRITER = "evidence_writer"


class ActionKind(StrEnum):
    WORK = "work"
    POLL = "poll"
    HUMAN_GATE = "human_gate"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"


class CampaignState(StrEnum):
    DRAFT = "DRAFT"
    DIAGNOSED = "DIAGNOSED"
    AUTHORIZED = "AUTHORIZED"
    PLANNED = "PLANNED"
    LOCKED = "LOCKED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class ResourceClaim:
    key: str
    mode: str
    exclusive: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ResourceClaim:
        key = require_nonempty_string(value, "key")
        mode = require_nonempty_string(value, "mode")
        if mode not in {"read", "write", "observe"}:
            raise ContractError(f"Unsupported resource claim mode {mode!r} for {key!r}")
        exclusive = bool(value.get("exclusive", mode == "write"))
        if mode == "write" and not exclusive:
            raise ContractError(f"Write claim {key!r} must be exclusive")
        return cls(key=key, mode=mode, exclusive=exclusive)


@dataclass(frozen=True)
class CompletionPredicate:
    artifact_kind: str
    required_fields: tuple[str, ...] = ()
    require_base_sha_match: bool = True
    require_empty_blockers: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CompletionPredicate:
        artifact_kind = require_nonempty_string(value, "artifact_kind")
        required_fields = tuple(
            require_string_list(value.get("required_fields", []), "required_fields")
        )
        return cls(
            artifact_kind=artifact_kind,
            required_fields=required_fields,
            require_base_sha_match=bool(value.get("require_base_sha_match", True)),
            require_empty_blockers=bool(value.get("require_empty_blockers", False)),
        )


@dataclass(frozen=True)
class Action:
    id: str
    role: Role
    kind: ActionKind
    depends_on: tuple[str, ...]
    mutation: bool
    resource_class: str
    claims: tuple[ResourceClaim, ...]
    completion: CompletionPredicate
    conditional_on: str | None = None
    independent_from: tuple[str, ...] = ()
    priority_weight: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Action:
        action_id = require_nonempty_string(value, "id")
        try:
            role = Role(require_nonempty_string(value, "role"))
        except ValueError as exc:
            raise ContractError(
                f"Action {action_id!r} has unsupported role: {value.get('role')!r}"
            ) from exc
        try:
            kind = ActionKind(value.get("kind", "work"))
        except ValueError as exc:
            raise ContractError(
                f"Action {action_id!r} has unsupported kind: {value.get('kind')!r}"
            ) from exc
        depends_on = tuple(require_string_list(value.get("depends_on", []), "depends_on"))
        claims_data = value.get("claims", [])
        if not isinstance(claims_data, list):
            raise ContractError(f"Action {action_id!r} field 'claims' must be a list")
        claims = tuple(ResourceClaim.from_dict(item) for item in claims_data)
        completion_data = value.get("completion")
        if not isinstance(completion_data, Mapping):
            raise ContractError(f"Action {action_id!r} requires a completion object")
        independent_from = tuple(
            require_string_list(
                value.get("independent_from", []),
                "independent_from",
            )
        )
        priority_weight = value.get("priority_weight", 1.0)
        if not isinstance(priority_weight, (int, float)) or priority_weight <= 0:
            raise ContractError(f"Action {action_id!r} priority_weight must be positive")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ContractError(f"Action {action_id!r} metadata must be an object")
        if "operations" in metadata:
            require_string_list(
                metadata.get("operations"),
                f"Action {action_id!r} metadata.operations",
            )
        return cls(
            id=action_id,
            role=role,
            kind=kind,
            depends_on=depends_on,
            mutation=bool(value.get("mutation", False)),
            resource_class=require_nonempty_string(value, "resource_class"),
            claims=claims,
            completion=CompletionPredicate.from_dict(completion_data),
            conditional_on=optional_nonempty_string(
                value.get("conditional_on"),
                "conditional_on",
            ),
            independent_from=independent_from,
            priority_weight=float(priority_weight),
            metadata=dict(metadata),
        )


@dataclass(frozen=True)
class CampaignAuthorization:
    schema_version: str
    campaign_id: str
    objective: str
    authority: Mapping[str, Any]
    scope: Mapping[str, Any]
    budgets: Mapping[str, Any]
    validation: Mapping[str, Any]
    base_state: Mapping[str, Any]
    revocation: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CampaignAuthorization:
        required_objects = (
            "authority",
            "scope",
            "budgets",
            "validation",
            "base_state",
            "revocation",
        )
        for field_name in required_objects:
            if not isinstance(value.get(field_name), Mapping):
                raise ContractError(f"Campaign field {field_name!r} must be an object")
        campaign = cls(
            schema_version=require_nonempty_string(value, "schema_version"),
            campaign_id=require_nonempty_string(value, "campaign_id"),
            objective=require_nonempty_string(value, "objective"),
            authority=dict(value["authority"]),
            scope=dict(value["scope"]),
            budgets=dict(value["budgets"]),
            validation=dict(value["validation"]),
            base_state=dict(value["base_state"]),
            revocation=dict(value["revocation"]),
        )
        campaign.validate_semantics()
        return campaign

    def validate_semantics(self) -> None:
        allowed_operations = set(
            require_string_list(
                self.scope.get("allowed_operations", []),
                "scope.allowed_operations",
            )
        )
        forbidden_operations = set(
            require_string_list(
                self.scope.get("forbidden_operations", []),
                "scope.forbidden_operations",
            )
        )
        overlap = allowed_operations & forbidden_operations
        if overlap:
            raise ContractError(
                "Campaign operations cannot be both allowed and forbidden: "
                + ", ".join(sorted(overlap))
            )
        forbidden_merge_operations = {
            "merge",
            "merge_pull_request",
            "admin_merge",
            "force_push",
        }
        unsafe = allowed_operations & forbidden_merge_operations
        if unsafe:
            raise ContractError(
                "Autonomy campaign grants forbidden high-risk operations: "
                + ", ".join(sorted(unsafe))
            )
        if self.validation.get("independent_review_required") is not True:
            raise ContractError("Campaign must require independent review")
        if self.validation.get("human_merge_required") is not True:
            raise ContractError("Campaign must require human-owned merge")
        base_sha = self.base_state.get("commit_sha")
        if not isinstance(base_sha, str) or not base_sha.strip():
            raise ContractError("Campaign base_state.commit_sha must be resolved before execution")
        normalized_sha = base_sha.strip().lower()
        if normalized_sha.startswith("replace_with") or "placeholder" in normalized_sha:
            raise ContractError(
                "Campaign base_state.commit_sha is still a placeholder; resolve the base SHA"
            )
        if len(normalized_sha) < 7 or any(ch not in "0123456789abcdef" for ch in normalized_sha):
            raise ContractError(
                "Campaign base_state.commit_sha must be a resolved git SHA (hex, ≥7 chars)"
            )
        max_mutation = self.budgets.get("max_mutation_agents")
        if not isinstance(max_mutation, int) or max_mutation < 1:
            raise ContractError("budgets.max_mutation_agents must be a positive integer")


@dataclass(frozen=True)
class DeploymentManifest:
    schema_version: str
    deployment_id: str
    campaign_id: str
    graph_id: str
    required_roles: Mapping[Role, Mapping[str, Any]]
    fail_closed: Mapping[str, bool]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> DeploymentManifest:
        roles_raw = value.get("required_roles")
        if not isinstance(roles_raw, Mapping):
            raise ContractError("Deployment required_roles must be an object")
        roles: dict[Role, Mapping[str, Any]] = {}
        for role_name, role_config in roles_raw.items():
            try:
                role = Role(role_name)
            except ValueError as exc:
                raise ContractError(f"Unsupported deployment role: {role_name!r}") from exc
            if not isinstance(role_config, Mapping):
                raise ContractError(f"Role configuration for {role_name!r} must be an object")
            minimum = role_config.get("min", 0)
            maximum = role_config.get("max", 0)
            if not isinstance(minimum, int) or minimum < 0:
                raise ContractError(f"Role {role_name!r} min must be a non-negative integer")
            if not isinstance(maximum, int) or maximum < minimum:
                raise ContractError(f"Role {role_name!r} max must be >= min")
            roles[role] = dict(role_config)
        fail_closed_raw = value.get("fail_closed")
        if not isinstance(fail_closed_raw, Mapping):
            raise ContractError("Deployment fail_closed must be an object")
        fail_closed = {str(name): bool(enabled) for name, enabled in fail_closed_raw.items()}
        required_fail_closed = {
            "missing_required_agent",
            "invalid_agent_output",
            "executor_without_synthesis",
            "self_review",
            "unverified_completion",
        }
        disabled = {name for name in required_fail_closed if fail_closed.get(name) is not True}
        if disabled:
            raise ContractError(
                "Mandatory fail-closed controls are missing or disabled: "
                + ", ".join(sorted(disabled))
            )
        return cls(
            schema_version=require_nonempty_string(value, "schema_version"),
            deployment_id=require_nonempty_string(value, "deployment_id"),
            campaign_id=require_nonempty_string(value, "campaign_id"),
            graph_id=require_nonempty_string(value, "graph_id"),
            required_roles=roles,
            fail_closed=fail_closed,
        )


def require_nonempty_string(
    value: Mapping[str, Any],
    field_name: str,
) -> str:
    raw = value.get(field_name)
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError(f"Field {field_name!r} must be a non-empty string")
    return raw.strip()


def optional_nonempty_string(
    raw: Any,
    field_name: str,
) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError(f"Field {field_name!r} must be null or a non-empty string")
    return raw.strip()


def require_string_list(raw: Any, field_name: str) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        raise ContractError(f"Field {field_name!r} must be a list")
    result: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ContractError(f"Field {field_name!r}[{index}] must be a non-empty string")
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise ContractError(f"Field {field_name!r} contains duplicate values")
    return result


def count_roles(actions: Iterable[Action]) -> dict[Role, int]:
    result = {role: 0 for role in Role}
    for action in actions:
        result[action.role] += 1
    return result
