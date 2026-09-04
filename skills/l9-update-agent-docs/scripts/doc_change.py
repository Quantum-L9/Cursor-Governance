"""Repository change, impact, managed-region, and capability mechanics."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from doc_policy import git, selector_paths


def changed_files_since(root: Path, base: str) -> tuple[list[str] | None, str | None]:
    if git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode != 0:
        return None, f"unable to resolve changed-since ref {base!r}"
    proc = git(root, "diff", "--name-only", f"{base}...HEAD")
    if proc.returncode == 0:
        return sorted(item for item in proc.stdout.splitlines() if item), None
    return None, proc.stderr.strip()


def worktree_changes(root: Path) -> list[str]:
    proc = git(root, "status", "--porcelain")
    if proc.returncode != 0:
        return []
    values = [line[3:].split(" -> ", 1)[-1] for line in proc.stdout.splitlines()]
    return sorted(set(item for item in values if item))


def automatic_changed_scope(
    root: Path,
) -> tuple[list[str], str | None, str | None]:
    dirty = worktree_changes(root)
    if dirty:
        head_exists = git(root, "rev-parse", "--verify", "HEAD^{commit}").returncode == 0
        return dirty, "HEAD" if head_exists else None, None
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch in {"", "main", "master"}:
        return [], None, None
    for base in ("origin/main", "origin/master", "main", "master"):
        if git(root, "rev-parse", "--verify", f"{base}^{{commit}}").returncode == 0:
            changed, error = changed_files_since(root, base)
            return changed or [], base, error
    return [], None, None


def impact_analysis(policy: dict[str, Any], changed: list[str]) -> dict[str, Any]:
    impacted: set[str] = set()
    matched: dict[str, list[str]] = {}
    for name, rule in policy["impact_rules"].items():
        hits = [
            path
            for path in changed
            if not any(
                fnmatch.fnmatch(path, pattern) for pattern in rule.get("exclude_patterns", [])
            )
            and any(fnmatch.fnmatch(path, pattern) for pattern in rule["patterns"])
        ]
        if hits:
            matched[name] = sorted(set(hits))
            impacted.update(rule["surfaces"])
    return {
        "impacted_surfaces": sorted(impacted),
        "matched_rules": matched,
    }


def semantic_harvest_required(
    policy: dict[str, Any],
    impact: dict[str, Any],
    root: Path | None = None,
) -> list[str]:
    matched = set(impact.get("matched_rules", {}))
    required = []
    for surface, rules in policy["semantic_harvest"]["activation"].items():
        if not matched.intersection(rules):
            continue
        spec = policy["surfaces"][surface]
        if root is not None and not selector_paths(root, spec["selectors"]):
            conditional_absent = (
                spec["requirement"] == "conditional" and spec["create_policy"] == "never"
            )
            if conditional_absent:
                continue
        required.append(surface)
    return sorted(required)


def managed_block_mutations(before: str, after: str, policy: dict[str, Any]) -> list[str]:
    errors = []
    for item in policy.get("managed_regions", {}).get("blocks", []):
        pattern = re.compile(
            re.escape(item["start"]) + r".*?" + re.escape(item["end"]),
            re.DOTALL,
        )
        if pattern.findall(before) != pattern.findall(after):
            errors.append(f"managed block changed: {item['id']}")
    for item in policy.get("managed_regions", {}).get("line_tokens", []):
        token = item["token"]
        old = [line for line in before.splitlines() if token in line]
        new = [line for line in after.splitlines() if token in line]
        if old != new:
            errors.append(f"managed marker lines changed: {item['id']}")
    return errors


def validate_managed_regions(
    root: Path,
    base: str | None,
    changed: list[str],
    policy: dict[str, Any],
) -> tuple[str, list[str]]:
    docs = [path for path in changed if Path(path).suffix.lower() in {".md", ".mdc", ".txt"}]
    if docs and not base:
        return "PARTIAL", ["managed-region comparison base unavailable for changed documentation"]
    errors = []
    for rel in docs:
        path = root / rel
        if not path.is_file() or base is None:
            continue
        before = git(root, "show", f"{base}:{rel}")
        if before.returncode == 0:
            after = path.read_text(encoding="utf-8")
            errors.extend(
                f"{rel}: {error}" for error in managed_block_mutations(before.stdout, after, policy)
            )
    return ("FAIL", errors) if errors else ("PASS", [])


def probe_module_readme_capability(
    root: Path,
    policy: dict[str, Any],
    changed: list[str] | None = None,
) -> dict[str, Any]:
    cap = policy["capabilities"]["module_readmes"]
    present = {name: (root / rel).is_file() for name, rel in cap["required_paths"].items()}
    count = sum(present.values())
    if count == len(present):
        status = "AVAILABLE"
    elif count == 0:
        status = cap["absence_behavior"]
    else:
        status = cap["partial_behavior"]
    extensions = {Path(path).suffix for path in changed or [] if Path(path).suffix}
    unsupported = sorted(extensions - set(cap.get("supported_extensions", [])))
    if status == "AVAILABLE" and unsupported:
        status = "PARTIAL"
    return {
        "status": status,
        "owner": cap["owner"],
        "present": present,
        "partial_repair_route": cap.get("partial_repair_route"),
        "polyglot_extension_owner": cap["polyglot_extension_owner"],
        "unsupported_impacted_extensions": unsupported,
    }
