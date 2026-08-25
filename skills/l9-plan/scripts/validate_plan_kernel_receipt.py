#!/usr/bin/env python3
"""Fail-closed kernel_pass receipt checker for a single Cursor .plan.md."""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import safe_cli_path

ZERO_DIGEST = "0" * 64
SHA_FIELD_RE = re.compile(r'(body_sha256:\s*["\']?)([^"\'\s]+)(["\']?)')
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
SLUG_RE = re.compile(
    r"^(?P<slug>.+)_(?P<id>"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"|[0-9]{1,2}-[0-9]{1,2}-[0-9]{2,4}"
    r"|[0-9a-fA-F]{8}"
    r")\.plan\.md$"
)
ETC_RE = re.compile(r"\betc\.|…|\band similar\b", re.I)
OWNED_LINE_RE = re.compile(r"owned_paths|\bexclusive\b", re.I)
EITHER_RE = re.compile(r"\beither\b|drop or keep|fold or exempt", re.I)
BLOCKER_RE = re.compile(r"\bblocker\b", re.I)
STATUS_EXECUTABLE_RE = re.compile(r"(?im)^\s*status\s*:\s*executable\s*$")

try:
    import yaml
except ImportError:  # pragma: no cover - stdlib fallback
    yaml = None  # type: ignore[assignment]


def canonicalize(text: str) -> str:
    return SHA_FIELD_RE.sub(lambda m: f"{m.group(1)}{ZERO_DIGEST}{m.group(3)}", text)


def canonical_sha256(text: str) -> str:
    return hashlib.sha256(canonicalize(text).encode("utf-8")).hexdigest()


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text in {"", "~", "null"}:
        return None
    if text in {"[]"}:
        return []
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    return text


def parse_kernel_pass_fallback(raw: str) -> dict[str, Any] | None:
    lines = raw.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if re.match(r"^kernel_pass:\s*$", line))
    except StopIteration:
        return None
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    current_key = ""
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        stripped = line.strip()
        if stripped.startswith("- "):
            if not isinstance(parent, dict) or not current_key:
                return None
            bucket = parent.setdefault(current_key, [])
            if not isinstance(bucket, list):
                return None
            bucket.append(_parse_scalar(stripped[2:]))
            continue
        if ":" not in stripped:
            return None
        key, rest = stripped.split(":", 1)
        current_key = key.strip()
        if current_key in {"improve", "validate_repair"} and rest.strip() == "":
            child: dict[str, Any] = {}
            if isinstance(parent, dict):
                parent[current_key] = child
            stack.append((indent, child))
        elif current_key == "deltas" and rest.strip() in {"", "[]"}:
            if isinstance(parent, dict):
                parent[current_key] = []
        elif isinstance(parent, dict):
            parent[current_key] = _parse_scalar(rest)
    return root


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    data: dict[str, Any] = {}
    if yaml is not None:
        try:
            loaded = yaml.safe_load(raw)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    if "kernel_pass" not in data:
        fallback = parse_kernel_pass_fallback(raw)
        if fallback is not None:
            data["kernel_pass"] = fallback
    return data, body


def slug_key(path: Path) -> str | None:
    match = SLUG_RE.match(path.name)
    return match.group("slug") if match else None


def newer_same_slug_exists(path: Path) -> bool:
    key = slug_key(path)
    if not key or not path.parent.is_dir():
        return False
    try:
        mine = path.stat().st_mtime
    except OSError:
        return False
    for sibling in path.parent.glob("*.plan.md"):
        if sibling.name == path.name:
            continue
        if slug_key(sibling) != key:
            continue
        try:
            if sibling.stat().st_mtime > mine:
                return True
        except OSError:
            continue
    return False


def _pass_block(kernel_pass: dict[str, Any], name: str) -> dict[str, Any] | None:
    block = kernel_pass.get(name)
    return block if isinstance(block, dict) else None


def _deltas(block: dict[str, Any]) -> list[str]:
    raw = block.get("deltas")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _parse_ran_at(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def check_content_gates(body: str) -> list[str]:
    errors: list[str] = []
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        if OWNED_LINE_RE.search(line) and ETC_RE.search(line):
            errors.append(f"G_PLAN_ETC: line {idx + 1} uses etc/ellipsis in an exclusive list")
        if EITHER_RE.search(line):
            window = " ".join(lines[idx : idx + 2])
            if not BLOCKER_RE.search(window):
                errors.append(f"G_PLAN_EITHER_OR: line {idx + 1} has an unresolved exclusive lock")
    return errors


def check_plan(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"G_PLAN_IO: cannot read {path}: {exc}"]

    fm, body = parse_frontmatter(text)
    kernel_pass = fm.get("kernel_pass")
    if not isinstance(kernel_pass, dict):
        errors.append("G_PLAN_KERNEL_PASS: frontmatter kernel_pass missing")
        errors.extend(check_content_gates(body))
        if STATUS_EXECUTABLE_RE.search(text):
            errors.append("G_PLAN_EXECUTABLE: status executable is illegal while checker FAILs")
        return errors

    bound = str(kernel_pass.get("bound_path") or "").strip()
    if Path(bound).name != path.name:
        errors.append(f"G_PLAN_BOUND: bound_path basename {Path(bound).name!r} != {path.name!r}")

    if newer_same_slug_exists(path):
        errors.append("G_PLAN_SUPERSEDED: a newer same-slug plan is the live target")

    improve = _pass_block(kernel_pass, "improve")
    repair = _pass_block(kernel_pass, "validate_repair")
    if improve is None:
        errors.append("G_PLAN_KERNEL_PASS: improve block missing")
    if repair is None:
        errors.append("G_PLAN_KERNEL_PASS: validate_repair block missing")

    if improve is not None:
        if not _deltas(improve):
            errors.append("G_PLAN_DELTAS: improve.deltas is empty")
        improve_at = _parse_ran_at(improve.get("ran_at"))
        if improve_at is None:
            errors.append("G_PLAN_RAN_AT: improve.ran_at missing or unparseable")
    else:
        improve_at = None

    if repair is not None:
        if not _deltas(repair):
            errors.append("G_PLAN_DELTAS: validate_repair.deltas is empty")
        repair_at = _parse_ran_at(repair.get("ran_at"))
        if repair_at is None:
            errors.append("G_PLAN_RAN_AT: validate_repair.ran_at missing or unparseable")
        claimed = str(repair.get("body_sha256") or "").strip().strip("\"'")
        if not claimed:
            errors.append("G_PLAN_SHA: validate_repair.body_sha256 unset")
        elif claimed != canonical_sha256(text):
            errors.append("G_PLAN_SHA: validate_repair.body_sha256 != canonical file sha")
    else:
        repair_at = None

    if improve_at is not None and repair_at is not None and not (improve_at < repair_at):
        errors.append("G_PLAN_ORDER: improve.ran_at must be earlier than validate_repair.ran_at")

    errors.extend(check_content_gates(body))

    if errors and STATUS_EXECUTABLE_RE.search(text):
        errors.append("G_PLAN_EXECUTABLE: status executable is illegal while checker FAILs")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", help="Cursor .plan.md files")
    args = parser.parse_args(argv)
    failed = False
    for raw in args.plans:
        path = safe_cli_path(raw)
        errors = check_plan(path)
        if errors:
            failed = True
            print(f"FAIL: {path}")
            for err in errors:
                print(f"  {err}")
        else:
            print(f"PASS: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
