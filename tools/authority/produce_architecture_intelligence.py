#!/usr/bin/env python3
"""Produce GAR's architecture-intelligence bundle by running the canonical compiler.

This tool is a driver, not a compiler: every selector, every digest, every composition and
every receipt comes from ``l9-semantic-compiler`` (``projection-coordinates``, ``project``,
``compose``) run against an exact ``Quantum-L9/.github`` revision. The tool copies the emitted
artifacts and receipts under stable names and writes ``bundle.lock.json``, which names each
file with its sha256 and binds the authority, profile, composition and producer coordinates.

``--check`` regenerates into a temporary directory and fails when any committed byte differs.
GAR verifies the committed bundle with
``skills/l9-global-architect/scripts/verify_architecture_intelligence.py``.
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
PROJECTION_PROFILE = "l9.projection/architecture-intelligence@1"
COMPOSITION_PROFILE = "l9.compose/architecture-intelligence@1"
LOCK_SCHEMA = "l9.gar.architecture-intelligence-bundle/v1"
DEFAULT_OUTPUT = Path("generated/governance/architecture_intelligence")
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


def _git_head(root: Path) -> str:
    return _run(["git", "-C", str(root), "rev-parse", "HEAD"]).strip()


def produce(
    *,
    compiler: list[str],
    authority_root: Path,
    revision: str,
    compiler_revision: str,
    output: Path,
) -> None:
    """Run the compiler at *revision* and write the bundle into *output* (which must not exist)."""
    if not _SHA.match(revision) or not _SHA.match(compiler_revision):
        raise ProductionError("--authority-revision and --compiler-revision are full 40-hex SHAs")
    if _git_head(authority_root) != revision:
        raise ProductionError(f"authority checkout HEAD is not {revision}")
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
                    PROJECTION_PROFILE,
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
        composition_pin = _composition_pin(authority_root, revision)
        components = [a["path"] for a in projected["artifacts"]]
        compose_request = scratch / "compose.yaml"
        compose_request.write_text(
            yaml.safe_dump(
                {
                    "schema": "l9.semantic-composition-request/v1",
                    "authority": authority,
                    "composition_profile": composition_pin,
                    "components": components,
                    "output_root": str(scratch / "out"),
                }
            )
        )
        composed = yaml.safe_load(_run([*compiler, "compose", str(compose_request)]))
        _assemble(
            projected=projected,
            composed=composed,
            coordinates=coordinates,
            composition_pin=composition_pin,
            revision=revision,
            compiler_revision=compiler_revision,
            output=output,
        )


def _composition_pin(authority_root: Path, revision: str) -> dict[str, str]:
    """The composition profile's exact ref and digest at *revision*.

    The digest is the producer's published convention (sha256 of the entry as canonical JSON);
    the compiler re-derives it and refuses a composition whose pin differs.
    """
    raw = _run(
        [
            "git",
            "-C",
            str(authority_root),
            "show",
            f"{revision}:semantics/composition_profiles.yaml",
        ]
    )
    entries = [p for p in yaml.safe_load(raw)["profiles"] if p.get("id") == COMPOSITION_PROFILE]
    if len(entries) != 1:
        raise ProductionError(f"{COMPOSITION_PROFILE} is not declared exactly once")
    encoded = json.dumps(
        entries[0], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {"ref": COMPOSITION_PROFILE, "digest": "sha256:" + hashlib.sha256(encoded).hexdigest()}


def _assemble(
    *,
    projected: dict[str, Any],
    composed: dict[str, Any],
    coordinates: dict[str, Any],
    composition_pin: dict[str, str],
    revision: str,
    compiler_revision: str,
    output: Path,
) -> None:
    if projected.get("result") != "pass" or composed.get("result") != "pass":
        raise ProductionError(
            "the compiler did not return PASS: "
            f"project={projected.get('result')} compose={composed.get('result')}"
        )
    (output / "projections").mkdir(parents=True)
    (output / "receipts").mkdir()
    composed_artifact = composed["artifacts"][0]
    composed_document = json.loads(Path(composed_artifact["path"]).read_text())
    classes = {c["source_ref"]: c["source_class"] for c in composed_document["components"]}
    entries = []
    for artifact in projected["artifacts"]:
        document = json.loads(Path(artifact["path"]).read_text())
        cls = classes[document["source_ref"]]
        path = Path("projections") / f"{cls}.projection.json"
        receipt = Path("receipts") / f"{cls}.receipt.json"
        shutil.copyfile(artifact["path"], output / path)
        shutil.copyfile(artifact["receipt_path"], output / receipt)
        entries.append(
            {
                "source_class": cls,
                "source_ref": document["source_ref"],
                "source_digest": document["source_digest"],
                "projection_digest": document["projection_digest"],
                "path": str(path),
                "sha256": _sha256(output / path),
                "receipt": str(receipt),
            }
        )
    order = [c["source_class"] for c in composed_document["components"]]
    entries.sort(key=lambda e: order.index(e["source_class"]))
    shutil.copyfile(composed_artifact["path"], output / "composed.json")
    shutil.copyfile(composed_artifact["receipt_path"], output / "receipts/composed.receipt.json")
    receipt = json.loads((output / "receipts/composed.receipt.json").read_text())
    lock = {
        "schema": LOCK_SCHEMA,
        "authority": {"repository": REPOSITORY, "revision": revision},
        "producer": {
            "compiler": receipt["producer_identity"]["compiler"],
            "version": receipt["producer_identity"]["version"],
            "repository": "Quantum-L9/l9-semantic-compiler-engine",
            "revision": compiler_revision,
            "revision_basis": "caller_asserted",
        },
        "generated_by": "tools/authority/produce_architecture_intelligence.py",
        "projection_profile": coordinates["projection_profile"],
        "composition_profile": composition_pin,
        "components": entries,
        "composed": {
            "path": "composed.json",
            "sha256": _sha256(output / "composed.json"),
            "composition_digest": composed_document["composition_digest"],
            "receipt": "receipts/composed.receipt.json",
        },
    }
    (output / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce GAR's architecture-intelligence bundle.")
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--authority-revision", required=True)
    parser.add_argument("--compiler-revision", required=True)
    parser.add_argument(
        "--compiler",
        default="l9-semantic-compiler",
        help="compiler command line, e.g. 'python3 -m l9_semantic_compiler'",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    compiler = shlex.split(args.compiler)
    try:
        with tempfile.TemporaryDirectory() as scratch_name:
            fresh = Path(scratch_name) / "bundle"
            produce(
                compiler=compiler,
                authority_root=args.authority_root.resolve(),
                revision=args.authority_revision,
                compiler_revision=args.compiler_revision,
                output=fresh,
            )
            if args.check:
                committed = _tree(args.output) if args.output.is_dir() else {}
                regenerated = _tree(fresh)
                drift = sorted(
                    name
                    for name in set(committed) | set(regenerated)
                    if committed.get(name) != regenerated.get(name)
                )
                if drift:
                    print(
                        "stale architecture-intelligence bundle:",
                        *drift,
                        sep="\n  ",
                        file=sys.stderr,
                    )
                    return 1
                print(f"architecture-intelligence bundle is current at {args.authority_revision}")
                return 0
            if args.output.exists():
                shutil.rmtree(args.output)
            shutil.copytree(fresh, args.output)
            print(f"wrote {args.output}")
            return 0
    except ProductionError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
