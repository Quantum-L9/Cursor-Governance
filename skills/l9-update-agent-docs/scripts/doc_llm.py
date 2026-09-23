"""Versioned llm.txt consumer documentation manifest mechanics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml
from consumer_snapshot import snapshot_document
from doc_owned_write import Admission, apply_owned_write
from doc_policy import LLM_SURFACE_ID, repo_slug, resolve_under_root

PROJECTION_FILENAME = "llm.txt"
LEGACY_FILENAME = "llms.txt"
LLM_MARKER = "<!-- l9-llm-txt: generated-projection -->"
MANIFEST_SCHEMA = "l9.repo-docs.llm-manifest.v1"

HEADINGS = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINKS = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)
_MANIFEST = re.compile(r"<!--\s*L9_DOC_MANIFEST\s*\n(.*?)\n\s*-->", re.DOTALL)


def llm_enabled(
    root: Path,
    policy: dict[str, Any],
    directives: dict[str, Any],
) -> tuple[bool, str]:
    del root, policy
    value = str(directives.get(LLM_SURFACE_ID) or "").lower()
    if value == "disabled":
        return False, "adapter_disabled"
    if value == "enabled":
        return True, "adapter"
    return True, "default"


def llm_base_url(directives: dict[str, Any], cli: str | None) -> tuple[str | None, str]:
    value = cli or directives.get("llm_base_url")
    if not value:
        return None, "repo_relative"
    source = "cli" if cli else "adapter"
    return str(value).rstrip("/") + "/", source


def _manifest_entry(
    root: Path,
    policy: dict[str, Any],
    snapshot: dict[str, Any],
    surface: str,
    base_url: str | None,
) -> dict[str, str] | None:
    spec = policy["surfaces"][surface]
    rel = next(
        (
            selector
            for selector in spec["selectors"]
            if not any(char in selector for char in "*?[") and (root / selector).is_file()
        ),
        None,
    )
    if not rel:
        return None
    document = snapshot_document(snapshot, rel)
    if document is None:
        return None
    published = bool(snapshot.get("publication_markers")) and base_url is not None
    href = urljoin(base_url, rel) if published and base_url else rel
    return {
        "id": surface,
        "path": rel,
        "href": href,
        "role": str(spec["role"]),
        "owner": str(spec["owner"]),
        "authority_class": str(spec["authority_class"]),
        "sha256": str(document["digest"]),
        "availability": "published" if published else "repository_local",
    }


def llm_manifest(
    root: Path,
    policy: dict[str, Any],
    snapshot: dict[str, Any],
    base_url: str | None,
) -> dict[str, Any]:
    entries = [
        entry
        for surface in policy[LLM_SURFACE_ID]["surface_order"]
        if policy["surfaces"][surface].get("llm_include")
        if (entry := _manifest_entry(root, policy, snapshot, surface, base_url)) is not None
    ]
    return {
        "schema": policy[LLM_SURFACE_ID]["manifest_schema"],
        "snapshot_digest": snapshot["digest"],
        "publication": "published"
        if any(item["availability"] == "published" for item in entries)
        else "repository_local",
        "entries": entries,
    }


def render_llm_txt(
    root: Path,
    policy: dict[str, Any],
    base_url: str | None,
    snapshot: dict[str, Any],
) -> str:
    title = repo_slug(root)
    manifest = llm_manifest(root, policy, snapshot, base_url)
    lines = [
        f"# {title}",
        "",
        f"> LLM-facing documentation manifest for {title}. Projection only; not authority.",
        "",
        LLM_MARKER,
        "",
        "<!-- L9_DOC_MANIFEST",
        yaml.safe_dump(manifest, sort_keys=False).rstrip(),
        "-->",
        "",
        "## Documentation",
        "",
    ]
    for entry in manifest["entries"]:
        lines.append(f"- [{entry['role']}]({entry['href']}): owner `{entry['owner']}`")
    return "\n".join(lines).rstrip() + "\n"


def retire_legacy_llms_txt(root: Path, *, rename_missing: bool = True) -> list[str]:
    """Keep handwritten bytes; only drop the obsolete name once llm.txt exists."""
    mutations: list[str] = []
    canonical = resolve_under_root(root, PROJECTION_FILENAME)
    legacy = resolve_under_root(root, LEGACY_FILENAME)
    if canonical is None or legacy is None:
        return mutations
    if canonical.is_file() and legacy.is_file():
        legacy.unlink()
        mutations.append(f"retired:{LEGACY_FILENAME}")
        return mutations
    if rename_missing and not canonical.is_file() and legacy.is_file():
        legacy.replace(canonical)
        mutations.append(PROJECTION_FILENAME)
        mutations.append(f"retired:{LEGACY_FILENAME}")
    return mutations


def write_llm_txt(root: Path, rendered: str) -> tuple[bool, Admission]:
    """Owned write of llm.txt."""
    target = resolve_under_root(root, PROJECTION_FILENAME)
    if target is None:
        raise ValueError(f"{PROJECTION_FILENAME} target escaped repository root")
    return apply_owned_write(target, rendered, LLM_MARKER)


def _manifest_from_text(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    match = _MANIFEST.search(text)
    if not match:
        return None, [f"{PROJECTION_FILENAME} missing L9_DOC_MANIFEST block"]
    try:
        manifest = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return None, [f"{PROJECTION_FILENAME} manifest is invalid YAML: {exc}"]
    if not isinstance(manifest, dict):
        return None, [f"{PROJECTION_FILENAME} manifest must be a mapping"]
    return manifest, []


def validate_llm_txt(
    text: str,
    *,
    root: Path | None = None,
    snapshot: dict[str, Any] | None = None,
) -> list[str]:
    errors = []
    if not text.startswith("# ") or text.startswith("## "):
        errors.append(f"{PROJECTION_FILENAME} must begin with one H1 title")
    if any(len(level) >= 3 for level, _ in HEADINGS.findall(text)):
        errors.append(f"{PROJECTION_FILENAME} must stay shallow")
    errors.extend(
        f"{PROJECTION_FILENAME} link is not a repo-relative path or absolute URL: {url}"
        for url in LINKS.findall(text)
        if not _link_allowed(url)
    )
    manifest, manifest_errors = _manifest_from_text(text)
    errors.extend(manifest_errors)
    if manifest is None:
        return errors
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append(f"{PROJECTION_FILENAME} manifest schema is invalid")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        errors.append(f"{PROJECTION_FILENAME} manifest entries must be a list")
        return errors
    ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(f"{PROJECTION_FILENAME} manifest contains a non-mapping entry")
            continue
        required = {
            "id",
            "path",
            "href",
            "role",
            "owner",
            "authority_class",
            "sha256",
            "availability",
        }
        if not required.issubset(entry):
            errors.append(f"{PROJECTION_FILENAME} manifest entry is incomplete")
            continue
        entry_id = str(entry["id"])
        if entry_id in ids:
            errors.append(f"{PROJECTION_FILENAME} manifest entry id is duplicated: {entry_id}")
        ids.add(entry_id)
        path = str(entry["path"])
        if root is not None:
            target = resolve_under_root(root, path)
            if target is None or not target.is_file():
                errors.append(f"{PROJECTION_FILENAME} manifest path does not resolve: {path}")
        if snapshot is not None:
            document = snapshot_document(snapshot, path)
            if document is None or document.get("digest") != entry["sha256"]:
                errors.append(f"{PROJECTION_FILENAME} manifest source digest is stale: {path}")
            if manifest.get("snapshot_digest") != snapshot.get("digest"):
                errors.append(f"{PROJECTION_FILENAME} manifest snapshot digest is stale")
                break
        if entry["availability"] == "repository_local" and str(entry["href"]) != path:
            errors.append(f"{PROJECTION_FILENAME} local manifest href must equal its path: {path}")
    return errors


def _link_allowed(url: str) -> bool:
    if url.startswith(("https://", "http://")):
        return True
    return (
        bool(url) and "://" not in url and not url.startswith("/") and ".." not in Path(url).parts
    )
