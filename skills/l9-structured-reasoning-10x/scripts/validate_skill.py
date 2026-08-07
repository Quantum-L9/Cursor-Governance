#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "expertise_model.yaml",
    "skill_intelligence_report.yaml",
    "references/reasoning-router.yaml",
    "references/evidence-decision-contract.yaml",
    "references/risk-and-autonomy-policy.md",
    "references/capability-adapters.md",
    "references/output-profiles.md",
    "scripts/route_reasoning.py",
    "scripts/evaluate_fixtures.py",
    "scripts/validate_ledger.py",
    "fixtures/router_cases.json",
]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter not closed")
    data = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"invalid frontmatter line: {line}")
        data[key.strip()] = value.strip()
    return data


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = []
    for item in REQUIRED:
        if not (root / item).exists():
            errors.append(f"missing required file: {item}")

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    try:
        frontmatter = parse_frontmatter(skill)
        if set(frontmatter) != {"name", "description"}:
            errors.append(f"frontmatter keys must be name and description only: {sorted(frontmatter)}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", frontmatter.get("name", "")):
            errors.append("name must be lowercase hyphenated")
        if len(frontmatter.get("description", "")) < 120:
            errors.append("description is too weak")
    except Exception as exc:
        errors.append(str(exc))

    if len(skill.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")

    required_terms = ["extract_expertise", "compress_expertise", "skill_intelligence_report", "exemplary_gate"]
    for term in required_terms:
        if term not in skill:
            errors.append(f"missing exemplary term: {term}")

    legacy_patterns = [
        r"Blocks? 0.?7.*MUST",
        r"Reasoning MUST be visible",
        r"min_execute",
        r"execute all 3 in parallel",
    ]
    scan_files = [root / "SKILL.md"] + sorted((root / "references").glob("*"))
    for path in scan_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in legacy_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                errors.append(f"legacy ritual detected in {path.relative_to(root)}: {pattern}")

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if "__MACOSX" in rel or path.name.startswith("._") or path.name == "__pycache__" or path.suffix == ".pyc":
            errors.append(f"forbidden generated artifact: {rel}")

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in [root / "SKILL.md"] + sorted((root / "references").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in link_pattern.findall(text):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"link escapes skill root: {path.name} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken link: {path.relative_to(root)} -> {target}")

    for path in [root / "expertise_model.yaml", root / "skill_intelligence_report.yaml", root / "fixtures/router_cases.json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON-compatible YAML/JSON {path.name}: {exc}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: skill structure and anti-drift validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
