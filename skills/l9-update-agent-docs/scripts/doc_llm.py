"""Small llm.txt projection mechanics for repository documentation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from doc_owned_write import Admission, apply_owned_write
from doc_policy import LLM_SURFACE_ID, repo_slug, resolve_under_root

PROJECTION_FILENAME = "llm.txt"
LEGACY_FILENAME = "llms.txt"
LLM_MARKER = "<!-- l9-llm-txt: generated-projection -->"

HEADINGS = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINKS = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)


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


def render_llm_txt(root: Path, policy: dict[str, Any], base_url: str | None) -> str:
    title = repo_slug(root)
    lines = [
        f"# {title}",
        "",
        f"> LLM-facing documentation index for {title}. Projection only; not authority.",
        "",
        LLM_MARKER,
        "",
        "## Documentation",
        "",
    ]
    for name in policy[LLM_SURFACE_ID]["surface_order"]:
        spec = policy["surfaces"][name]
        if not spec.get("llm_include"):
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
            href = urljoin(base_url, rel) if base_url else rel
            lines.append(f"- [{spec['role']}]({href}): owner `{spec['owner']}`")
    return "\n".join(lines).rstrip() + "\n"


def retire_legacy_llms_txt(root: Path) -> list[str]:
    """Keep handwritten bytes; only drop the obsolete name once llm.txt exists.

    Missing llm.txt + present llms.txt → rename (preserve content).
    Both present → delete leftover llms.txt.
    """
    mutations: list[str] = []
    canonical = resolve_under_root(root, PROJECTION_FILENAME)
    legacy = resolve_under_root(root, LEGACY_FILENAME)
    if canonical is None or legacy is None:
        return mutations
    if canonical.is_file() and legacy.is_file():
        legacy.unlink()
        mutations.append(f"retired:{LEGACY_FILENAME}")
        return mutations
    if not canonical.is_file() and legacy.is_file():
        legacy.replace(canonical)
        mutations.append(PROJECTION_FILENAME)
        mutations.append(f"retired:{LEGACY_FILENAME}")
    return mutations


def write_llm_txt(root: Path, rendered: str) -> tuple[bool, Admission]:
    target = resolve_under_root(root, PROJECTION_FILENAME)
    if target is None:
        raise ValueError(f"{PROJECTION_FILENAME} target escaped repository root")
    return apply_owned_write(target, rendered, LLM_MARKER)


def validate_llm_txt(text: str) -> list[str]:
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
    return errors


def _link_allowed(url: str) -> bool:
    if url.startswith(("https://", "http://")):
        return True
    return bool(url) and "://" not in url and not url.startswith("/")
