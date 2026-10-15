#!/usr/bin/env python3
"""Classify the bound coding projection for SessionStart (report-only).

One classifier for both surfaces; Claude prints ``--format line`` and Cursor
``--format markdown`` (SURFACE_BOOTSTRAP_CONTRACT: share the classifier, not
the presentation). It never fetches, never writes, and never blocks: the
binding's ``enforcement.mode`` is ``report_only``.

Status, strongest claim first — each only with the proof named:

* ``CURRENT``    committed outputs reproduce byte-for-byte from the pinned
                 revision of a verified Quantum-L9/.github checkout, and that
                 revision IS the checkout's ``origin/main`` ref.
* ``BOUND``      as CURRENT, but ``origin/main`` is ahead and the pinned
                 revision is its ancestor with the profile and every input
                 unchanged.
* ``STALE``      the pinned revision reproduces, but ``origin/main`` changed the
                 profile or an input (or no longer contains the pin): rebind.
* ``UNVERIFIED`` committed outputs are internally consistent, but upstream was
                 not observed (no verified checkout, or the pinned commit is not
                 in it). Never upgraded from file age.
* ``BLOCKED``    binding or outputs missing, malformed, tampered, forged, or not
                 reproducible from the source they claim.

``origin/main`` is the checkout's local ref — this reader does not fetch — and
the line says so, with the age of the last fetch when git recorded one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.authority.project_canonical_identity import ProjectionError  # noqa: E402
from tools.authority.project_coding_projection import (  # noqa: E402
    BINDING_PATH,
    OUTPUT_DIR,
    check_integrity,
    has_commit,
    is_ancestor,
    load_binding,
    render,
    resolve_ref,
    verify_authority,
)

ENV_AUTHORITY_ROOT = "L9_AUTHORITY_ROOT"
STATUSES = ("CURRENT", "BOUND", "STALE", "UNVERIFIED", "BLOCKED")


def _candidates(workspace: Path | None, explicit: Path | None) -> list[Path]:
    seen: list[Path] = []
    env_root = os.environ.get(ENV_AUTHORITY_ROOT, "").strip()
    raw = [explicit, Path(env_root) if env_root else None]
    if workspace is not None:
        raw += [workspace / ".github", workspace.parent / ".github"]
    for path in raw:
        if path is not None and path.is_dir() and path.resolve() not in seen:
            seen.append(path.resolve())
    return seen


def _authority(workspace: Path | None, explicit: Path | None) -> tuple[Path | None, list[str]]:
    rejected: list[str] = []
    for candidate in _candidates(workspace, explicit):
        try:
            verify_authority(candidate)
        except ProjectionError as exc:
            rejected.append(f"{candidate}: {exc}")
            continue
        return candidate, rejected
    return None, rejected


def _fetch_age(root: Path) -> str:
    head = root / ".git" / "FETCH_HEAD"
    if not head.is_file():
        return "never fetched"
    hours = (time.time() - head.stat().st_mtime) / 3600
    return f"fetched {hours:.1f} h ago"


def classify(
    *,
    repo_root: Path = REPO_ROOT,
    workspace: Path | None = None,
    authority_root: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "l9.coding-projection-status/v1",
        "enforcement": "report_only",
    }

    def done(status: str, detail: str, **extra: Any) -> dict[str, Any]:
        result.update(status=status, detail=detail, **extra)
        return result

    try:
        binding = load_binding(repo_root / BINDING_PATH)
    except (OSError, ProjectionError) as exc:
        return done("BLOCKED", f"binding unreadable: {exc}")
    revision = binding["upstream"]["revision"]
    result["pinned_revision"] = revision
    result["profile_ref"] = binding["upstream"]["profile_ref"]

    output_dir = repo_root / OUTPUT_DIR
    problems = check_integrity(output_dir, binding)
    if problems:
        return done("BLOCKED", "; ".join(problems[:3]))

    root, rejected = _authority(workspace, authority_root)
    if rejected:
        result["rejected_authority_roots"] = rejected
    if root is None:
        return done(
            "UNVERIFIED",
            f"outputs consistent for @{revision[:12]}; upstream not observed "
            f"(no verified Quantum-L9/.github checkout; set {ENV_AUTHORITY_ROOT})",
        )
    result["authority_root"] = str(root)
    if not has_commit(root, revision):
        return done("UNVERIFIED", f"pinned @{revision[:12]} is not in {root} (fetch it)")

    try:
        pinned = render(root, binding, revision)
    except ProjectionError as exc:
        return done("BLOCKED", f"pinned source does not project: {exc}")
    differs = sorted(
        name
        for name, content in pinned.items()
        if not (output_dir / name).is_file() or (output_dir / name).read_bytes() != content
    )
    if differs:
        return done(
            "BLOCKED", f"committed outputs do not reproduce from @{revision[:12]}: {differs}"
        )

    main = resolve_ref(root, "refs/remotes/origin/main")
    age = _fetch_age(root)
    if main is None:
        return done(
            "UNVERIFIED", f"reproduces from @{revision[:12]}; checkout has no origin/main ref"
        )
    result["observed_main"] = main
    where = f"local origin/main @{main[:12]}, {age}; not fetched by this check"
    if main == revision:
        return done("CURRENT", f"reproduces from @{revision[:12]} = {where}")
    if not is_ancestor(root, revision, main):
        return done("STALE", f"pinned @{revision[:12]} is not on {where}")
    try:
        latest = render(root, binding, main)
    except ProjectionError as exc:
        return done("STALE", f"profile or inputs changed at {where}: {exc}")
    if _strip_revision(latest) != _strip_revision(pinned):
        return done("STALE", f"selected records changed at {where}: rebind")
    return done("BOUND", f"reproduces from @{revision[:12]}; inputs unchanged at {where}")


def _strip_revision(files: dict[str, bytes]) -> dict[str, bytes]:
    """Outputs with revision coordinates removed, to compare content only."""
    import yaml

    stripped: dict[str, bytes] = {}
    for name, content in files.items():
        data = yaml.safe_load(content)
        data.pop("receipt_identity", None)
        data.pop("claim", None)
        data.pop("receipt_digest", None)
        data.get("provenance", {}).pop("source_revision", None)
        data.get("governing_coordinates", {}).pop("source_revision", None)
        stripped[name] = json.dumps(data, sort_keys=True).encode()
    return stripped


def render_line(result: dict[str, Any]) -> str:
    return f"coding projection: {result['status']} — {result['detail']} (report-only)"


def render_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "### coding projection",
            f"- {result['status']}: {result['detail']}",
            f"- profile: {result.get('profile_ref', 'unknown')} (enforcement: report-only)",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--authority-root", type=Path, default=None)
    parser.add_argument("--format", choices=("line", "markdown", "json"), default="line")
    parser.add_argument(
        "--fail-on",
        default="",
        help="comma-separated statuses that exit 1 (CI); SessionStart passes none",
    )
    args = parser.parse_args(argv)
    try:
        result = classify(workspace=args.workspace, authority_root=args.authority_root)
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
