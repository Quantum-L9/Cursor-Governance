#!/usr/bin/env python3
"""Produce a consumer-committed projection bundle by running the canonical compiler.

One driver for every projection profile Cursor-Governance consumes (Quantum-L9/.github
ADR-021, ``docs/PROJECTION_PUBLICATION.md``). It is a driver, not a compiler: every selector,
digest, composition and receipt comes from ``l9-semantic-compiler`` (``projection-coordinates``,
``project``, and ``compose`` when the profile has a composition profile) run against an exact
``Quantum-L9/.github`` revision. The driver copies the emitted artifacts and receipts under
stable names and writes ``bundle.lock.json`` (``l9.projection-bundle/v1``), which names each
file with its sha256 and binds the authority, profile, composition and producer coordinates.

``--binding`` takes a canonical domain consumer binding
(``semantics/domain_consumer_bindings.yaml``, ADR-033) instead of a profile. It enforces
BINDING-001..004 at the pinned revision, writes one such bundle per required domain under
``<output>/<domain>/`` and a ``binding.lock.json`` (``l9.domain-binding-bundle/v1``) indexing
them. It records conditional domains without materializing them, records cross-domain
composition as not produced, and activates nothing.

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
    "l9.projection/cursor-governance-operating-plane@2": {
        "composition_profile": None,
        "output": Path("generated/governance/operating_plane_v2"),
    },
    "l9.projection/pr-audit@1": {
        "composition_profile": "l9.compose/pr-audit@1",
        "output": Path("generated/governance/pr_audit"),
    },
    # Domain projections (Quantum-L9/.github v3.36.0, ADR-033) bound by architect mode
    # (governance/architect-mode/MODE.yaml).
    "l9.projection/architecture@1": {
        "composition_profile": "l9.compose/architecture@1",
        "output": Path("generated/governance/domain_architecture"),
    },
    "l9.projection/governance@1": {
        "composition_profile": "l9.compose/governance@1",
        "output": Path("generated/governance/domain_governance"),
    },
    "l9.projection/evidence-provenance@1": {
        "composition_profile": "l9.compose/evidence-provenance@1",
        "output": Path("generated/governance/domain_evidence_provenance"),
    },
    "l9.projection/contracts-conformance@1": {
        "composition_profile": "l9.compose/contracts-conformance@1",
        "output": Path("generated/governance/domain_contracts_conformance"),
    },
    "l9.projection/capabilities-dependencies@1": {
        "composition_profile": "l9.compose/capabilities-dependencies@1",
        "output": Path("generated/governance/domain_capabilities_dependencies"),
    },
    "l9.projection/strategic-value@1": {
        "composition_profile": "l9.compose/strategic-value@1",
        "output": Path("generated/governance/domain_strategic_value"),
    },
    # Technical coordination role projection (Quantum-L9/.github v3.39.0, ADR-036) bound by
    # CTO mode (governance/cto-mode/MODE.yaml).
    "l9.projection/technical-coordination@1": {
        "composition_profile": "l9.compose/technical-coordination@1",
        "output": Path("generated/governance/technical_coordination"),
    },
    # Bound by CTO mode only (governance/cto-mode/MODE.yaml).
    "l9.projection/identity-attribution@1": {
        "composition_profile": "l9.compose/identity-attribution@1",
        "output": Path("generated/governance/domain_identity_attribution"),
    },
    "l9.projection/signals@1": {
        "composition_profile": "l9.compose/signals@1",
        "output": Path("generated/governance/domain_signals"),
    },
}

# Canonical domain consumer bindings (Quantum-L9/.github ADR-033) this repository materializes,
# and the directory each binding bundle is committed to. A binding is read from the authority at
# the pinned revision; this map names only where its bundle lives.
BINDING_CATALOG = "semantics/domain_consumer_bindings.yaml"
BINDING_LOCK_SCHEMA = "l9.domain-binding-bundle/v1"
DOMAIN_CLASS = "domain"
BINDINGS: dict[str, dict[str, Any]] = {
    "l9.domain-consumer-binding/coding-agent@1": {
        "output": Path("generated/governance/domain_bindings/coding_agent"),
    },
}
# No producer revision exposes composition of a binding's domain set (the compatibility and
# provenance contracts); .github v3.36.0 records it as an open blocker. The lock says so instead
# of implying a composed view.
CROSS_DOMAIN_COMPOSITION_REASON = (
    "the producer exposes no binding-domain-set composition; "
    "Quantum-L9/.github docs/candidates/domain-projection-architecture-v1 open blocker"
)
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


def domain_directory(profile_ref: str) -> str:
    """``l9.projection/capabilities-dependencies@1`` -> ``capabilities_dependencies``."""
    match = re.fullmatch(r"l9\.projection/([a-z0-9]+(?:-[a-z0-9]+)*)@[0-9]+", profile_ref)
    if match is None:
        raise ProductionError(f"{profile_ref} is not a projection profile ref")
    return match.group(1).replace("-", "_")


def binding_plan(authority_root: Path, revision: str, binding_ref: str) -> dict[str, Any]:
    """Resolve *binding_ref* at *revision* and enforce BINDING-001..004 before producing anything.

    Everything comes from the canonical catalogs at the pinned commit: the binding selects, the
    driver only checks that the selection is well formed and grants nothing.
    """
    catalog = _git_show(authority_root, revision, BINDING_CATALOG) or {}
    entries = [
        b for b in catalog.get("bindings", []) if isinstance(b, dict) and b.get("id") == binding_ref
    ]
    if len(entries) != 1:
        raise ProductionError(f"{binding_ref} is not declared exactly once at {revision}")
    binding = entries[0]
    profiles = (_git_show(authority_root, revision, PROFILE_CATALOG) or {}).get(
        "projection_profiles", []
    )

    def _domain(ref: Any) -> dict[str, Any]:
        matches = [p for p in profiles if isinstance(p, dict) and p.get("id") == ref]
        if len(matches) != 1 or matches[0].get("class") != DOMAIN_CLASS:
            msg = f"BINDING-001: {ref} does not resolve to exactly one domain profile"
            raise ProductionError(msg)
        return matches[0]

    required = binding.get("requires")
    conditional = binding.get("conditional") or []
    if not isinstance(required, list) or not required or not isinstance(conditional, list):
        raise ProductionError(f"{binding_ref} declares no required domain list")
    if len(set(required)) != len(required):
        raise ProductionError(f"BINDING-001: {binding_ref} requires a domain twice")
    activations = set((catalog.get("activation_conditions") or {}).keys())
    conditional_refs = []
    for item in conditional:
        ref = item.get("profile") if isinstance(item, dict) else None
        if ref in required or ref in conditional_refs:
            raise ProductionError(f"BINDING-002: {ref} is both required and conditional")
        if item.get("activation") not in activations:
            raise ProductionError(f"BINDING-002: {ref} names an undeclared activation condition")
        conditional_refs.append(ref)
    pinned = {str(ref): _canonical_digest(_domain(ref)) for ref in required}
    for ref in conditional_refs:
        _domain(ref)
    consumer = binding.get("consumer") or {}
    kind = (catalog.get("consumer_kinds") or {}).get(consumer.get("kind"))
    if not isinstance(kind, dict):
        raise ProductionError(f"BINDING-003: {binding_ref} names an undeclared consumer kind")
    if any(consumer.get(k) in (None, "", []) for k in kind.get("requires") or []) or any(
        k in consumer for k in kind.get("forbids") or []
    ):
        raise ProductionError(f"BINDING-003: {binding_ref} consumer identity has the wrong shape")
    authority = binding.get("authority") or {}
    if authority.get("binding_grants_permissions") is not False or (
        authority.get("action_authority") != "externally_resolved"
    ):
        raise ProductionError(f"BINDING-004: {binding_ref} is not authority-neutral")
    return {
        "binding": {"ref": binding_ref, "digest": _canonical_digest(binding)},
        "consumer": {"kind": consumer.get("kind"), "identity": consumer.get("identity")},
        "required": [{"ref": str(ref), "digest": pinned[str(ref)]} for ref in required],
        "conditional": [
            {"ref": str(item["profile"]), "activation": str(item["activation"])}
            for item in conditional
        ],
        "unresolved": [
            {"coordinate": str(u.get("coordinate")), "blocks": str(u.get("blocks"))}
            for u in binding.get("unresolved") or []
            if isinstance(u, dict)
        ],
        "composition": catalog.get("composition") or {},
    }


def produce_binding(
    *,
    compiler: list[str],
    authority_root: Path,
    revision: str,
    compiler_revision: str,
    binding_ref: str,
    output: Path,
) -> None:
    """One per-domain bundle for every required domain of *binding_ref*, plus binding.lock.json.

    Each domain bundle is exactly what ``produce`` writes for that profile (no per-domain
    composition). Conditional domains are recorded, never materialized. The binding lock indexes
    the domain locks by digest; it composes nothing and activates nothing.
    """
    if not _SHA.match(revision) or not _SHA.match(compiler_revision):
        raise ProductionError("--authority-revision and --compiler-revision are full 40-hex SHAs")
    if _git_head(authority_root) != revision:
        raise ProductionError(f"authority checkout HEAD is not {revision}")
    plan = binding_plan(authority_root, revision, binding_ref)
    output.mkdir(parents=True)
    domains: list[dict[str, Any]] = []
    producer: dict[str, Any] | None = None
    for domain in plan["required"]:
        directory = domain_directory(domain["ref"])
        produce(
            compiler=compiler,
            authority_root=authority_root,
            revision=revision,
            compiler_revision=compiler_revision,
            profile_ref=domain["ref"],
            composition_ref=None,
            output=output / directory,
        )
        lock_path = output / directory / "bundle.lock.json"
        lock = json.loads(lock_path.read_text())
        if lock["projection_profile"] != domain:
            raise ProductionError(f"the compiler bound {domain['ref']} to another profile digest")
        if producer is not None and lock["producer"] != producer:
            raise ProductionError("the domain bundles were cut by different producers")
        producer = lock["producer"]
        domains.append(
            {
                "profile": domain,
                "path": directory,
                "lock": f"{directory}/bundle.lock.json",
                "lock_sha256": _sha256(lock_path),
            }
        )
    blocked_by = [u["coordinate"] for u in plan["unresolved"]] + ["cross_domain_composition"]
    binding_lock: dict[str, Any] = {
        "schema": BINDING_LOCK_SCHEMA,
        "authority": {"repository": REPOSITORY, "revision": revision},
        "producer": producer,
        "generated_by": GENERATED_BY,
        "binding": plan["binding"],
        "consumer": plan["consumer"],
        "domains": domains,
        "conditional": plan["conditional"],
        "unresolved": plan["unresolved"],
        "cross_domain_composition": {
            "status": "not_produced",
            "compatibility_contract": plan["composition"].get("compatibility_contract"),
            "provenance_contract": plan["composition"].get("provenance_contract"),
            "reason": CROSS_DOMAIN_COMPOSITION_REASON,
        },
        "activation": {"status": "blocked", "blocked_by": blocked_by},
    }
    (output / "binding.lock.json").write_text(
        json.dumps(binding_lock, indent=2, sort_keys=True) + "\n"
    )


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
    subject = parser.add_mutually_exclusive_group(required=True)
    subject.add_argument("--profile", choices=sorted(BUNDLES), help="projection profile ref")
    subject.add_argument(
        "--binding",
        choices=sorted(BINDINGS),
        help="canonical domain consumer binding ref: one bundle per required domain",
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
    if args.binding is not None and args.composition_profile is not None:
        parser.error("--composition-profile applies to --profile only")
    label = args.profile or args.binding
    declared = BUNDLES[args.profile] if args.profile else BINDINGS[args.binding]
    output: Path = args.output if args.output is not None else declared["output"]
    compiler = shlex.split(args.compiler)
    try:
        with tempfile.TemporaryDirectory() as scratch_name:
            fresh = Path(scratch_name) / "bundle"
            if args.binding is not None:
                produce_binding(
                    compiler=compiler,
                    authority_root=args.authority_root.resolve(),
                    revision=args.authority_revision,
                    compiler_revision=args.compiler_revision,
                    binding_ref=args.binding,
                    output=fresh,
                )
            else:
                composition_ref = (
                    declared["composition_profile"]
                    if args.composition_profile is None
                    else (None if args.composition_profile == "none" else args.composition_profile)
                )
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
                        f"stale projection bundle {label}:",
                        *drift,
                        sep="\n  ",
                        file=sys.stderr,
                    )
                    return 1
                print(f"projection bundle {label} is current at {args.authority_revision}")
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
