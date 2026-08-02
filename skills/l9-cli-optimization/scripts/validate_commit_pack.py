#!/usr/bin/env python3
"""Validate an optimize CLI PR commit pack."""

from __future__ import annotations

import argparse
import hashlib
import json

try:
    import jsonschema as _jsonschema
except ImportError:
    _jsonschema = None
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from build_commit_pack import (
    calculate_leverage_score,
    improvement_from_measurements,
    leverage_decision,
)
from validate_decision_ledger import validate_decision_contract

VALID_STATUSES = {"PR_READY", "BLOCKED"}
WIRING_STRATEGIES = {
    "activate_latent_capability",
    "repair_wiring",
    "connect_signal_consumer",
    "surface_existing_cli_path",
}
REQUIRED_FILES = {
    "MANIFEST.json",
    "README.md",
    "change/commit.patch",
    "change/OPTIMIZATION_PLAN.json",
    "pr/COMMIT_MESSAGE.txt",
    "pr/PR_BODY.md",
    "pr/PR_CHECKLIST.md",
    "deploy/DEPLOY_PLAYBOOK.md",
    "deploy/ROLLBACK_PLAYBOOK.md",
    "deploy/RELEASE_CHECKLIST.md",
    "handoff/AGENT_HANDOFF.md",
    "handoff/NEXT_AGENT_TASK.json",
    "evidence/EXECUTION_ROUTE.json",
    "evidence/DECISION_LEDGER.json",
    "evidence/DECISION_RECORD.md",
    "evidence/CLI_REVISION_SYNTHESIS.json",
    "evidence/CLI_REVISION_PLAN.md",
    "evidence/DOCS_CODE_DIVERGENCE_FINDINGS.md",
    "evidence/VALIDATION.md",
    "evidence/PERFORMANCE.md",
    "evidence/commands.jsonl",
    "evidence/checksums.sha256",
}
FORBIDDEN_PATTERNS = {
    "unfinished-work marker": re.compile(r"\bTO" + r"DO\b", re.IGNORECASE),
    "fix-later marker": re.compile(r"\bFIX" + r"ME\b", re.IGNORECASE),
    "template-residue marker": re.compile(r"\bPLACE" + r"HOLDER\b", re.IGNORECASE),
    "fabrication marker": re.compile(r"\bASSUMED[_ -]?PASS\b", re.IGNORECASE),
}


class ValidationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: str) -> bool:
    posix = PurePosixPath(value)
    return (
        bool(posix.parts)
        and not posix.is_absolute()
        and ".." not in posix.parts
        and "." not in posix.parts
    )


