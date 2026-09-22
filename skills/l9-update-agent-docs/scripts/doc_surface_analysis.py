"""Closed-world assessment of executable repository contract surfaces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from root_contracts import assess_architecture_index, assess_root_agent_contract
from surface_analyzers.makefile import analyze as analyze_makefile
from surface_analyzers.openapi import analyze as analyze_openapi
from surface_analyzers.pyproject import analyze as analyze_pyproject
from surface_analyzers.workflow import analyze as analyze_workflow

Analyzer = Callable[[Path, Path], dict[str, Any]]

ANALYZERS: dict[str, Analyzer] = {
    "architecture-index-contract-v1": analyze_makefile,
    "makefile-contract-v1": analyze_makefile,
    "openapi-contract-v1": analyze_openapi,
    "python-project-contract-v1": analyze_pyproject,
    "root-agent-contract-v1": analyze_makefile,
    "workflow-contract-v1": analyze_workflow,
}


def _hash(*parts: str, size: int = 12) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:size]


def _validation_result(
    name: str,
    status: str,
    detail: str,
    evidence_ids: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence_ids": sorted(set(evidence_ids)),
        "detail": detail,
    }


def _guard_resolution(
    root: Path,
    guard_id: str | None,
    target: str | None,
) -> dict[str, Any] | None:
    if not guard_id:
        return None
    if guard_id == "external-owner":
        # The repository-docs skill may assess this target but may not mutate
        # it. Its semantic owner receives any deterministic findings.
        return None
    if guard_id != "root-file-protection":
        return {
            "id": guard_id,
            "status": "BLOCKED",
            "source": None,
            "rule": None,
            "tier": None,
            "justification_marker": None,
            "evidence_ids": [],
            "detail": f"unknown mutation guard {guard_id!r}",
        }
    source = "ops/config/root-file-protection.json"
    path = root / source
    if not path.is_file():
        # Consumer repos do not declare this Cursor-Governance guard.
        # Assessment still runs; the guard applies only when the file exists.
        return None
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "id": guard_id,
            "status": "BLOCKED",
            "source": source,
            "rule": None,
            "tier": None,
            "justification_marker": None,
            "evidence_ids": [],
            "detail": f"root-file protection contract is unreadable: {exc}",
        }
    entry = next(
        (row for row in contract.get("protected_files", []) if row.get("path") == target),
        None,
    )
    if entry is None:
        return {
            "id": guard_id,
            "status": "BLOCKED",
            "source": source,
            "rule": None,
            "tier": None,
            "justification_marker": None,
            "evidence_ids": [],
            "detail": f"target {target!r} is not declared in root-file protection",
        }
    evidence_id = f"ev-{_hash('guard', source, str(target), str(entry.get('rule')))}"
    return {
        "id": guard_id,
        "status": "RESOLVED",
        "source": source,
        "rule": entry.get("rule"),
        "tier": entry.get("tier"),
        "justification_marker": (contract.get("justification") or {}).get("marker"),
        "evidence_ids": [evidence_id],
        "detail": "mutation guard resolved from canonical root-file protection contract",
    }


def _ownership(spec: dict[str, Any]) -> dict[str, Any]:
    declared = spec.get("ownership") or {}
    mutation = spec.get("mutation") or {}
    return {
        "obligation_owner": spec["owner"],
        "semantic_owner": declared.get("semantic_owner", spec["owner"]),
        "execution_owner": declared.get("execution_owner", spec["owner"]),
        "mutation_guard": mutation.get("guard"),
    }


def _not_required_assessment() -> dict[str, Any]:
    return {
        "analyzer": None,
        "status": "NOT_REQUIRED",
        "findings": [],
        "disposition": "NOT_APPLICABLE",
        "mutation_guard": None,
    }


def assess_surface_obligations(
    root: Path,
    policy: dict[str, Any],
    obligations: list[dict[str, Any]],
    *,
    snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Attach deterministic assessment and separated ownership to obligations."""

    for obligation in obligations:
        surface = obligation["surface"]
        spec = policy["surfaces"][surface]
        obligation["ownership"] = _ownership(spec)
        analysis = spec.get("analysis")
        if not analysis:
            obligation["assessment"] = _not_required_assessment()
            continue

        analyzer_id = str(analysis.get("analyzer") or "")
        target_rel = obligation["target"].get("path")
        if not target_rel or not obligation["target"].get("present"):
            obligation["assessment"] = {
                "analyzer": analyzer_id or None,
                "status": "NOT_APPLICABLE",
                "findings": [],
                "disposition": "NOT_APPLICABLE",
                "mutation_guard": None,
            }
            continue

        guard = _guard_resolution(
            root,
            obligation["ownership"]["mutation_guard"],
            target_rel,
        )
        if guard and guard["status"] == "RESOLVED":
            for evidence_id in guard["evidence_ids"]:
                obligation["evidence"].append(
                    {
                        "id": evidence_id,
                        "type": "validation",
                        "source": guard["source"],
                        "locator": {
                            "kind": "rule",
                            "value": f"protected_files.{target_rel}",
                        },
                        "epistemic": "CONFIRMED",
                        "supports": "mutation_guard",
                    }
                )
        if guard and guard["status"] == "BLOCKED" and guard.get("source") is None:
            obligation["assessment"] = {
                "analyzer": analyzer_id or None,
                "status": "BLOCKED",
                "findings": [],
                "disposition": "UNKNOWN",
                "mutation_guard": guard,
            }
            obligation["lifecycle"] = {
                "status": "BLOCKED",
                "reason": "operational surface mutation guard could not be resolved",
                "terminal": False,
            }
            obligation["blockers"] = sorted(set(obligation["blockers"] + [guard["detail"]]))
            continue

        analyzer = ANALYZERS.get(analyzer_id)
        if analyzer is None:
            detail = f"surface analyzer {analyzer_id!r} is not registered"
            obligation["assessment"] = {
                "analyzer": analyzer_id or None,
                "status": "BLOCKED",
                "findings": [],
                "disposition": "UNKNOWN",
                "mutation_guard": guard,
            }
            obligation["lifecycle"] = {
                "status": "BLOCKED",
                "reason": "operational surface analyzer is unresolved",
                "terminal": False,
            }
            obligation["blockers"] = sorted(set(obligation["blockers"] + [detail]))
            continue

        root_contract = analyzer_id in {
            "architecture-index-contract-v1",
            "root-agent-contract-v1",
        }
        if root_contract and not isinstance(snapshot, dict):
            detail = "snapshot-aware root contract assessment requires consumer snapshot evidence"
            obligation["assessment"] = {
                "analyzer": analyzer_id,
                "status": "BLOCKED",
                "findings": [],
                "disposition": "UNKNOWN",
                "mutation_guard": guard,
            }
            obligation["lifecycle"] = {
                "status": "BLOCKED",
                "reason": "root contract evidence is unavailable",
                "terminal": False,
            }
            obligation["blockers"] = sorted(set(obligation["blockers"] + [detail]))
            continue
        if analyzer_id == "architecture-index-contract-v1":
            result = assess_architecture_index(root, root / target_rel, snapshot)
        elif analyzer_id == "root-agent-contract-v1":
            result = assess_root_agent_contract(root, root / target_rel, snapshot)
        else:
            result = analyzer(root, root / target_rel)
        if result.get("status") == "BLOCKED":
            blockers = [str(item) for item in result.get("blockers", [])]
            obligation["assessment"] = {
                "analyzer": analyzer_id,
                "status": "BLOCKED",
                "findings": [],
                "disposition": "UNKNOWN",
                "mutation_guard": guard,
            }
            obligation["lifecycle"] = {
                "status": "BLOCKED",
                "reason": "operational surface assessment could not complete",
                "terminal": False,
            }
            obligation["blockers"] = sorted(set(obligation["blockers"] + blockers))
            continue

        normalized: list[dict[str, Any]] = []
        finding_evidence_ids: list[str] = []
        for raw in result.get("findings", []):
            line = raw.get("line")
            evidence_source = str(raw.get("source") or target_rel)
            finding_id = "sf-" + _hash(
                surface,
                str(raw.get("rule_id")),
                str(raw.get("property")),
                evidence_source,
                str(line),
            )
            evidence_id = f"ev-{_hash('assessment', evidence_source, finding_id)}"
            finding_evidence_ids.append(evidence_id)
            locator = f"{evidence_source}:{line}" if line else evidence_source
            obligation["evidence"].append(
                {
                    "id": evidence_id,
                    "type": "validation",
                    "source": evidence_source,
                    "locator": {"kind": "path", "value": locator},
                    "epistemic": "CONFIRMED",
                    "supports": f"surface_assessment:{finding_id}",
                }
            )
            normalized.append(
                {
                    "finding_id": finding_id,
                    "rule_id": str(raw["rule_id"]),
                    "severity": str(raw.get("severity") or "material"),
                    "property": str(raw["property"]),
                    "observed_state": str(raw["observed_state"]),
                    "expected_state": str(raw["expected_state"]),
                    "evidence_ids": [evidence_id],
                    "remediation_class": str(raw.get("remediation_class") or "SURGICAL"),
                }
            )

        if normalized:
            handoff = root_contract or any(
                row.get("remediation_class") == "HANDOFF" for row in normalized
            )
            if handoff:
                obligation["assessment"] = {
                    "analyzer": analyzer_id,
                    "status": "NEEDS_IMPROVEMENT",
                    "findings": normalized,
                    "disposition": "HANDOFF",
                    "mutation_guard": guard,
                }
                obligation["required_action"].update(
                    type="HANDOFF",
                    mode="EXTERNAL_OWNER",
                    owner=obligation["ownership"]["semantic_owner"],
                )
                obligation["lifecycle"] = {
                    "status": "HANDOFF_REQUIRED",
                    "reason": "operational-surface finding belongs to another authority",
                    "terminal": False,
                }
            elif guard and guard["status"] == "BLOCKED":
                obligation["assessment"] = {
                    "analyzer": analyzer_id,
                    "status": "BLOCKED",
                    "findings": normalized,
                    "disposition": "UNKNOWN",
                    "mutation_guard": guard,
                }
                obligation["lifecycle"] = {
                    "status": "BLOCKED",
                    "reason": "operational surface mutation guard could not be resolved",
                    "terminal": False,
                }
                obligation["blockers"] = sorted(set(obligation["blockers"] + [guard["detail"]]))
            else:
                obligation["assessment"] = {
                    "analyzer": analyzer_id,
                    "status": "NEEDS_IMPROVEMENT",
                    "findings": normalized,
                    "disposition": "IMPROVE",
                    "mutation_guard": guard,
                }
                obligation["required_action"].update(
                    type="REFRESH",
                    mode="OWNER_NATIVE",
                    owner=obligation["ownership"]["execution_owner"],
                )
                obligation["lifecycle"] = {
                    "status": "OPEN",
                    "reason": "material operational-surface findings remain unresolved",
                    "terminal": False,
                }
            required = set(obligation["validation"]["required"])
            required.add("material_improvement")
            obligation["validation"]["required"] = sorted(required)
            existing = {row["name"]: row for row in obligation["validation"]["results"]}
            existing["material_improvement"] = _validation_result(
                "material_improvement",
                "UNKNOWN",
                "material assessment findings remain on the evaluated target",
                finding_evidence_ids,
            )
            obligation["validation"]["results"] = [existing[name] for name in sorted(existing)]
        elif root_contract:
            # Root-document validation is evidence for the existing semantic
            # obligation.  A clean structural check must not erase a Harvest
            # refresh requirement by replacing it with PRESERVE.
            obligation["assessment"] = {
                "analyzer": analyzer_id,
                "status": "PASS",
                "findings": [],
                "disposition": "PRESERVE",
                "mutation_guard": guard,
            }
        else:
            obligation["assessment"] = {
                "analyzer": analyzer_id,
                "status": "PASS",
                "findings": [],
                "disposition": "PRESERVE",
                "mutation_guard": guard,
            }
            obligation["required_action"].update(
                type="PRESERVE",
                mode="NONE",
                owner=obligation["ownership"]["execution_owner"],
            )
            existing = {row["name"]: row for row in obligation["validation"]["results"]}
            if "target_freshness" in obligation["validation"]["required"]:
                existing["target_freshness"] = _validation_result(
                    "target_freshness",
                    "NotApplicable",
                    "deterministic assessment found no target mutation requirement",
                    [],
                )
            obligation["validation"]["results"] = [existing[name] for name in sorted(existing)]
            obligation["lifecycle"] = {
                "status": "PRESERVED",
                "reason": "deterministic surface assessment found no material improvement",
                "terminal": True,
            }
    return obligations
