#!/usr/bin/env python3
"""Repository-level consumer of the coding-agent execution projection bundle.

Cursor-Governance commits ``generated/governance/coding_agent_execution`` (cut by
``tools/authority/produce_projection_bundle.py`` from a pinned ``l9-semantic-compiler``
revision at a pinned ``Quantum-L9/.github`` revision, ADR-021) and verifies it with the one
verifier the coding agent itself uses,
``skills/l9-coding-agent/scripts/verify_canonical_binding.py`` in ``--bundle`` mode. This
module holds no second digest, subject or receipt convention: it locates the bundle, runs
that verifier against a checkout of the authority at the bundle's
revision, and judges currency against the authority's ``main`` by recomputing the same source
and profile digests the verifier recomputes. It produces nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNER_REPOSITORY = "Quantum-L9/.github"
BUNDLE_PATH = Path("generated/governance/coding_agent_execution")
VERIFIER_PATH = Path("skills/l9-coding-agent/scripts/verify_canonical_binding.py")
PROFILES_PATH = "semantics/projection_profiles.yaml"
SOURCES_PATH = "semantics/canonical_sources.yaml"
_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)Quantum-L9/\.github(?:\.git)?/?$"
)
_SHA = re.compile(r"^[0-9a-f]{40}$")


class Rejected(Exception):
    """The bundle, its lock or its authority inputs contradict verification (``BLOCKED``)."""


class Unobserved(Exception):
    """Proof is not available here (``UNVERIFIED``); nothing was contradicted."""


def load_verifier(repo_root: Path = REPO_ROOT) -> ModuleType:
    path = repo_root / VERIFIER_PATH
    spec = importlib.util.spec_from_file_location("coding_agent_verify_canonical_binding", path)
    if spec is None or spec.loader is None:
        raise Unobserved(f"verifier not importable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
        timeout=30,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
    )


def resolve(root: Path, ref: str) -> str | None:
    out = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    sha = out.stdout.decode("ascii", "replace").strip()
    return sha if out.returncode == 0 and _SHA.match(sha) else None


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def blob_at(root: Path, commit: str, path: str) -> bytes | None:
    out = _git(root, "cat-file", "blob", f"{commit}:{path}")
    return out.stdout if out.returncode == 0 else None


def verify_authority(root: Path) -> None:
    """A checkout is observed only when it is a repository whose origin is the canonical owner."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.decode().strip()).resolve() != root.resolve():
        raise Unobserved(f"{root} is not the top of a git checkout")
    url = _git(root, "remote", "get-url", "origin")
    origin = url.stdout.decode().strip()
    if url.returncode != 0 or not _ORIGIN.fullmatch(origin):
        raise Unobserved(f"{root} origin is not {OWNER_REPOSITORY}: {origin or 'none'}")


def read_lock(bundle: Path) -> dict[str, Any]:
    try:
        lock = json.loads((bundle / "bundle.lock.json").read_text(encoding="utf-8"))
    except OSError as exc:
        raise Unobserved(f"no bundle at {bundle}: {exc}") from exc
    except ValueError as exc:
        raise Rejected(f"bundle.lock.json malformed: {exc}") from exc
    revision = (lock.get("authority") or {}).get("revision")
    if not isinstance(revision, str) or not _SHA.match(revision):
        raise Rejected("bundle.lock.json names no 40-hex authority revision")
    return lock


def pinned_checkout(root: Path, revision: str) -> tempfile.TemporaryDirectory[str]:
    """A disposable checkout of *root* at *revision*, sharing its objects, origin set to the owner.

    The verifier requires HEAD to be the pin and reads law from commit objects; a session's
    own authority clone sits on whatever branch its operator is on, so the pin is checked out
    beside it, never in it. The object store is shared, so no bytes are copied.
    """
    holder = tempfile.TemporaryDirectory(prefix="l9-coding-projection-")
    target = Path(holder.name) / "authority"
    steps = (
        ["clone", "-q", "--shared", "--no-checkout", str(root), str(target)],
        [
            "-C",
            str(target),
            "remote",
            "set-url",
            "origin",
            f"https://github.com/{OWNER_REPOSITORY}",
        ],
        [
            "-C",
            str(target),
            "fetch",
            "-q",
            str(root),
            "+refs/remotes/origin/*:refs/remotes/origin/*",
        ],
        ["-C", str(target), "checkout", "-q", "--detach", revision],
    )
    for step in steps:
        out = subprocess.run(["git", *step], capture_output=True, check=False, timeout=60)
        if out.returncode != 0:
            holder.cleanup()
            raise Unobserved(
                f"could not check out the bundle revision beside {root}: "
                f"{out.stderr.decode('utf-8', 'replace').strip()}"
            )
    return holder


def verify_bundle(
    root: Path, bundle: Path, revision: str, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Run the coding agent's own verifier in bundle mode; return its record.

    ``REJECTED`` and ``STALE`` are contradictions (``Rejected``); ``BLOCKED`` is Unknown
    (``Unobserved``). The verifier's record is returned unchanged on ``BOUND``.
    """
    verifier = load_verifier(repo_root)
    args = verifier.argparse.Namespace(
        authority_root=str(root),
        artifact=None,
        receipt=None,
        bundle=str(bundle),
        expect_revision=revision,
        require_invariant=None,
        prior_binding=None,
    )
    try:
        return verifier.verify_bundle(args)
    except verifier.Outcome as outcome:
        detail = f"{outcome.status} {outcome.reason}"
        if outcome.status == "BLOCKED":
            raise Unobserved(detail) from outcome
        raise Rejected(detail) from outcome


def _canonical_digest(value: Any) -> str:
    def normalize(v: Any) -> Any:
        if isinstance(v, dict):
            return {str(k): normalize(v[k]) for k in sorted(v, key=str)}
        if isinstance(v, (list, tuple)):
            return [normalize(x) for x in v]
        return v

    raw = json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def material_change(root: Path, main: str, lock: dict[str, Any]) -> list[str]:
    """Source classes, or ``profile``, whose bytes at *main* differ from the bundle's pins."""
    registry_raw = blob_at(root, main, SOURCES_PATH)
    catalog_raw = blob_at(root, main, PROFILES_PATH)
    if registry_raw is None or catalog_raw is None:
        raise Rejected(f"the authority at {main[:12]} no longer carries its registry or catalog")
    paths = {
        str(s.get("id")): str(s.get("path"))
        for s in (yaml.safe_load(registry_raw) or {}).get("sources", [])
        if isinstance(s, dict)
    }
    changed: list[str] = []
    for component in lock.get("components") or []:
        path = paths.get(str(component.get("source_ref")))
        current = blob_at(root, main, path) if path else None
        if current is None:
            changed.append(str(component.get("source_class")))
            continue
        if "sha256:" + hashlib.sha256(current).hexdigest() != component.get("source_digest"):
            changed.append(str(component.get("source_class")))
    pin = lock.get("projection_profile") or {}
    entries = [
        p
        for p in (yaml.safe_load(catalog_raw) or {}).get("projection_profiles", [])
        if isinstance(p, dict) and p.get("id") == pin.get("ref")
    ]
    if len(entries) != 1 or _canonical_digest(entries[0]) != pin.get("digest"):
        changed.append("profile")
    return changed
