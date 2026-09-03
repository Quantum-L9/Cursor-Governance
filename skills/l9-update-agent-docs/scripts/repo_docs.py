#!/usr/bin/env python3
"""Machine-first repository documentation obligation controller."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from compile_semantic_obligations import compile_obligations
from doc_change import (
    automatic_changed_scope,
    changed_files_since,
    freshness_analysis,
    impact_analysis,
    probe_module_readme_capability,
    semantic_harvest_required,
    validate_managed_regions,
)
from doc_llms import (
    llms_base_url,
    llms_enabled,
    render_llms_txt,
    validate_llms_txt,
)
from doc_policy import (
    RECEIPT_SCHEMA,
    adapter_directives,
    discover_surfaces,
    git,
    load_json,
    load_policy,
    pointer_validate_root,
    resolve_adapter,
    resolve_under_root,
    schema_errors,
    validate_policy,
)

RECEIPT_ID = "l9.repo-docs.receipt.v2"
STATUS = {"PASS": 0, "PARTIAL": 1, "BLOCKED": 2, "FAIL": 3}
PACK = Path(__file__).resolve().parents[1]


def head(root: Path) -> str:
    proc = git(root, "rev-parse", "HEAD")
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "UNKNOWN"


def build_harvest_request(root: Path, surfaces: list[str], sha: str) -> dict[str, Any]:
    target = ",".join(surfaces)
    digest = hashlib.sha256(f"{sha}:{target}".encode()).hexdigest()[:12]
    return {
        "request_id": f"repo-docs-{digest}",
        "donor": str(root),
        "beneficiary": str(root),
        "harvest_target": f"repo-docs:{target}",
        "access_mode": "read-only",
        "depth": "standard",
        "brief": False,
    }


def semantic_harvest_state(
    root: Path,
    policy: dict[str, Any],
    impact: dict[str, Any],
    harvest_path: str | None,
) -> dict[str, Any]:
    required = semantic_harvest_required(policy, impact, root)
    state: dict[str, Any] = {
        "owner": policy["semantic_harvest"]["owner"],
        "status": "NotApplicable",
        "required_surfaces": required,
        "input": harvest_path,
        "request": None,
        "obligations": [],
        "resolved_surfaces": [],
        "unresolved_surfaces": [],
        "blockers": [],
    }
    if not required:
        return state
    state["request"] = build_harvest_request(root, required, head(root))
    if not harvest_path:
        state.update(status="PARTIAL", unresolved_surfaces=required)
        state["blockers"] = ["semantic harvest required but harvest.json was not supplied"]
        return state
    target = resolve_under_root(root, harvest_path)
    if target is None or not target.is_file():
        state.update(status="BLOCKED", unresolved_surfaces=required)
        state["blockers"] = ["harvest input is missing or escapes repository root"]
        return state
    result = compile_obligations(
        load_json(target),
        required,
        policy["semantic_harvest"]["destinations"],
        (PACK / policy["semantic_harvest"]["input_schema"]).resolve(),
    )
    state.update(
        status=result["status"],
        obligations=result["obligations"],
        resolved_surfaces=result["resolved_surfaces"],
        unresolved_surfaces=result["unresolved_surfaces"],
        blockers=result["blockers"],
    )
    return state


def merge_status(current: str, incoming: str) -> str:
    return incoming if STATUS[incoming] > STATUS[current] else current


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    return schema_errors(receipt, RECEIPT_SCHEMA)


def build_llms_state(
    root: Path,
    policy: dict[str, Any],
    directives: dict[str, Any],
    base_url_value: str | None,
    write_llms: bool,
) -> tuple[dict[str, Any], list[str]]:
    enabled, enabled_reason = llms_enabled(root, policy, directives)
    base_url, base_source = llms_base_url(directives, base_url_value)
    mutations: list[str] = []
    state: dict[str, Any] = {
        "status": "NotApplicable",
        "enabled": enabled,
        "enabled_reason": enabled_reason,
        "base_url_source": base_source,
        "path": "llms.txt",
        "written": False,
        "findings": [],
    }
    if enabled and not base_url:
        state.update(
            status="PARTIAL",
            findings=["llms.txt eligible but canonical llms_base_url is UNKNOWN"],
        )
    elif enabled and base_url:
        rendered = render_llms_txt(root, policy, base_url)
        state["findings"] = validate_llms_txt(rendered)
        state["status"] = "FAIL" if state["findings"] else "PASS"
        if write_llms and state["status"] == "PASS":
            target = resolve_under_root(root, "llms.txt")
            if target is None:
                state.update(
                    status="BLOCKED",
                    findings=["llms.txt target escaped repository root"],
                )
            else:
                target.write_text(rendered, encoding="utf-8")
                state["written"] = True
                mutations.append("llms.txt")
    return state, mutations


def audit_repository(
    root: Path,
    *,
    changed_since: str | None = None,
    adapter: str | None = None,
    llms_base_url_value: str | None = None,
    write_llms: bool = False,
    harvest_path: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    blockers: list[str] = []
    try:
        policy = load_policy()
        policy_errors = validate_policy(policy)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        return {
            "schema": RECEIPT_ID,
            "final_status": "BLOCKED",
            "blockers": [str(exc)],
        }
    if policy_errors:
        return {
            "schema": RECEIPT_ID,
            "final_status": "FAIL",
            "blockers": policy_errors,
        }

    adapter_rel, adapter_state = resolve_adapter(root, adapter)
    if adapter_state == "BLOCKED":
        blockers.append("explicit adapter is missing or escapes repository root")
    directives = adapter_directives(root, adapter_rel)
    if changed_since:
        changed, error = changed_files_since(root, changed_since)
        changed_files, base = changed or [], changed_since
    else:
        changed_files, base, error = automatic_changed_scope(root)
    if error:
        blockers.append(error)

    impact = impact_analysis(policy, changed_files)
    pointer = pointer_validate_root(root)
    managed_status, managed_findings = validate_managed_regions(root, base, changed_files, policy)
    semantic = semantic_harvest_state(root, policy, impact, harvest_path)
    module_cap = probe_module_readme_capability(
        root,
        policy,
        impact["matched_rules"].get("module_implementation_change", []),
    )
    llms, run_mutations = build_llms_state(
        root, policy, directives, llms_base_url_value, write_llms
    )
    freshness = freshness_analysis(root, policy, impact, llms["enabled"], run_mutations)
    surfaces = discover_surfaces(root, policy, llms["enabled"])
    impacted = set(impact["impacted_surfaces"])
    for row in surfaces:
        row["impacted"] = row["id"] in impacted

    validators = [
        {"name": "doc_surface_policy", "status": "PASS", "findings": []},
        {
            "name": "pointer_headings",
            "status": pointer["status"],
            "findings": pointer["findings"],
        },
        {
            "name": "managed_regions",
            "status": managed_status,
            "findings": managed_findings,
        },
        {
            "name": "semantic_harvest",
            "status": semantic["status"],
            "findings": semantic["blockers"] + semantic["unresolved_surfaces"],
        },
        {
            "name": "doc_freshness",
            "status": freshness["status"],
            "findings": freshness["stale_surfaces"] + freshness["missing_surfaces"],
        },
        {
            "name": "module_readme_capability",
            "status": module_cap["status"],
            "findings": module_cap["unsupported_impacted_extensions"],
        },
        {
            "name": "llms_txt",
            "status": llms["status"],
            "findings": llms["findings"],
        },
    ]
    status = "PASS"
    for validator in validators:
        if validator["status"] in STATUS:
            status = merge_status(status, validator["status"])
    if blockers:
        status = merge_status(status, "BLOCKED")

    unknown = [
        row["id"]
        for row in surfaces
        if row["requirement"] == "required" and not row["present"] and row["action"] != "EXTERNAL"
    ]
    if unknown:
        status = merge_status(status, "PARTIAL")
    skipped = [
        item
        for row in surfaces
        if row["action"] in {"SKIP", "EXTERNAL"}
        for item in (row["paths"] or [row["id"]])
    ]

    evidence = {
        "references/doc-surface-policy.yaml",
        "references/pointer-heading-map.yaml",
    }
    if adapter_rel:
        evidence.add(adapter_rel)
    if harvest_path and semantic["status"] not in {"NotApplicable", "BLOCKED"}:
        evidence.add(harvest_path)
        for obligation in semantic["obligations"]:
            for item in obligation["evidence"]:
                locator = item.get("locator") or {}
                if locator.get("value"):
                    evidence.add(str(locator["value"]))

    receipt = {
        "schema": RECEIPT_ID,
        "final_status": status,
        "target": {
            "repository_root": str(root),
            "sha": head(root),
            "changed_since": base,
        },
        "adapter": {"path": adapter_rel, "resolution": adapter_state},
        "surfaces": surfaces,
        "changes": {
            "changed_files": changed_files,
            "skipped_files": sorted(set(skipped)),
            "unknown_files": sorted(set(unknown)),
            "run_mutations": sorted(set(run_mutations)),
        },
        "impact": impact,
        "freshness": freshness,
        "semantic_harvest": semantic,
        "capabilities": {"module_readmes": module_cap},
        "llms_txt": llms,
        "validators_executed": validators,
        "evidence_sources": sorted(evidence),
        "blockers": blockers,
    }
    receipt_errors = validate_receipt_shape(receipt)
    if receipt_errors:
        receipt["final_status"] = "FAIL"
        receipt["blockers"].extend(receipt_errors)
    return receipt


def exit_code_for_receipt(receipt: dict[str, Any], fail_on_partial: bool = False) -> int:
    status = receipt["final_status"]
    if status == "PARTIAL":
        semantic = receipt.get("semantic_harvest", {})
        freshness = receipt.get("freshness", {})
        actionable = bool(
            semantic.get("unresolved_surfaces")
            or freshness.get("stale_surfaces")
            or freshness.get("missing_surfaces")
        )
        return 3 if fail_on_partial or actionable else 0
    return {"PASS": 0, "BLOCKED": 2, "FAIL": 1}[status]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed-since")
    parser.add_argument("--adapter")
    parser.add_argument("--receipt")
    parser.add_argument("--llms-base-url")
    parser.add_argument("--write-llms", action="store_true")
    parser.add_argument("--harvest")
    parser.add_argument("--fail-on-partial", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = audit_repository(
        root,
        changed_since=args.changed_since,
        adapter=args.adapter,
        llms_base_url_value=args.llms_base_url,
        write_llms=args.write_llms,
        harvest_path=args.harvest,
    )
    if args.receipt:
        target = resolve_under_root(root, args.receipt)
        if target is None:
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(receipt, indent=2 if args.json else None, sort_keys=True))
    return exit_code_for_receipt(receipt, args.fail_on_partial)


if __name__ == "__main__":
    raise SystemExit(main())
