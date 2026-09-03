"""Small llms.txt projection mechanics for repository documentation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from doc_policy import repo_slug

HEADINGS = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINKS = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)


def llms_enabled(
    root: Path,
    policy: dict[str, Any],
    directives: dict[str, Any],
) -> tuple[bool, str]:
    value = str(directives.get("llms_txt") or "").lower()
    if value in {"enabled", "disabled"}:
        reason = "adapter" if value == "enabled" else "adapter_disabled"
        return value == "enabled", reason
    markers = policy["llms_txt"]["published_surface_markers"]
    if any((root / marker).exists() for marker in markers):
        return True, "published_docs_surface"
    return False, "no_published_docs_surface"


def llms_base_url(directives: dict[str, Any], cli: str | None) -> tuple[str | None, str]:
    value = cli or directives.get("llms_base_url")
    if not value:
        return None, "UNKNOWN"
    source = "cli" if cli else "adapter"
    return str(value).rstrip("/") + "/", source


def render_llms_txt(root: Path, policy: dict[str, Any], base_url: str) -> str:
    title = repo_slug(root)
    lines = [
        f"# {title}",
        "",
        f"> LLM-facing documentation index for {title}. Projection only; not authority.",
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
    errors.extend(
        f"llms.txt link is not absolute: {url}"
        for url in LINKS.findall(text)
        if not url.startswith(("https://", "http://"))
    )
    return errors
