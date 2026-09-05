#!/usr/bin/env python3
"""Required simple-plan sections — derived from owners, not a third list.

JSON keys come from ``skills/l9-plan/schemas/plan-document.schema.json``.
Markdown headings come from the canonical executable-plan template with the
Cursor Build execute swap declared by ``plan-workflow-simple.md``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
PLAN_SCHEMA_REL = "skills/l9-plan/schemas/plan-document.schema.json"
TEMPLATE_REL = (
    "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
)
GAR_SKILL_REF = "skills/l9-global-architect"
EXECUTE_BUILD = "Execute via Cursor Build"
EXECUTE_EMBEDDED = "Handoff to Caller"
MODE_BUILD = "cursor-build"
MODE_EMBEDDED = "embedded"
# The l9-plan-simple handoff axis: mode -> the heading that replaces the PE
# execute section. Both modes are kind:simple; only the handoff differs.
HANDOFF_HEADINGS = {MODE_BUILD: EXECUTE_BUILD, MODE_EMBEDDED: EXECUTE_EMBEDDED}
FRONTMATTER_KEYS = ("name", "overview", "todos", "isProject", "kind", "execute_via")
NEGATION_RE = re.compile(r"(?i)\b(do not|don't|never|not a|not the|must not|forbidden)\b")
OPTIONAL_HEADING_RE = re.compile(r"\*+\(optional", re.I)
HEADING_RE = re.compile(r"^## +(.+)$", re.M)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)

try:
    import yaml
except ImportError:  # pragma: no cover - stdlib fallback
    yaml = None  # type: ignore[assignment]


def plan_schema_path() -> Path:
    return REPO_ROOT / PLAN_SCHEMA_REL


def template_path() -> Path:
    return REPO_ROOT / TEMPLATE_REL


def json_required_keys(schema: dict[str, Any] | None = None) -> list[str]:
    data = (
        schema if schema is not None else json.loads(plan_schema_path().read_text(encoding="utf-8"))
    )
    required = data.get("required")
    if not isinstance(required, list) or not required:
        raise ValueError(f"{PLAN_SCHEMA_REL} has no required array")
    return [str(item) for item in required]


def md_required_headings(template_text: str | None = None, mode: str = MODE_BUILD) -> list[str]:
    text = (
        template_text if template_text is not None else template_path().read_text(encoding="utf-8")
    )
    handoff = HANDOFF_HEADINGS.get(mode, EXECUTE_BUILD)
    headings: list[str] = []
    seen: set[str] = set()
    for match in HEADING_RE.finditer(text):
        title = match.group(1).strip()
        if OPTIONAL_HEADING_RE.search(title) or title.startswith("Machine stub"):
            continue
        if "program-execution" in title:
            title = handoff
        if title in seen:
            continue
        seen.add(title)
        headings.append(title)
    if handoff not in seen:
        headings.append(handoff)
    if not headings:
        raise ValueError(f"{TEMPLATE_REL} produced no required headings")
    return headings


def heading_present(text: str, required: str) -> bool:
    for match in HEADING_RE.finditer(text):
        got = match.group(1).strip()
        if got == required or got.startswith(f"{required} ") or got.startswith(f"{required} ("):
            return True
    return False


def parse_frontmatter(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    raw = match.group(1)
    if yaml is not None:
        try:
            loaded = yaml.safe_load(raw)
        except yaml.YAMLError:
            loaded = None
        if isinstance(loaded, dict):
            return loaded
    data: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith(" ") or line.startswith("-"):
            continue
        key, rest = line.split(":", 1)
        data[key.strip()] = rest.strip().strip("\"'")
    return data


def handoff_mode(text: str) -> str:
    """The plan's declared handoff mode; cursor-build is the default."""
    fm = parse_frontmatter(text)
    mode = str(fm.get("execute_via") or "").strip()
    return mode if mode in HANDOFF_HEADINGS else MODE_BUILD


def frontmatter_presence(text: str) -> dict[str, bool]:
    fm = parse_frontmatter(text)
    present = {key: key in fm and fm[key] not in (None, "", []) for key in FRONTMATTER_KEYS}
    if str(fm.get("kind") or "").strip() != "simple":
        present["kind"] = False
    if str(fm.get("execute_via") or "").strip() not in HANDOFF_HEADINGS:
        present["execute_via"] = False
    return present


def live_pe_heading(text: str) -> bool:
    for match in HEADING_RE.finditer(text):
        if "program-execution" in match.group(1):
            return True
    return False


def live_make_campaign(text: str) -> bool:
    for line in text.splitlines():
        if "make campaign" not in line:
            continue
        if NEGATION_RE.search(line):
            continue
        return True
    return False


def json_section_presence(plan: dict[str, Any]) -> dict[str, bool]:
    return {key: key in plan for key in json_required_keys()}


def md_section_presence(text: str) -> dict[str, bool]:
    headings = md_required_headings(mode=handoff_mode(text))
    return {title: heading_present(text, title) for title in headings}


def execute_swap_presence(text: str) -> dict[str, bool]:
    mode = handoff_mode(text)
    return {
        "handoff_heading": heading_present(text, HANDOFF_HEADINGS[mode]),
        "live_pe_heading": live_pe_heading(text),
        "live_make_campaign": live_make_campaign(text),
    }


def receipt_status(
    json_sections: dict[str, bool],
    md_sections: dict[str, bool],
    frontmatter: dict[str, bool],
    execute_swap: dict[str, bool],
    gar_invoked: bool,
) -> str:
    if not gar_invoked:
        return "fail"
    if not all(json_sections.values()):
        return "fail"
    if not all(md_sections.values()):
        return "fail"
    if not all(frontmatter.values()):
        return "fail"
    if not execute_swap.get("handoff_heading"):
        return "fail"
    if execute_swap.get("live_pe_heading") or execute_swap.get("live_make_campaign"):
        return "fail"
    return "pass"


def missing_labels(
    json_sections: dict[str, bool],
    md_sections: dict[str, bool],
    frontmatter: dict[str, bool],
    execute_swap: dict[str, bool],
    gar_invoked: bool,
) -> list[str]:
    errors: list[str] = []
    if not gar_invoked:
        errors.append("G_GAR_UPSTREAM: l9-global-architect was not recorded as invoked")
    for key, ok in json_sections.items():
        if not ok:
            errors.append(f"G_JSON_SECTION: missing PLAN_DOCUMENT key {key}")
    for title, ok in md_sections.items():
        if not ok:
            errors.append(f"G_MD_SECTION: missing heading {title!r}")
    for key, ok in frontmatter.items():
        if not ok:
            errors.append(f"G_FRONTMATTER: missing or invalid {key}")
    if not execute_swap.get("handoff_heading"):
        expected = " or ".join(sorted(HANDOFF_HEADINGS.values()))
        errors.append(f"G_EXECUTE_SWAP: missing handoff heading ({expected})")
    if execute_swap.get("live_pe_heading"):
        errors.append("G_EXECUTE_SWAP: live PE execute heading present")
    if execute_swap.get("live_make_campaign"):
        errors.append("G_EXECUTE_SWAP: live make campaign command present")
    return errors