def validate_checksums(root: Path) -> list[str]:
    errors: list[str] = []
    checksum_path = root / "evidence" / "checksums.sha256"
    recorded: dict[str, str] = {}
    for line_number, line in enumerate(
        checksum_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[a-f0-9]{64}", parts[0]):
            errors.append(f"invalid checksum line {line_number}")
            continue
        recorded[parts[1]] = parts[0]
    expected: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path == checksum_path or path.suffix == ".gz":
            continue
        relative = path.relative_to(root).as_posix()
        expected.add(relative)
        if recorded.get(relative) != sha256_file(path):
            errors.append(f"checksum mismatch or missing: {relative}")
    extra = set(recorded) - expected
    if extra:
        errors.append(f"checksums contain nonexistent paths: {sorted(extra)}")
    return errors


def validate_revision_synthesis(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any], pr_body: str
) -> list[str]:
    errors: list[str] = []
    synthesis = read_json(root / "evidence" / "CLI_REVISION_SYNTHESIS.json")
    required = {
        "synthesis_version",
        "synthesis_status",
        "all_material_findings_synthesized",
        "leverage_policy_version",
        "findings",
        "targets",
        "options",
        "selected_option_ids",
        "unresolved_divergence_ids",
        "unknowns",
        "selection_rationale",
    }
    for key in sorted(required - set(synthesis)):
        errors.append(f"CLI_REVISION_SYNTHESIS.json missing key: {key}")
    findings_list = synthesis.get("findings", [])
    targets_list = synthesis.get("targets", [])
    options_list = synthesis.get("options", [])
    if not all(isinstance(value, list) for value in (findings_list, targets_list, options_list)):
        return errors + ["revision synthesis findings, targets, and options must be arrays"]
    findings = {
        item.get("id"): item
        for item in findings_list
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    targets = {
        item.get("id"): item
        for item in targets_list
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    options = {
        item.get("id"): item
        for item in options_list
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(findings) != len(findings_list):
        errors.append("revision finding IDs must be present and unique")
    if len(targets) != len(targets_list):
        errors.append("revision target IDs must be present and unique")
    if len(options) != len(options_list):
        errors.append("revision option IDs must be present and unique")

    finding_refs: set[str] = set()
    for target_id, target in targets.items():
        source_ids = target.get("source_finding_ids", [])
        option_ids = target.get("option_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(f"target {target_id} lacks source_finding_ids")
            source_ids = []
        if not isinstance(option_ids, list) or not option_ids:
            errors.append(f"target {target_id} lacks option_ids")
            option_ids = []
        missing = set(source_ids) - set(findings)
        if missing:
            errors.append(f"target {target_id} references missing findings: {sorted(missing)}")
        finding_refs.update(source_ids)
        actual = {
            option_id
            for option_id, option in options.items()
            if target_id in option.get("target_ids", [])
        }
        if set(option_ids) != actual:
            errors.append(f"target {target_id} option_ids mismatch")
    if finding_refs != set(findings):
        errors.append(
            f"every finding must map to a target; unmapped={sorted(set(findings) - finding_refs)}"
        )

    target_refs: set[str] = set()
    for option_id, option in options.items():
        target_ids = option.get("target_ids", [])
        if not isinstance(target_ids, list) or not target_ids:
            errors.append(f"option {option_id} lacks target_ids")
            continue
        missing = set(target_ids) - set(targets)
        if missing:
            errors.append(f"option {option_id} references missing targets: {sorted(missing)}")
        target_refs.update(target_ids)
        dimensions = option.get("leverage_dimensions")
        if not isinstance(dimensions, dict):
            errors.append(f"option {option_id} lacks leverage_dimensions")
            continue
        try:
            calculated = calculate_leverage_score(dimensions)
        except Exception as exc:
            errors.append(f"option {option_id} leverage dimensions invalid: {exc}")
            continue
        recorded = option.get("leverage_score")
        if (
            not isinstance(recorded, (int, float))
            or isinstance(recorded, bool)
            or abs(float(recorded) - calculated) > 0.001
        ):
            errors.append(f"option {option_id} leverage_score mismatch; expected {calculated}")
        expected = leverage_decision(calculated)
        if option.get("decision") != expected:
            errors.append(f"option {option_id} decision mismatch; expected {expected}")
    if target_refs != set(targets):
        errors.append(
            f"every target must map to an option; unmapped={sorted(set(targets) - target_refs)}"
        )

    selected = synthesis.get("selected_option_ids", [])
    if not isinstance(selected, list):
        errors.append("selected_option_ids must be an array")
        selected = []
    selected_flags = {
        option_id for option_id, option in options.items() if option.get("selected") is True
    }
    if set(selected) != selected_flags:
        errors.append("selected_option_ids do not match selected option flags")
    for option_id in selected:
        option = options.get(option_id)
        if not option:
            errors.append(f"selected option missing: {option_id}")
            continue
        if option.get("scope") != "in_scope":
            errors.append(f"selected option is not in_scope: {option_id}")
        if option.get("decision") not in {"approve", "prioritize"}:
            errors.append(f"selected option is not leverage-approved: {option_id}")
        if option.get("unknowns"):
            errors.append(f"selected option retains unknowns: {option_id}")

    divergence_ids = {
        fid for fid, finding in findings.items() if finding.get("kind") == "docs_code_divergence"
    }
    unresolved = synthesis.get("unresolved_divergence_ids", [])
    if not isinstance(unresolved, list):
        errors.append("unresolved_divergence_ids must be an array")
        unresolved = []
    expected_unresolved = {
        fid for fid in divergence_ids if findings[fid].get("reconciliation") != "fixed_in_scope"
    }
    if set(unresolved) != expected_unresolved:
        errors.append(f"unresolved_divergence_ids mismatch; expected {sorted(expected_unresolved)}")
    divergence_text = (root / "evidence" / "DOCS_CODE_DIVERGENCE_FINDINGS.md").read_text(
        encoding="utf-8"
    )
    for finding_id in unresolved:
        finding = findings.get(finding_id, {})
        if finding_id not in divergence_text:
            errors.append(f"divergence report omits {finding_id}")
        if finding_id not in pr_body:
            errors.append(f"PR body omits unresolved divergence {finding_id}")
        for field in (
            "docs_claim",
            "code_observation",
            "divergence_type",
            "reconciliation",
            "owner",
            "recommended_action",
        ):
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"docs-code divergence {finding_id} lacks {field}")
        owner = finding.get("owner")
        if isinstance(owner, str) and owner.strip().lower() == "unknown":
            errors.append(f"unresolved divergence {finding_id} owner must not be 'unknown'")
        if finding.get("scope") == "unknown" or finding.get("reconciliation") == "unknown":
            if manifest.get("status") == "PR_READY":
                errors.append(f"PR_READY retains unknown docs-code divergence: {finding_id}")

    if plan.get("selected_revision_option_ids") != selected:
        errors.append("OPTIMIZATION_PLAN selected_revision_option_ids mismatch")
    if plan.get("revision_synthesis_path") != "evidence/CLI_REVISION_SYNTHESIS.json":
        errors.append("OPTIMIZATION_PLAN revision_synthesis_path mismatch")

    manifest_expectations = {
        "revision_synthesis_status": synthesis.get("synthesis_status"),
        "revision_finding_count": len(findings_list),
        "revision_target_count": len(targets_list),
        "revision_option_count": len(options_list),
        "selected_revision_options": selected,
        "unresolved_docs_code_divergences": unresolved,
    }
    for key, expected in manifest_expectations.items():
        if manifest.get(key) != expected:
            errors.append(f"manifest {key} mismatch")
    scores = [options[item].get("leverage_score") for item in selected if item in options]
    highest = max(scores) if scores else None
    if manifest.get("highest_selected_leverage_score") != highest:
        errors.append("manifest highest_selected_leverage_score mismatch")

    plan_text = (root / "evidence" / "CLI_REVISION_PLAN.md").read_text(encoding="utf-8")
    for heading in (
        "## Findings",
        "## Revision Targets",
        "## Options and Leverage",
        "## Selected Options",
        "## Unresolved Documentation-Code Divergence",
    ):
        if heading not in plan_text:
            errors.append(f"CLI_REVISION_PLAN.md missing section: {heading}")

    if manifest.get("status") == "PR_READY":
        if (
            synthesis.get("synthesis_status") != "complete"
            or synthesis.get("all_material_findings_synthesized") is not True
        ):
            errors.append("PR_READY requires complete all-findings synthesis")
        if synthesis.get("unknowns"):
            errors.append("PR_READY revision synthesis retains unknowns")
        if not selected:
            errors.append("PR_READY requires selected revision options")
        blocking = [
            fid
            for fid, finding in findings.items()
            if finding.get("blocks_release") is True and finding.get("status") != "reconciled"
        ]
        if blocking:
            errors.append(f"PR_READY has unresolved release-blocking findings: {blocking}")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"pack root is not a directory: {root}"]
    present = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    for required in sorted(REQUIRED_FILES - present):
        errors.append(f"missing required file: {required}")
    if errors:
        return errors

    manifest = read_json(root / "MANIFEST.json")
    required_manifest = {
        "schema_version",
        "pack_name",
        "version",
        "repository",
        "base_ref",
        "branch",
        "status",
        "changed_files",
        "patch_sha256",
        "created_utc",
        "generator",
        "utilization_gap_class",
        "ownership",
        "improvement_percent",
        "wiring_analysis_performed",
        "selected_wiring_findings",
        "unresolved_wiring_unknowns",
        "revision_synthesis_status",
        "revision_finding_count",
        "revision_target_count",
        "revision_option_count",
        "selected_revision_options",
        "unresolved_docs_code_divergences",
        "highest_selected_leverage_score",
        "reasoning_depth",
        "initial_action",
        "final_action",
        "proof_obligation_count",
        "satisfied_proof_obligation_count",
        "unresolved_material_unknowns",
        "decision_convergence_status",
    }
    for key in sorted(required_manifest - set(manifest)):
        errors.append(f"manifest missing key: {key}")
    if _jsonschema is None:
        errors.append(
            "jsonschema is required to validate MANIFEST.json; install it (pip install -r requirements.txt)"
        )
    else:
        manifest_schema = json.loads(
            (
                Path(__file__).resolve().parents[1] / "schemas" / "pack-manifest.schema.json"
            ).read_text(encoding="utf-8")
        )
        try:
            _jsonschema.validate(manifest, manifest_schema)
        except _jsonschema.ValidationError as exc:
            errors.append(f"MANIFEST.json violates pack-manifest.schema.json: {exc.message}")
    if manifest.get("schema_version") != "2.0.0":
        errors.append("manifest.schema_version must be 2.0.0")
    if manifest.get("generator") != "optimize-cli-pr-pack":
        errors.append("manifest.generator mismatch")
    if manifest.get("status") not in VALID_STATUSES:
        errors.append("manifest.status is invalid")

    route = read_json(root / "evidence" / "EXECUTION_ROUTE.json")
    ledger = read_json(root / "evidence" / "DECISION_LEDGER.json")
    synthesis_for_contract = read_json(root / "evidence" / "CLI_REVISION_SYNTHESIS.json")
    decision_errors = validate_decision_contract(
        {
            "status": manifest.get("status"),
            "execution_route": route,
            "decision_ledger": ledger,
            "optimization": read_json(root / "change" / "OPTIMIZATION_PLAN.json"),
            "wiring": read_json(root / "evidence" / "LATENT_CAPABILITY_FINDINGS.json")
            if (root / "evidence" / "LATENT_CAPABILITY_FINDINGS.json").is_file()
            else {},
            "revision_synthesis": synthesis_for_contract,
        }
    )
    errors.extend(f"adaptive decision contract: {item}" for item in decision_errors)
    if manifest.get("reasoning_depth") != route.get("reasoning_depth"):
        errors.append("manifest reasoning_depth mismatch")
    if manifest.get("initial_action") != route.get("initial_action"):
        errors.append("manifest initial_action mismatch")
    decision = ledger.get("decision", {}) if isinstance(ledger, dict) else {}
    convergence = ledger.get("convergence", {}) if isinstance(ledger, dict) else {}
    proofs = ledger.get("proof_obligations", []) if isinstance(ledger, dict) else []
    satisfied = sum(
        1 for item in proofs if isinstance(item, dict) and item.get("status") == "satisfied"
    )
    if manifest.get("final_action") != decision.get("final_action"):
        errors.append("manifest final_action mismatch")
    if manifest.get("proof_obligation_count") != len(proofs):
        errors.append("manifest proof_obligation_count mismatch")
    if manifest.get("satisfied_proof_obligation_count") != satisfied:
        errors.append("manifest satisfied_proof_obligation_count mismatch")
    if manifest.get("unresolved_material_unknowns") != convergence.get(
        "remaining_material_unknown_ids"
    ):
        errors.append("manifest unresolved_material_unknowns mismatch")
    if manifest.get("decision_convergence_status") != convergence.get("status"):
        errors.append("manifest decision_convergence_status mismatch")
    decision_record = (root / "evidence" / "DECISION_RECORD.md").read_text(encoding="utf-8")
    for heading in (
        "## Objective",
        "## Active Proof Obligations",
        "## Selected Options",
        "## Material Unknowns",
        "## Decision",
        "## Stop Reason",
    ):
        if heading not in decision_record:
            errors.append(f"DECISION_RECORD.md missing section: {heading}")

    plan = read_json(root / "change" / "OPTIMIZATION_PLAN.json")
    required_plan = {
        "utilization_gap_class",
        "ownership",
        "evidence",
        "strategy",
        "preserved_constraints",
        "external_limits_not_bypassed",
        "resource_envelope",
        "rollback_trigger",
        "selected_revision_option_ids",
        "revision_synthesis_path",
    }
    for key in sorted(required_plan - set(plan)):
        errors.append(f"OPTIMIZATION_PLAN.json missing key: {key}")
    if plan.get("utilization_gap_class") != manifest.get("utilization_gap_class"):
        errors.append("manifest and plan utilization_gap_class mismatch")
    if plan.get("ownership") != manifest.get("ownership"):
        errors.append("manifest and plan ownership mismatch")
    if route.get("utilization_gap_class") != plan.get("utilization_gap_class"):
        errors.append("execution route and plan utilization_gap_class mismatch")
    if route.get("ownership") != plan.get("ownership"):
        errors.append("execution route and plan ownership mismatch")
    # K2: recompute improvement from the embedded measurements so a self-declared
    # improvement_percent cannot pass on garbage (candidate worse than baseline).
    perf = manifest.get("performance") or {}
    activation = False
    cand_value = perf.get("candidate_value")
    if cand_value is not None:
        computed, perr = improvement_from_measurements(
            perf.get("baseline_value"), cand_value, perf.get("direction", "lower_is_better")
        )
        if perr:
            errors.append(f"manifest performance is inconsistent: {perr}")
        elif computed is None:
            activation = True
        else:
            declared = perf.get("improvement_percent")
            if (
                not isinstance(declared, (int, float))
                or isinstance(declared, bool)
                or abs(float(declared) - computed) > 0.5
            ):
                errors.append(
                    f"manifest improvement_percent {declared} does not match recomputed {computed}"
                )
            if manifest.get("improvement_percent") != declared:
                errors.append(
                    "manifest improvement_percent disagrees with performance.improvement_percent"
                )
    if manifest.get("status") == "PR_READY":
        label = manifest.get("status")
        if plan.get("ownership") != "repository_owned":
            errors.append(f"{label} requires repository-owned ownership")
        if cand_value is None:
            errors.append(f"{label} requires a candidate measurement")
        elif not activation:
            improvement = manifest.get("improvement_percent")
            if (
                not isinstance(improvement, (int, float))
                or isinstance(improvement, bool)
                or improvement <= 0
            ):
                errors.append(f"{label} requires positive measured improvement")
        if plan.get("strategy") in {None, "none"}:
            errors.append(f"{label} requires an active optimize strategy")
    if plan.get("ownership") in {"external", "unknown"} and manifest.get("status") != "BLOCKED":
        errors.append("external or unknown bottleneck ownership must be BLOCKED")

    wiring_active = bool(manifest.get("wiring_analysis_performed"))
    selected_manifest = manifest.get("selected_wiring_findings")
    unknowns_manifest = manifest.get("unresolved_wiring_unknowns")
    if not isinstance(selected_manifest, list) or not isinstance(unknowns_manifest, list):
        errors.append("manifest wiring fields must be arrays")
        selected_manifest = []
        unknowns_manifest = []
    if plan.get("strategy") in WIRING_STRATEGIES and not wiring_active:
        errors.append("latent-capability strategy requires wiring analysis evidence")
    wiring_json_path = root / "evidence" / "LATENT_CAPABILITY_FINDINGS.json"
    wiring_map_path = root / "evidence" / "WIRING_MAP.md"
    if wiring_active:
        for required_path in (wiring_json_path, wiring_map_path):
            if not required_path.is_file():
                errors.append(
                    f"missing required wiring artifact: {required_path.relative_to(root).as_posix()}"
                )
        if wiring_json_path.is_file():
            wiring = read_json(wiring_json_path)
            selected = wiring.get("selected_finding_ids", [])
            unknowns = wiring.get("unresolved_unknowns", [])
            findings = {
                item.get("id"): item
                for item in wiring.get("findings", [])
                if isinstance(item, dict)
            }
            if selected != selected_manifest:
                errors.append("manifest selected_wiring_findings mismatch")
            if unknowns != unknowns_manifest:
                errors.append("manifest unresolved_wiring_unknowns mismatch")
            if (
                wiring.get("convergence_status") != "converged"
                and manifest.get("status") == "PR_READY"
            ):
                errors.append("PR_READY wiring analysis must be converged")
            if manifest.get("status") == "PR_READY" and unknowns:
                errors.append("PR_READY wiring analysis cannot retain unresolved unknowns")
            if manifest.get("status") == "PR_READY" and not selected:
                errors.append("PR_READY latent-capability pack requires selected findings")
            for finding_id in selected:
                finding = findings.get(finding_id)
                if not finding:
                    errors.append(f"selected wiring finding missing: {finding_id}")
                    continue
                if finding.get("verdict") != "activate":
                    errors.append(f"selected wiring finding must be activate: {finding_id}")
                if finding.get("dynamic_dispatch_checked") is not True:
                    errors.append(
                        f"selected wiring finding lacks dynamic-dispatch review: {finding_id}"
                    )
                if finding.get("dormant_by_design") is not False:
                    errors.append(
                        f"selected wiring finding is dormant by design or unclassified: {finding_id}"
                    )
                for field in ("definition_evidence", "consumer_evidence", "downstream_capability"):
                    value = finding.get(field)
                    if (
                        not isinstance(value, str)
                        or not value.strip()
                        or value.strip().lower() == "unknown"
                    ):
                        errors.append(f"selected wiring finding lacks {field}: {finding_id}")
        if wiring_map_path.is_file():
            wiring_text = wiring_map_path.read_text(encoding="utf-8")
            for heading in (
                "## Entrypoints",
                "## Registries and Dynamic Dispatch",
                "## Producer to Consumer Edges",
                "## Selected Findings",
                "## Unresolved Unknowns",
            ):
                if heading not in wiring_text:
                    errors.append(f"WIRING_MAP.md missing section: {heading}")
    elif wiring_json_path.exists() or wiring_map_path.exists():
        errors.append("wiring artifacts exist while manifest says analysis was not performed")

    changed = manifest.get("changed_files")
    deleted = set(manifest.get("deleted_files", []))
    if not isinstance(changed, list) or not changed:
        errors.append("manifest.changed_files must be a non-empty array")
        changed = []
    elif len(set(changed)) != len(changed):
        errors.append("manifest.changed_files contains duplicates")
    for raw in changed:
        if not isinstance(raw, str) or not safe_relative(raw):
            errors.append(f"unsafe changed file path: {raw!r}")
            continue
        if (
            raw not in deleted
            and not (root / "change" / "files" / Path(*PurePosixPath(raw).parts)).is_file()
        ):
            errors.append(f"changed file not copied: {raw}")

    patch = (root / "change" / "commit.patch").read_bytes()
    if not patch.strip():
        errors.append("commit.patch is empty")
    if hashlib.sha256(patch).hexdigest() != manifest.get("patch_sha256"):
        errors.append("manifest.patch_sha256 does not match commit.patch")
    patch_text = patch.decode("utf-8", "replace")
    patch_paths = set()
    for match in re.finditer(r"^\+\+\+ b/(.+)$", patch_text, re.MULTILINE):
        patch_paths.add(match.group(1).strip())
    for match in re.finditer(r"^diff --git a/.+? b/(.+)$", patch_text, re.MULTILINE):
        patch_paths.add(match.group(1).strip())
    for raw in changed:
        if isinstance(raw, str) and raw not in deleted and raw not in patch_paths:
            errors.append(f"commit.patch does not modify declared changed file: {raw}")

    commit_message = (root / "pr" / "COMMIT_MESSAGE.txt").read_text(encoding="utf-8").strip()
    if not commit_message or len(commit_message.splitlines()[0]) > 72:
        errors.append("commit subject must be non-empty and at most 72 characters")
    pr_body = (root / "pr" / "PR_BODY.md").read_text(encoding="utf-8")
    if len(pr_body.strip()) < 100:
        errors.append("PR body is too thin to explain the change and evidence")
    errors.extend(validate_revision_synthesis(root, manifest, plan, pr_body))

    performance = (root / "evidence" / "PERFORMANCE.md").read_text(encoding="utf-8")
    for heading in (
        "## Baseline",
        "## Candidate",
        "## Comparison Method",
        "## Correctness Checks",
        "## Resource Checks",
    ):
        if heading not in performance:
            errors.append(f"PERFORMANCE.md missing section: {heading}")
    if manifest.get("status") == "PR_READY" and "Candidate measurement: `UNKNOWN`" in performance:
        errors.append("PR_READY performance evidence cannot have unknown candidate measurement")

    next_task = read_json(root / "handoff" / "NEXT_AGENT_TASK.json")
    required_task = {
        "objective",
        "status",
        "repository",
        "base_ref",
        "branch",
        "pack_manifest",
        "next_action",
        "validation_entrypoint",
        "deploy_entrypoint",
        "blockers",
        "unknowns",
        "do_not",
    }
    for key in sorted(required_task - set(next_task)):
        errors.append(f"NEXT_AGENT_TASK.json missing key: {key}")
    if next_task.get("status") != manifest.get("status"):
        errors.append("handoff status does not match manifest status")
    if manifest.get("status") == "PR_READY" and next_task.get("unknowns"):
        errors.append("PR_READY handoff must not retain material unknowns")

    command_count = 0
    for line_number, line in enumerate(
        (root / "evidence" / "commands.jsonl").read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        command_count += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid commands.jsonl line {line_number}: {exc}")
            continue
        if (
            not isinstance(record, dict)
            or not record.get("command")
            or not record.get("status")
            or not record.get("evidence")
        ):
            errors.append(f"commands.jsonl line {line_number} lacks command/status/evidence")
        elif manifest.get("status") == "PR_READY" and str(
            record.get("status")
        ).strip().lower() not in {"pass", "passed", "ok", "success", "green", "0"}:
            errors.append(
                f"commands.jsonl line {line_number}: PR_READY requires a passing command status, got {record.get('status')!r}"
            )
    if manifest.get("status") == "PR_READY" and command_count == 0:
        errors.append("PR_READY pack requires command evidence")

    issue_files = list((root / "issues").glob("ISSUE-*.md")) if (root / "issues").is_dir() else []
    if manifest.get("status") == "BLOCKED" and not issue_files:
        errors.append("BLOCKED pack requires at least one issue file")

    text_targets = [
        root / "README.md",
        root / "pr" / "PR_BODY.md",
        root / "deploy" / "DEPLOY_PLAYBOOK.md",
        root / "deploy" / "ROLLBACK_PLAYBOOK.md",
        root / "handoff" / "AGENT_HANDOFF.md",
        root / "evidence" / "DECISION_RECORD.md",
        root / "evidence" / "CLI_REVISION_PLAN.md",
        root / "evidence" / "DOCS_CODE_DIVERGENCE_FINDINGS.md",
        root / "evidence" / "VALIDATION.md",
        root / "evidence" / "PERFORMANCE.md",
        *issue_files,
    ]
    if wiring_map_path.is_file():
        text_targets.append(wiring_map_path)
    for path in text_targets:
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} found in {path.relative_to(root).as_posix()}")

    deploy = (root / "deploy" / "DEPLOY_PLAYBOOK.md").read_text(encoding="utf-8").lower()
    # Structural intent, not three magic words: accept common synonyms so a
    # semantically-complete playbook is not failed for wording.
    deploy_requirements = {
        "rollback": ("rollback", "roll back", "revert", "restore"),
        "verify": ("verify", "validate", "confirm", "smoke"),
        "abort": ("abort", "halt", "stop", "cease"),
    }
    for label, synonyms in deploy_requirements.items():
        if not any(term in deploy for term in synonyms):
            errors.append(
                f"deployment playbook missing {label} guidance (any of: {', '.join(synonyms)})"
            )

    errors.extend(validate_checksums(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack_root", type=Path)
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        errors = validate(args.pack_root.resolve())
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: optimize commit pack is structurally and evidentially valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
