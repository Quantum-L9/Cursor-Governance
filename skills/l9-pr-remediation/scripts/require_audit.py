#!/usr/bin/env python3
"""Bind a same-head /l9-pr-audit remediation-handoff to the remediator fleet.

Absent or stale packets do not fail Converge and do not hold merge. Same-head
``mutation_eligible`` work units do: they enter remediation first and set
``hold_merge``. Generators (``_emit*.py``) are never loaded. Legal Defense and
secret globs are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_PREFIX = "l9.pr-audit.remediation-handoff"
BIND_SCHEMA = "l9.pr-audit.bind.v1"
HANDOFF_NAME = "remediation-handoff.json"
SKIP_PARTS = frozenset({"Legal Defense", "legal-defense"})
SECRET_GLOBS = ("*secret*", "*credential*", "*.pem", "*.key")


def _is_skipped(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    parts = set(rel.split("/"))
    if parts & SKIP_PARTS:
        return True
    name = path.name.lower()
    return any(
        name.endswith(suffix.removeprefix("*")) if suffix.startswith("*.") else False
        for suffix in SECRET_GLOBS
        if suffix.startswith("*.")
    ) or any(token in name for token in ("secret", "credential"))


def discover_handoffs(root: Path) -> list[Path]:
    found: list[Path] = []
    for base in (root / "WIP", root / ".l9" / "pr"):
        if not base.is_dir():
            continue
        for path in base.rglob(HANDOFF_NAME):
            if not path.is_file():
                continue
            if _is_skipped(path, root):
                continue
            found.append(path)
    found.sort(key=lambda p: (p.stat().st_mtime, p.as_posix()), reverse=True)
    return found


def _repo_of(doc: dict[str, Any]) -> str:
    binding = doc.get("repository_binding") or {}
    repo = str(binding.get("repository") or binding.get("github_repo") or "").strip()
    if not repo and binding.get("owner") and binding.get("name"):
        repo = f"{binding['owner']}/{binding['name']}"
    return repo.removeprefix("https://github.com/").rstrip("/")


def _schema_ok(doc: dict[str, Any]) -> bool:
    version = str(doc.get("schema_version") or "")
    return version.startswith(SCHEMA_PREFIX)


def _load(path: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict) or not _schema_ok(doc):
        return None
    return doc


def fleet_heads(fleet: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for pr in fleet.get("prs") or []:
        if not isinstance(pr, dict) or pr.get("number") is None:
            continue
        number = int(pr["number"])
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        sha = str(head.get("sha") or pr.get("head_sha") or "")
        out[number] = sha
    return out


def bound_head(handoff: dict[str, Any], number: int) -> str:
    for binding in handoff.get("pr_bindings") or []:
        if not isinstance(binding, dict):
            continue
        raw = binding.get("pr_number")
        if raw is None:
            raw = binding.get("number", binding.get("pr"))
        try:
            if int(raw) != number:
                continue
        except (TypeError, ValueError):
            continue
        return str(binding.get("head_sha") or binding.get("source_head_sha") or "")
    return ""


def bind(
    *,
    repo: str,
    fleet: dict[str, Any] | None = None,
    heads: dict[int, str] | None = None,
    handoff_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Return an audit-bind receipt. Never raises for a missing packet."""
    root = root or Path.cwd()
    empty = {
        "schema_version": BIND_SCHEMA,
        "repo": repo,
        "path": None,
        "audit_id": None,
        "hold_merge": False,
        "eligible_prs": [],
        "stale_prs": [],
        "eligible_units": [],
        "reason": "no_handoff",
    }
    current_heads = heads or (fleet_heads(fleet) if fleet else {})
    chosen: tuple[Path, dict[str, Any]] | None = None
    if handoff_path is not None:
        doc = _load(handoff_path)
        if doc is None:
            empty["reason"] = "unreadable_handoff"
            return empty
        if _repo_of(doc) != repo:
            empty["path"] = str(handoff_path)
            empty["reason"] = "repo_mismatch"
            return empty
        chosen = (handoff_path, doc)
    else:
        for path in discover_handoffs(root):
            doc = _load(path)
            if doc is None:
                continue
            if _repo_of(doc) != repo:
                continue
            chosen = (path, doc)
            break
    if chosen is None:
        return empty
    path, doc = chosen
    eligible: list[int] = []
    stale: list[int] = []
    units: list[dict[str, Any]] = []
    seen_eligible: set[int] = set()
    seen_stale: set[int] = set()
    for unit in doc.get("work_units") or []:
        if not isinstance(unit, dict) or not unit.get("mutation_eligible"):
            continue
        finding_id = str(unit.get("finding_id") or "")
        for raw in unit.get("affected_prs") or []:
            try:
                number = int(raw)
            except (TypeError, ValueError):
                continue
            if number not in current_heads:
                continue
            bound = bound_head(doc, number)
            live = current_heads.get(number) or ""
            if bound and live and bound == live:
                if number not in seen_eligible:
                    seen_eligible.add(number)
                    eligible.append(number)
                units.append(
                    {
                        "finding_id": finding_id,
                        "pr": number,
                        "write_surfaces": list(unit.get("write_surfaces") or []),
                    }
                )
            elif number not in seen_stale:
                seen_stale.add(number)
                stale.append(number)
    eligible.sort()
    stale.sort()
    hold = bool(eligible)
    if hold:
        reason = "same_head_mutation_eligible"
    elif stale:
        reason = "stale_heads"
    else:
        reason = "no_eligible_units"
    return {
        "schema_version": BIND_SCHEMA,
        "repo": repo,
        "path": str(path),
        "audit_id": doc.get("audit_id"),
        "hold_merge": hold,
        "eligible_prs": eligible,
        "stale_prs": stale,
        "eligible_units": units,
        "reason": reason,
    }


def _parse_heads(raw: str) -> dict[int, str]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--heads must be a JSON object of pr->sha")
    return {int(key): str(value) for key, value in data.items()}


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--repo", required=True, help="owner/name")
    out.add_argument("--fleet", type=Path, help="fleet.json from pr_fleet.py plan")
    out.add_argument("--heads", help="JSON object {pr: head_sha} when no fleet receipt")
    out.add_argument("--handoff", type=Path, help="explicit remediation-handoff.json")
    out.add_argument("--root", type=Path, default=Path.cwd())
    out.add_argument("--output", type=Path, default=Path(".l9/pr/audit-bind.json"))
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    fleet: dict[str, Any] | None = None
    heads: dict[int, str] | None = None
    if args.fleet:
        if not args.fleet.is_file():
            print(f"FAIL: fleet missing: {args.fleet}", file=sys.stderr)
            return 1
        try:
            loaded = json.loads(args.fleet.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: fleet is not JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(loaded, dict):
            print("FAIL: fleet is not an object", file=sys.stderr)
            return 1
        fleet = loaded
    if args.heads:
        try:
            heads = _parse_heads(args.heads)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            print(f"FAIL: heads: {exc}", file=sys.stderr)
            return 1
    receipt = bind(
        repo=args.repo,
        fleet=fleet,
        heads=heads,
        handoff_path=args.handoff,
        root=args.root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
