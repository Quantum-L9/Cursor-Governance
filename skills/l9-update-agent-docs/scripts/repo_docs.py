#!/usr/bin/env python3
"""Machine-first Repository Documentation Obligation Compiler."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from compile_semantic_obligations import compile_harvest_evidence
from doc_change import (
    automatic_changed_scope,
    changed_files_since,
    impact_analysis,
    probe_module_readme_capability,
    semantic_harvest_required,
    validate_managed_regions,
)
from doc_llms import llms_base_url, llms_enabled, render_llms_txt, validate_llms_txt
from doc_obligations import (
    apply_semantic_resolutions,
    build_obligations,
    semantic_source_digest,
    status_from_obligations,
    summarize_obligations,
    validate_and_close_obligations,
)
from doc_policy import (
    RECEIPT_SCHEMA,
    adapter_directives,
    discover_surfaces,
    git,
    load_json,
    load_policy,
    pointer_validate_root,
    repository_identity,
    resolve_adapter,
    resolve_under_root,
    schema_errors,
    validate_policy,
)

RECEIPT_ID = "l9.repo-docs.receipt.v3"
PACK = Path(__file__).resolve().parents[1]


def head(root: Path) -> str:
    proc = git(root, "rev-parse", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "UNKNOWN"


def resolve_sha(root: Path, ref: str | None) -> str | None:
    if not ref:
        return None
    proc = git(root, "rev-parse", f"{ref}^{{commit}}")
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def revision_identity(
    root: Path,
    *,
    base_ref: str | None,
    source_head_sha: str | None,
    tested_revision_sha: str | None,
    dirty_scope: bool,
) -> dict[str, Any]:
    tested = tested_revision_sha or head(root)
    source = source_head_sha or tested
    if base_ref:
        mode = "worktree_to_head" if base_ref == "HEAD" and dirty_scope else "merge_base_to_head"
    else:
        mode = "snapshot" if source != "UNKNOWN" else "unknown"
    return {
        "repository": repository_identity(root),
        "base_ref": base_ref,
        "base_sha": resolve_sha(root, base_ref),
        "source_head_sha": source,
        "tested_revision_sha": tested,
        "comparison_mode": mode,
    }


def build_harvest_request(
    repository: str, surfaces: list[str], semantic_digest: str
) -> dict[str, Any]:
    target = ",".join(surfaces)
    digest = hashlib.sha256(f"{repository}:{semantic_digest}:{target}".encode()).hexdigest()[:12]
    return {
        "request_id": f"repo-docs-{digest}",
        "donor": repository,
        "beneficiary": repository,
        "harvest_target": f"repo-docs:{target}",
        "access_mode": "read-only",
        "depth": "standard",
        "brief": False,
    }


def _harvest_candidates(changed_files: list[str]) -> list[str]:
    return sorted(
        path
        for path in changed_files
        if Path(path).name == "harvest.json" or path.endswith(".harvest.json")
    )


def _harvest_binding_errors(
    harvest: dict[str, Any],
    *,
    repository: str,
    required_surfaces: list[str],
    semantic_digest: str,
) -> list[str]:
    errors: list[str] = []
    expected_target = f"repo-docs:{','.join(required_surfaces)}"
    request = harvest.get("request") if isinstance(harvest.get("request"), dict) else {}
    if request.get("harvest_target") != expected_target:
        actual_target = request.get("harvest_target")
        errors.append(
            f"harvest target mismatch: expected {expected_target!r}, got {actual_target!r}"
        )
    raw_source = harvest.get("source_identity")
    source = raw_source if isinstance(raw_source, dict) else {}
    binding = source.get("repo_docs") if isinstance(source.get("repo_docs"), dict) else {}
    if binding.get("repository") != repository:
        errors.append("harvest repo_docs.repository does not match evaluated repository")
    if binding.get("semantic_source_digest") != semantic_digest:
        errors.append("harvest semantic_source_digest does not match current semantic source files")
    if sorted(binding.get("required_surfaces") or []) != sorted(required_surfaces):
        errors.append("harvest required_surfaces do not match current semantic obligations")
    return errors


def semantic_harvest_state(
    root: Path,
    policy: dict[str, Any],
    impact: dict[str, Any],
    changed_files: list[str],
    harvest_path: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    required = semantic_harvest_required(policy, impact, root)
    semantic_digest, source_paths = semantic_source_digest(root, policy, impact, required)
    state: dict[str, Any] = {
        "owner": policy["semantic_harvest"]["owner"],
        "status": "NotApplicable",
        "required_surfaces": required,
        "input": None,
        "discovered": False,
        "request": None,
        "semantic_source_digest": semantic_digest,
        "source_paths": source_paths,
        "blockers": [],
    }
    if not required:
        return state, None
    if semantic_digest is None:
        state.update(status="BLOCKED", blockers=["semantic source digest could not be derived"])
        return state, None
    repository = repository_identity(root)
    state["request"] = build_harvest_request(repository, required, semantic_digest)
    candidates = [harvest_path] if harvest_path else _harvest_candidates(changed_files)
    candidates = [item for item in candidates if item]
    if not candidates:
        state.update(status="PARTIAL")
        state["blockers"] = [
            "semantic Harvest required but no bound harvest.json was supplied or changed"
        ]
        return state, None
    admitted: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    rejected: list[str] = []
    schema_path = (PACK / policy["semantic_harvest"]["input_schema"]).resolve()
    for rel in candidates:
        target = resolve_under_root(root, rel)
        if target is None or not target.is_file():
            rejected.append(f"{rel}: harvest input is missing or escapes repository root")
            continue
        try:
            harvest = load_json(target)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            rejected.append(f"{rel}: {exc}")
            continue
        binding_errors = _harvest_binding_errors(
            harvest,
            repository=repository,
            required_surfaces=required,
            semantic_digest=semantic_digest,
        )
        if binding_errors:
            rejected.extend(f"{rel}: {item}" for item in binding_errors)
            continue
        compiled = compile_harvest_evidence(
            harvest,
            required,
            policy["semantic_harvest"]["destinations"],
            schema_path,
            accepted_dispositions=policy["semantic_harvest"]["accepted_dispositions"],
        )
        if compiled["status"] in {"FAIL", "BLOCKED"}:
            rejected.extend(f"{rel}: {item}" for item in compiled.get("blockers", []))
            continue
        admitted.append((rel, harvest, compiled))
    if len(admitted) > 1:
        state.update(status="BLOCKED", blockers=["multiple bound harvest inputs match this change"])
        return state, None
    if not admitted:
        state.update(status="BLOCKED" if harvest_path else "PARTIAL", blockers=rejected)
        return state, None
    rel, _harvest, compiled = admitted[0]
    state.update(
        status=compiled["status"],
        input=rel,
        discovered=harvest_path is None,
        blockers=compiled.get("blockers", []),
    )
    return state, compiled


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
            status="PARTIAL", findings=["llms.txt eligible but canonical llms_base_url is UNKNOWN"]
        )
    elif enabled and base_url:
        rendered = render_llms_txt(root, policy, base_url)
        state["findings"] = validate_llms_txt(rendered)
        state["status"] = "FAIL" if state["findings"] else "PASS"
        if write_llms and state["status"] == "PASS":
            target = resolve_under_root(root, "llms.txt")
            if target is None:
                state.update(status="BLOCKED", findings=["llms.txt target escaped repository root"])
            else:
                target.write_text(rendered, encoding="utf-8")
                state["written"] = True
                mutations.append("llms.txt")
    return state, mutations


def _structural_failure(code: str, severity: str, detail: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "detail": detail}


def _status_with_structural(obligation_status: str, failures: list[dict[str, str]]) -> str:
    if any(item["severity"] == "FAIL" for item in failures):
        return "FAIL"
    if any(item["severity"] == "BLOCKED" for item in failures):
        return "BLOCKED"
    return obligation_status


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    return schema_errors(receipt, RECEIPT_SCHEMA)


def audit_repository(
    root: Path,
    *,
    changed_since: str | None = None,
    adapter: str | None = None,
    llms_base_url_value: str | None = None,
    write_llms: bool = False,
    harvest_path: str | None = None,
    source_head_sha: str | None = None,
    tested_revision_sha: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    structural: list[dict[str, str]] = []
    try:
        policy = load_policy()
        policy_errors = validate_policy(policy)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"unable to load documentation topology: {exc}") from exc
    if policy_errors:
        raise RuntimeError("documentation topology invalid: " + "; ".join(policy_errors))
    adapter_rel, adapter_state = resolve_adapter(root, adapter)
    if adapter_state == "BLOCKED":
        structural.append(
            _structural_failure(
                "adapter_resolution",
                "BLOCKED",
                "explicit adapter is missing or escapes repository root",
            )
        )
    directives = adapter_directives(root, adapter_rel)
    if changed_since:
        changed, error = changed_files_since(root, changed_since)
        changed_files, base_ref = changed or [], changed_since
    else:
        changed_files, base_ref, error = automatic_changed_scope(root)
    if error:
        structural.append(_structural_failure("change_scope", "BLOCKED", error))
    dirty_scope = base_ref == "HEAD" and bool(changed_files)
    revision = revision_identity(
        root,
        base_ref=base_ref,
        source_head_sha=source_head_sha,
        tested_revision_sha=tested_revision_sha,
        dirty_scope=dirty_scope,
    )
    impact = impact_analysis(policy, changed_files)
    impact_internal = dict(impact)
    impact_internal["all_changed_files"] = changed_files
    pointer = pointer_validate_root(root)
    if pointer["status"] == "FAIL":
        structural.append(
            _structural_failure("pointer_validation", "FAIL", "; ".join(pointer["findings"]))
        )
    managed_status, managed_findings = validate_managed_regions(
        root, base_ref, changed_files, policy
    )
    if managed_status == "FAIL":
        structural.append(
            _structural_failure("managed_regions", "FAIL", "; ".join(managed_findings))
        )
    elif managed_status == "PARTIAL":
        structural.append(
            _structural_failure("managed_regions", "BLOCKED", "; ".join(managed_findings))
        )
    module_changes = impact.get("matched_rules", {}).get("module_implementation_change", [])
    module_cap = probe_module_readme_capability(root, policy, module_changes)
    llms, run_mutations = build_llms_state(
        root, policy, directives, llms_base_url_value, write_llms
    )
    semantic_required = semantic_harvest_required(policy, impact, root)
    obligations = build_obligations(
        root,
        policy,
        impact_internal,
        revision,
        llms_enabled=llms["enabled"],
        run_mutations=run_mutations,
        semantic_required=semantic_required,
        module_capability=module_cap,
    )
    semantic_state, semantic_compiled = semantic_harvest_state(
        root, policy, impact, changed_files, harvest_path
    )
    if semantic_compiled is not None:
        obligations = apply_semantic_resolutions(
            obligations, semantic_compiled, changed_files=changed_files, run_mutations=run_mutations
        )
    elif semantic_state["status"] in {"BLOCKED", "FAIL"}:
        obligations = apply_semantic_resolutions(
            obligations,
            {"status": semantic_state["status"], "blockers": semantic_state["blockers"]},
            changed_files=changed_files,
            run_mutations=run_mutations,
        )
    obligations = validate_and_close_obligations(
        obligations, changed_files=changed_files, run_mutations=run_mutations
    )
    if llms["status"] in {"FAIL", "BLOCKED"}:
        for obligation in obligations:
            if obligation["surface"] == "llms_txt" and not obligation["lifecycle"]["terminal"]:
                obligation["lifecycle"] = {
                    "status": "BLOCKED",
                    "reason": "llms.txt projection failed validation",
                    "terminal": False,
                }
                obligation["blockers"] = sorted(set(obligation["blockers"] + llms["findings"]))
    surfaces = discover_surfaces(root, policy, llms["enabled"])
    impacted = set(impact["impacted_surfaces"])
    for row in surfaces:
        row["impacted"] = row["id"] in impacted
    validators = [
        {"name": "doc_surface_policy", "status": "PASS", "findings": []},
        {"name": "pointer_headings", "status": pointer["status"], "findings": pointer["findings"]},
        {"name": "managed_regions", "status": managed_status, "findings": managed_findings},
        {
            "name": "semantic_harvest",
            "status": semantic_state["status"],
            "findings": semantic_state["blockers"],
        },
        {
            "name": "module_readme_capability",
            "status": module_cap["status"] if module_cap["status"] != "AVAILABLE" else "PASS",
            "findings": module_cap["unsupported_impacted_extensions"],
        },
        {"name": "llms_txt", "status": llms["status"], "findings": llms["findings"]},
    ]
    summary = summarize_obligations(obligations)
    final_status = _status_with_structural(status_from_obligations(obligations), structural)
    evidence_index = sorted(
        {
            f"{item['source']}::{item['locator']['kind']}={item['locator']['value']}"
            for obligation in obligations
            for item in obligation["evidence"]
        }
    )
    blockers = sorted(
        {item["detail"] for item in structural}
        | {blocker for obligation in obligations for blocker in obligation["blockers"]}
    )
    receipt = {
        "schema": RECEIPT_ID,
        "final_status": final_status,
        "revision": revision,
        "adapter": {"path": adapter_rel, "resolution": adapter_state},
        "changes": {
            "changed_files": sorted(set(changed_files)),
            "run_mutations": sorted(set(run_mutations)),
        },
        "impact": impact,
        "surfaces": surfaces,
        "obligations": obligations,
        "summary": summary,
        "semantic_harvest": semantic_state,
        "capabilities": {"module_readmes": module_cap},
        "llms_txt": llms,
        "validators_executed": validators,
        "evidence_index": evidence_index,
        "structural_failures": structural,
        "blockers": blockers,
    }
    receipt_errors = validate_receipt_shape(receipt)
    if receipt_errors:
        receipt["structural_failures"].append(
            _structural_failure("receipt_schema", "FAIL", "; ".join(receipt_errors))
        )
        receipt["blockers"] = sorted(set(receipt["blockers"] + receipt_errors))
        receipt["final_status"] = "FAIL"
    return receipt


def exit_code_for_receipt(receipt: dict[str, Any], fail_on_partial: bool = False) -> int:
    del fail_on_partial
    return {"PASS": 0, "PARTIAL": 3, "BLOCKED": 2, "FAIL": 1}[receipt["final_status"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed-since")
    parser.add_argument("--adapter")
    parser.add_argument("--receipt")
    parser.add_argument("--llms-base-url")
    parser.add_argument("--write-llms", action="store_true")
    parser.add_argument("--harvest")
    parser.add_argument("--source-head-sha")
    parser.add_argument("--tested-revision-sha")
    parser.add_argument("--fail-on-partial", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        receipt = audit_repository(
            root,
            changed_since=args.changed_since,
            adapter=args.adapter,
            llms_base_url_value=args.llms_base_url,
            write_llms=args.write_llms,
            harvest_path=args.harvest,
            source_head_sha=args.source_head_sha,
            tested_revision_sha=args.tested_revision_sha,
        )
    except RuntimeError as exc:
        print(json.dumps({"schema": RECEIPT_ID, "final_status": "FAIL", "error": str(exc)}))
        return 1
    if args.receipt:
        target = resolve_under_root(root, args.receipt)
        if target is None:
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2 if args.json else None, sort_keys=True))
    return exit_code_for_receipt(receipt, args.fail_on_partial)


if __name__ == "__main__":
    raise SystemExit(main())
