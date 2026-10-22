#!/usr/bin/env python3
"""Produce a consumer-committed projection bundle by running the canonical compiler.

One driver for every projection profile Cursor-Governance consumes (Quantum-L9/.github
ADR-021, ``docs/PROJECTION_PUBLICATION.md``). It is a driver, not a compiler: every selector,
digest, composition and receipt comes from ``l9-semantic-compiler`` (``projection-coordinates``,
``project``, and ``compose`` when the profile has a composition profile) run against an exact
``Quantum-L9/.github`` revision. The driver copies the emitted artifacts and receipts under
stable names and writes ``bundle.lock.json`` (``l9.projection-bundle/v1``), which names each
file with its sha256 and binds the authority, profile, composition and producer coordinates.

``--check`` regenerates into a temporary directory and fails when any committed byte differs.
Consumers verify the committed bundle with their own skill verifier:
``skills/l9-global-architect/scripts/verify_architecture_intelligence.py`` and
``skills/l9-coding-agent/scripts/verify_canonical_binding.py --bundle``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPOSITORY = "Quantum-L9/.github"
PRODUCER_REPOSITORY = "Quantum-L9/l9-semantic-compiler-engine"
LOCK_SCHEMA = "l9.projection-bundle/v1"
GENERATED_BY = "tools/authority/produce_projection_bundle.py"
PROFILE_CATALOG = "semantics/projection_profiles.yaml"
COMPOSITION_CATALOG = "semantics/composition_profiles.yaml"
SOURCE_REGISTRY = "semantics/canonical_sources.yaml"
# The profiles this repository consumes, with the composition profile each declares upstream
# (None when the profile is consumed per source) and the directory its bundle is committed to.
BUNDLES: dict[str, dict[str, Any]] = {
    "l9.projection/architecture-intelligence@1": {
        "composition_profile": "l9.compose/architecture-intelligence@1",
        "output": Path("generated/governance/architecture_intelligence"),
    },
    "l9.projection/coding-agent-execution@1": {
        "composition_profile": None,
        "output": Path("generated/governance/coding_agent_execution"),
    },
    "l9.projection/pr-audit@1": {
        "composition_profile": "l9.compose/pr-audit@1",
        "output": Path("generated/governance/pr_audit"),
    },
}
_SHA = re.compile(r"^[0-9a-f]{40}$")


class ProductionError(RuntimeError):
    pass


def _run(command: list[str], *, ok: tuple[int, ...] = (0,)) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode not in ok:
        raise ProductionError(
            f"{shlex.join(command)} exited {completed.returncode}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(value: Any) -> str:
    """The producer's semantic_digest (projection_engine_contract binding_conventions)."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _git_head(root: Path) -> str:
    return _run(["git", "-C", str(root), "rev-parse", "HEAD"]).strip()


def _git_show(root: Path, revision: str, path: str) -> Any:
    return yaml.safe_load(_run(["git", "-C", str(root), "show", f"{revision}:{path}"]))


def source_classes(authority_root: Path, revision: str, profile_ref: str) -> list[tuple[str, str]]:
    """``(source_class, source_ref)`` in the order the canonical profile declares its sources.

    Read from the commit objects at *revision*, never from a working tree: the profile's
    ``sources`` keys name classes, the catalog's ``source_classes`` map each class to its
    canonical artifact file, and the source registry maps that file back to its ref.
    """
    catalog = _git_show(authority_root, revision, PROFILE_CATALOG) or {}
    profiles = [
        p
        for p in catalog.get("projection_profiles", [])
        if isinstance(p, dict) and p.get("id") == profile_ref
    ]
    if len(profiles) != 1:
        raise ProductionError(f"{profile_ref} is not declared exactly once at {revision}")
    registry = _git_show(authority_root, revision, SOURCE_REGISTRY) or {}
    by_file = {
        Path(str(s.get("path"))).name: str(s.get("id"))
        for s in registry.get("sources", [])
        if isinstance(s, dict) and s.get("path") and s.get("id")
    }
    classes = catalog.get("source_classes") or {}
    ordered: list[tuple[str, str]] = []
    for cls in profiles[0].get("sources") or {}:
        artifact = (classes.get(cls) or {}).get("canonical_artifact")
        ref = by_file.get(str(artifact))
        if ref is None:
            raise ProductionError(f"source class {cls} of {profile_ref} has no registered source")
        ordered.append((str(cls), ref))
    if not ordered:
        raise ProductionError(f"{profile_ref} declares no sources")
    return ordered


