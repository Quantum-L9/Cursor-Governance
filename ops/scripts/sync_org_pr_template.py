#!/usr/bin/env python3
"""Pin ``<owner>/.github``'s PR template into Cursor-Governance.

``make pr`` composes every PR body from the organization's canonical template,
read live at the org repository's default-branch head
(``compose_pr_body.resolve_template``). Since ``Quantum-L9/.github`` went
private (2026-11-16), a Claude Code cloud session reaches it only when the
session was *started* with it selected: ``add_repo`` refuses dot-named
repositories and ``create_session`` takes one source, so most agent sessions
can never read it, and ``make pr`` refused to push in every one of them.

This tool writes the template, at one exact commit, into
``generated/governance/org_pr_template/<owner>/`` beside a receipt naming that
commit and the bytes' sha256. ``resolve_template`` reads the live template first
and falls back to this pinned copy only when the live read fails, and only when
the pinned bytes still match their receipt. It is a projection of the authority,
not a second source: bytes, commit and digest come from ``<owner>/.github``
through ``org_dotgithub.read_org_file`` (the single reader), and ``--check``
reports drift whenever the live template is reachable.

Usage::

    python3 ops/scripts/sync_org_pr_template.py            # write / refresh
    python3 ops/scripts/sync_org_pr_template.py --check    # exit 1 on drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import org_dotgithub  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PROJECTION_ROOT = REPO / "generated" / "governance" / "org_pr_template"
TEMPLATE_PATH = ".github/pull_request_template.md"
TEMPLATE_NAME = "pull_request_template.md"
RECEIPT_NAME = "pull_request_template.receipt.json"
SCHEMA = "l9.org_pr_template_projection.v1"
#: Owners whose template is pinned. Another owner keeps the live-only read.
OWNERS = ("Quantum-L9",)


def projection_dir(owner: str, root: Path = PROJECTION_ROOT) -> Path:
    return root / owner


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def write(owner: str, root: Path = PROJECTION_ROOT) -> dict[str, str]:
    org = org_dotgithub.read_org_file(owner, TEMPLATE_PATH)
    target = projection_dir(owner, root)
    target.mkdir(parents=True, exist_ok=True)
    (target / TEMPLATE_NAME).write_text(org.text, encoding="utf-8")
    receipt = {
        "schema": SCHEMA,
        "authority_repository": f"{owner}/.github",
        "path": TEMPLATE_PATH,
        "revision": org.sha,
        "sha256": digest(org.text),
        "read_transport": org.transport,
        "pinned_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (target / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def check(owner: str, root: Path = PROJECTION_ROOT) -> str | None:
    """``None`` when the pinned copy matches the live template, else why not."""
    target = projection_dir(owner, root)
    try:
        receipt = json.loads((target / RECEIPT_NAME).read_text(encoding="utf-8"))
        pinned = (target / TEMPLATE_NAME).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return f"{owner}: no readable pinned template ({exc})"
    if digest(pinned) != receipt.get("sha256"):
        return f"{owner}: pinned template does not match its receipt digest"
    org = org_dotgithub.read_org_file(owner, TEMPLATE_PATH)
    if digest(org.text) != receipt.get("sha256"):
        return (
            f"{owner}: pinned template is stale (pinned {receipt.get('revision')}, "
            f"live {org.sha}); run python3 ops/scripts/sync_org_pr_template.py"
        )
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift; write nothing")
    args = parser.parse_args(argv)
    status = 0
    for owner in OWNERS:
        try:
            if args.check:
                problem = check(owner)
                print(problem or f"OK: {owner} pinned PR template matches the live template")
                status = status or (1 if problem else 0)
            else:
                receipt = write(owner)
                print(f"pinned {receipt['authority_repository']}@{receipt['revision']}")
        except org_dotgithub.OrgFileError as exc:
            print(f"{owner}: live template unreachable ({exc})", file=sys.stderr)
            status = 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
