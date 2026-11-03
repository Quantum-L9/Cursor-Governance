#!/usr/bin/env python3
"""Classify how a repository publishes a release, from its GitHub Actions files.

The release model decides who creates the tag. Deciding it from evidence, not
from memory of a similar repository, is what keeps an agent from racing the
repository's own tagger or from waiting on automation that does not exist.

Models:
  TAG_TRIGGERED   a job runs on `push: tags:`; the operator-admitted tag is
                  pushed and that job publishes. The agent never writes the
                  version; the tag object is the release identity.
  MAIN_TAGGER     a job on a branch push creates the tag itself (`git tag`,
                  `gh release create`, a release action); the release is the
                  version bump that job watches. The agent never creates the tag.
  NO_AUTOMATION   no job creates or reacts to a tag; the agent creates the
                  annotated tag and the host Release itself.
  AMBIGUOUS       both a tag-push publisher and a branch-push tagger exist; stop.

Print one JSON object on stdout.

Exit 0: model decided
Exit 1: AMBIGUOUS, or the workflows could not be read (UNKNOWN)
Exit 2: bad input
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
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

# Malformed YAML is UNKNOWN, never a crash or a guessed model.
_YAML_ERRORS: tuple[type[BaseException], ...] = (yaml.YAMLError,) if yaml is not None else ()

# Writes that create a tag. Reading one (`git ls-remote --tags`,
# `startsWith(github.ref, 'refs/tags/v')`, `git tag --list`) is not creation.
_RELEASE_ACTIONS = re.compile(
    r"(?i)uses:\s*[\w.-]+/"
    r"(?:action-gh-release|create-release|release-action|release-please-action)\b"
)
_TAGGERS = (
    re.compile(
        r"\bgit\s+tag\s+"
        r"(?!-l\b|--list\b|-d\b|--delete\b|-v\b|--verify\b|--contains\b|--points-at\b|-n\b)"
    ),
    re.compile(r"\bgit\s+push\b[^\n]*(?:refs/tags/|--tags\b)"),
    re.compile(r"\bgh\s+release\s+create\b"),
    re.compile(r"\bgh\s+api\b[^\n]*git/refs\b[^\n]*refs/tags/"),
    _RELEASE_ACTIONS,
    re.compile(r"(?i)\bsemantic-release\b"),
)
_RELEASE_CREATORS = (
    re.compile(r"\bgh\s+release\s+create\b"),
    _RELEASE_ACTIONS,
    re.compile(r"(?i)\bsemantic-release\b"),
)
_VERSION_FILES = (
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "setup.cfg",
    "VERSION",
    "version.txt",
)


def _triggers(doc: dict[Any, Any]) -> Any:
    # YAML 1.1 reads a bare `on:` key as boolean True.
    if "on" in doc:
        return doc["on"]
    return doc.get(True)


def _push_block(triggers: Any) -> dict[str, Any] | None:
    if isinstance(triggers, str):
        return {} if triggers == "push" else None
    if isinstance(triggers, list):
        return {} if "push" in triggers else None
    if isinstance(triggers, dict) and "push" in triggers:
        block = triggers["push"]
        return block if isinstance(block, dict) else {}
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def inspect_workflow(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is not installed")
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError(f"{path.name}: not a workflow mapping")
    push = _push_block(_triggers(doc))
    tag_patterns = _as_list(push.get("tags")) if push is not None else []
    branches = _as_list(push.get("branches")) if push is not None else []
    paths = _as_list(push.get("paths")) if push is not None else []
    return {
        "file": path.name,
        "push_tags": tag_patterns,
        "push_branches": branches,
        "push_paths": paths,
        "creates_tag": any(p.search(text) for p in _TAGGERS),
        "creates_release": any(p.search(text) for p in _RELEASE_CREATORS),
    }


def version_authority(repo: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for name in _VERSION_FILES:
        candidate = repo / name
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        version = ""
        if name == "package.json":
            try:
                version = str(json.loads(text).get("version") or "")
            except json.JSONDecodeError:
                version = ""
        else:
            match = re.search(r'(?m)^\s*version\s*=\s*["\']?([0-9][^"\'\s]*)', text)
            match = match or re.search(r"\A\s*([0-9]+\.[0-9]+\.[0-9]+\S*)", text)
            version = match.group(1) if match else ""
        found.append({"file": name, "version": version})
    return found


def classify(workflows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    tag_publishers = [w["file"] for w in workflows if w["push_tags"]]
    branch_taggers = [
        w["file"]
        for w in workflows
        if w["push_branches"] and w["creates_tag"] and not w["push_tags"]
    ]
    evidence = [
        f"tag_push_workflows={','.join(tag_publishers) or 'none'}",
        f"branch_push_taggers={','.join(branch_taggers) or 'none'}",
    ]
    if tag_publishers and branch_taggers:
        return "AMBIGUOUS", evidence
    if tag_publishers:
        return "TAG_TRIGGERED", evidence
    if branch_taggers:
        return "MAIN_TAGGER", evidence
    return "NO_AUTOMATION", evidence


def responsibilities(model: str, workflows: list[dict[str, Any]]) -> dict[str, str]:
    """Who creates the tag and who creates the host Release, under this model."""
    if model == "TAG_TRIGGERED":
        tag_jobs = [w for w in workflows if w["push_tags"]]
        creator = "workflow" if any(w["creates_release"] for w in tag_jobs) else "agent"
        return {"tag_creator": "operator_admitted_tag", "release_creator": creator}
    if model == "MAIN_TAGGER":
        taggers = [w for w in workflows if w["push_branches"] and w["creates_tag"]]
        creator = "workflow" if any(w["creates_release"] for w in taggers) else "agent"
        return {"tag_creator": "workflow", "release_creator": creator}
    if model == "NO_AUTOMATION":
        return {"tag_creator": "agent", "release_creator": "agent"}
    return {"tag_creator": "unknown", "release_creator": "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo-dir", required=True, help="checkout of the repository to release")
    args = parser.parse_args()
    repo = Path(args.repo_dir)
    if not repo.is_dir():
        print(json.dumps({"status": "BAD_INPUT", "detail": "--repo-dir is not a directory"}))
        return 2
    workflow_dir = repo / ".github" / "workflows"
    files: list[Path] = []
    if workflow_dir.is_dir():
        files = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    try:
        workflows = [inspect_workflow(path) for path in files]
    except (OSError, ValueError, RuntimeError, *_YAML_ERRORS) as error:
        unknown = {"status": "UNKNOWN", "model": "UNKNOWN", "detail": str(error)}
        print(json.dumps(unknown, sort_keys=True))
        return 1
    model, evidence = classify(workflows)
    payload = {
        "status": "DECIDED" if model != "AMBIGUOUS" else "AMBIGUOUS",
        "model": model,
        "evidence": evidence,
        **responsibilities(model, workflows),
        "release_workflows": [
            w for w in workflows if w["push_tags"] or w["creates_tag"] or w["creates_release"]
        ],
        "version_authority": version_authority(repo),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if model != "AMBIGUOUS" else 1


if __name__ == "__main__":
    sys.exit(main())
