#!/usr/bin/env python3
"""CLI for the deterministic, read-only L9 pre-remediation PR digest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pr_digest_core import digest, validate
from pr_evidence import live_evidence


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--fixture", type=Path)
    out.add_argument("--repo")
    out.add_argument("--pr-number", type=int)
    out.add_argument("--workspace", type=Path)
    out.add_argument("--base-sha")
    out.add_argument("--head-sha")
    out.add_argument("--intent", type=Path)
    out.add_argument("--output", type=Path)
    out.add_argument("--validate-only", type=Path)
    return out


def main() -> int:
    args = parser().parse_args()
    if args.validate_only:
        doc = json.loads(args.validate_only.read_text(encoding="utf-8"))
        errors = validate(doc)
        if errors:
            print("\n".join(f"FAIL: {error}" for error in errors), file=sys.stderr)
            return 1
        print("PASS: PR digest schema and exact revision binding")
        return 0

    if args.fixture:
        evidence = json.loads(args.fixture.read_text(encoding="utf-8"))
    else:
        if not args.repo or not args.pr_number:
            parser().error("provide --fixture or both --repo and --pr-number")
        evidence = live_evidence(args.repo, args.pr_number, args.workspace)
    if args.base_sha:
        evidence["base_sha"] = args.base_sha
    if args.head_sha:
        evidence["head_sha"] = args.head_sha
    if args.intent:
        evidence["intent"] = json.loads(args.intent.read_text(encoding="utf-8"))

    result = digest(evidence, args.workspace)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    errors = validate(result)
    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
