#!/usr/bin/env python3
# pyright: strict
"""Fail closed when a projection binding no longer matches its target or its contract.

For every binding instance under ``projection_binding_generation.output_root`` (or the files
given), recompute from the working tree and compare:

* PROJECTION-001 -- the binding pins an exact ``contract_version`` and ``contract_digest``;
  both must equal the contract's current version and freshly computed digest, and the
  registry's entry for it.
* PROJECTION-002 -- ``ownership`` keeps the contract as normative owner, and the target is not
  a semantic owner declared by the pack manifest.
* PROJECTION-003 / 006 -- a manually maintained projection names this executable validator; a
  generated one names an existing generator.
* PROJECTION-004 -- ``drift_policy`` is ``fail_closed`` and any difference below exits non-zero.
* PROJECTION-005 -- every ``clause_refs`` id exists in the pinned contract's normative clauses.
* ``reference_only`` parity -- the target names the contract's path and contains every anchor
  its ``projection_targets`` entry declares, and its sha256 equals
  ``projected_content_sha256``.

Also validates each instance against ``canonical.schema.contract_projection_binding.v1`` and
reports bindings with no declared target, or declared targets with no binding, as drift.

Parity is structural. That the target restates no clause semantics is semantic review
(GOV-CONTRACT-006), which this validator does not claim.

Exit codes: 0 CURRENT, 1 DRIFT, 3 BLOCKED.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

_GEN = Path(__file__).resolve().parent / "governance_generation.py"
SELF_REF = "tools/authority/validate_projection_parity.py"


def _lib() -> Any:
    import importlib.util
    import sys

    key = "authority_governance_generation"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, _GEN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{_GEN} is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


gen = _lib()


def target_specs(ctx: Any) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for spec in gen.as_maps(ctx.binding.get("projection_targets")):
        binding_id = str(spec.get("binding_id"))
        if binding_id in specs:
            raise gen.GenerationRefused(f"projection target {binding_id} is declared twice")
        specs[binding_id] = spec
    return specs


def problems(
    ctx: Any,
    instance: dict[str, Any],
    spec: dict[str, Any],
    source: Any,
    registry_entry: dict[str, Any] | None,
) -> list[str]:
    """Every parity difference between *instance* and the current tree; empty means CURRENT."""
    found: list[str] = []
    binding = gen.as_map(instance.get("binding"))
    target = gen.as_map(instance.get("target"))
    generation = gen.as_map(instance.get("generation"))
    integrity = gen.as_map(instance.get("integrity"))
    ownership = gen.as_map(instance.get("ownership"))
    document = cast(dict[str, Any], source.document)
    metadata = gen.as_map(document.get("metadata"))

    # PROJECTION-001: exact version-pinned contract, current and registered
    if binding.get("contract_id") != metadata.get("contract_id"):
        found.append(f"PROJECTION-001 contract_id {binding.get('contract_id')} is not the source's")
    if binding.get("contract_version") != metadata.get("version"):
        found.append(
            f"PROJECTION-001 pinned version {binding.get('contract_version')} != "
            f"current {metadata.get('version')}"
        )
    if binding.get("contract_digest") != source.digest:
        found.append(
            f"PROJECTION-001 pinned digest {binding.get('contract_digest')} != "
            f"current {source.digest}"
        )
    if registry_entry is None:
        found.append(f"PROJECTION-001 {binding.get('contract_id')} is not in the registry")
    else:
        for key, pinned in (("version", "contract_version"), ("digest", "contract_digest")):
            if registry_entry.get(key) != binding.get(pinned):
                found.append(f"PROJECTION-001 registry {key} != binding {pinned}")
        if binding.get("binding_id") not in gen.as_list(
            registry_entry.get("projection_binding_refs")
        ):
            found.append("PROJECTION-001 registry entry does not reference this binding")

    # PROJECTION-002: the target never becomes a normative owner
    if (
        ownership.get("normative_owner") != "contract"
        or ownership.get("target_may_redefine_semantics") is not False
    ):
        found.append("PROJECTION-002 ownership does not keep the contract as normative owner")
    target_rel = str(target.get("path"))
    if target_rel in ctx.manifest_semantic_owner_paths():
        found.append(f"PROJECTION-002 target {target_rel} is a declared semantic owner")

    # PROJECTION-003 / 006: executable parity or an explicit generator
    mode = generation.get("mode")
    if mode == "manually_maintained_with_parity_check":
        ref = str(generation.get("parity_validator_ref") or "")
        if ref != SELF_REF or not (ctx.root / ref).is_file():
            found.append(f"PROJECTION-003 parity_validator_ref {ref!r} is not {SELF_REF}")
    elif mode == "generated":
        ref = generation.get("generator_ref")
        if not ref or not (ctx.root / str(ref)).is_file():
            found.append(f"PROJECTION-006 generator_ref {ref!r} does not resolve")
    else:
        found.append(f"PROJECTION-003 unknown generation mode {mode!r}")

    # PROJECTION-004
    if integrity.get("drift_policy") != "fail_closed":
        found.append("PROJECTION-004 drift_policy is not fail_closed")

    # PROJECTION-005: projected clauses exist in the pinned contract version
    clause_ids = {str(c.get("clause_id")) for c in gen.as_maps(document.get("normative_clauses"))}
    for clause in gen.as_list(binding.get("clause_refs")):
        if str(clause) not in clause_ids:
            found.append(f"PROJECTION-005 clause {clause} is not in {source.rel}")

    # declared target and reference_only parity
    declared = gen.as_map(spec.get("target"))
    expected = {
        "type": declared.get("type"),
        "path": ctx.repo_rel(str(declared.get("path"))),
        "projection_mode": declared.get("projection_mode"),
    }
    if target != expected:
        found.append(f"target {target} is not the declared {expected}")
    declared_clauses = [str(c) for c in gen.as_map(spec.get("clause_anchors"))]
    if [str(c) for c in gen.as_list(binding.get("clause_refs"))] != declared_clauses:
        found.append("clause_refs are not the declared clause_anchors")
    if not (ctx.root / target_rel).is_file():
        found.append(f"target {target_rel} is absent")
        return found
    content = ctx.read(target_rel)
    text = content.decode("utf-8", errors="replace")
    reference = str(spec.get("contract_reference") or "")
    if declared.get("projection_mode") == "reference_only":
        if not reference or reference not in text:
            found.append(f"reference_only target does not name {reference!r}")
        for clause, anchors in gen.as_map(spec.get("clause_anchors")).items():
            for anchor in gen.as_list(anchors):
                if str(anchor) not in text:
                    found.append(f"anchor for {clause} absent from target: {anchor!r}")
    actual = gen.canonical.bytes_digest(content)
    if integrity.get("projected_content_sha256") != actual:
        found.append(
            f"projected_content_sha256 {integrity.get('projected_content_sha256')} != "
            f"target sha256 {actual}"
        )
    return found


def validate_tree(ctx: Any, files: Sequence[Path] | None = None) -> dict[str, Any]:
    """Validate committed binding instances against the current tree."""
    validator = gen.sibling("validate_canonical_contract")
    disposition = validator.Disposition.from_binding(ctx.binding)
    schema_root = ctx.root / str(ctx.section("schema_resolution").get("schema_root"))
    schema_ref = str(ctx.section("projection_binding_generation").get("schema_ref"))
    registry_rel = str(ctx.section("contract_registry_output").get("path"))
    output_root = ctx.root / str(ctx.section("projection_binding_generation").get("output_root"))

    registry_path = ctx.root / registry_rel
    if not registry_path.is_file():
        raise gen.GenerationBlocked(f"{registry_rel} is absent; run `make contract-registry`")
    registry = gen.as_map(gen.canonical.load_yaml(registry_path.read_text(encoding="utf-8")))
    entries = {str(e.get("contract_id")): e for e in gen.as_maps(registry.get("contracts"))}
    sources = {
        str(gen.as_map(s.document.get("metadata")).get("contract_id")): s for s in ctx.sources()
    }
    specs = target_specs(ctx)

    paths = sorted(files) if files else sorted(output_root.glob("*.yaml"))
    report: dict[str, Any] = {}
    seen: set[str] = set()
    for path in paths:
        rel = path.resolve().relative_to(ctx.root.resolve()).as_posix()
        instance = gen.as_map(gen.canonical.load_yaml(path.read_text(encoding="utf-8")))
        found: list[str] = []
        result = validator.validate(
            instance, schema_ref, schema_root=schema_root, disposition=disposition
        )
        if result.status == "BLOCKED":
            raise gen.GenerationBlocked(f"{rel}: {result.as_dict()['blocked']}")
        found += [f"SCHEMA {f.rule} {f.path}: {f.message}" for f in result.findings]
        binding_id = str(gen.as_map(instance.get("binding")).get("binding_id"))
        seen.add(binding_id)
        spec = specs.get(binding_id)
        contract_id = str(gen.as_map(instance.get("binding")).get("contract_id"))
        if spec is None:
            found.append(f"binding {binding_id} has no declared projection target")
        elif contract_id not in sources:
            found.append(f"PROJECTION-001 {contract_id} is not a schema-aligned source")
        else:
            found += problems(ctx, instance, spec, sources[contract_id], entries.get(contract_id))
        report[rel] = {
            "binding_id": binding_id,
            "status": "DRIFT" if found else "CURRENT",
            "problems": found,
        }
    if not files:
        for missing in sorted(set(specs) - seen):
            report[f"<declared {missing}>"] = {
                "binding_id": missing,
                "status": "DRIFT",
                "problems": ["declared projection target has no binding instance"],
            }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=gen.REPO_ROOT)
    parser.add_argument("--binding", type=Path, default=gen.DEFAULT_BINDING)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        ctx = gen.Context.load(root, args.binding)
        ctx.verify_tooling(projections=True)
        report = validate_tree(ctx, [p if p.is_absolute() else root / p for p in args.files])
    except gen.GenerationBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, indent=2))
        return 3
    except gen.GenerationRefused as exc:
        print(json.dumps({"status": "DRIFT", "reason": str(exc)}, indent=2))
        return 1
    drift = any(r["status"] != "CURRENT" for r in report.values())
    status = "DRIFT" if drift or not report else "CURRENT"
    if not report:
        report["<none>"] = {"status": "DRIFT", "problems": ["no binding instance found"]}
    print(json.dumps({"status": status, "bindings": report}, indent=2, sort_keys=True))
    return 1 if status == "DRIFT" else 0


if __name__ == "__main__":
    sys.exit(main())
