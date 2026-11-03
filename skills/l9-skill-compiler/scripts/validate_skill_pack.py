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

#: A backticked path in SKILL.md is a resource reference when it starts with one
#: of the pack's resource directories or names a pack root file. The directories
#: are these conventional names plus every top-level directory the pack actually
#: has (`contracts/`, `runtime/`, ...; see `resource_dirs`). Paths into the host
#: repository (`ops/...`, `AGENTS.md`, `../...`) are not pack resources.
PACK_DIRS = {
    "adapters",
    "agents",
    "assets",
    "fixtures",
    "policies",
    "references",
    "schemas",
    "scripts",
    "templates",
    "tests",
}
PACK_ROOT_FILES = {
    "SKILL.md",
    "README.md",
    "RUNBOOK.md",
    "MANIFEST.md",
    "CHANGELOG.md",
    "VALIDATION.md",
    "expertise_model.yaml",
    "skill_intelligence_report.yaml",
}
BACKTICK = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*(```|~~~)")
#: A clause that tells the reader *not* to ship or use a path names an absent
#: file on purpose ("Do not include `agents/openai.yaml` unless ..."). Only the
#: clause before the path counts: a later "Never ..." sentence on the same line
#: does not exempt the paths the line requires.
NEGATED = re.compile(r"(?i)\b(do not|don't|never|must not)\b")
CLAUSE_BREAK = re.compile(r"[.;!?](?:\s|$)|\s[—–]\s")
NOT_A_PATH = re.compile(r"[*?\[\]<>{}$]|://")


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


def resource_dirs(root: Path) -> set[str]:
    """Conventional resource directories plus every top-level directory in the pack."""
    present = {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))}
    return PACK_DIRS | present


def _negated_before(line: str, start: int) -> bool:
    """Whether the clause leading up to position `start` is a prohibition."""
    prefix = line[:start]
    breaks = list(CLAUSE_BREAK.finditer(prefix))
    clause = prefix[breaks[-1].end() :] if breaks else prefix
    return bool(NEGATED.search(clause))


def referenced_pack_paths(
    body: str, dirs: set[str] | frozenset[str] = frozenset(PACK_DIRS)
) -> list[str]:
    """Backticked pack resource paths in a SKILL.md body, outside code fences."""
    found: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in BACKTICK.finditer(line):
            if _negated_before(line, match.start()):
                continue
            raw = match.group(1)
            token = raw.strip().split()[0] if raw.strip() else ""
            token = token.split("::", 1)[0]  # `file.py::symbol` names the file
            token = token.rstrip(".,;:")
            if not token or NOT_A_PATH.search(token) or token.startswith(("/", "~", ".")):
                continue
            if token.endswith("/"):
                continue  # a directory named as a convention, not a file the pack ships
            head = token.split("/", 1)[0]
            if ("/" in token and head in dirs) or token in PACK_ROOT_FILES:
                if token not in found:
                    found.append(token)
    return found


def host_repository(root: Path) -> Path | None:
    """The repository holding the pack: the parent of its nearest `skills/` ancestor."""
    for parent in root.resolve().parents:
        if parent.name == "skills":
            return parent.parent
    return None


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
    host = host_repository(root)
    for ref in referenced_pack_paths(body, resource_dirs(root)):
        if (root / ref).exists():
            continue
        if host is not None and (host / ref).exists():
            continue  # a path into the repository that hosts the pack, not a pack file
        errors.append(f"SKILL.md references a pack file that does not exist: {ref}")

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
