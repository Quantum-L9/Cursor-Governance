#!/usr/bin/env python3
"""Classify the coding projection bundle for SessionStart and CI (report-only).

Cursor-Governance commits ``generated/governance/coding_agent_execution`` and
verifies it with the coding agent's own verifier (Quantum-L9/.github ADR-021);
it never produces it. One classifier serves both surfaces: Claude prints
``--format line``, Cursor ``--format markdown`` (SURFACE_BOOTSTRAP_CONTRACT:
share the classifier, not the presentation). It never fetches the network,
never writes the repository, and never blocks.

Status, each only with the proof named:

* ``CURRENT``    the committed bundle verifies at the revision its lock names,
                 nothing material changed on ``main``, the binding's admission
                 decision admits the exact profile digest (the shared resolver
                 GAR is judged by), and ``main`` equals an independent record
                 passed with ``--expect-main`` (CI passes its fresh checkout).
* ``BOUND``      as CURRENT, judged against the checkout's local
                 ``origin/main`` ref with no independent record (SessionStart).
* ``STALE``      the pinned profile or a bundled source changed on ``main``, or
                 the verifier reports STALE.
* ``UNVERIFIED`` proof is not available: no verified Quantum-L9/.github
                 checkout, no ``origin/main``, no committed bundle, the bundle
                 revision not fetched, no admission decision for the profile,
                 or the verifier reports BLOCKED (Unknown).
* ``BLOCKED``    the binding is unreadable, the bundle revision is off ``main``,
                 the admission decision does not admit this exact profile, or
                 the verifier reports REJECTED (tamper, forgery, wrong
                 producer role, unbound receipt).
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
    BUNDLE_PATH,
    Rejected,
    Unobserved,
    is_ancestor,
    material_change,
    pinned_checkout,
    read_lock,
    resolve,
    resolve_admission,
    verify_authority,
    verify_bundle,
)

BINDING_PATH = Path("governance/authority-bindings/coding-agent-execution.yaml")
BINDING_SCHEMA = "l9.cursor-governance.coding-projection-binding/v3"
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
    bundle = binding.get("bundle") or {}
    for key in ("profile_ref", "profile_digest"):
        if not isinstance(upstream.get(key), str) or not upstream[key]:
            raise Rejected(f"binding.upstream.{key} is required")
    classes = upstream.get("source_classes")
    if not isinstance(classes, list) or not classes or not all(isinstance(c, str) for c in classes):
        raise Rejected("binding.upstream.source_classes must list the profile's classes")
    if not isinstance(bundle.get("path"), str) or not bundle["path"]:
        raise Rejected("binding.bundle.path is required")
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
        "schema": "l9.coding-projection-status/v3",
        "enforcement": "report_only",
        "role": "consumer_verifier",
        # Reporting never blocks. Coding-agent mutation is gated separately, while a
        # run is active, by the PreToolUse gate the governance binding names.
        "mutation_gate": "ops/autonomy/coding_agent_binding_gate.py",
    }

    def done(status: str, detail: str) -> dict[str, Any]:
        result.update(status=status, detail=detail)
        return result

    try:
        binding = load_binding(repo_root / BINDING_PATH)
    except Rejected as exc:
        return done("BLOCKED", str(exc))
    upstream = binding["upstream"]
    profile_ref = upstream["profile_ref"]
    result["profile_ref"] = profile_ref
    bundle = repo_root / binding["bundle"]["path"]
    if bundle != repo_root / BUNDLE_PATH:
        return done("BLOCKED", f"binding.bundle.path is not the committed bundle {BUNDLE_PATH}")

    try:
        lock = read_lock(bundle)
    except Unobserved as exc:
        return done("UNVERIFIED", f"no committed bundle: {exc}")
    except Rejected as exc:
        return done("BLOCKED", str(exc))
    revision = lock["authority"]["revision"]
    result["bundle_revision"] = revision
    if (lock.get("projection_profile") or {}).get("digest") != upstream["profile_digest"]:
        return done("STALE", f"the bundle's profile pin is not this binding's {profile_ref} digest")
    if [c.get("source_class") for c in lock.get("components") or []] != upstream["source_classes"]:
        return done("BLOCKED", "the bundle's components are not the binding's source classes")

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
    if resolve(root, revision) is None:
        return done("UNVERIFIED", f"bundle revision {revision[:12]} is not fetched in {root}")
    if not is_ancestor(root, revision, main):
        return done("BLOCKED", f"bundle revision {revision[:12]} is not on {where}")

    try:
        with pinned_checkout(root, revision) as holder:
            record = verify_bundle(Path(holder) / "authority", bundle, revision, repo_root)
    except Unobserved as exc:
        return done("UNVERIFIED", f"{exc} at bundle revision {revision[:12]}")
    except Rejected as exc:
        status = "STALE" if str(exc).startswith("STALE ") else "BLOCKED"
        return done(status, f"{exc} at bundle revision {revision[:12]}")
    result["components"] = [c["source_class"] for c in record["components"]]
    result["projected_invariant_count"] = record["projected_invariant_count"]

    try:
        changed = material_change(root, main, lock)
    except Rejected as exc:
        return done("STALE", f"{exc}")
    if changed:
        return done("STALE", f"changed on {where} since the bundle: {changed}")

    try:
        admission = resolve_admission(root, main, lock, binding, repo_root)
    except Unobserved as exc:
        return done("UNVERIFIED", f"admission unresolved: {exc}")
    except Rejected as exc:
        status = "STALE" if str(exc).startswith("STALE ") else "BLOCKED"
        return done(status, f"admission refused: {exc}")
    result["admission"] = {"status": admission["status"], "reason": admission["reason"]}
    if admission["status"] == "ADMISSION_UNRESOLVED":
        return done(
            "UNVERIFIED", f"no admission decision for {admission.get('undecided')} in the binding"
        )
    if admission["status"] != "ADMITTED_AND_CURRENT":
        return done("BLOCKED", f"{profile_ref} is not admitted: {admission['reason']}")
    if expect_main is not None:
        if expect_main != main:
            return done("STALE", f"independent main record @{expect_main[:12]} is not {where}")
        return done(
            "CURRENT",
            f"bundle @{revision[:12]} verifies and is current at main @{main[:12]}"
            " (independently confirmed)",
        )
    return done(
        "BOUND",
        f"bundle @{revision[:12]} verifies and is current at {where}; not independently confirmed",
    )


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
