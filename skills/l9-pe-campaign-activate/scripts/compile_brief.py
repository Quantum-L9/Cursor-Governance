#!/usr/bin/env python3
"""Compile a free-form campaign memo or plan into an activate seed.

Factory IR only. Does not write CAMPAIGN_SOURCE.yaml or INTENT.yaml under
campaigns/<id>/. Assigns campaign_id from the filename slug.

Accepted high-level intent (all compile to the same activate seed):
- memo brief (Release blocks / Program ordering / numbered tasks)
- Cursor .plan.md (frontmatter todos from the PE+autonomy template)
- PLAN_DOCUMENT JSON (mode: plan + todos)
- activate YAML (passthrough)

Plans are an additional input shape. They do not replace memos.
"""

from __future__ import annotations

import argparse
import json
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
REPO_PATH_OWNERS = frozenset(
    {
        "environment",
        "ops",
        "docs",
        "skills",
        "tests",
        "engine",
        "chassis",
        "agents",
        "tools",
        "scripts",
        "commands",
        "core",
        "autonomy",
    }
)
TARGET_REPO_RE = re.compile(
    r"target_repo\s*[|:]\s*`?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)`?",
    re.I,
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
PLAN_ID_RE = re.compile(r"(?:^|\b)plan_id:\s*[`*]*(plan\.[A-Za-z0-9._-]+)", re.M)
OBJECTIVE_HEADING_RE = re.compile(
    r"^##\s+Objective\b[^\n]*\n+(.*?)(?:\n##\s+|\Z)",
    re.I | re.M | re.S,
)
PLAN_DOCUMENT_CITE_RE = re.compile(
    r"PLAN_DOCUMENT\s+`([^`]+?\.json)`",
    re.I,
)


class BriefError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def slugify_token(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    if len(slug) < 3:
        slug = f"campaign-{slug or 'brief'}"
    return slug[:63].strip("-")


def slugify_filename(filename: str) -> str:
    stem = Path(filename).stem
    if stem.endswith(".plan"):
        stem = stem[: -len(".plan")]
    return slugify_token(stem)


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


FILE_PATH_RE = re.compile(
    r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+"
    r"|[A-Za-z0-9_.-]+\.(?:py|ini|ya?ml|md|sh|toml|json))`"
)
FILES_HEADING_RE = re.compile(r"^Files:\s*$", re.M)
RELEASE_BODY_STOP_RE = re.compile(r"^##\s+(Validation|Execute|Do not build)\b", re.M | re.I)
SKIP_PATH_LINE_RE = re.compile(r"read-only|\borphan\b|do not import", re.I)


def extract_release_paths(body: str) -> list[str]:
    """Bind file paths from a Release `Files:` list. Skip read-only or orphan entries."""
    heading = FILES_HEADING_RE.search(body)
    block = body[heading.end() :] if heading is not None else body
    if heading is not None:
        lines: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                if lines:
                    break
                continue
            if stripped.startswith("- ") or stripped.startswith("* "):
                lines.append(stripped)
                continue
            if lines:
                break
        block = "\n".join(lines)
    found: list[str] = []
    for match in FILE_PATH_RE.finditer(block):
        path = match.group(1)
        line_start = block.rfind("\n", 0, match.start()) + 1
        line_end = block.find("\n", match.end())
        line = block[line_start : len(block) if line_end < 0 else line_end]
        if SKIP_PATH_LINE_RE.search(line):
            continue
        if path not in found:
            found.append(path)
    return found


def extract_release_tasks(text: str) -> list[dict[str, Any]]:
    matches = list(RELEASE_RE.finditer(text))
    tasks: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        stopper = RELEASE_BODY_STOP_RE.search(body)
        if stopper is not None:
            body = body[: stopper.start()]
        objective = _paragraph_after(body, 0) or title
        task: dict[str, Any] = {"title": title, "objective": objective}
        paths = extract_release_paths(body)
        if paths:
            task["paths"] = paths
        tasks.append(task)
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


def extract_tasks(text: str) -> list[dict[str, Any]]:
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


def normalize_text(raw: str) -> str:
    """LF line endings, no BOM, trailing newline.

    The same three rules as `compiler.architecture_intent.normalize_source`,
    applied before frontmatter is matched: `FRONTMATTER_RE` anchors at the
    first byte, so a byte-order mark or CRLF endings used to hide a declared
    header and reroute the document as a plain memo.
    """
    text = raw.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    match = FRONTMATTER_RE.match(normalize_text(text))
    if match is None or yaml is None:
        return None
    try:
        raw = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return raw if isinstance(raw, dict) else None


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


def is_plan_intent(raw: Any) -> bool:
    """Cursor .plan.md frontmatter or PLAN_DOCUMENT JSON. Not a memo or activate seed."""
    if not isinstance(raw, dict):
        return False
    if is_activate_seed(raw):
        return False
    schema = str(raw.get("schema") or "").strip()
    if schema in {"l9.program-execution.campaign-source.v2", "program-execution.intent.v1"}:
        return False
    todos = raw.get("todos")
    if not isinstance(todos, list) or not todos:
        return False
    if str(raw.get("mode") or "").strip() == "plan" and (
        str(raw.get("title") or "").strip() or str(raw.get("objective") or "").strip()
    ):
        return True
    if str(raw.get("name") or "").strip() and str(raw.get("overview") or "").strip():
        return True
    if str(raw.get("title") or "").strip() and str(raw.get("objective") or "").strip():
        return True
    return False


def extract_plan_todos(raw: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for item in raw.get("todos") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("content") or item.get("task") or item.get("title") or "").strip()
        if not title:
            continue
        task: dict[str, Any] = {"title": title, "objective": title}
        task_id = str(item.get("id") or "").strip()
        if task_id:
            task["id"] = task_id
        files = item.get("files") or item.get("paths")
        if isinstance(files, list) and files:
            task["paths"] = [str(path) for path in files if path]
        deps = item.get("depends_on") or item.get("dependencies")
        if isinstance(deps, list) and deps:
            task["depends_on"] = [str(dep) for dep in deps if dep]
        tasks.append(task)
    if not tasks:
        raise BriefError("plan has no extractable todos; will not invent tasks")
    return tasks


def load_companion_plan_document(plan_path: Path, text: str) -> dict[str, Any] | None:
    """Load a cited PLAN_DOCUMENT JSON so todo files survive into the seed.

    Candidates live in the plan's own directory only: a citation is resolved
    by basename beside the plan, never followed to an arbitrary absolute path,
    so a plan cannot make the compiler read JSON from anywhere on disk. A
    cited companion that exists but does not parse is an error, not an absent
    companion — silently dropping it dropped every todo's `files` with it.
    """
    candidates: list[tuple[Path, bool]] = []
    cited = PLAN_DOCUMENT_CITE_RE.search(text)
    if cited:
        raw_name = Path(cited.group(1).strip())
        candidates.append((plan_path.parent / raw_name.name, True))
    candidates.append((plan_path.with_suffix(".json"), False))
    seen: set[Path] = set()
    for candidate, was_cited in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen or not candidate.is_file():
            continue
        seen.add(resolved)
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            if was_cited:
                raise BriefError(
                    f"cited PLAN_DOCUMENT {candidate.name} does not parse: {exc}"
                ) from exc
            continue
        if isinstance(payload, dict) and isinstance(payload.get("todos"), list):
            return payload
    return None


def merge_companion_todo_files(
    tasks: list[dict[str, Any]], companion: dict[str, Any]
) -> list[dict[str, Any]]:
    """Copy `files` from the PLAN_DOCUMENT onto compiled todos matched by id."""
    by_id: dict[str, dict[str, Any]] = {}
    for item in companion.get("todos") or []:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("id") or "").strip()
        if task_id:
            by_id[task_id] = item
    merged: list[dict[str, Any]] = []
    for task in tasks:
        updated = dict(task)
        extra = by_id.get(str(updated.get("id") or ""))
        if extra is not None and not updated.get("paths"):
            files = extra.get("files") or extra.get("paths")
            if isinstance(files, list) and files:
                updated["paths"] = [str(path) for path in files if path]
        merged.append(updated)
    return merged


def extract_plan_objective(raw: dict[str, Any], text: str) -> str:
    for key in ("objective", "overview"):
        paragraph = " ".join(str(raw.get(key) or "").split())
        if paragraph:
            return paragraph
    match = OBJECTIVE_HEADING_RE.search(text)
    if match:
        paragraph = " ".join(match.group(1).split())
        if paragraph:
            return paragraph
    raise BriefError("plan has no extractable objective (overview / objective / ## Objective)")


def extract_plan_title(raw: dict[str, Any], filename: str, text: str = "") -> str:
    for key in ("name", "title"):
        title = str(raw.get(key) or "").strip()
        if title:
            return title
    heading = re.search(r"^#\s+PLAN:\s+(.+)$", text, re.M)
    if heading:
        return heading.group(1).strip()
    return title_from_filename(filename)


def extract_plan_campaign_id(
    raw: dict[str, Any],
    text: str,
    filename: str,
    existing_ids: set[str],
) -> str:
    plan_id = str(raw.get("plan_id") or "").strip()
    if not plan_id:
        match = PLAN_ID_RE.search(text)
        if match:
            plan_id = match.group(1)
    base = slugify_token(plan_id) if plan_id else slugify_filename(filename)
    return assign_campaign_id(base, existing_ids)


def extract_objective(text: str) -> str:
    judgment = re.search(r"Final architectural judgment\s*(.+)$", text, re.I | re.S)
    if judgment:
        match = IT_IS_RE.search(judgment.group(1))
        if match:
            paragraph = " ".join(match.group(1).split())
            if paragraph:
                return paragraph
    matches = list(IT_IS_RE.finditer(text))
    if matches:
        paragraph = " ".join(matches[-1].group(1).split())
        if paragraph:
            return paragraph
    raise BriefError("memo has no extractable objective (no 'It is:' / final judgment)")


def extract_owner(text: str) -> str:
    match = OWNER_LINE_RE.search(text)
    if match:
        return match.group(1).strip()
    return DEFAULT_OWNER


def _is_github_repo(value: str) -> bool:
    if value.count("/") != 1 or value.startswith("http"):
        return False
    owner, repo = value.split("/", 1)
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$", owner):
        return False
    if not re.match(r"^[A-Za-z0-9._-]+$", repo):
        return False
    if owner.lower() in REPO_PATH_OWNERS:
        return False
    return "-" in owner or "-" in repo


def extract_target(text: str, override: str | None = None) -> str:
    if override:
        return override.strip()
    named = TARGET_REPO_RE.search(text)
    if named and _is_github_repo(named.group(1)):
        return named.group(1)
    hosted = re.search(
        r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
        text,
        re.I,
    )
    if hosted and _is_github_repo(hosted.group(1)):
        return hosted.group(1)
    for match in REPO_RE.finditer(text):
        value = match.group(1)
        if _is_github_repo(value):
            return value
    return DEFAULT_TARGET


def plan_to_seed(
    raw: dict[str, Any],
    text: str,
    *,
    filename: str,
    source_path: Path | None = None,
    existing_ids: set[str] | None = None,
    target_override: str | None = None,
) -> dict[str, Any]:
    ids = existing_ids or set()
    seed = {
        "campaign_id": extract_plan_campaign_id(raw, text, filename, ids),
        "title": extract_plan_title(raw, filename, text),
        "owner": extract_owner(text),
        "objective": extract_plan_objective(raw, text),
        "problem_statement": text,
        "target": {
            "repository_id": extract_target(text, target_override),
            "source_of_truth": "repository_origin_main",
            "adapter": "git",
        },
        "tasks": extract_plan_todos(raw),
    }
    companion = load_companion_plan_document(source_path or Path(filename), text)
    if companion is not None:
        seed["tasks"] = merge_companion_todo_files(seed["tasks"], companion)
    return seed


def load_mapping(path: Path) -> Any:
    if yaml is None:
        raise BriefError("PyYAML required")
    try:
        return yaml.safe_load(normalize_text(path.read_text(encoding="utf-8")))
    except yaml.YAMLError:
        return None


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
    primed_dir: Path | None = None,
    existing_ids: set[str] | None = None,
    target_override: str | None = None,
) -> dict[str, Any]:
    brief_path = brief_path.resolve()
    if not brief_path.is_file():
        raise BriefError(f"brief not found: {brief_path}")
    text = normalize_text(brief_path.read_text(encoding="utf-8"))
    raw = load_mapping(brief_path)
    if not isinstance(raw, dict):
        raw = parse_frontmatter(text)
    if str((raw or {}).get("schema") or "") == "program-execution.intent.v1":
        raise BriefError("program-execution.intent.v1 is not an activate seed or memo brief")
    if is_activate_seed(raw):
        seed = dict(raw)
    elif is_plan_intent(raw):
        seed = plan_to_seed(
            raw or {},
            text,
            filename=brief_path.name,
            source_path=brief_path,
            existing_ids=existing_ids,
            target_override=target_override,
        )
    else:
        seed = brief_to_seed(
            text,
            filename=brief_path.name,
            existing_ids=existing_ids,
            target_override=target_override,
        )
    target = output or (
        (primed_dir or (Path.home() / ".l9/primed")) / f"{seed['campaign_id']}.activate.yaml"
    )
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