def composition_pin(authority_root: Path, revision: str, composition_ref: str) -> dict[str, str]:
    """The composition profile's exact ref and canonical digest at *revision*."""
    catalog = _git_show(authority_root, revision, COMPOSITION_CATALOG) or {}
    entries = [
        p
        for p in catalog.get("profiles", [])
        if isinstance(p, dict) and p.get("id") == composition_ref
    ]
    if len(entries) != 1:
        raise ProductionError(f"{composition_ref} is not declared exactly once at {revision}")
    return {"ref": composition_ref, "digest": _canonical_digest(entries[0])}


def produce(
    *,
    compiler: list[str],
    authority_root: Path,
    revision: str,
    compiler_revision: str,
    profile_ref: str,
    composition_ref: str | None,
    output: Path,
) -> None:
    """Run the compiler at *revision* and write the bundle into *output* (which must not exist)."""
    if not _SHA.match(revision) or not _SHA.match(compiler_revision):
        raise ProductionError("--authority-revision and --compiler-revision are full 40-hex SHAs")
    if _git_head(authority_root) != revision:
        raise ProductionError(f"authority checkout HEAD is not {revision}")
    classes = source_classes(authority_root, revision, profile_ref)
    with tempfile.TemporaryDirectory() as scratch_name:
        scratch = Path(scratch_name)
        coordinates = yaml.safe_load(
            _run(
                [
                    *compiler,
                    "projection-coordinates",
                    "--authority-root",
                    str(authority_root),
                    "--revision",
                    revision,
                    "--repository",
                    REPOSITORY,
                    "--profile",
                    profile_ref,
                ]
            )
        )
        authority = {"repository": REPOSITORY, "root": str(authority_root), "revision": revision}
        request = scratch / "project.yaml"
        request.write_text(
            yaml.safe_dump(
                {
                    "schema": "l9.semantic-projection-request/v1",
                    "authority": authority,
                    "projection_profile": coordinates["projection_profile"],
                    "sources": coordinates["sources"],
                    "output_root": str(scratch / "out"),
                }
            )
        )
        projected = yaml.safe_load(_run([*compiler, "project", str(request)]))
        composed: dict[str, Any] | None = None
        pin: dict[str, str] | None = None
        if composition_ref is not None:
            pin = composition_pin(authority_root, revision, composition_ref)
            compose_request = scratch / "compose.yaml"
            compose_request.write_text(
                yaml.safe_dump(
                    {
                        "schema": "l9.semantic-composition-request/v1",
                        "authority": authority,
                        "composition_profile": pin,
                        "components": [a["path"] for a in projected["artifacts"]],
                        "output_root": str(scratch / "out"),
                    }
                )
            )
            composed = yaml.safe_load(_run([*compiler, "compose", str(compose_request)]))
        _assemble(
            projected=projected,
            composed=composed,
            coordinates=coordinates,
            composition=pin,
            classes=classes,
            revision=revision,
            compiler_revision=compiler_revision,
            output=output,
        )


