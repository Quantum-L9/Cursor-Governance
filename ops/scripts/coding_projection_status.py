#!/usr/bin/env python3
"""Classify the coding projection for SessionStart and CI (report-only).

Cursor-Governance verifies ``l9.projection/coding-agent-execution@1``; it never
produces it (Quantum-L9/.github ``docs/PROJECTION_PUBLICATION.md``). One
classifier serves both surfaces: Claude prints ``--format line``, Cursor
``--format markdown`` (SURFACE_BOOTSTRAP_CONTRACT: share the classifier, not
the presentation). It never fetches, never writes, and never blocks.

Status, each only with the proof named:

* ``CURRENT``    every source class has a published ``l9-semantic-compiler``
                 pair that verifies against the authority, nothing material
                 changed on ``main``, and ``main`` equals an independent record
                 passed with ``--expect-main`` (CI passes its fresh checkout).
* ``BOUND``      as CURRENT, judged against the checkout's local
                 ``origin/main`` ref with no independent record (SessionStart).
* ``STALE``      the pinned profile changed on ``main``, or a published pair is
                 genuine but ``main`` has since changed its source or profile.
* ``UNVERIFIED`` proof is not available: no verified Quantum-L9/.github
                 checkout, no ``origin/main``, or no published pair. Never
                 upgraded from cache age.
* ``BLOCKED``    the binding is unreadable, or a published pair, its index or
                 its authority inputs fail verification (tamper, forgery, wrong
                 producer role, revision off ``main``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.authority.verify_coding_projection import (  # noqa: E402
    Rejected,
    Unobserved,
    compute_pins,
    resolve,
    verify_authority,
    verify_published,
)

BINDING_PATH = Path("governance/authority-bindings/coding-agent-execution.yaml")
BINDING_SCHEMA = "l9.cursor-governance.coding-projection-binding/v2"
ENV_AUTHORITY_ROOT = "L9_AUTHORITY_ROOT"
STATUSES = ("CURRENT", "BOUND", "STALE", "UNVERIFIED", "BLOCKED")


def load_binding(path: Path) -> dict[str, Any]:
    try:
        binding = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Rejected(f"binding unreadable: {exc}") from exc
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise Rejected(f"binding schema is not {BINDING_SCHEMA}")
    upstream = binding.get("upstream") or {}
    publication = binding.get("publication") or {}
    for key in ("profile_ref", "profile_digest"):
        if not isinstance(upstream.get(key), str) or not upstream[key]:
            raise Rejected(f"binding.upstream.{key} is required")
    classes = upstream.get("source_classes")
    if not isinstance(classes, list) or not classes or not all(isinstance(c, str) for c in classes):
        raise Rejected("binding.upstream.source_classes must list the profile's classes")
    if not isinstance(publication.get("ref"), str) or not publication["ref"]:
        raise Rejected("binding.publication.ref is required")
    return binding


def _authority(workspace: Path | None, explicit: Path | None) -> tuple[Path | None, list[str]]:
    env_root = os.environ.get(ENV_AUTHORITY_ROOT, "").strip()
    raw = [explicit, Path(env_root) if env_root else None]
    if workspace is not None:
        raw += [workspace / ".github", workspace.parent / ".github"]
    seen: list[Path] = []
    rejected: list[str] = []
    for path in raw:
        if path is None or not path.is_dir() or path.resolve() in seen:
            continue
        seen.append(path.resolve())
        try:
            verify_authority(path.resolve())
        except Unobserved as exc:
            rejected.append(str(exc))
            continue
        return path.resolve(), rejected
    return None, rejected


def _fetch_age(root: Path) -> str:
    head = root / ".git" / "FETCH_HEAD"
    if not head.is_file():
        return "never fetched"
    return f"fetched {(time.time() - head.stat().st_mtime) / 3600:.1f} h ago"


def classify(
    *,
    repo_root: Path = REPO_ROOT,
    workspace: Path | None = None,
    authority_root: Path | None = None,
    expect_main: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "l9.coding-projection-status/v2",
        "enforcement": "report_only",
        "role": "consumer_verifier",
    }

    def done(status: str, detail: str) -> dict[str, Any]:
        result.update(status=status, detail=detail)
        return result

    try:
        binding = load_binding(repo_root / BINDING_PATH)
    except Rejected as exc:
        return done("BLOCKED", str(exc))
    upstream, publication = binding["upstream"], binding["publication"]
    profile_ref = upstream["profile_ref"]
    result["profile_ref"] = profile_ref

    root, rejected = _authority(workspace, authority_root)
    if rejected:
        result["rejected_authority_roots"] = rejected
    if root is None:
        return done(
            "UNVERIFIED",
            "upstream not observed (no verified Quantum-L9/.github checkout; "
            f"set {ENV_AUTHORITY_ROOT})",
        )
    result["authority_root"] = str(root)
    main = resolve(root, "refs/remotes/origin/main")
    if main is None:
        return done("UNVERIFIED", f"{root} has no origin/main ref")
    result["observed_main"] = main
    where = f"local origin/main @{main[:12]}, {_fetch_age(root)}"

    try:
        pins = compute_pins(root, main, profile_ref, upstream["source_classes"][0])
    except Rejected as exc:
        return done("STALE", f"{profile_ref} no longer resolves at {where}: {exc}")
    if pins["profile_digest"] != upstream["profile_digest"]:
        return done("STALE", f"{profile_ref} changed at {where}: rebind deliberately")

    published = resolve(root, publication["ref"])
    if published is None:
        return done(
            "UNVERIFIED",
            f"no producer pair published ({publication['ref']} absent in this checkout; "
            f"{publication.get('upstream_state', 'publisher state unknown')})",
        )
    result["publication_commit"] = published

    outcomes: dict[str, Any] = {}
    try:
        for source_class in upstream["source_classes"]:
            outcomes[source_class] = verify_published(
                root, published, main, profile_ref, source_class
            )
    except Unobserved as exc:
        return done("UNVERIFIED", f"{exc} at {publication['ref']} @{published[:12]}")
    except Rejected as exc:
        return done("BLOCKED", f"{exc} at {publication['ref']} @{published[:12]}")
    result["pairs"] = outcomes
    stale = sorted(c for c, o in outcomes.items() if not o["current"])
    if stale:
        return done("STALE", f"source changed since publication for {stale} at {where}")
    if expect_main is not None:
        if expect_main != main:
            return done("STALE", f"independent main record @{expect_main[:12]} is not {where}")
        return done("CURRENT", f"all pairs verify at main @{main[:12]} (independently confirmed)")
    return done("BOUND", f"all pairs verify at {where}; not independently confirmed")


def render_line(result: dict[str, Any]) -> str:
    return f"coding projection: {result['status']} — {result['detail']} (report-only)"


def render_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "### coding projection",
            f"- {result['status']}: {result['detail']}",
            f"- profile: {result.get('profile_ref', 'unknown')} (consumer verifier; report-only)",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--authority-root", type=Path, default=None)
    parser.add_argument(
        "--expect-main", default=None, help="independent record of canonical main (CI)"
    )
    parser.add_argument("--format", choices=("line", "markdown", "json"), default="line")
    parser.add_argument(
        "--fail-on", default="", help="comma-separated statuses that exit 1 (CI only)"
    )
    args = parser.parse_args(argv)
    try:
        result = classify(
            workspace=args.workspace,
            authority_root=args.authority_root,
            expect_main=args.expect_main,
        )
    except Exception as exc:  # noqa: BLE001 - a report-only line must always print
        result = {"status": "BLOCKED", "detail": f"classifier error: {type(exc).__name__}: {exc}"}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(render_markdown(result))
    else:
        print(render_line(result))
    fail_on = {s.strip().upper() for s in args.fail_on.split(",") if s.strip()}
    return 1 if result["status"] in fail_on else 0


if __name__ == "__main__":
    raise SystemExit(main())
