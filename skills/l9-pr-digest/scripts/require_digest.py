#!/usr/bin/env python3
"""Fail-closed check that a digest exists, is revision-bound, and (for Converge) is READY."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pr_digest_core import validate

READY = frozenset({"READY_FOR_REMEDIATION", "READY_WITH_NON_BLOCKING_NOTES"})


def check(
    doc: dict,
    *,
    head_sha: str | None = None,
    mode: str = "diagnose",
) -> list[str]:
    errors = validate(doc)
    identity = doc.get("PR_identity") or {}
    bound_head = str(identity.get("head_sha") or "")
    if head_sha and bound_head and head_sha != bound_head:
        errors.append(f"digest head {bound_head} != current head {head_sha}")
    decision = str(doc.get("decision") or "")
    if mode == "converge" and decision not in READY:
        errors.append(f"converge requires READY digest, got {decision or 'missing'}")
    return errors


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--path", type=Path, default=Path(".l9/pr/pr-digest-result.json"))
    out.add_argument("--head-sha")
    out.add_argument("--mode", choices=("diagnose", "converge"), default="diagnose")
    return out


def main() -> int:
    args = parser().parse_args()
    if not args.path.is_file():
        print(f"FAIL: digest missing: {args.path}", file=sys.stderr)
        return 1
    try:
        doc = json.loads(args.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: digest is not JSON: {exc}", file=sys.stderr)
        return 1
    errors = check(doc, head_sha=args.head_sha, mode=args.mode)
    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors), file=sys.stderr)
        return 3 if args.mode == "converge" and args.path.is_file() else 1
    print(f"PASS: digest {args.mode} {doc.get('decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
