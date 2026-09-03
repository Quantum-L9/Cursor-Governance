#!/usr/bin/env python3
"""Evidence helpers for l9-pr-digest. Pure/read-only except subprocess collection."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

CI_FAIL = {"failure", "failed", "cancelled", "timed_out", "action_required"}
CI_ACCEPT = {"success", "skipped", "neutral"}
DEPS = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock", "uv.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.toml",
    "Cargo.lock", "go.mod", "go.sum",
}
LOCKS = {
    "poetry.lock", "uv.lock", "package-lock.json", "pnpm-lock.yaml",
    "yarn.lock", "Cargo.lock", "go.sum",
}
MANIFESTS = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    "package.json", "Cargo.toml", "go.mod",
}
BINARY = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip",
    ".tar", ".gz", ".whl", ".bin", ".exe", ".dmg",
}
GOV_PREFIX = (".github/workflows/", "rules/", "ops/config/", "skills/AUTONOMY_MANIFEST.yaml")
GENERATED = ("generated/", "dist/", "build/", "manifest.json", "skill-registry.json")
PATTERNS = {
    "new_registry": re.compile(r"\b(class|def)\s+\w*Registry\b|\bregistry\s*=", re.I),
    "new_factory": re.compile(r"\b(class|def)\s+\w*Factory\b|\bfactory\s*=", re.I),
    "new_adapter": re.compile(r"\b(class|def)\s+\w*Adapter\b", re.I),
    "new_service": re.compile(r"\b(class|def)\s+\w*Service\b", re.I),
    "compatibility_layer_added": re.compile(
        r"\bcompat(?:ibility)?\b|\blegacy\b|\bbackward[- ]compat", re.I
    ),
    "feature_flag_added": re.compile(r"\bfeature[_ -]?flag\b|\bENABLE_[A-Z0-9_]+\b"),
    "suppression_or_ignore_added": re.compile(
        r"#\s*noqa\b|type:\s*ignore|eslint-disable|NOSONAR|continue-on-error", re.I
    ),
    "timeout_or_retry_increase": re.compile(
        r"\b(timeout|max_retries|retries|retry_count)\b", re.I
    ),
    "debug_artifact": re.compile(
        r"\bprint\s*\(|console\.log\s*\(|breakpoint\s*\(|pdb\.set_trace", re.I
    ),
    "placeholder_added": re.compile(r"\b(?:FIXME|TBD|PLACEHOLDER)\b", re.I),
}


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        message = f"command failed ({proc.returncode}): {' '.join(cmd)}"
        raise RuntimeError(f"{message}\n{proc.stderr.strip()}")
    return proc.stdout


def live_evidence(repo: str, pr_number: int, workspace: Path | None) -> dict[str, Any]:
    fields = (
        "number,title,body,baseRefName,baseRefOid,headRefName,headRefOid,"
        "commits,files,statusCheckRollup"
    )
    command = ["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", fields]
    doc = json.loads(run(command, workspace))
    return {
        "repository": repo,
        "pr_number": doc.get("number"),
        "title": doc.get("title") or "",
        "body": doc.get("body") or "",
        "base_ref": doc.get("baseRefName"),
        "base_sha": doc.get("baseRefOid"),
        "head_ref": doc.get("headRefName"),
        "head_sha": doc.get("headRefOid"),
        "commits": [c.get("oid") for c in doc.get("commits", []) if c.get("oid")],
        "files": [
            {
                "path": f.get("path"),
                "status": f.get("status") or "modified",
                "additions": int(f.get("additions") or 0),
                "deletions": int(f.get("deletions") or 0),
                "patch": None,
            }
            for f in doc.get("files", [])
        ],
        "ci_checks": [
            {
                "name": c.get("name") or c.get("context") or "UNKNOWN",
                "conclusion": c.get("conclusion") or c.get("state") or "UNKNOWN",
            }
            for c in doc.get("statusCheckRollup") or []
        ],
    }


def git_patches(
    workspace: Path | None,
    base: str | None,
    head: str | None,
) -> tuple[str | None, dict[str, str]]:
    if not workspace or not base or not head:
        return None, {}
    try:
        merge_base = run(["git", "merge-base", base, head], workspace).strip() or None
        text = run(
            ["git", "diff", "--no-ext-diff", "--unified=1", base, head],
            workspace,
        )
    except RuntimeError:
        return None, {}
    patches: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            patches.setdefault(current, [])
        if current:
            patches[current].append(line)
    return merge_base, {path: "\n".join(lines) for path, lines in patches.items()}


def section_line(text: str, names: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        match = re.match(r"^#+\s*(.+?)\s*$", raw.strip())
        if not match or match.group(1).strip().lower() not in names:
            continue
        for line in lines[idx + 1 :]:
            value = line.strip()
            if value.startswith("#"):
                break
            if value and not value.startswith("<!--"):
                return value.lstrip("-* ")[:1000]
    return None


def non_goals(text: str) -> list[str]:
    out: list[str] = []
    active = False
    for raw in text.splitlines():
        value = raw.strip()
        if re.match(r"^#+\s*(non[- ]?goals?|out of scope)\b", value, re.I):
            active = True
            continue
        if active and value.startswith("#"):
            break
        if active and value.startswith(("-", "*")):
            out.append(value[1:].strip())
    return out[:30]


def intent_of(evidence: dict[str, Any]) -> tuple[dict[str, Any], str]:
    explicit = evidence.get("intent")
    if isinstance(explicit, dict) and explicit.get("requested_outcome"):
        return explicit, "explicit_task_contract"
    body = str(evidence.get("body") or "").strip()
    title = str(evidence.get("title") or "").strip()
    if body:
        outcome = section_line(body, ("problem", "objective", "why", "summary"))
        if not outcome:
            outcome = next(
                (
                    line.strip(" -*#\t")
                    for line in body.splitlines()
                    if line.strip() and not line.lstrip().startswith("<!--")
                ),
                None,
            )
        return (
            {
                "requested_outcome": outcome,
                "explicit_scope": [],
                "explicit_non_goals": non_goals(body),
                "acceptance_criteria": [],
                "source_excerpt": body[:4000],
                "pr_title": title or None,
            },
            "pr_body",
        )
    if title:
        return {
            "requested_outcome": title,
            "explicit_scope": [],
            "explicit_non_goals": [],
            "acceptance_criteria": [],
            "source_excerpt": title,
            "pr_title": title,
        }, "pr_title"
    return {
        "requested_outcome": None,
        "explicit_scope": [],
        "explicit_non_goals": [],
        "acceptance_criteria": [],
        "source_excerpt": None,
    }, "UNKNOWN"


def tokens(text: str | None) -> set[str]:
    stop = {
        "the", "and", "for", "with", "this", "that", "from",
        "into", "apply", "feat", "fix", "chore", "style",
    }
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {word for word in words if len(word) >= 4 and word not in stop}


def is_test(path: str) -> bool:
    parsed = Path(path.lower())
    if {"test", "tests"} & set(parsed.parts[:-1]):
        return True
    name = parsed.name
    if not name.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java")):
        return False
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or ".spec." in name
        or ".test." in name
    )


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def format_only(patch: str) -> bool:
    added = [
        line[1:].strip()
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:].strip()
        for line in patch.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    return bool(added and removed and sorted(added) == sorted(removed))


def question(code: str, paths: list[str], text: str) -> dict[str, Any]:
    return {"code": code, "evidence_paths": sorted(set(paths)), "question": text}


def growth(kind: str, path: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": path,
        "classification": "UNKNOWN",
        "evidence": "deterministic_diff",
    }
