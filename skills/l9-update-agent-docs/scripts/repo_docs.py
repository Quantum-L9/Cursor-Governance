#!/usr/bin/env python3
"""Machine-first repository documentation obligation controller."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml
from jsonschema import Draft202012Validator

from compile_semantic_obligations import compile_obligations

PACK = Path(__file__).resolve().parents[1]
POLICY_PATH = PACK / "references/doc-surface-policy.yaml"
POLICY_SCHEMA = PACK / "contracts/doc-surface-policy.schema.json"
RECEIPT_SCHEMA = PACK / "contracts/repo-docs-receipt.schema.json"
POINTER_MAP = PACK / "references/pointer-heading-map.yaml"
RECEIPT_ID = "l9.repo-docs.receipt.v2"
STATUS = {"PASS": 0, "PARTIAL": 1, "BLOCKED": 2, "FAIL": 3}
HEADINGS = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINKS = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)
DIRECTIVES = re.compile(r"<!--\s*L9_DOCS\s*\n(.*?)\n\s*-->", re.DOTALL)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True, text=True
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def schema_errors(value: dict[str, Any], path: Path) -> list[str]:
    validator = Draft202012Validator(load_json(path))
    return [
        f"{'.'.join(map(str, error.path)) or '$'}: {error.message}"
        for error in validator.iter_errors(value)
    ]


def load_policy() -> dict[str, Any]:
    value = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("documentation policy must be a mapping")
    return value


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors = schema_errors(policy, POLICY_SCHEMA)
    if errors:
        return errors
    surfaces = policy["surfaces"]
    operating = [k for k, v in surfaces.items() if v["authority_class"] == "operating_ssot"]
    canonical = [k for k, v in surfaces.items() if v["authority_class"] == "canonical_authority"]
    if len(operating) != 1:
        errors.append(f"exactly one operating_ssot required; found {operating or 'none'}")
    if len(canonical) > 1:
        errors.append(f"at most one canonical_authority allowed; found {canonical}")
    known = set(surfaces)
    for name, rule in policy["impact_rules"].items():
        unknown = sorted(set(rule["surfaces"]) - known)
        if unknown:
            errors.append(f"impact rule {name}: unknown surfaces {unknown}")
    return errors


def resolve_under_root(root: Path, rel: str) -> Path | None:
    raw = Path((rel or "").strip())
    if not str(raw) or raw.is_absolute() or ".." in raw.parts:
        return None
    root = root.resolve()
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def repo_slug(root: Path) -> str:
    proc = git(root, "remote", "get-url", "origin")
    raw = proc.stdout.strip().rstrip("/") if proc.returncode == 0 else root.name
    return raw.rsplit("/", 1)[-1].removesuffix(".git").lower().replace("_", "-")


def resolve_adapter(root: Path, explicit: str | None = None) -> tuple[str | None, str]:
    if explicit:
        path = resolve_under_root(root, explicit)
        return (explicit, "EXPLICIT") if path and path.is_file() else (None, "BLOCKED")
    candidates = [f".claude/adapters/{repo_slug(root)}-update-agent-docs.md"]
    if any((root / item).exists() for item in ("odoo.conf", "addons", "custom_addons")):
        candidates.append(".claude/adapters/plasticos-update-agent-docs.md")
    for rel in candidates:
        if (root / rel).is_file():
            return rel, "DISCOVERED"
    return None, "NONE"


def adapter_directives(root: Path, adapter: str | None) -> dict[str, Any]:
    if not adapter or not (root / adapter).is_file():
        return {}
    match = DIRECTIVES.search((root / adapter).read_text(encoding="utf-8"))
    value = yaml.safe_load(match.group(1)) if match else {}
    return value if isinstance(value, dict) else {}


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", value)).lower()


def pointer_validate_root(root: Path) -> dict[str, Any]:
    mapping = yaml.safe_load(POINTER_MAP.read_text(encoding="utf-8"))
    forbidden = {normalize_heading(item) for item in mapping["forbidden_donor_sections"]}
    rows, findings, unknown = [], [], []
    for rel, spec in mapping["files"].items():
        path = root / rel
        if not path.is_file():
            rows.append({"path": rel, "status": "Unknown"})
            unknown.append(f"{rel}: missing on disk")
            continue
        text = path.read_text(encoding="utf-8")
        headings = {normalize_heading(m.group(2)) for m in HEADINGS.finditer(text)}
        local = []
        for heading in spec.get("required_headings", []):
            normalized = normalize_heading(heading)
            if normalized in forbidden or normalized not in headings:
                local.append(f"{rel}: missing/forbidden heading {heading!r}")
        for pointer in spec.get("required_pointers", []):
            if pointer not in text:
                local.append(f"{rel}: missing required pointer {pointer!r}")
        rows.append({"path": rel, "status": "Failed" if local else "Passed"})
        findings.extend(local)
    status = "FAIL" if findings else "PARTIAL" if unknown else "PASS"
    return {"status": status, "findings": findings + unknown, "files": rows}


def selector_paths(root: Path, selectors: list[str]) -> list[str]:
    found: set[str] = set()
    for selector in selectors:
        if any(char in selector for char in "*?["):
            found.update(
                path.relative_to(root).as_posix()
                for path in root.glob(selector)
                if path.is_file()
            )
        elif (root / selector).is_file():
            found.add(selector)
    return sorted(found)


def surface_action(spec: dict[str, Any], *, exists: bool, enabled: bool = False) -> str:
    if exists:
        return "EXTERNAL" if spec["refresh_policy"] in {"never", "external_only"} else "REFRESH"
    create = spec["create_policy"]
    if create == "create_if_absent" or (create == "create_if_enabled" and enabled):
        return "CREATE"
    if create == "generator_owned":
        return "GENERATOR"
    return "EXTERNAL" if create == "external_only" else "SKIP"


def discover_surfaces(root: Path, policy: dict[str, Any], llms_enabled: bool) -> list[dict[str, Any]]:
    rows = []
    for name, spec in policy["surfaces"].items():
        paths = selector_paths(root, spec["selectors"])
        rows.append(
            {
                "id": name,
                "owner": spec["owner"],
                "role": spec["role"],
                "authority_class": spec["authority_class"],
                "requirement": spec["requirement"],
                "paths": paths,
                "present": bool(paths),
                "action": surface_action(
                    spec, exists=bool(paths), enabled=llms_enabled if name == "llms_txt" else False
                ),
            }
        )
    return rows


def changed_files_since(root: Path, base: str) -> tuple[list[str] | None, str | None]:
    if git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode != 0:
        return None, f"unable to resolve changed-since ref {base!r}"
    proc = git(root, "diff", "--name-only", f"{base}...HEAD")
    return ([item for item in proc.stdout.splitlines() if item], None) if proc.returncode == 0 else (None, proc.stderr.strip())


def worktree_changes(root: Path) -> list[str]:
    proc = git(root, "status", "--porcelain")
    values = [line[3:].split(" -> ", 1)[-1] for line in proc.stdout.splitlines()] if proc.returncode == 0 else []
    return sorted(set(item for item in values if item))


def automatic_changed_scope(root: Path) -> tuple[list[str], str | None, str | None]:
    dirty = worktree_changes(root)
    if dirty:
        base = "HEAD" if git(root, "rev-parse", "--verify", "HEAD^{commit}").returncode == 0 else None
        return dirty, base, None
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch in {"", "main", "master"}:
        return [], None, None
    for base in ("origin/main", "origin/master", "main", "master"):
        if git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode == 0:
            changed, error = changed_files_since(root, base)
            return changed or [], base, error
    return [], None, None


def impact_analysis(policy: dict[str, Any], changed: list[str]) -> dict[str, Any]:
    impacted, matched = set(), {}
    for name, rule in policy["impact_rules"].items():
        hits = [
            path
            for path in changed
            if not any(fnmatch.fnmatch(path, p) for p in rule.get("exclude_patterns", []))
            and any(fnmatch.fnmatch(path, p) for p in rule["patterns"])
        ]
        if hits:
            matched[name] = hits
            impacted.update(rule["surfaces"])
    return {"changed_files": changed, "impacted_surfaces": sorted(impacted), "matched_rules": matched}


def semantic_harvest_required(
    policy: dict[str, Any], impact: dict[str, Any], root: Path | None = None
) -> list[str]:
    matched, required = set(impact.get("matched_rules", {})), []
    for surface, rules in policy["semantic_harvest"]["activation"].items():
        if not matched.intersection(rules):
            continue
        spec = policy["surfaces"][surface]
        if root is not None and not selector_paths(root, spec["selectors"]):
            if spec["requirement"] == "conditional" and spec["create_policy"] == "never":
                continue
        required.append(surface)
    return sorted(required)


def head(root: Path) -> str:
    proc = git(root, "rev-parse", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "UNKNOWN"


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
    root: Path, policy: dict[str, Any], impact: dict[str, Any], harvest_path: str | None
) -> dict[str, Any]:
    required = semantic_harvest_required(policy, impact, root)
    state = {
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


def managed_block_mutations(before: str, after: str, policy: dict[str, Any]) -> list[str]:
    errors = []
    for item in policy.get("managed_regions", {}).get("blocks", []):
        pattern = re.compile(re.escape(item["start"]) + r".*?" + re.escape(item["end"]), re.DOTALL)
        if pattern.findall(before) != pattern.findall(after):
            errors.append(f"managed block changed: {item['id']}")
    for item in policy.get("managed_regions", {}).get("line_tokens", []):
        token = item["token"]
        old = [line for line in before.splitlines() if token in line]
        new = [line for line in after.splitlines() if token in line]
        if old != new:
            errors.append(f"managed marker lines changed: {item['id']}")
    return errors


def validate_managed_regions(
    root: Path, base: str | None, changed: list[str], policy: dict[str, Any]
) -> tuple[str, list[str]]:
    docs = [path for path in changed if Path(path).suffix.lower() in {".md", ".mdc", ".txt"}]
    if docs and not base:
        return "PARTIAL", ["managed-region comparison base unavailable for changed documentation"]
    errors = []
    for rel in docs:
        path = root / rel
        if not path.is_file():
            continue
        before = git(root, "show", f"{base}:{rel}")
        if before.returncode == 0:
            errors.extend(
                f"{rel}: {error}"
                for error in managed_block_mutations(before.stdout, path.read_text(encoding="utf-8"), policy)
            )
    return ("FAIL", errors) if errors else ("PASS", [])


def probe_module_readme_capability(
    root: Path, policy: dict[str, Any], changed: list[str] | None = None
) -> dict[str, Any]:
    cap = policy["capabilities"]["module_readmes"]
    present = {name: (root / rel).is_file() for name, rel in cap["required_paths"].items()}
    count = sum(present.values())
    status = "AVAILABLE" if count == len(present) else "NotApplicable" if count == 0 else "BLOCKED"
    extensions = {Path(path).suffix for path in changed or [] if Path(path).suffix}
    unsupported = sorted(extensions - set(cap.get("supported_extensions", [])))
    if status == "AVAILABLE" and unsupported:
        status = "PARTIAL"
    return {
        "status": status,
        "owner": cap["owner"],
        "present": present,
        "partial_repair_route": cap.get("partial_repair_route"),
        "polyglot_extension_owner": cap["polyglot_extension_owner"],
        "unsupported_impacted_extensions": unsupported,
    }


def llms_enabled(root: Path, policy: dict[str, Any], directives: dict[str, Any]) -> tuple[bool, str]:
    value = str(directives.get("llms_txt") or "").lower()
    if value in {"enabled", "disabled"}:
        return value == "enabled", "adapter" if value == "enabled" else "adapter_disabled"
    if any((root / marker).exists() for marker in policy["llms_txt"]["published_surface_markers"]):
        return True, "published_docs_surface"
    return False, "no_published_docs_surface"


def llms_base_url(directives: dict[str, Any], cli: str | None) -> tuple[str | None, str]:
    value = cli or directives.get("llms_base_url")
    return ((str(value).rstrip("/") + "/", "cli" if cli else "adapter") if value else (None, "UNKNOWN"))


def render_llms_txt(root: Path, policy: dict[str, Any], base_url: str) -> str:
    title = repo_slug(root)
    lines = [f"# {title}", "", f"> LLM-facing documentation index for {title}. Projection only; not authority.", "", "## Documentation", ""]
    for name in policy["llms_txt"]["surface_order"]:
        spec = policy["surfaces"][name]
        if not spec.get("llms_include"):
            continue
        rel = next(
            (
                selector
                for selector in spec["selectors"]
                if not any(char in selector for char in "*?[") and (root / selector).is_file()
            ),
            None,
        )
        if rel:
            lines.append(f"- [{spec['role']}]({urljoin(base_url, rel)}): owner `{spec['owner']}`")
    return "\n".join(lines).rstrip() + "\n"


def validate_llms_txt(text: str) -> list[str]:
    errors = []
    if not text.startswith("# ") or text.startswith("## "):
        errors.append("llms.txt must begin with one H1 title")
    if any(len(level) >= 3 for level, _ in HEADINGS.findall(text)):
        errors.append("llms.txt must stay shallow")
    errors.extend(f"llms.txt link is not absolute: {url}" for url in LINKS.findall(text) if not url.startswith(("https://", "http://")))
    return errors


def freshness_analysis(
    root: Path,
    policy: dict[str, Any],
    impact: dict[str, Any],
    llms_is_enabled: bool,
    run_mutations: list[str] | None = None,
) -> dict[str, Any]:
    changed = sorted(set(impact.get("changed_files", [])) | set(run_mutations or []))
    rows, stale, missing = [], [], []
    for surface in impact.get("impacted_surfaces", []):
        spec = policy["surfaces"][surface]
        if surface == "llms_txt" and not llms_is_enabled:
            rows.append({"surface": surface, "status": "NotApplicable", "changed_paths": []})
            continue
        present = selector_paths(root, spec["selectors"])
        touched = sorted(
            path for path in changed if any(fnmatch.fnmatch(path, selector) for selector in spec["selectors"])
        )
        if touched:
            state = "CURRENT"
        elif not present and spec["requirement"] == "conditional" and spec["create_policy"] == "never":
            state = "NotApplicable"
        elif not present:
            state = "MISSING"
            missing.append(surface)
        else:
            state = "STALE"
            stale.append(surface)
        rows.append({"surface": surface, "status": state, "changed_paths": touched})
    return {
        "status": "PARTIAL" if stale or missing else "PASS",
        "surfaces": rows,
        "stale_surfaces": sorted(stale),
        "missing_surfaces": sorted(missing),
    }


def merge_status(current: str, incoming: str) -> str:
    return incoming if STATUS[incoming] > STATUS[current] else current


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
) -> dict[str, Any]:
    root, blockers = root.resolve(), []
    try:
        policy = load_policy()
        policy_errors = validate_policy(policy)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        return {"schema": RECEIPT_ID, "final_status": "BLOCKED", "blockers": [str(exc)]}
    if policy_errors:
        return {"schema": RECEIPT_ID, "final_status": "FAIL", "blockers": policy_errors}
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
        root, policy, impact["matched_rules"].get("module_implementation_change", [])
    )
    enabled, enabled_reason = llms_enabled(root, policy, directives)
    base_url, base_source = llms_base_url(directives, llms_base_url_value)
    run_mutations: list[str] = []
    llms = {
        "status": "NotApplicable",
        "enabled": enabled,
        "enabled_reason": enabled_reason,
        "base_url_source": base_source,
        "path": "llms.txt",
        "written": False,
        "findings": [],
    }
    if enabled and not base_url:
        llms.update(status="PARTIAL", findings=["llms.txt eligible but canonical llms_base_url is UNKNOWN"])
    elif enabled and base_url:
        rendered = render_llms_txt(root, policy, base_url)
        llms["findings"] = validate_llms_txt(rendered)
        llms["status"] = "FAIL" if llms["findings"] else "PASS"
        if write_llms and llms["status"] == "PASS":
            target = resolve_under_root(root, "llms.txt")
            if target is None:
                llms.update(status="BLOCKED", findings=["llms.txt target escaped repository root"])
            else:
                target.write_text(rendered, encoding="utf-8")
                llms["written"] = True
                run_mutations.append("llms.txt")
    freshness = freshness_analysis(root, policy, impact, enabled, run_mutations)
    surfaces = discover_surfaces(root, policy, enabled)
    impacted = set(impact["impacted_surfaces"])
    for row in surfaces:
        row["impacted"] = row["id"] in impacted
    validators = [
        {"name": "doc_surface_policy", "status": "PASS", "findings": []},
        {"name": "pointer_headings", "status": pointer["status"], "findings": pointer["findings"]},
        {"name": "managed_regions", "status": managed_status, "findings": managed_findings},
        {"name": "semantic_harvest", "status": semantic["status"], "findings": semantic["blockers"] + semantic["unresolved_surfaces"]},
        {"name": "doc_freshness", "status": freshness["status"], "findings": freshness["stale_surfaces"] + freshness["missing_surfaces"]},
        {"name": "module_readme_capability", "status": module_cap["status"], "findings": module_cap["unsupported_impacted_extensions"]},
        {"name": "llms_txt", "status": llms["status"], "findings": llms["findings"]},
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
    evidence = {"references/doc-surface-policy.yaml", "references/pointer-heading-map.yaml"}
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
        "target": {"repository_root": str(root), "sha": head(root), "changed_since": base},
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
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2 if args.json else None, sort_keys=True))
    return exit_code_for_receipt(receipt, args.fail_on_partial)


if __name__ == "__main__":
    raise SystemExit(main())
