"""Intent Resolver: user goal -> INTENT_RESOLUTION.yaml (contract §5-§6, §14)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .intent import Intent, intent_id
from .mission_admission import (
    MissionAdmission,
    MissionAdmissionError,
    mission_narrowed_ceiling,
    validate_mission_context,
)
from .policy import DEFAULT_PROFILE, load_policy, narrowed_ceiling
from .program_action import decide
from .repo_truth import RepoTruth, discover

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "intent-resolution.schema.json"

REMOTE_RE = re.compile(
    r"(?:git@|https://|ssh://git@)?([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$"
)


@dataclass
class ResolutionIssue:
    topic: str
    issue_class: str  # evidence | policy | reversible | authority
    resolved_value: Any = None
    provenance: dict[str, Any] | None = None
    blocks: list[str] = None  # type: ignore[assignment]


def resolve(
    intent: Intent,
    truth: RepoTruth | None = None,
    profile_id: str | None = None,
    existing_programs: list[dict[str, Any]] | None = None,
    admission: MissionAdmission | None = None,
) -> dict[str, Any]:
    """Produce the canonical INTENT_RESOLUTION artifact for a parsed intent.

    Classification (contract §6):
      evidence-determined  -> auto-resolve with evidence provenance
      policy-determined    -> auto-resolve with policy provenance
      reversible planning  -> auto within the authority envelope
      authority-bearing    -> explicit decision/Unknown; block only dependents

    ``admission`` is an optional validated :class:`MissionAdmission`. When it is
    present the resolution is Mission-bound: the resolved authorization ceiling
    is intersected action-by-action with the Mission ceiling, and the exact
    minimal Mission projection is emitted as first-class ``mission_context``
    provenance. Mission can only narrow. When it is absent the resolution is an
    ordinary unbound one and nothing about this function's behaviour changes.
    """
    if admission is not None:
        # Fail closed on anything that merely looks like an admission: a
        # duck-typed object could carry a Mission digest nobody parsed.
        if not isinstance(admission, MissionAdmission):
            raise MissionAdmissionError(
                "mission admission must be a validated MissionAdmission from "
                "compiler.mission_admission.admit()"
            )
        validate_mission_context(admission.mission_context())

    truth = truth or discover(Path.cwd())
    profile_id = profile_id or intent.policy_profile or DEFAULT_PROFILE
    policy = load_policy(profile_id)

    issues: list[ResolutionIssue] = []

    # --- target resolution -------------------------------------------------
    targets, target_evidence = _resolve_targets(intent, truth, issues)
    owner = _resolve_owner(truth, policy, issues)
    ceiling = _resolve_ceiling(policy, intent, issues)
    if admission is not None:
        ceiling = mission_narrowed_ceiling(ceiling, admission)
        issues.append(
            ResolutionIssue(
                topic=(
                    "Authorization ceiling intersected with the Mission authority ceiling of "
                    f"{admission.authority_reference()}; a Mission may narrow an action and "
                    "never widen one."
                ),
                issue_class="decision",
                resolved_value=ceiling,
                provenance={"type": "decision", "ref": admission.authority_reference()},
            )
        )
    test_command = _resolve_test_command(truth, issues)

    requirements: list[dict[str, Any]] = []
    for issue in issues:
        if issue.issue_class != "authority" and issue.provenance:
            requirements.append(
                {
                    "id": f"REQ-{len(requirements) + 1:03d}",
                    "statement": issue.topic,
                    "source": issue.provenance,
                }
            )
    requirements.append(
        {
            "id": f"REQ-{len(requirements) + 1:03d}",
            "statement": "Execute within the authorization ceiling of the active autonomy profile; "
            "no remote mutation beyond the published campaign ceiling.",
            "source": {"type": "policy", "ref": profile_id},
        }
    )

    unknowns: list[dict[str, Any]] = []
    blocked_tasks: set[str] = set()
    for issue in issues:
        if issue.issue_class != "authority":
            continue
        unknown_id = f"UNK-{len(unknowns) + 1:03d}"
        unknowns.append(
            {
                "id": unknown_id,
                "topic": issue.topic,
                "blocks": sorted(issue.blocks or []),
                "safe_state": "Do not execute dependent work; independent lanes may proceed.",
                "resolution_requirements": [f"Resolve {issue.topic} via accepted authority."],
            }
        )
        blocked_tasks.update(issue.blocks or [])

    requires_human = [f"DEC-{index + 1:03d}" for index in range(len(unknowns))]

    if not targets:
        synthesis_status = "blocked"
    elif requires_human:
        synthesis_status = "requires_authority"
    else:
        synthesis_status = "ready"

    confidence = {
        "intent_resolution": "high",
        "target_resolution": "high" if targets else "low",
        "authority_resolution": "high" if owner else "medium",
        "repository_understanding": _repo_confidence(truth),
    }

    resolution: dict[str, Any] = {
        "schema": "program-execution.intent-resolution.v1",
        "intent": {
            "id": intent_id(intent),
            "original_objective": intent.objective,
            "normalized_objective": intent.objective,
        },
        "targets": [
            {
                "repository_id": repository_id,
                "resolution_source": "evidence" if evidence else "user",
                "evidence_ids": list(evidence),
                "confidence": "high" if evidence else "medium",
            }
            for repository_id, evidence in targets
        ],
        "governing_authority": {
            "policy_profile": profile_id,
            "source_ids": ["POLICY:" + profile_id],
            "decision_ids": [d for d in requires_human],
        },
        "derived_requirements": requirements,
        "decisions": {
            "accepted_from_authority": [],
            "accepted_from_policy": ["POLICY:" + profile_id],
            "requires_human_authority": requires_human,
        },
        "unknowns": unknowns,
        "evidence": {
            "authoritative": [e for e in target_evidence],
            "supporting": ["EVID-REPO-" + kind for kind in _evidence_kinds(truth)],
            "stale_or_conflicting": [],
        },
        "program_action": decide(
            existing_programs or [],
            {
                "intent": {
                    "normalized_objective": intent.objective,
                },
                "targets": [{"repository_id": r} for r, _ in targets],
            },
        ),
        "confidence": confidence,
        "synthesis_status": synthesis_status,
    }
    if admission is not None:
        # First-class, not `_compiler_meta`: write_resolution() strips private
        # keys, and the Mission projection has to reach the synthesizer.
        reference = admission.authority_reference()
        resolution["mission_context"] = admission.mission_context()
        resolution["governing_authority"]["source_ids"].append(reference)
        resolution["decisions"]["accepted_from_authority"].append(reference)
    _validate(resolution)
    resolution["_compiler_meta"] = {
        "ceiling": ceiling,
        "owner": owner,
        "test_command": test_command,
        "target_root": str(truth.root),
        "target_revision": truth.revision,
    }
    return resolution


def _resolve_targets(
    intent: Intent, truth: RepoTruth, issues: list[ResolutionIssue]
) -> tuple[list[tuple[str, str]], list[str]]:
    resolved: list[tuple[str, str]] = []
    evidence: list[str] = []
    if intent.targets:
        for target in intent.targets:
            resolved.append((target, []))
        return resolved, evidence
    if truth.remote:
        repo_id = _repo_id_from_remote(truth.remote)
        if repo_id:
            resolved.append((repo_id, ["EVID-TARGET-001"]))
            evidence.append("EVID-TARGET-001")
            issues.append(
                ResolutionIssue(
                    topic=(
                        f"Target repository resolved from verified repository evidence: {repo_id}"
                    ),
                    issue_class="evidence",
                    resolved_value=repo_id,
                    provenance={"type": "evidence", "ref": f"git remote origin @ {truth.remote}"},
                )
            )
            return resolved, evidence
    issues.append(
        ResolutionIssue(
            topic="Target repository could not be resolved; no user target, registered target, "
            "or repository evidence available.",
            issue_class="authority",
            blocks=["TASK-002"],
        )
    )
    return resolved, evidence


def _resolve_owner(
    truth: RepoTruth, policy: dict[str, Any], issues: list[ResolutionIssue]
) -> str | None:
    if truth.owner:
        issues.append(
            ResolutionIssue(
                topic=f"Program owner resolved from repository truth: {truth.owner}",
                issue_class="evidence",
                resolved_value=truth.owner,
                provenance={"type": "evidence", "ref": "AGENTS.md/CANONICAL_LAW owner field"},
            )
        )
        return truth.owner
    default_owner = (policy.get("provenance") or [{}])[0].get("default_owner") if policy else None
    if default_owner:
        issues.append(
            ResolutionIssue(
                topic=f"Program owner resolved from policy default: {default_owner}",
                issue_class="policy",
                resolved_value=default_owner,
                provenance={"type": "policy", "ref": policy["id"]},
            )
        )
        return str(default_owner)
    issues.append(
        ResolutionIssue(
            topic="Program owner is unresolved; no owner evidence and no governing default policy "
            "exist. No owner will be invented.",
            issue_class="authority",
            blocks=["TASK-001"],
        )
    )
    return None


def _resolve_ceiling(
    policy: dict[str, Any], intent: Intent, issues: list[ResolutionIssue]
) -> dict[str, bool]:
    try:
        ceiling = narrowed_ceiling(policy, intent.constraints)
    except ValueError as exc:
        issues.append(
            ResolutionIssue(
                topic=str(exc),
                issue_class="authority",
                blocks=["TASK-002"],
            )
        )
        return dict(policy["authorization_ceiling"])
    issues.append(
        ResolutionIssue(
            topic="Authorization ceiling applied from the active autonomy policy profile.",
            issue_class="policy",
            resolved_value=ceiling,
            provenance={"type": "policy", "ref": policy["id"]},
        )
    )
    return ceiling


def _resolve_test_command(truth: RepoTruth, issues: list[ResolutionIssue]) -> str | None:
    if truth.test_command:
        issues.append(
            ResolutionIssue(
                topic=f"Test command resolved from repository truth: {truth.test_command}",
                issue_class="evidence",
                resolved_value=truth.test_command,
                provenance={
                    "type": "evidence",
                    "ref": truth.source_priority.get("test_command", ""),
                },
            )
        )
        return truth.test_command
    return None


def _repo_confidence(truth: RepoTruth) -> str:
    if truth.revision and truth.owner:
        return "high"
    if truth.revision or truth.owner:
        return "medium"
    return "low"


def _evidence_kinds(truth: RepoTruth) -> list[str]:
    kinds = []
    if truth.revision:
        kinds.append("revision")
    if truth.dpk:
        kinds.append("dpk")
    if truth.adr_files:
        kinds.append("adr")
    return kinds


def _repo_id_from_remote(remote: str) -> str | None:
    match = REMOTE_RE.search(remote.rstrip("/"))
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def _schema_registry() -> Registry:
    """Resolve compiler schema ``$ref`` by ``$id``.

    ``mission_context`` refs the canonical mission-context schema rather than
    restating its four fields, so the projection keeps exactly one owner and
    cannot drift between the compiler and the artifact it emits.
    """
    resources = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        schema_id = document.get("$id")
        if schema_id:
            resources.append((schema_id, Resource.from_contents(document)))
    return Registry().with_resources(resources)


def _validate(resolution: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, registry=_schema_registry()).iter_errors(resolution),
        key=lambda e: list(e.path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"resolution violates program-execution.intent-resolution.v1: {details}")


def write_resolution(resolution: dict[str, Any], path: Path) -> Path:
    payload = {k: v for k, v in resolution.items() if not k.startswith("_")}
    path.write_text(yaml.safe_dump(payload, sort_keys=False, width=110), encoding="utf-8")
    return path


__all__ = [
    "ResolutionIssue",
    "resolve",
    "write_resolution",
]
