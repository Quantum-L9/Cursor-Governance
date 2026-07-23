#!/usr/bin/env python3
"""
IgorBot SKILL_META checker + autofixer
═══════════════════════════════════════════════════════════════
Ensures skill markdown files carry a canonical SKILL_META HTML
comment block (see gmail_command_center/references/draft-reply-rules.md).

This is NOT meta.json.
  - meta.json  → machine registry (name, version, description, deps)
  - SKILL_META → human/agent governance header inside .md files

Target files (under workspace/skills/):
  - **/SKILL.md
  - **/references/*.md
  - cron_contracts/*.md  (job contracts; not nested clawhub cruft)

Excluded:
  - README.md, LEARNINGS.md, assets/, .learnings/, .clawhub/, package.json peers

Modes:
  python3 ci/check_skill_meta.py              # report only (exit 1 if gaps)
  python3 ci/check_skill_meta.py --fix       # autofix missing/invalid in place
  python3 ci/check_skill_meta.py --fix path  # limit to given paths (pre-commit)

Pre-commit: runs with --fix on staged skill markdown; exits 1 when it
rewrote files so the commit aborts and the user can re-stage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "workspace" / "skills"

REQUIRED_FIELDS = (
    "skill_schema",
    "origin",
    "layer",
    "role",
    "tags",
    "owner",
    "status",
    "version",
    "updated",
)

SKILL_META_RE = re.compile(
    r"<!--\s*\n--- SKILL_META ---\n(?P<body>.*?)\n--- /SKILL_META ---\n"
    r"(?P<purpose>.*?)\n?-->",
    re.DOTALL,
)

# Legacy credit_app_completer header — normalize to SKILL_META.
L9_META_RE = re.compile(
    r"<!--\s*L9_META\n(?P<body>.*?)\n/L9_META\s*-->",
    re.DOTALL,
)

YAML_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

EXCLUDE_NAME_RE = re.compile(r"(^|/)(README\.md|LEARNINGS\.md|package\.json)$")
EXCLUDE_DIR_PARTS = {".learnings", ".clawhub", "assets", "dist", "node_modules"}


def today_iso() -> str:
    return date.today().isoformat()


def skill_root_for(path: Path) -> Path | None:
    """Return workspace/skills/<skill_name> for a path under it."""
    try:
        rel = path.resolve().relative_to(SKILLS_DIR.resolve())
    except ValueError:
        return None
    if not rel.parts:
        return None
    return SKILLS_DIR / rel.parts[0]


def load_meta_json(skill_dir: Path) -> dict:
    meta_path = skill_dir / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def should_have_skill_meta(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    try:
        rel = path.resolve().relative_to(SKILLS_DIR.resolve())
    except ValueError:
        return False

    parts = set(rel.parts)
    if parts & EXCLUDE_DIR_PARTS:
        return False
    if EXCLUDE_NAME_RE.search(str(rel)):
        return False

    name = path.name
    parent = path.parent.name

    if name == "SKILL.md":
        return True
    if parent == "references":
        return True
    # cron_contracts job files live directly under cron_contracts/
    if rel.parts[0] == "cron_contracts" and name != "SKILL.md" and len(rel.parts) == 2:
        return True
    return False


def iter_target_files(paths: list[Path] | None) -> list[Path]:
    if paths:
        out: list[Path] = []
        for raw in paths:
            p = raw if raw.is_absolute() else REPO_ROOT / raw
            if p.is_file() and should_have_skill_meta(p):
                out.append(p.resolve())
            elif p.is_dir():
                for child in sorted(p.rglob("*.md")):
                    if should_have_skill_meta(child):
                        out.append(child.resolve())
        return sorted(set(out))

    return sorted(p for p in SKILLS_DIR.rglob("*.md") if should_have_skill_meta(p))


def parse_kv_block(body: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        data[key.strip()] = val.strip()
    return data


def extract_purpose_from_markdown(text: str) -> str:
    """Best-effort one-line purpose from the first heading/paragraph."""
    # Strip existing meta / frontmatter for purpose inference
    stripped = YAML_FRONTMATTER_RE.sub("", text, count=1)
    stripped = SKILL_META_RE.sub("", stripped, count=1)
    stripped = L9_META_RE.sub("", stripped, count=1)
    stripped = stripped.lstrip()

    for line in stripped.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()[:200]
        if s.startswith("<!--") or s.startswith("---"):
            continue
        return s[:200]
    return "Skill documentation."


def derive_layer_role(path: Path, skill_dir: Path) -> tuple[str, str]:
    rel = path.relative_to(skill_dir)
    stem = path.stem

    if path.name == "SKILL.md":
        return "control_plane", "skill_entrypoint"

    if rel.parts and rel.parts[0] == "references":
        role = stem.replace("-", "_")
        return "reference", role

    if skill_dir.name == "cron_contracts":
        return "cron_contract", stem.replace("-", "_")

    return "documentation", stem.replace("-", "_")


def derive_tags(skill_name: str, path: Path, meta: dict) -> str:
    tags: list[str] = []
    if skill_name:
        tags.append(skill_name)
    stem = path.stem.replace("-", "_")
    if stem and stem not in tags and stem != "SKILL":
        tags.append(stem)
    for dep in meta.get("deps") or []:
        if isinstance(dep, str) and dep not in tags:
            tags.append(dep)
        if len(tags) >= 6:
            break
    if not tags:
        tags = ["igorbot"]
    return "[" + ", ".join(tags[:8]) + "]"


def build_defaults(path: Path) -> dict[str, str]:
    skill_dir = skill_root_for(path) or path.parent
    meta = load_meta_json(skill_dir)
    skill_name = skill_dir.name
    layer, role = derive_layer_role(path, skill_dir)

    version = str(meta.get("version") or "1.0.0")
    status = str(meta.get("status") or "active")
    owner = str(meta.get("owner") or "igor_beylin")

    return {
        "skill_schema": "1",
        "origin": f"igorbot/{skill_name}",
        "layer": layer,
        "role": role,
        "tags": derive_tags(skill_name, path, meta),
        "owner": owner,
        "status": status,
        "version": version,
        "updated": today_iso(),
    }


def render_skill_meta(fields: dict[str, str], purpose: str) -> str:
    lines = ["<!--", "--- SKILL_META ---"]
    for key in REQUIRED_FIELDS:
        lines.append(f"{key}: {fields[key]}")
    # Preserve optional extras (depends_on, obsoletes_on, parent, …)
    for key, val in fields.items():
        if key not in REQUIRED_FIELDS:
            lines.append(f"{key}: {val}")
    lines.append("--- /SKILL_META ---")
    lines.append("")
    purpose = purpose.strip()
    if not purpose.lower().startswith("purpose:"):
        purpose = f"Purpose:\n{purpose}"
    lines.append(purpose)
    lines.append("-->")
    return "\n".join(lines) + "\n\n"


def missing_required(fields: dict[str, str]) -> list[str]:
    return [k for k in REQUIRED_FIELDS if not fields.get(k)]


def analyze(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = SKILL_META_RE.search(text)
    l9 = L9_META_RE.search(text)

    if m:
        fields = parse_kv_block(m.group("body"))
        purpose = m.group("purpose").strip()
        miss = missing_required(fields)
        if miss or not purpose:
            return {
                "status": "incomplete",
                "fields": fields,
                "purpose": purpose,
                "missing": miss + ([] if purpose else ["Purpose"]),
                "text": text,
                "match": m,
                "l9": None,
            }
        return {
            "status": "ok",
            "fields": fields,
            "purpose": purpose,
            "missing": [],
            "text": text,
            "match": m,
            "l9": None,
        }

    if l9:
        fields = parse_kv_block(l9.group("body"))
        # Map legacy parent → keep as optional; ensure origin exists
        if "parent" in fields and "origin" not in fields:
            fields["origin"] = f"igorbot/{fields['parent']}"
        return {
            "status": "legacy_l9",
            "fields": fields,
            "purpose": extract_purpose_from_markdown(text),
            "missing": missing_required(fields),
            "text": text,
            "match": None,
            "l9": l9,
        }

    return {
        "status": "missing",
        "fields": {},
        "purpose": extract_purpose_from_markdown(text),
        "missing": list(REQUIRED_FIELDS) + ["Purpose"],
        "text": text,
        "match": None,
        "l9": None,
    }


def merge_fields(existing: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    out = dict(defaults)
    for k, v in existing.items():
        if v:
            out[k] = v
    # Always keep schema at 1 if blank/missing
    out["skill_schema"] = out.get("skill_schema") or "1"
    if not out.get("updated"):
        out["updated"] = today_iso()
    return out


def insert_or_replace(text: str, block: str, analysis: dict) -> str:
    if analysis["match"] is not None:
        m = analysis["match"]
        return text[: m.start()] + block.rstrip() + "\n\n" + text[m.end() :].lstrip("\n")

    if analysis["l9"] is not None:
        m = analysis["l9"]
        return text[: m.start()] + block.rstrip() + "\n\n" + text[m.end() :].lstrip("\n")

    fm = YAML_FRONTMATTER_RE.match(text)
    if fm:
        return text[: fm.end()] + block + text[fm.end() :].lstrip("\n")
    return block + text.lstrip("\n")


def autofix(path: Path, analysis: dict) -> str:
    defaults = build_defaults(path)
    fields = merge_fields(analysis["fields"], defaults)
    purpose = analysis["purpose"] or extract_purpose_from_markdown(analysis["text"])
    if purpose.lower().startswith("purpose:"):
        purpose_body = purpose
    else:
        purpose_body = f"Purpose:\n{purpose}"
    block = render_skill_meta(fields, purpose_body)
    return insert_or_replace(analysis["text"], block, analysis)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite files missing/invalid SKILL_META in place",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional file/dir paths (defaults to all skill targets)",
    )
    args = parser.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"ERROR: skills dir not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    targets = iter_target_files(args.paths or None)
    ok = incomplete = missing = legacy = 0
    fixed: list[str] = []
    problems: list[str] = []

    for path in targets:
        analysis = analyze(path)
        status = analysis["status"]

        if status == "ok":
            ok += 1
            continue

        if status == "incomplete":
            incomplete += 1
            problems.append(f"INCOMPLETE  {rel(path)}  missing={analysis['missing']}")
        elif status == "legacy_l9":
            legacy += 1
            problems.append(f"LEGACY_L9   {rel(path)}  (normalize to SKILL_META)")
        else:
            missing += 1
            problems.append(f"MISSING     {rel(path)}")

        if args.fix:
            new_text = autofix(path, analysis)
            if new_text != analysis["text"]:
                path.write_text(new_text, encoding="utf-8")
                fixed.append(rel(path))

    print("SKILL_META audit")
    print(f"  targets:     {len(targets)}")
    print(f"  ok:          {ok}")
    print(f"  missing:     {missing}")
    print(f"  incomplete:  {incomplete}")
    print(f"  legacy_l9:   {legacy}")
    if fixed:
        print(f"  fixed:       {len(fixed)}")
        for p in fixed:
            print(f"    + {p}")
    elif problems and not args.fix:
        print("  problems:")
        for line in problems[:40]:
            print(f"    {line}")
        if len(problems) > 40:
            print(f"    … and {len(problems) - 40} more")

    # Exit codes:
    #  0 — all ok (or fixed and nothing left)
    #  1 — gaps remain (check mode) OR files were rewritten (fix mode → re-stage)
    if args.fix:
        if fixed:
            print(
                "\nRewrote files with SKILL_META. Re-stage them and commit again.",
                file=sys.stderr,
            )
            return 1
        return 0

    if missing or incomplete or legacy:
        print(
            "\nRun: python3 ci/check_skill_meta.py --fix",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
