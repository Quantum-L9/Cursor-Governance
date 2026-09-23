#!/usr/bin/env python3
"""Closed-world consumer repository facts shared by documentation surfaces.

The snapshot is deliberately observation-only.  It reads policy-selected
consumer documents and static project declarations, records locators and
digests, and never executes a consumer command or imports consumer code.
Renderers and analyzers consume the same object so their claims cannot drift.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import unquote

__all__ = ["SNAPSHOT_SCHEMA", "build_consumer_snapshot", "snapshot_document"]

SNAPSHOT_SCHEMA = "l9.repo-docs.consumer-snapshot.v1"
_ROOT_DOCUMENTS = (
    "CANONICAL_LAW.md",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "INVARIANTS.md",
)
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", re.MULTILINE)
_LOCKED_UV_RE = re.compile(r"\buv\s+(?:sync\s+--locked|lock\s+--check)\b")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _anchor(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[`*_~]", "", lowered)
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    return re.sub(r"\s+", "-", lowered).strip("-")


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _safe_relative(root: Path, current: Path, raw: str) -> tuple[str | None, str | None]:
    """Return root-relative path plus fragment only when a local link stays in root."""
    path_part, _separator, fragment = unquote(raw).partition("#")
    if not path_part:
        return current.relative_to(root).as_posix(), fragment or None
    candidate = (current.parent / path_part).resolve()
    try:
        return candidate.relative_to(root).as_posix(), fragment or None
    except ValueError:
        return None, fragment or None


def _document(root: Path, rel: str) -> dict[str, Any] | None:
    path = root / rel
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    headings = [
        {
            "anchor": _anchor(match.group(2)),
            "line": _line(text, match.start()),
            "text": match.group(2),
        }
        for match in _HEADING_RE.finditer(text)
        if _anchor(match.group(2))
    ]
    links: list[dict[str, Any]] = []
    for match in _LINK_RE.finditer(text):
        raw_link = match.group(1).strip().strip("<>")
        if not raw_link or raw_link.startswith(("http://", "https://", "mailto:")):
            continue
        target, fragment = _safe_relative(root, path, raw_link)
        links.append(
            {
                "raw": raw_link,
                "target": target,
                "fragment": fragment,
                "line": _line(text, match.start()),
            }
        )
    return {
        "path": rel,
        "digest": _sha256(raw),
        "headings": headings,
        "links": links,
    }


def _literal_surface_paths(root: Path, policy: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for surface, spec in policy["surfaces"].items():
        paths: list[str] = []
        for selector in spec["selectors"]:
            if any(char in selector for char in "*?["):
                paths.extend(
                    sorted(
                        path.relative_to(root).as_posix()
                        for path in root.glob(selector)
                        if path.is_file()
                    )
                )
            elif (root / selector).is_file():
                paths.append(selector)
        result[surface] = sorted(set(paths))
    return result


def _workflow_facts(root: Path) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    workflow_root = root / ".github/workflows"
    if not workflow_root.is_dir():
        return facts
    for path in sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        for match in _LOCKED_UV_RE.finditer(text):
            facts.append(
                {
                    "id": f"workflow-locked-uv:{rel}:{_line(text, match.start())}",
                    "kind": "workflow_locked_uv",
                    "path": rel,
                    "line": _line(text, match.start()),
                    "value": match.group(0),
                }
            )
    return facts


def _project_facts(root: Path) -> list[dict[str, Any]]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return []
    facts: list[dict[str, Any]] = []
    scripts = (data.get("project") or {}).get("scripts") or {}
    if isinstance(scripts, dict):
        for name, value in sorted(scripts.items()):
            if not isinstance(value, str):
                continue
            module = value.split(":", 1)[0].strip()
            key = re.escape(str(name))
            assignment = re.search(
                rf"^\s*(?:{key}|\"{key}\"|'{key}')\s*=",
                text,
                re.MULTILINE,
            )
            candidates = [
                f"{module.replace('.', '/')}.py",
                f"src/{module.replace('.', '/')}.py",
            ]
            resolution = next((item for item in candidates if (root / item).is_file()), None)
            facts.append(
                {
                    "id": f"project-script:{name}",
                    "kind": "project_script",
                    "path": "pyproject.toml",
                    "line": _line(text, assignment.start()) if assignment else None,
                    "name": str(name),
                    "value": value,
                    "resolution": resolution,
                }
            )
    return facts


def _make_facts(root: Path) -> list[dict[str, Any]]:
    path = root / "Makefile"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [
        {
            "id": f"make-target:{match.group(1)}",
            "kind": "make_target",
            "path": "Makefile",
            "line": _line(text, match.start()),
            "value": match.group(1),
        }
        for match in _MAKE_TARGET_RE.finditer(text)
    ]


def _authority_graph(documents: dict[str, dict[str, Any]], root_docs: set[str]) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    for source, document in sorted(documents.items()):
        if source not in root_docs:
            continue
        for link in document["links"]:
            target = link["target"]
            if target in root_docs:
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "line": link["line"],
                        "relation": "references",
                    }
                )
    adjacency: dict[str, set[str]] = {name: set() for name in root_docs}
    for edge in edges:
        adjacency[edge["source"]].add(edge["target"])
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, chain: tuple[str, ...]) -> None:
        for target in sorted(adjacency.get(node, set())):
            if target in chain:
                index = chain.index(target)
                cycles.add(chain[index:] + (target,))
            elif len(chain) <= len(root_docs):
                visit(target, chain + (target,))

    for node in sorted(root_docs):
        visit(node, (node,))
    return {"edges": edges, "cycles": [list(item) for item in sorted(cycles)]}


def build_consumer_snapshot(
    root: Path,
    policy: dict[str, Any],
    revision: dict[str, Any],
    *,
    changed_files: list[str],
) -> dict[str, Any]:
    """Build a stable, serializable observation bundle for one audit revision."""
    root = root.resolve()
    surface_paths = _literal_surface_paths(root, policy)
    wanted = set(_ROOT_DOCUMENTS)
    wanted.update(path for paths in surface_paths.values() for path in paths)
    documents = {
        rel: document for rel in sorted(wanted) if (document := _document(root, rel)) is not None
    }
    root_docs = set(_ROOT_DOCUMENTS).intersection(documents)
    facts = _workflow_facts(root) + _project_facts(root) + _make_facts(root)
    publication_markers = [
        marker
        for marker in policy["llm_txt"]["published_surface_markers"]
        if (root / marker).is_file()
    ]
    value: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA,
        "revision": {
            "repository": revision["repository"],
            "tested_revision_sha": revision["tested_revision_sha"],
        },
        "changed_files": sorted(set(changed_files)),
        "surface_paths": surface_paths,
        "documents": documents,
        "facts": sorted(facts, key=lambda item: item["id"]),
        "publication_markers": publication_markers,
        "authority_graph": _authority_graph(documents, root_docs),
    }
    # Change scope is audit provenance, not a consumer state input. Keeping it
    # out of the identity lets a rerun over a different base prove the same
    # rendered projection byte-identical instead of forcing a false refresh.
    identity = {key: item for key, item in value.items() if key != "changed_files"}
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    value["digest"] = _sha256(canonical.encode("utf-8"))
    return value


def snapshot_document(snapshot: dict[str, Any], path: str) -> dict[str, Any] | None:
    """Return one observed document without exposing a filesystem fallback."""
    value = (snapshot.get("documents") or {}).get(path)
    return value if isinstance(value, dict) else None
