"""Compile repository documentation topology into first-class obligation objects."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from doc_policy import OBLIGATION_SCHEMA, schema_errors, selector_paths

OBLIGATION_ID = "l9.repo-docs.obligation.v1"


def _hash(*parts: str, size: int = 16) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:size]


def _evidence_id(kind: str, value: str) -> str:
    return f"ev-{_hash(kind, value, size=12)}"


def _literal_selector(selectors: list[str]) -> str | None:
    return next((item for item in selectors if not any(char in item for char in "*?[")), None)


def source_changes_for_surface(
    policy: dict[str, Any], impact: dict[str, Any], surface: str
) -> tuple[list[str], list[str]]:
    rules: list[str] = []
    paths: set[str] = set()
    for name, changed in impact.get("matched_rules", {}).items():
        if surface in policy["impact_rules"][name]["surfaces"]:
            rules.append(name)
            paths.update(changed)
    return sorted(rules), sorted(paths)


def semantic_source_digest(
    root: Path,
    policy: dict[str, Any],
    impact: dict[str, Any],
    required_surfaces: list[str],
) -> tuple[str | None, list[str]]:
    active_rules: set[str] = set()
    for surface in required_surfaces:
        active_rules.update(policy["semantic_harvest"]["activation"].get(surface, []))
    paths = sorted(
        {
            path
            for rule in active_rules
            for path in impact.get("matched_rules", {}).get(rule, [])
        }
    )
    if not paths:
        return None, []
    digest = hashlib.sha256()
    for rel in paths:
        digest.update(rel.encode("utf-8") + b"\0")
        path = root / rel
        digest.update(path.read_bytes() if path.is_file() else b"<deleted>")
        digest.update(b"\0")
    return digest.hexdigest(), paths


def _module_targets(
    root: Path,
    policy: dict[str, Any],
    changed: list[str],
) -> list[dict[str, Any]]:
    config_rel = policy["capabilities"]["module_readmes"]["required_paths"]["config"]
    config_path = root / config_rel
    if not config_path.is_file():
        return []
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    subsystems = raw.get("subsystems") or {}
    targets: dict[str, dict[str, Any]] = {}
    for key, spec in subsystems.items():
        if not isinstance(spec, dict) or spec.get("skip"):
            continue
        prefix = str(spec.get("path") or "").strip("/")
        if not prefix:
            continue
        hits = sorted(path for path in changed if path == prefix or path.startswith(prefix + "/"))
        if not hits:
            continue
        target = f"{prefix}/README.md"
        targets[target] = {
            "kind": "generated_file",
            "path": target,
            "selector": f"subsystem:{key}",
            "present": (root / target).is_file(),
            "source_changes": hits,
        }
    return [targets[key] for key in sorted(targets)]


def _generic_targets(
    root: Path,
    surface: str,
    spec: dict[str, Any],
    *,
    llms_enabled: bool,
) -> list[dict[str, Any]]:
    paths = selector_paths(root, spec["selectors"])
    if paths:
        kind = "external" if spec["create_policy"] == "external_only" else "file"
        return [
            {"kind": kind, "path": path, "selector": path, "present": True}
            for path in paths
        ]
    if surface == "llms_txt" and not llms_enabled:
        return [{"kind": "surface", "path": None, "selector": "llms_txt", "present": False}]
    if spec["requirement"] == "conditional" and spec["create_policy"] in {
        "never",
        "external_only",
    }:
        return [{"kind": "surface", "path": None, "selector": None, "present": False}]
    literal = _literal_selector(spec["selectors"])
    kind = "external" if spec["create_policy"] == "external_only" else "file"
    return [{"kind": kind, "path": literal, "selector": literal, "present": False}]


def _execution(spec: dict[str, Any], applicable: bool) -> tuple[str, str | None]:
    if not applicable:
        return "none", None
    if spec["create_policy"] == "generator_owned":
        return "generator", spec.get("generator")
    if spec["authority_class"] == "specialist":
        return "specialist", spec.get("generator")
    if spec["create_policy"] == "external_only" or spec["authority_class"] == "external":
        return "external", spec.get("generator")
    return "owner_native", spec.get("generator")


def _action(spec: dict[str, Any], target: dict[str, Any], applicable: bool) -> tuple[str, str]:
    if not applicable:
        return "NO_ACTION", "NONE"
    if spec["create_policy"] == "generator_owned":
        return "REGENERATE", "OWNER_NATIVE"
    if spec["create_policy"] == "external_only":
        return "HANDOFF", "EXTERNAL_OWNER"
    if not target["present"] and spec["create_policy"] in {"create_if_absent", "create_if_enabled"}:
        return "CREATE", "OWNER_NATIVE"
    return "REFRESH", "OWNER_NATIVE"


def _target_applicable(
    surface: str,
    spec: dict[str, Any],
    target: dict[str, Any],
    *,
    llms_enabled: bool,
) -> bool:
    if surface == "llms_txt" and not llms_enabled:
        return False
    if target.get("path") is None:
        return False
    if not target["present"] and spec["requirement"] == "conditional" and spec["create_policy"] in {
        "never",
        "external_only",
    }:
        return False
    return True


def _validation_result(
    name: str,
    status: str,
    detail: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence_ids": sorted(set(evidence_ids or [])),
        "detail": detail,
    }


def build_obligations(
    root: Path,
    policy: dict[str, Any],
    impact: dict[str, Any],
    revision: dict[str, Any],
    *,
    llms_enabled: bool,
    run_mutations: list[str],
    semantic_required: list[str],
    module_capability: dict[str, Any],
) -> list[dict[str, Any]]:
    impacted = set(impact.get("impacted_surfaces", []))
    for surface, spec in policy["surfaces"].items():
        if spec["requirement"] == "required" and not selector_paths(root, spec["selectors"]):
            impacted.add(surface)
    obligations: list[dict[str, Any]] = []
    touched_paths = set(impact.get("all_changed_files", [])) | set(run_mutations)
    for surface in sorted(impacted):
        spec = policy["surfaces"][surface]
        rules, source_changes = source_changes_for_surface(policy, impact, surface)
        basis = "changed_files" if source_changes else "baseline"
        if surface == "module_readmes":
            module_changes = impact.get("matched_rules", {}).get("module_implementation_change", [])
            targets = _module_targets(root, policy, module_changes)
            if not targets:
                targets = [{"kind": "surface", "path": None, "selector": "no_configured_subsystem_target", "present": False, "source_changes": module_changes}]
        else:
            targets = _generic_targets(root, surface, spec, llms_enabled=llms_enabled)
        for target in targets:
            local_sources = sorted(set(target.get("source_changes", source_changes)))
            applicable = _target_applicable(surface, spec, target, llms_enabled=llms_enabled)
            if surface == "module_readmes" and target.get("path") is None:
                applicable = False
            execution_mode, executor = _execution(spec, applicable)
            action_type, action_mode = _action(spec, target, applicable)
            semantic = surface in semantic_required and applicable
            if semantic:
                action_mode = "SEMANTICALLY_QUALIFIED"
            evidence: list[dict[str, Any]] = []
            for rule in rules:
                value = f"impact_rules.{rule}"
                evidence.append({"id": _evidence_id("rule", value), "type": "topology", "source": "skills/l9-update-agent-docs/references/doc-surface-policy.yaml", "locator": {"kind": "rule", "value": value}, "epistemic": "CONFIRMED", "supports": "trigger"})
            for path in local_sources:
                evidence.append({"id": _evidence_id("change", path), "type": "change", "source": "git_diff", "locator": {"kind": "path", "value": path}, "epistemic": "CONFIRMED", "supports": "trigger"})
            target_value = target.get("path") or f"surface:{surface}"
            evidence.append({"id": _evidence_id("target", target_value), "type": "target", "source": "repository", "locator": {"kind": "path" if target.get("path") else "value", "value": target_value}, "epistemic": "CONFIRMED", "supports": "target_resolution"})
            evidence.append({"id": _evidence_id("revision", revision["tested_revision_sha"]), "type": "revision", "source": "git", "locator": {"kind": "sha", "value": revision["tested_revision_sha"]}, "epistemic": "CONFIRMED", "supports": "source_revision"})
            required_validation = ["target_freshness"] if applicable else []
            results: list[dict[str, Any]] = []
            if surface == "module_readmes" and applicable:
                required_validation.append("owner_capability")
                cap_status = module_capability["status"]
                cap_ev = _evidence_id("capability", cap_status)
                evidence.append({"id": cap_ev, "type": "capability", "source": "readme-pipeline-v1", "locator": {"kind": "value", "value": cap_status}, "epistemic": "CONFIRMED", "supports": "owner_capability"})
                results.append(_validation_result("owner_capability", "PASS" if cap_status == "AVAILABLE" else "BLOCKED", f"module README capability is {cap_status}", [cap_ev]))
            if semantic:
                required_validation.append("semantic_qualification")
            touched = bool(target.get("path") and target["path"] in touched_paths)
            if not applicable:
                lifecycle = {"status": "NOT_APPLICABLE", "reason": "surface has no applicable target for this change", "terminal": True}
                qualification = {"kind": "deterministic", "status": "NOT_REQUIRED", "semantic_owner": None, "harvest_target": None, "harvest_request_id": None, "concept_ids": []}
            elif semantic:
                lifecycle = {"status": "AWAITING_QUALIFICATION", "reason": "semantic Harvest evidence required", "terminal": False}
                qualification = {"kind": "semantic", "status": "AWAITING", "semantic_owner": policy["semantic_harvest"]["owner"], "harvest_target": policy["semantic_harvest"]["destinations"].get(surface), "harvest_request_id": None, "concept_ids": []}
            elif touched:
                lifecycle = {"status": "SATISFIED", "reason": "owner target changed in the evaluated change set", "terminal": False}
                qualification = {"kind": "deterministic", "status": "QUALIFIED", "semantic_owner": None, "harvest_target": None, "harvest_request_id": None, "concept_ids": []}
            elif action_type == "HANDOFF":
                lifecycle = {"status": "HANDOFF_REQUIRED", "reason": "specialist or external owner action required", "terminal": False}
                qualification = {"kind": "deterministic", "status": "QUALIFIED", "semantic_owner": None, "harvest_target": None, "harvest_request_id": None, "concept_ids": []}
            else:
                lifecycle = {"status": "OPEN", "reason": "owner target has not been refreshed in this change set", "terminal": False}
                qualification = {"kind": "deterministic", "status": "QUALIFIED", "semantic_owner": None, "harvest_target": None, "harvest_request_id": None, "concept_ids": []}
            obligation = {
                "schema": OBLIGATION_ID,
                "obligation_id": "docobl-" + _hash(surface, str(target.get("path")), *local_sources, revision["source_head_sha"]),
                "surface": surface,
                "target": {"kind": target["kind"], "path": target.get("path"), "selector": target.get("selector"), "present": bool(target.get("present"))},
                "owner": {"id": spec["owner"], "authority_class": spec["authority_class"], "execution_mode": execution_mode, "executor": executor},
                "trigger": {"rules": rules, "source_changes": local_sources, "basis": basis},
                "revision": dict(revision),
                "qualification": qualification,
                "required_action": {"type": action_type, "mode": action_mode, "owner": spec["owner"], "executor": executor},
                "evidence": evidence,
                "lifecycle": lifecycle,
                "validation": {"required": sorted(set(required_validation)), "results": results},
                "blockers": [],
            }
            if surface == "module_readmes" and applicable and module_capability["status"] in {"PARTIAL", "BLOCKED"}:
                obligation["lifecycle"] = {"status": "BLOCKED", "reason": f"owner capability is {module_capability['status']}", "terminal": False}
                obligation["blockers"] = [f"module README owner capability is {module_capability['status']}"]
            errors = schema_errors(obligation, OBLIGATION_SCHEMA)
            if errors:
                raise ValueError("invalid compiled obligation: " + "; ".join(errors))
            obligations.append(obligation)
    return sorted(obligations, key=lambda row: (row["surface"], str(row["target"]["path"])))


def apply_semantic_resolutions(
    obligations: list[dict[str, Any]],
    semantic: dict[str, Any],
    *,
    changed_files: list[str],
    run_mutations: list[str],
) -> list[dict[str, Any]]:
    touched = set(changed_files) | set(run_mutations)
    by_surface = semantic.get("concepts_by_surface", {})
    request_id = (semantic.get("request") or {}).get("request_id")
    for obligation in obligations:
        if obligation["qualification"]["kind"] != "semantic":
            continue
        surface = obligation["surface"]
        if semantic.get("status") in {"BLOCKED", "FAIL"}:
            obligation["qualification"]["status"] = "BLOCKED"
            obligation["lifecycle"] = {"status": "BLOCKED", "reason": "semantic Harvest evidence failed admission", "terminal": False}
            obligation["blockers"] = sorted(set(semantic.get("blockers", [])))
            continue
        concepts = by_surface.get(surface, [])
        if not concepts:
            continue
        obligation["qualification"]["status"] = "QUALIFIED"
        obligation["qualification"]["harvest_request_id"] = request_id
        obligation["qualification"]["concept_ids"] = sorted({str(item["concept_id"]) for item in concepts})
        actions = {item["action"] for item in concepts}
        for concept in concepts:
            for item in concept.get("evidence", []):
                locator = item.get("locator") or {}
                value = str(locator.get("value") or item.get("id") or concept["concept_id"])
                evidence = {"id": f"harvest-{item.get('id') or _hash(value, size=10)}", "type": "harvest", "source": str(item.get("source") or "harvest.json"), "locator": {"kind": "path" if locator.get("kind") == "path_lines" else "value", "value": value}, "epistemic": "CONFIRMED", "supports": f"semantic_qualification:{concept['concept_id']}"}
                if evidence["id"] not in {row["id"] for row in obligation["evidence"]}:
                    obligation["evidence"].append(evidence)
        if actions == {"PRESERVE"}:
            obligation["required_action"]["type"] = "PRESERVE"
            obligation["lifecycle"] = {"status": "PRESERVED", "reason": "Harvest found beneficiary semantics stronger; no mutation required", "terminal": True}
            continue
        if actions == {"HANDOFF"}:
            obligation["required_action"]["type"] = "HANDOFF"
            obligation["required_action"]["mode"] = "EXTERNAL_OWNER"
        elif "RECONCILE" in actions:
            obligation["required_action"]["type"] = "RECONCILE"
        elif obligation["required_action"]["type"] != "CREATE":
            obligation["required_action"]["type"] = "REFRESH"
        target = obligation["target"]["path"]
        if target and target in touched:
            obligation["lifecycle"] = {"status": "SATISFIED", "reason": "semantically qualified owner target changed in the evaluated change set", "terminal": False}
        elif obligation["required_action"]["type"] == "HANDOFF":
            obligation["lifecycle"] = {"status": "HANDOFF_REQUIRED", "reason": "Harvest qualified a specialist-owner handoff", "terminal": False}
        else:
            obligation["lifecycle"] = {"status": "OPEN", "reason": "Harvest qualified the obligation; owner target still requires action", "terminal": False}
    return obligations


def validate_and_close_obligations(
    obligations: list[dict[str, Any]],
    *,
    changed_files: list[str],
    run_mutations: list[str],
) -> list[dict[str, Any]]:
    touched = set(changed_files) | set(run_mutations)
    for obligation in obligations:
        lifecycle = obligation["lifecycle"]
        if lifecycle["status"] in {"NOT_APPLICABLE", "PRESERVED", "BLOCKED"}:
            continue
        existing = {row["name"]: row for row in obligation["validation"]["results"]}
        target = obligation["target"]["path"]
        if "target_freshness" in obligation["validation"]["required"]:
            if obligation["required_action"]["type"] in {"NO_ACTION", "PRESERVE"}:
                existing["target_freshness"] = _validation_result("target_freshness", "NotApplicable", "no target mutation required")
            elif target and target in touched:
                target_ev = next((row["id"] for row in obligation["evidence"] if row["type"] == "target"), None)
                existing["target_freshness"] = _validation_result("target_freshness", "PASS", "target changed in the evaluated change set", [target_ev] if target_ev else [])
            else:
                existing["target_freshness"] = _validation_result("target_freshness", "UNKNOWN", "target was not changed in the evaluated change set")
        if "semantic_qualification" in obligation["validation"]["required"]:
            qualified = obligation["qualification"]["status"] == "QUALIFIED"
            harvest_ids = [row["id"] for row in obligation["evidence"] if row["type"] == "harvest"]
            existing["semantic_qualification"] = _validation_result("semantic_qualification", "PASS" if qualified else "UNKNOWN", "qualified by admitted Harvest evidence" if qualified else "semantic qualification missing", harvest_ids)
        obligation["validation"]["results"] = [existing[name] for name in sorted(existing)]
        statuses = {row["status"] for row in obligation["validation"]["results"] if row["name"] in obligation["validation"]["required"]}
        if "BLOCKED" in statuses or "FAIL" in statuses:
            obligation["lifecycle"] = {"status": "BLOCKED", "reason": "required validation blocked or failed", "terminal": False}
            continue
        if obligation["required_action"]["type"] == "HANDOFF" and target not in touched:
            continue
        if statuses and statuses.issubset({"PASS", "NotApplicable"}):
            obligation["lifecycle"] = {"status": "CLOSED", "reason": "required owner action and validation are evidenced", "terminal": True}
        elif lifecycle["status"] == "SATISFIED":
            obligation["lifecycle"] = {"status": "VALIDATED", "reason": "owner action observed but required validation remains incomplete", "terminal": False}
        errors = schema_errors(obligation, OBLIGATION_SCHEMA)
        if errors:
            obligation["lifecycle"] = {"status": "BLOCKED", "reason": "obligation failed canonical schema validation", "terminal": False}
            obligation["blockers"] = sorted(set(obligation["blockers"] + errors))
    return obligations


def summarize_obligations(obligations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["lifecycle"]["status"] for row in obligations)
    terminal = sum(1 for row in obligations if row["lifecycle"]["terminal"])
    return {
        "total": len(obligations),
        "terminal": terminal,
        "open": len(obligations) - terminal,
        "blocked": counts.get("BLOCKED", 0),
        "awaiting_qualification": counts.get("AWAITING_QUALIFICATION", 0),
        "by_status": dict(sorted(counts.items())),
    }


def status_from_obligations(obligations: list[dict[str, Any]]) -> str:
    if any(row["lifecycle"]["status"] == "BLOCKED" for row in obligations):
        return "BLOCKED"
    if any(not row["lifecycle"]["terminal"] for row in obligations):
        return "PARTIAL"
    return "PASS"
