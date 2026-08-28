#!/usr/bin/env python3
"""Validate a standalone skill pack for structure, metadata, references, and executable scripts."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required: {exc}")

#: L9 frontmatter contract (docs/skills-standard.md in Cursor-Governance, enforced
#: by ops/scripts/check_skills_standard.py). This is the DEFAULT and the one a
#: compiled pack must satisfy: a pack that ships `license` or `allowed-tools` at
#: top level is rejected by that gate on install, which is exactly how three packs
#: reached this repository needing hand repair.
L9_FRONTMATTER = {"name", "description", "paths", "disable-model-invocation", "metadata"}

#: Anthropic Agent Skills accept two further top-level keys. Opt in per build with
#: --frontmatter-profile agent-skills; never the default, so portability can never
#: silently produce a pack the L9 gate rejects.
AGENT_SKILLS_EXTRA = {"license", "allowed-tools"}

FRONTMATTER_PROFILES = {
    "l9": L9_FRONTMATTER,
    "agent-skills": L9_FRONTMATTER | AGENT_SKILLS_EXTRA,
}

#: docs/skills-standard.md §3. Under the floor the triggers are missing; over the
#: ceiling the body is leaking into the routing signal.
DESC_MIN, DESC_MAX = 150, 500
TRIGGER_CLAUSES = ("use when", "use for")
UNFINISHED = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:TODO|FIXME|TBD|PLACEHOLDER|LOREM IPSUM|COMING SOON)\b\s*[:\[]?"
)
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SKIP_UNFINISHED = {"CHANGELOG.md"}


def load_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md must start with one YAML frontmatter block")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, text[match.end() :]


def local_links(path: Path) -> list[str]:
    links: list[str] = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        links.append(target.split("#", 1)[0])
    return links


def validate(root: Path, profile: str = "l9") -> list[str]:
    errors: list[str] = []
    skill = root / "SKILL.md"
    if not skill.exists():
        return ["missing SKILL.md"]
    try:
        fm, body = load_frontmatter(skill)
    except Exception as exc:
        return [str(exc)]
    allowed = FRONTMATTER_PROFILES.get(profile)
    if allowed is None:
        return [f"unknown frontmatter profile: {profile!r}"]
    extra = set(fm) - allowed
    if extra:
        errors.append(
            f"unsupported top-level frontmatter keys: {sorted(extra)} "
            f"(profile {profile!r}) - nest them under `metadata:`"
        )
    name = fm.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("name must be lowercase hyphen-case")
    elif name != root.name:
        # Not "only when the platform requires it": the folder IS the identity for
        # every discovery surface this compiler targets, and a mismatch makes the
        # pack undiscoverable rather than merely untidy.
        errors.append(f"name {name!r} must match the pack directory {root.name!r}")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("description is required")
    else:
        if len(desc) < DESC_MIN:
            errors.append(
                f"description is {len(desc)} chars, under {DESC_MIN} - triggers are missing"
            )
        elif len(desc) > DESC_MAX:
            errors.append(
                f"description is {len(desc)} chars, over {DESC_MAX} - body leaking into frontmatter"
            )
        if not any(clause in desc.lower() for clause in TRIGGER_CLAUSES):
            errors.append(
                "description states no trigger - it must say "
                f"{' or '.join(repr(c) for c in TRIGGER_CLAUSES)}"
            )
    if "paths" in fm and not fm.get("paths"):
        errors.append("empty `paths` hides the skill from discovery; omit the key instead")
    archived = "_archived" in root.parts or root.name.endswith("-deprecated")
    if archived and fm.get("disable-model-invocation") is not True:
        errors.append(
            "an archived pack needs `disable-model-invocation: true` - "
            "prose saying 'do not activate' is not a mechanism"
        )
    if len(body.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")

    files = [p for p in root.rglob("*") if p.is_file()]

    for p in files:
        if p.stat().st_size == 0:
            errors.append(f"empty file: {p.relative_to(root)}")
        if (
            p.suffix.lower() in {".md", ".yaml", ".yml", ".py", ".json"}
            and p.name not in SKIP_UNFINISHED
        ):
            text = p.read_text(encoding="utf-8", errors="replace")
            if UNFINISHED.search(text):
                errors.append(f"unfinished marker in {p.relative_to(root)}")
        if p.suffix.lower() == ".md":
            for target in local_links(p):
                resolved = (p.parent / target).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"link escapes skill root: {p.relative_to(root)} -> {target}")
                    continue
                if not resolved.exists():
                    errors.append(f"broken link: {p.relative_to(root)} -> {target}")

    for py in (root / "scripts").glob("*.py") if (root / "scripts").exists() else []:
        try:
            ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {py.relative_to(root)}: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_folder")
    parser.add_argument(
        "--frontmatter-profile",
        choices=sorted(FRONTMATTER_PROFILES),
        default="l9",
        help=(
            "Top-level frontmatter keys to accept. 'l9' (default) is the contract "
            "every governed repository enforces; 'agent-skills' also permits "
            "license/allowed-tools for a pack published outside L9."
        ),
    )
    args = parser.parse_args()
    root = Path(args.skill_folder).resolve()
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}", file=sys.stderr)
        return 2
    errors = validate(root, profile=args.frontmatter_profile)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: skill pack validation passed ({sum(1 for p in root.rglob('*') if p.is_file())} files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
