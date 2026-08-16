#!/usr/bin/env python3
"""Compile a free-form campaign memo into an activate seed.

Factory IR only. Does not write CAMPAIGN_SOURCE.yaml or INTENT.yaml under
campaigns/<id>/. Assigns campaign_id from the filename slug.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
OWNER_LINE_RE = re.compile(r"^owner:\s*(.+)$", re.I | re.M)
REPO_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")
RELEASE_RE = re.compile(
    r"^\s*(\d+)\.\s+Release\s+[A-Z]\s+[—–-]\s+(.+?)\s*$",
    re.M,
)
NUMBERED_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$", re.M)
IT_IS_RE = re.compile(
    r"(?:Final architectural judgment.*?)?^\s*It is:\s*\n+(.+?)(?:\n\s*\n|\Z)",
    re.I | re.M | re.S,
)
DEFAULT_OWNER = "Igor Beylin"
DEFAULT_TARGET = "Quantum-L9/Cursor-Governance"


class BriefError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def slugify_filename(filename: str) -> str:
    stem = Path(filename).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if len(slug) < 3:
        slug = f"campaign-{slug or 'brief'}"
    return slug[:63].strip("-")


def title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = re.sub(r"[-_]+", " ", stem).strip()
    return re.sub(r"\s+", " ", cleaned) or "Campaign"


def assign_campaign_id(base: str, existing_ids: set[str]) -> str:
    if not CAMPAIGN_ID_RE.match(base):
        raise BriefError(f"assigned campaign_id {base!r} is not a valid kebab id")
    if base not in existing_ids:
        return base
    for index in range(2, 100):
        candidate = f"{base}-v{index}"
        if len(candidate) > 63:
            candidate = f"{base[: 63 - len(f'-v{index}')]}-v{index}"
        if candidate not in existing_ids and CAMPAIGN_ID_RE.match(candidate):
            return candidate
    raise BriefError(f"could not assign a free campaign_id from {base}")


def _paragraph_after(text: str, start: int) -> str:
    rest = text[start:]
    lines: list[str] = []
    begun = False
    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            if begun:
                break
            continue
        if begun and (
            RELEASE_RE.match(stripped)
            or re.match(r"^\d+\.\s+", stripped)
            or stripped.startswith("#")
        ):
            break
        begun = True
        lines.append(stripped)
    return " ".join(lines).strip()


def extract_release_tasks(text: str) -> list[dict[str, str]]:
    matches = list(RELEASE_RE.finditer(text))
    tasks: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        objective = _paragraph_after(body, 0) or title
        tasks.append({"title": title, "objective": objective})
    return tasks


def extract_program_ordering_tasks(text: str) -> list[dict[str, str]]:
    marker = re.search(r"^Program ordering\s*$", text, re.I | re.M)
    if marker is None:
        return []
    block = text[marker.end() :]
    stop = re.search(r"^#{1,3}\s+\S|^Final architectural", block, re.M)
    if stop is not None:
        block = block[: stop.start()]
    tasks: list[dict[str, str]] = []
    for match in NUMBERED_ITEM_RE.finditer(block):
        title = match.group(2).strip()
        if title:
            tasks.append({"title": title, "objective": title})
    return tasks


def extract_numbered_fallback_tasks(text: str) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for match in NUMBERED_ITEM_RE.finditer(text):
        title = match.group(2).strip()
        if title.lower().startswith("release "):
            continue
        if title:
            tasks.append({"title": title, "objective": title})
    return tasks


def extract_tasks(text: str) -> list[dict[str, str]]:
    releases = extract_release_tasks(text)
    if releases:
        return releases
    ordering = extract_program_ordering_tasks(text)
    if ordering:
        return ordering
    fallback = extract_numbered_fallback_tasks(text)
    if fallback:
        return fallback
    raise BriefError(
        "memo has no numbered Release blocks and no numbered program-ordering "
        "or task list; will not invent tasks"
    )


def extract_objective(text: str) -> str:
    match = IT_IS_RE.search(text)
    if match:
        paragraph = " ".join(match.group(1).split())
        if paragraph:
            return paragraph
    judgment = re.search(
        r"Final architectural judgment\s*(.+)$",
        text,
        re.I | re.S,
    )
    if judgment:
        paragraph = " ".join(judgment.group(1).split())
        if paragraph:
            return paragraph[:2000]
    raise BriefError("memo has no extractable objective (no 'It is:' / final judgment)")


def extract_owner(text: str) -> str:
    match = OWNER_LINE_RE.search(text)
    if match:
        return match.group(1).strip()
    return DEFAULT_OWNER


def extract_target(text: str, override: str | None = None) -> str:
    if override:
        return override.strip()
    for match in REPO_RE.finditer(text):
        value = match.group(1)
        if value.count("/") == 1 and not value.startswith("http"):
            return value
    return DEFAULT_TARGET


def load_mapping(path: Path) -> Any:
    if yaml is None:
        raise BriefError("PyYAML required")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None


def is_activate_seed(raw: Any) -> bool:
    if not isinstance(raw, dict):
        return False
    if str(raw.get("schema") or "") == "program-execution.intent.v1":
        return False
    tasks = raw.get("tasks")
    return bool(
        str(raw.get("campaign_id") or "").strip()
        and str(raw.get("title") or "").strip()
        and str(raw.get("objective") or "").strip()
        and isinstance(tasks, list)
        and tasks
    )


def brief_to_seed(
    text: str,
    *,
    filename: str,
    existing_ids: set[str] | None = None,
    target_override: str | None = None,
) -> dict[str, Any]:
    campaign_id = assign_campaign_id(slugify_filename(filename), existing_ids or set())
    tasks = extract_tasks(text)
    seed = {
        "campaign_id": campaign_id,
        "title": title_from_filename(filename),
        "owner": extract_owner(text),
        "objective": extract_objective(text),
        "problem_statement": text,
        "target": {
            "repository_id": extract_target(text, target_override),
            "source_of_truth": "repository_origin_main",
            "adapter": "git",
        },
        "tasks": tasks,
    }
    return seed


def dump_seed(path: Path, seed: dict[str, Any]) -> None:
    if yaml is None:
        raise BriefError("PyYAML required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(seed, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )


def compile_brief(
    brief_path: Path,
    *,
    output: Path | None = None,
    existing_ids: set[str] | None = None,
    target_override: str | None = None,
) -> dict[str, Any]:
    brief_path = brief_path.resolve()
    if not brief_path.is_file():
        raise BriefError(f"brief not found: {brief_path}")
    raw = load_mapping(brief_path)
    if str((raw or {}).get("schema") or "") == "program-execution.intent.v1":
        raise BriefError("program-execution.intent.v1 is not an activate seed or memo brief")
    if is_activate_seed(raw):
        seed = dict(raw)
    else:
        seed = brief_to_seed(
            brief_path.read_text(encoding="utf-8"),
            filename=brief_path.name,
            existing_ids=existing_ids,
            target_override=target_override,
        )
    target = output or (Path.home() / ".l9/primed" / f"{seed['campaign_id']}.activate.yaml")
    dump_seed(target, seed)
    return {"seed": seed, "output": str(target)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compile_brief")
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--existing-id", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = compile_brief(
            args.brief,
            output=args.output,
            existing_ids=set(args.existing_id),
            target_override=args.target,
        )
    except BriefError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code
    print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
