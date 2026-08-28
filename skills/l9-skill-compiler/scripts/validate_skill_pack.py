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

ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata"}
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


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skill = root / "SKILL.md"
    if not skill.exists():
        return ["missing SKILL.md"]
    try:
        fm, body = load_frontmatter(skill)
    except Exception as exc:
        return [str(exc)]
    extra = set(fm) - ALLOWED_FRONTMATTER
    if extra:
        errors.append(f"unsupported frontmatter keys: {sorted(extra)}")
    name = fm.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("name must be lowercase hyphen-case")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("description is required")
    elif len(desc) > 1024:
        errors.append("description exceeds 1024 characters")
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
    args = parser.parse_args()
    root = Path(args.skill_folder).resolve()
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}", file=sys.stderr)
        return 2
    errors = validate(root)
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
