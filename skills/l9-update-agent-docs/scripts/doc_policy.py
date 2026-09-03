"""Typed documentation topology and repository-surface mechanics."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

PACK = Path(__file__).resolve().parents[1]
POLICY_PATH = PACK / "references/doc-surface-policy.yaml"
POLICY_SCHEMA = PACK / "contracts/doc-surface-policy.schema.json"
RECEIPT_SCHEMA = PACK / "contracts/repo-docs-receipt.schema.json"
POINTER_MAP = PACK / "references/pointer-heading-map.yaml"
HEADINGS = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
DIRECTIVES = re.compile(r"<!--\s*L9_DOCS\s*\n(.*?)\n\s*-->", re.DOTALL)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
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
    operating = [
        key
        for key, spec in surfaces.items()
        if spec["authority_class"] == "operating_ssot"
    ]
    canonical = [
        key
        for key, spec in surfaces.items()
        if spec["authority_class"] == "canonical_authority"
    ]
    if len(operating) != 1:
        errors.append(
            f"exactly one operating_ssot required; found {operating or 'none'}"
        )
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
        if path and path.is_file():
            return explicit, "EXPLICIT"
        return None, "BLOCKED"
    candidates = [f".claude/adapters/{repo_slug(root)}-update-agent-docs.md"]
    plasticos_markers = ("odoo.conf", "addons", "custom_addons")
    if any((root / item).exists() for item in plasticos_markers):
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
    forbidden = {
        normalize_heading(item) for item in mapping["forbidden_donor_sections"]
    }
    rows: list[dict[str, str]] = []
    findings: list[str] = []
    unknown: list[str] = []
    for rel, spec in mapping["files"].items():
        path = root / rel
        if not path.is_file():
            rows.append({"path": rel, "status": "Unknown"})
            unknown.append(f"{rel}: missing on disk")
            continue
        text = path.read_text(encoding="utf-8")
        headings = {
            normalize_heading(match.group(2)) for match in HEADINGS.finditer(text)
        }
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


def surface_action(
    spec: dict[str, Any], *, exists: bool, enabled: bool = False
) -> str:
    if exists:
        if spec["refresh_policy"] in {"never", "external_only"}:
            return "EXTERNAL"
        return "REFRESH"
    create = spec["create_policy"]
    if create == "create_if_absent":
        return "CREATE"
    if create == "create_if_enabled" and enabled:
        return "CREATE"
    if create == "generator_owned":
        return "GENERATOR"
    return "EXTERNAL" if create == "external_only" else "SKIP"


def discover_surfaces(
    root: Path, policy: dict[str, Any], llms_enabled: bool
) -> list[dict[str, Any]]:
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
                    spec,
                    exists=bool(paths),
                    enabled=llms_enabled if name == "llms_txt" else False,
                ),
            }
        )
    return rows
