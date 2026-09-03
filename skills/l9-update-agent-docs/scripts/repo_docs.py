#!/usr/bin/env python3
"""Repository-doc topology, impact, optional llms.txt projection, and run receipt."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml

PACK = Path(__file__).resolve().parents[1]
POLICY_PATH = PACK / "references" / "doc-surface-policy.yaml"
POINTER_MAP_PATH = PACK / "references" / "pointer-heading-map.yaml"
RECEIPT_SCHEMA = "l9.repo-docs.receipt.v1"
STATUS_ORDER = {"PASS": 0, "PARTIAL": 1, "BLOCKED": 2, "FAIL": 3}
DOC_DIRECTIVE_RE = re.compile(r"<!--\s*L9_DOCS\s*\n(.*?)\n\s*-->", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)(?::\s*.*)?$", re.MULTILINE)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True, text=True
    )


def load_policy() -> dict[str, Any]:
    data = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("documentation policy must be a mapping")
    return data


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("schema") != "l9.repo-docs.surface-policy.v1":
        errors.append("wrong documentation policy schema")
    surfaces = policy.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        return errors + ["surfaces must be a non-empty mapping"]
    required = {
        "owner",
        "role",
        "authority_class",
        "selectors",
        "create_policy",
        "refresh_policy",
        "generator",
        "evidence_sources",
        "prohibited_mutations",
    }
    operating = []
    canonical = []
    for name, spec in surfaces.items():
        if not isinstance(spec, dict):
            errors.append(f"{name}: surface must be a mapping")
            continue
        missing = sorted(required - set(spec))
        if missing:
            errors.append(f"{name}: missing fields {missing}")
        if spec.get("authority_class") == "operating_ssot":
            operating.append(name)
        if spec.get("authority_class") == "canonical_authority":
            canonical.append(name)
        if spec.get("authority_class") in {"pointer", "index", "projection"}:
            if spec.get("owns_doctrine"):
                errors.append(f"{name}: pointer/index/projection cannot own doctrine")
        if spec.get("authority_class") in {"canonical_authority", "operating_ssot"}:
            if spec.get("generator") not in (None, "none"):
                errors.append(f"{name}: authoritative SSOT cannot be generated")
    if len(operating) != 1:
        errors.append(f"exactly one operating_ssot required; found {operating or 'none'}")
    if len(canonical) > 1:
        errors.append(f"at most one canonical_authority allowed; found {canonical}")
    known = set(surfaces)
    for name, rule in (policy.get("impact_rules") or {}).items():
        if not isinstance(rule, dict) or not rule.get("patterns") or not rule.get("surfaces"):
            errors.append(f"impact rule {name}: patterns and surfaces are required")
            continue
        unknown = sorted(set(rule["surfaces"]) - known)
        if unknown:
            errors.append(f"impact rule {name}: unknown surfaces {unknown}")
    return errors


def resolve_under_root(root: Path, rel: str) -> Path | None:
    raw = Path((rel or "").strip())
    if not str(raw) or raw.is_absolute() or ".." in raw.parts:
        return None
    root = root.resolve()
    dest = (root / raw).resolve()
    try:
        dest.relative_to(root)
    except ValueError:
        return None
    return dest


def _repo_slug(root: Path) -> str:
    proc = _git(root, "remote", "get-url", "origin")
    raw = proc.stdout.strip().rstrip("/") if proc.returncode == 0 else root.name
    name = raw.rsplit("/", 1)[-1].removesuffix(".git")
    return name.lower().replace("_", "-")


def _is_plasticos(root: Path) -> bool:
    return any((root / p).exists() for p in ("odoo.conf", "addons", "custom_addons"))


def resolve_adapter(root: Path, explicit: str | None = None) -> tuple[str | None, str]:
    if explicit:
        path = resolve_under_root(root, explicit)
        if path is None or not path.is_file():
            return None, "BLOCKED: explicit adapter is missing or escapes root"
        return path.relative_to(root.resolve()).as_posix(), "EXPLICIT"
    candidates = [f".claude/adapters/{_repo_slug(root)}-update-agent-docs.md"]
    if _is_plasticos(root):
        candidates.append(".claude/adapters/plasticos-update-agent-docs.md")
    for rel in candidates:
        if (root / rel).is_file():
            return rel, "DISCOVERED"
    return None, "NONE"


def adapter_directives(root: Path, adapter: str | None) -> dict[str, Any]:
    if not adapter or not (root / adapter).is_file():
        return {}
    match = DOC_DIRECTIVE_RE.search((root / adapter).read_text(encoding="utf-8"))
    if not match:
        return {}
    data = yaml.safe_load(match.group(1)) or {}
    return data if isinstance(data, dict) else {}


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", text)).lower()


def pointer_validate_root(root: Path) -> dict[str, Any]:
    try:
        mapping = yaml.safe_load(POINTER_MAP_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return {"status": "BLOCKED", "findings": [str(exc)], "files": []}
    forbidden = {_normalize_heading(x) for x in mapping.get("forbidden_donor_sections", [])}
    errors: list[str] = []
    unknown: list[str] = []
    blocked: list[str] = []
    files: list[dict[str, str]] = []
    for rel, spec in (mapping.get("files") or {}).items():
        path = root / rel
        if not path.is_file():
            files.append({"path": rel, "status": "Unknown"})
            unknown.append(f"{rel}: missing on disk")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            files.append({"path": rel, "status": "BLOCKED"})
            blocked.append(f"{rel}: unable to read: {exc}")
            continue
        headings = {_normalize_heading(m.group(2)) for m in HEADING_RE.finditer(text)}
        findings = []
        for heading in spec.get("required_headings", []):
            normalized = _normalize_heading(heading)
            if normalized in forbidden:
                findings.append(f"{rel}: forbidden donor heading {heading!r}")
            elif normalized not in headings:
                findings.append(f"{rel}: missing required heading {heading!r}")
        for pointer in spec.get("required_pointers", []):
            if pointer not in text:
                findings.append(f"{rel}: missing required pointer {pointer!r}")
        files.append({"path": rel, "status": "Failed" if findings else "Passed"})
        errors.extend(findings)
    status = "FAIL" if errors else "BLOCKED" if blocked else "PARTIAL" if unknown else "PASS"
    return {"status": status, "findings": errors + blocked + unknown, "files": files}


def _selector_paths(root: Path, selectors: list[str]) -> list[str]:
    found: set[str] = set()
    for selector in selectors:
        if any(ch in selector for ch in "*?["):
            found.update(p.relative_to(root).as_posix() for p in root.glob(selector) if p.is_file())
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
    if create == "external_only":
        return "EXTERNAL"
    return "SKIP"


def discover_surfaces(
    root: Path, policy: dict[str, Any], llms_enabled: bool
) -> list[dict[str, Any]]:
    rows = []
    for name, spec in policy["surfaces"].items():
        paths = _selector_paths(root, spec["selectors"])
        rows.append(
            {
                "id": name,
                "owner": spec["owner"],
                "role": spec["role"],
                "authority_class": spec["authority_class"],
                "paths": paths,
                "present": bool(paths),
                "action": surface_action(
                    spec,
                    exists=bool(paths),
                    enabled=llms_enabled if name == "llms_txt" else False,
                ),
            }
        )
    return rows


def changed_files_since(root: Path, base: str) -> tuple[list[str] | None, str | None]:
    if _git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode != 0:
        return None, f"unable to resolve changed-since ref {base!r}"
    proc = _git(root, "diff", "--name-only", f"{base}...HEAD")
    if proc.returncode != 0:
        return None, proc.stderr.strip() or "unable to compute changed files"
    return [x for x in proc.stdout.splitlines() if x], None


def _worktree_changes(root: Path) -> list[str]:
    proc = _git(root, "status", "--porcelain")
    if proc.returncode != 0:
        return []
    values = []
    for line in proc.stdout.splitlines():
        value = line[3:] if len(line) >= 4 else ""
        values.append(value.split(" -> ", 1)[-1])
    return sorted(set(x for x in values if x))


def automatic_changed_scope(root: Path) -> tuple[list[str], str | None, str | None]:
    dirty = _worktree_changes(root)
    if dirty:
        return dirty, None, None
    branch = _git(root, "branch", "--show-current").stdout.strip()
    if branch in {"", "main", "master"}:
        return [], None, None
    for base in ("origin/main", "origin/master", "main", "master"):
        if _git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode == 0:
            changed, error = changed_files_since(root, base)
            return changed or [], base, error
    return [], None, None


def impact_analysis(policy: dict[str, Any], changed: list[str]) -> dict[str, Any]:
    impacted: set[str] = set()
    matched: dict[str, list[str]] = {}
    for name, rule in policy["impact_rules"].items():
        hits = []
        for path in changed:
            excluded = any(fnmatch.fnmatch(path, p) for p in rule.get("exclude_patterns", []))
            if not excluded and any(fnmatch.fnmatch(path, p) for p in rule["patterns"]):
                hits.append(path)
        if hits:
            matched[name] = hits
            impacted.update(rule["surfaces"])
    return {
        "changed_files": changed,
        "impacted_surfaces": sorted(impacted),
        "matched_rules": matched,
    }


def _blocks(text: str, start: str, end: str) -> list[str]:
    found = []
    pos = 0
    while (i := text.find(start, pos)) >= 0:
        j = text.find(end, i)
        if j < 0:
            found.append(text[i:])
            break
        j += len(end)
        found.append(text[i:j])
        pos = j
    return found


def managed_block_mutations(before: str, after: str, policy: dict[str, Any]) -> list[str]:
    errors = []
    for item in policy.get("managed_regions", {}).get("blocks", []):
        old_blocks = _blocks(before, item["start"], item["end"])
        new_blocks = _blocks(after, item["start"], item["end"])
        if old_blocks != new_blocks:
            errors.append(f"managed block changed: {item['id']}")
    for item in policy.get("managed_regions", {}).get("line_tokens", []):
        token = item["token"]
        old = [x for x in before.splitlines() if token in x]
        new = [x for x in after.splitlines() if token in x]
        if old != new:
            errors.append(f"managed marker lines changed: {item['id']}")
    return errors


def validate_managed_regions(
    root: Path, base: str, changed: list[str], policy: dict[str, Any]
) -> list[str]:
    errors = []
    for rel in changed:
        path = root / rel
        if path.suffix.lower() not in {".md", ".mdc", ".txt"} or not path.is_file():
            continue
        before = _git(root, "show", f"{base}:{rel}")
        if before.returncode != 0:
            continue
        after = path.read_text(encoding="utf-8")
        errors.extend(f"{rel}: {x}" for x in managed_block_mutations(before.stdout, after, policy))
    return errors


def probe_module_readme_capability(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    cap = policy["capabilities"]["module_readmes"]
    present = {name: (root / rel).is_file() for name, rel in cap["required_paths"].items()}
    count = sum(present.values())
    status = "AVAILABLE" if count == len(present) else "NotApplicable" if count == 0 else "BLOCKED"
    return {
        "status": status,
        "owner": cap["owner"],
        "present": present,
        "partial_repair_route": cap.get("partial_repair_route"),
        "polyglot_extension_owner": cap["polyglot_extension_owner"],
    }


def llms_enabled(
    root: Path, policy: dict[str, Any], directives: dict[str, Any]
) -> tuple[bool, str]:
    value = str(directives.get("llms_txt") or "").lower()
    if value == "enabled":
        return True, "adapter"
    if value == "disabled":
        return False, "adapter_disabled"
    markers = policy["llms_txt"]["published_surface_markers"]
    if any((root / x).exists() for x in markers):
        return True, "published_docs_surface"
    return False, "no_published_docs_surface"


def llms_base_url(directives: dict[str, Any], cli: str | None) -> tuple[str | None, str]:
    value = cli or directives.get("llms_base_url")
    if value:
        return str(value).rstrip("/") + "/", "cli" if cli else "adapter"
    return None, "UNKNOWN"


def render_llms_txt(root: Path, policy: dict[str, Any], base_url: str) -> str:
    title = _repo_slug(root)
    lines = [
        f"# {title}",
        "",
        f"> LLM-facing documentation index for {title}. This file is a projection, not authority.",
        "",
        "## Documentation",
        "",
    ]
    for name in policy["llms_txt"]["surface_order"]:
        spec = policy["surfaces"][name]
        if not spec.get("llms_include"):
            continue
        rel = next(
            (
                x
                for x in spec["selectors"]
                if not any(ch in x for ch in "*?[") and (root / x).is_file()
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
    for level, _heading in HEADING_RE.findall(text):
        if len(level) >= 3:
            errors.append("llms.txt must stay shallow")
            break
    for url in LINK_RE.findall(text):
        if not url.startswith(("https://", "http://")):
            errors.append(f"llms.txt link is not absolute: {url}")
    return errors


def write_llms_txt(root: Path, text: str) -> Path:
    target = resolve_under_root(root, "llms.txt")
    if target is None or target.parent != root.resolve():
        raise ValueError("llms.txt target must be repository root")
    target.write_text(text, encoding="utf-8")
    return target


def _head(root: Path) -> str:
    proc = _git(root, "rev-parse", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "UNKNOWN"


def _merge_status(current: str, incoming: str) -> str:
    return incoming if STATUS_ORDER[incoming] > STATUS_ORDER[current] else current


def audit_repository(
    root: Path,
    *,
    changed_since: str | None = None,
    adapter: str | None = None,
    llms_base_url_value: str | None = None,
    write_llms: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    blockers: list[str] = []
    try:
        policy = load_policy()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {"schema": RECEIPT_SCHEMA, "final_status": "BLOCKED", "blockers": [str(exc)]}
    policy_errors = validate_policy(policy)
    if policy_errors:
        return {"schema": RECEIPT_SCHEMA, "final_status": "FAIL", "blockers": policy_errors}

    adapter_rel, adapter_state = resolve_adapter(root, adapter)
    if adapter_state.startswith("BLOCKED"):
        blockers.append(adapter_state)
    directives = adapter_directives(root, adapter_rel)
    if changed_since:
        changed, error = changed_files_since(root, changed_since)
        changed_files, base = changed or [], changed_since
    else:
        changed_files, base, error = automatic_changed_scope(root)
    if error:
        blockers.append(error)
    impact = impact_analysis(policy, changed_files)
    managed = (
        validate_managed_regions(root, base, changed_files, policy)
        if base and not blockers
        else []
    )
    module_cap = probe_module_readme_capability(root, policy)
    pointer = pointer_validate_root(root)

    enabled, enabled_reason = llms_enabled(root, policy, directives)
    base_url, base_source = llms_base_url(directives, llms_base_url_value)
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
        llms["status"] = "PARTIAL"
        llms["findings"] = ["llms.txt eligible but canonical llms_base_url is UNKNOWN"]
    elif enabled and base_url:
        rendered = render_llms_txt(root, policy, base_url)
        llms["findings"] = validate_llms_txt(rendered)
        llms["status"] = "FAIL" if llms["findings"] else "PASS"
        if write_llms and llms["status"] == "PASS":
            target = resolve_under_root(root, "llms.txt")
            assert target is not None and target.parent == root
            target.write_text(rendered, encoding="utf-8")
            llms["written"] = True

    surfaces = discover_surfaces(root, policy, enabled)
    impacted = set(impact["impacted_surfaces"])
    for row in surfaces:
        row["impacted"] = row["id"] in impacted
    status = "PASS"
    validators = [
        {"name": "doc_surface_policy", "status": "PASS", "findings": []},
        {"name": "pointer_headings", "status": pointer["status"], "findings": pointer["findings"]},
        {"name": "managed_regions", "status": "FAIL" if managed else "PASS", "findings": managed},
        {
            "name": "module_readme_capability",
            "status": module_cap["status"],
            "findings": module_cap["present"],
        },
        {"name": "llms_txt", "status": llms["status"], "findings": llms["findings"]},
    ]
    for item in validators:
        value = item["status"]
        if value == "FAIL":
            status = _merge_status(status, "FAIL")
        elif value == "BLOCKED":
            status = _merge_status(status, "BLOCKED")
        elif value in {"PARTIAL", "NotApplicable"}:
            status = _merge_status(status, "PARTIAL")
    if blockers:
        status = _merge_status(status, "BLOCKED")
    unknown = [
        row["id"]
        for row in surfaces
        if not row["present"] and row["action"] in {"CREATE", "GENERATOR"}
    ]
    if unknown:
        status = _merge_status(status, "PARTIAL")
    skipped = [
        item
        for row in surfaces
        if row["action"] in {"SKIP", "EXTERNAL"}
        for item in (row["paths"] or [row["id"]])
    ]
    evidence = sorted(
        {
            "references/doc-surface-policy.yaml",
            "references/pointer-heading-map.yaml",
            *(x for spec in policy["surfaces"].values() for x in spec["evidence_sources"]),
            *(filter(None, [adapter_rel])),
        }
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "final_status": status,
        "target": {"repository_root": str(root), "sha": _head(root), "changed_since": base},
        "adapter": {"path": adapter_rel, "resolution": adapter_state},
        "surfaces": surfaces,
        "changes": {
            "changed_files": changed_files,
            "skipped_files": sorted(set(skipped)),
            "unknown_files": sorted(set(unknown)),
        },
        "impact": impact,
        "capabilities": {"module_readmes": module_cap},
        "llms_txt": llms,
        "validators_executed": validators,
        "evidence_sources": evidence,
        "blockers": blockers,
    }


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    required = {
        "schema",
        "final_status",
        "target",
        "surfaces",
        "changes",
        "evidence_sources",
        "validators_executed",
    }
    missing = sorted(required - set(receipt))
    errors = [f"receipt missing fields: {missing}"] if missing else []
    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("receipt schema mismatch")
    if receipt.get("final_status") not in STATUS_ORDER:
        errors.append("invalid receipt status")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--changed-since")
    parser.add_argument("--adapter")
    parser.add_argument("--receipt")
    parser.add_argument("--llms-base-url")
    parser.add_argument("--write-llms", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = audit_repository(
        root,
        changed_since=args.changed_since,
        adapter=args.adapter,
        llms_base_url_value=args.llms_base_url,
        write_llms=args.write_llms,
    )
    if args.receipt:
        target = resolve_under_root(root, args.receipt)
        if target is None:
            print("BLOCKED: receipt path escapes repository root", file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(f"STATUS: {receipt['final_status']}")
        if receipt.get("impact", {}).get("impacted_surfaces"):
            print("IMPACTED: " + ", ".join(receipt["impact"]["impacted_surfaces"]))
        print("RECEIPT: " + json.dumps(receipt, sort_keys=True))
    return {"PASS": 0, "PARTIAL": 0, "BLOCKED": 2, "FAIL": 1}[receipt["final_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