def _assemble(
    *,
    projected: dict[str, Any],
    composed: dict[str, Any] | None,
    coordinates: dict[str, Any],
    composition: dict[str, str] | None,
    classes: list[tuple[str, str]],
    revision: str,
    compiler_revision: str,
    output: Path,
) -> None:
    if projected.get("result") != "pass" or (
        composed is not None and composed.get("result") != "pass"
    ):
        raise ProductionError(
            "the compiler did not return PASS: "
            f"project={projected.get('result')}"
            + (f" compose={composed.get('result')}" if composed is not None else "")
        )
    (output / "projections").mkdir(parents=True)
    (output / "receipts").mkdir()
    class_of = {ref: cls for cls, ref in classes}
    order = [cls for cls, _ in classes]
    entries = []
    producer: dict[str, Any] | None = None
    for artifact in projected["artifacts"]:
        document = json.loads(Path(artifact["path"]).read_text())
        cls = class_of.get(document["source_ref"])
        if cls is None:
            raise ProductionError(
                f"the compiler emitted an undeclared source {document['source_ref']}"
            )
        path = Path("projections") / f"{cls}.projection.json"
        receipt_path = Path("receipts") / f"{cls}.receipt.json"
        shutil.copyfile(artifact["path"], output / path)
        shutil.copyfile(artifact["receipt_path"], output / receipt_path)
        receipt = json.loads((output / receipt_path).read_text())
        producer = producer or receipt["producer_identity"]
        entries.append(
            {
                "source_class": cls,
                "source_ref": document["source_ref"],
                "source_digest": document["source_digest"],
                "projection_digest": document["projection_digest"],
                "path": str(path),
                "sha256": _sha256(output / path),
                "receipt": str(receipt_path),
            }
        )
    if sorted(e["source_class"] for e in entries) != sorted(order):
        raise ProductionError("the compiler did not emit exactly the profile's declared sources")
    entries.sort(key=lambda e: order.index(e["source_class"]))
    if producer is None:
        raise ProductionError("the compiler emitted no artifact")
    lock: dict[str, Any] = {
        "schema": LOCK_SCHEMA,
        "authority": {"repository": REPOSITORY, "revision": revision},
        "producer": {
            "compiler": producer["compiler"],
            "version": producer["version"],
            "repository": PRODUCER_REPOSITORY,
            "revision": compiler_revision,
            "revision_basis": "caller_asserted",
        },
        "generated_by": GENERATED_BY,
        "projection_profile": coordinates["projection_profile"],
        "components": entries,
    }
    if composed is not None and composition is not None:
        composed_artifact = composed["artifacts"][0]
        composed_document = json.loads(Path(composed_artifact["path"]).read_text())
        declared = [(c["source_class"], c["source_ref"]) for c in composed_document["components"]]
        if declared != classes:
            raise ProductionError(
                "the composed component list is not the profile's declared sources"
            )
        shutil.copyfile(composed_artifact["path"], output / "composed.json")
        shutil.copyfile(
            composed_artifact["receipt_path"], output / "receipts/composed.receipt.json"
        )
        lock["composition_profile"] = composition
        lock["composed"] = {
            "path": "composed.json",
            "sha256": _sha256(output / "composed.json"),
            "composition_digest": composed_document["composition_digest"],
            "receipt": "receipts/composed.receipt.json",
        }
    (output / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce a consumer-committed projection bundle.")
    parser.add_argument(
        "--profile", required=True, choices=sorted(BUNDLES), help="projection profile ref"
    )
    parser.add_argument(
        "--composition-profile",
        default=None,
        help="composition profile ref; defaults to the one declared for --profile (none to skip)",
    )
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--authority-revision", required=True)
    parser.add_argument("--compiler-revision", required=True)
    parser.add_argument(
        "--compiler",
        default="l9-semantic-compiler",
        help="compiler command line, e.g. 'python3 -m l9_semantic_compiler'",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="defaults to the profile's bundle directory"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    declared = BUNDLES[args.profile]
    composition_ref = (
        declared["composition_profile"]
        if args.composition_profile is None
        else (None if args.composition_profile == "none" else args.composition_profile)
    )
    output: Path = args.output if args.output is not None else declared["output"]
    compiler = shlex.split(args.compiler)
    try:
        with tempfile.TemporaryDirectory() as scratch_name:
            fresh = Path(scratch_name) / "bundle"
            produce(
                compiler=compiler,
                authority_root=args.authority_root.resolve(),
                revision=args.authority_revision,
                compiler_revision=args.compiler_revision,
                profile_ref=args.profile,
                composition_ref=composition_ref,
                output=fresh,
            )
            if args.check:
                committed = _tree(output) if output.is_dir() else {}
                regenerated = _tree(fresh)
                drift = sorted(
                    name
                    for name in set(committed) | set(regenerated)
                    if committed.get(name) != regenerated.get(name)
                )
                if drift:
                    print(
                        f"stale projection bundle {args.profile}:",
                        *drift,
                        sep="\n  ",
                        file=sys.stderr,
                    )
                    return 1
                print(f"projection bundle {args.profile} is current at {args.authority_revision}")
                return 0
            if output.exists():
                shutil.rmtree(output)
            shutil.copytree(fresh, output)
            print(f"wrote {output}")
            return 0
    except ProductionError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
