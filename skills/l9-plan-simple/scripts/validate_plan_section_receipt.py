#!/usr/bin/env python3
"""Fail-closed check that a simple plan has every skill-required section."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from paths import is_under, plans_store_root, safe_cli_path
from plan_sections import (
    GAR_SKILL_REF,
    PLAN_SCHEMA_REL,
    REPO_ROOT,
    SKILL_ROOT,
    TEMPLATE_REL,
    execute_swap_presence,
    frontmatter_presence,
    json_required_keys,
    json_section_presence,
    md_required_headings,
    md_section_presence,
    missing_labels,
    receipt_status,
)

RECEIPT_SCHEMA = SKILL_ROOT / "schemas" / "plan-section-receipt.schema.json"

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"jsonschema required: {exc}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_declared(rel: str) -> Path:
    if not str(rel).strip():
        raise ValueError("empty declared path")
    raw = Path(rel)
    repo = REPO_ROOT.resolve()
    resolved = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
    allowed = [repo]
    store = plans_store_root()
    if store is not None:
        allowed.append(store)
    if not any(is_under(resolved, root) for root in allowed):
        raise ValueError(f"declared path escapes repo and plans store: {rel}")
    return resolved


def _schema_errors(receipt: dict[str, Any]) -> list[str]:
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    return [
        f"G_RECEIPT_SCHEMA: {'.'.join(str(x) for x in err.path) or '<root>'}: {err.message}"
        for err in sorted(
            jsonschema.Draft202012Validator(schema).iter_errors(receipt),
            key=lambda e: list(e.path),
        )
    ]


def _coverage_errors(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    claimed_json = receipt.get("json_sections") or {}
    claimed_md = receipt.get("md_sections") or {}
    for key in json_required_keys():
        if key not in claimed_json:
            errors.append(f"G_RECEIPT_COVERAGE: receipt omits JSON section {key}")
    for title in md_required_headings(mode=str(receipt.get("handoff_mode") or "cursor-build")):
        if title not in claimed_md:
            errors.append(f"G_RECEIPT_COVERAGE: receipt omits MD section {title!r}")
    if receipt.get("section_schema_ref") != PLAN_SCHEMA_REL:
        errors.append("G_RECEIPT_OWNER: section_schema_ref is not the PLAN_DOCUMENT schema")
    if receipt.get("template_ref") != TEMPLATE_REL:
        errors.append("G_RECEIPT_OWNER: template_ref is not the canonical executable plan")
    gar = receipt.get("gar_upstream") or {}
    if gar.get("skill_ref") != GAR_SKILL_REF:
        errors.append("G_GAR_UPSTREAM: skill_ref must be skills/l9-global-architect")
    return errors


def check_receipt(path: Path) -> list[str]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"G_RECEIPT_IO: cannot load {path}: {exc}"]
    if not isinstance(receipt, dict):
        return ["G_RECEIPT_IO: receipt root must be an object"]

    errors = _schema_errors(receipt)
    errors.extend(_coverage_errors(receipt))

    json_rel = str(receipt.get("plan_json_path") or "")
    md_rel = str(receipt.get("plan_md_path") or "")
    try:
        plan_json_path = _resolve_declared(json_rel)
        plan_md_path = _resolve_declared(md_rel)
    except (OSError, ValueError) as exc:
        return [*errors, f"G_RECEIPT_PATH: {exc}"]

    if not plan_json_path.is_file():
        errors.append(f"G_RECEIPT_PATH: plan JSON missing: {json_rel}")
        return errors
    if not plan_md_path.is_file():
        errors.append(f"G_RECEIPT_PATH: plan markdown missing: {md_rel}")
        return errors

    if _sha256(plan_json_path) != str(receipt.get("plan_json_sha256") or ""):
        errors.append("G_RECEIPT_SHA: plan_json_sha256 does not match current file")
    if _sha256(plan_md_path) != str(receipt.get("plan_md_sha256") or ""):
        errors.append("G_RECEIPT_SHA: plan_md_sha256 does not match current file")

    try:
        plan = json.loads(plan_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"G_RECEIPT_IO: cannot load plan JSON: {exc}")
        return errors
    if not isinstance(plan, dict):
        errors.append("G_RECEIPT_IO: plan JSON root must be an object")
        return errors

    md_text = plan_md_path.read_text(encoding="utf-8")
    observed_json = json_section_presence(plan)
    observed_md = md_section_presence(md_text)
    observed_fm = frontmatter_presence(md_text)
    observed_swap = execute_swap_presence(md_text)
    gar_invoked = bool((receipt.get("gar_upstream") or {}).get("invoked"))

    if receipt.get("json_sections") != observed_json:
        errors.append("G_RECEIPT_STALE: json_sections does not match current PLAN_DOCUMENT")
    if receipt.get("md_sections") != observed_md:
        errors.append("G_RECEIPT_STALE: md_sections does not match current .plan.md")
    if receipt.get("frontmatter") != observed_fm:
        errors.append("G_RECEIPT_STALE: frontmatter does not match current .plan.md")
    if receipt.get("execute_swap") != observed_swap:
        errors.append("G_RECEIPT_STALE: execute_swap does not match current .plan.md")

    observed_status = receipt_status(
        observed_json, observed_md, observed_fm, observed_swap, gar_invoked
    )
    if receipt.get("status") != observed_status:
        errors.append(
            f"G_RECEIPT_STATUS: claimed {receipt.get('status')!r} != observed {observed_status!r}"
        )
    errors.extend(
        missing_labels(observed_json, observed_md, observed_fm, observed_swap, gar_invoked)
    )

    out: list[str] = []
    seen: set[str] = set()
    for err in errors:
        if err not in seen:
            seen.add(err)
            out.append(err)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="+", help="section receipt JSON files")
    args = parser.parse_args(argv)
    failed = False
    for raw in args.receipts:
        path = safe_cli_path(raw)
        errors = check_receipt(path)
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
