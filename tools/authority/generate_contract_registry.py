#!/usr/bin/env python3
# pyright: strict
"""Generate ``generated/governance/CONTRACT_REGISTRY.yaml`` and its projection bindings.

Executes ``generation_order`` of a generation binding
(``skills/l9-global-architect/bindings/GOVERNANCE_GENERATION.yaml`` by default):

1. observe the tooling the binding requires, else CAPABILITY_BLOCK;
2. validate every schema-aligned source against its declared schema
   (``validate_canonical_contract.py``);
3. apply the registration gate and digest each source (``canonical_json.py``);
4. resolve every reference (``reference_resolution``) and build the dependency and
   supersession graphs, refusing cycles, unresolved refs and unresolved conflicts;
5. build each declared projection binding against the digests of this run, refusing any that
   fails parity (``validate_projection_parity.py``);
6. validate the registry and the bindings against their own schemas, then write them.

Modes:
  (default)           generate and write; every generation input must be committed at HEAD
  --check             regenerate with the committed metadata and compare bytes (no git history)
  --check-provenance  --check, plus each input's bytes at metadata.source_commit_sha

Rules this tool evaluates because they need the whole registry: GOV-CONTRACT-002 / 007 / 009
and REGISTRY-001..010 (``validation_rule_disposition.delegated``).

Exit codes: 0 written / CURRENT, 1 refused / DRIFT, 3 BLOCKED.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

_GEN = Path(__file__).resolve().parent / "governance_generation.py"
GENERATED_BY = "tools/authority/generate_contract_registry.py"
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_TIERS = {"constitutional", "execution", "domain", "skill_local"}
_INACTIVE = {"deprecated", "retired"}


def _lib() -> Any:
    import importlib.util

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
binding_gen = gen.sibling("generate_projection_binding")
parity = gen.sibling("validate_projection_parity")
validator = gen.sibling("validate_canonical_contract")


def _cycle(edges: dict[str, list[str]]) -> list[str] | None:
    """One cycle in *edges* as a node path, or None. Deterministic: nodes visited sorted."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, [])):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt) :] + [nxt]
            if nxt not in state:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return None

    for node in sorted(edges):
        if node not in state:
            found = visit(node)
            if found:
                return found
    return None


class Built:
    """One deterministic generation: the registry, its bindings, and their inputs."""

    def __init__(
        self, registry: dict[str, Any], bindings: dict[str, dict[str, Any]], inputs: list[str]
    ) -> None:
        self.registry = registry
        self.bindings = bindings
        self.inputs = inputs


def build(ctx: Any, metadata: dict[str, str] | None, prior: dict[str, Any] | None) -> Built:
    """Steps 1-6. *metadata* is None to take it from HEAD; *prior* is the committed registry."""
    specs = parity.target_specs(ctx)
    ctx.verify_tooling(projections=bool(specs))
    disposition = validator.Disposition.from_binding(ctx.binding)
    schema_root = ctx.root / str(ctx.section("schema_resolution").get("schema_root"))

    # 2. schema validation
    sources = ctx.sources()
    validation: list[dict[str, Any]] = []
    for source in sources:
        result = validator.validate(
            source.document, source.schema_ref, schema_root=schema_root, disposition=disposition
        )
        if result.status == "BLOCKED":
            raise gen.GenerationBlocked(f"{source.rel}: {result.as_dict()['blocked']}")
        if result.status == "INVALID":
            detail = "; ".join(f"{f.rule} {f.path}: {f.message}" for f in result.findings)
            raise gen.GenerationRefused(f"{source.rel} does not validate: {detail}")
        validation.append(
            {
                "path": source.rel,
                "schema_ref": source.schema_ref,
                "evaluated_rules": sorted(result.evaluated_rules),
                "delegated_rules": sorted(result.delegated_rules),
                "semantic_review_rules": sorted(result.semantic_review_rules),
            }
        )

    # 3. registration gate
    prior_ids = {
        str(e.get("path")): str(e.get("contract_id"))
        for e in gen.as_maps((prior or {}).get("contracts"))
    }
    by_id: dict[str, Any] = {}
    unowned = 0
    for source in sources:
        meta = gen.as_map(source.document.get("metadata"))
        authority = gen.as_map(source.document.get("authority"))
        contract_id = str(meta.get("contract_id"))
        if source.rel in prior_ids and prior_ids[source.rel] != contract_id:
            raise gen.GenerationRefused(
                f"GOV-CONTRACT-002 {source.rel} changed contract_id "
                f"{prior_ids[source.rel]} -> {contract_id}"
            )
        if not _SEMVER.match(str(meta.get("version"))):
            raise gen.GenerationRefused(f"{source.rel} version is not semver")
        if authority.get("tier") not in _TIERS:
            raise gen.GenerationRefused(f"{source.rel} authority tier is unresolved")
        if authority.get("semantic_owner") != source.pack_rel:
            unowned += 1
        if contract_id in by_id:
            # coexistence is never declared by these sources (REGISTRY-010), so any second
            # declaration of an id is refused, active or not
            raise gen.GenerationRefused(
                f"REGISTRY-003 {contract_id} is declared by "
                f"{by_id[contract_id].rel} and {source.rel}"
            )
        by_id[contract_id] = source
    if unowned:
        raise gen.GenerationRefused(
            f"REGISTRY-008 {unowned} source(s) name a semantic_owner other than themselves"
        )

    # 4. references and graphs
    identities = ctx.pack_identities()
    resolution: list[dict[str, Any]] = []
    unresolved: list[str] = []
    external: dict[str, str] = {}

    def resolve(ref: str) -> None:
        if ref in by_id or ref in external:
            return
        paths = [p for p in identities.get(ref, []) if p not in {s.rel for s in sources}]
        if len(paths) == 1:
            external[ref] = paths[0]
        else:
            unresolved.append(ref)

    dependencies: dict[str, list[str]] = {}
    supersession: dict[str, list[str]] = {}
    conflicts: list[str] = []
    for contract_id, source in by_id.items():
        deps = gen.as_map(source.document.get("dependencies"))
        lifecycle = gen.as_map(source.document.get("lifecycle"))
        requires = [str(r) for r in gen.as_list(deps.get("requires_contracts"))]
        supersedes = [str(r) for r in gen.as_list(lifecycle.get("supersedes"))]
        deprecated_by = lifecycle.get("deprecated_by")
        for ref in (
            requires + supersedes + [str(r) for r in gen.as_list(deps.get("conflicts_with"))]
        ):
            resolve(ref)
        if deprecated_by:
            resolve(str(deprecated_by))
        dependencies[contract_id] = requires
        # One direction, successor -> superseded: "B supersedes A" and "A deprecated_by B" are
        # the same edge B -> A, so a reciprocal declaration is not a cycle.
        supersession.setdefault(contract_id, []).extend(supersedes)
        if deprecated_by:
            supersession.setdefault(str(deprecated_by), []).append(contract_id)
        status = gen.as_map(source.document.get("metadata")).get("status")
        for other in gen.as_list(deps.get("conflicts_with")):
            peer = by_id.get(str(other))
            peer_status = gen.as_map(peer.document.get("metadata")).get("status") if peer else None
            if status not in _INACTIVE and peer is not None and peer_status not in _INACTIVE:
                conflicts.append(f"{contract_id} conflicts_with {other}")
    if unresolved:
        raise gen.GenerationRefused(
            f"REGISTRY-004 unresolved references: {sorted(set(unresolved))}"
        )
    for name, edges in (("dependency", dependencies), ("supersession", supersession)):
        cycle = _cycle(edges)
        if cycle:
            rule = "REGISTRY-005" if name == "dependency" else "GOV-CONTRACT-009"
            raise gen.GenerationRefused(f"{rule} {name} cycle: {' -> '.join(cycle)}")
    if conflicts:
        raise gen.GenerationRefused(f"REGISTRY-006 unresolved conflicts: {sorted(conflicts)}")
    for ref, path in sorted(external.items()):
        document = gen.canonical.load_yaml(ctx.read(path).decode("utf-8"))
        resolution.append(
            {
                "ref": ref,
                "resolves_to": "pack_semantic_owner",
                "path": path,
                "digest": ctx.digest_of(document),
            }
        )

    # 5. projection bindings, pinned to this run's digests
    binding_refs: dict[str, list[str]] = {}
    for binding_id, spec in sorted(specs.items()):
        binding_refs.setdefault(str(spec.get("contract_id")), []).append(binding_id)

    def entry(source: Any) -> dict[str, Any]:
        meta = gen.as_map(source.document.get("metadata"))
        deps = gen.as_map(source.document.get("dependencies"))
        lifecycle = gen.as_map(source.document.get("lifecycle"))
        contract_id = str(meta.get("contract_id"))
        return {
            "contract_id": contract_id,
            "version": str(meta.get("version")),
            "kind": str(meta.get("kind")),
            "status": str(meta.get("status")),
            "path": source.rel,
            "digest": source.digest,
            "authority_tier": str(gen.as_map(source.document.get("authority")).get("tier")),
            "owner": str(meta.get("owner")),
            "requires_contracts": [str(r) for r in gen.as_list(deps.get("requires_contracts"))],
            "supersedes": [str(r) for r in gen.as_list(lifecycle.get("supersedes"))],
            "conflicts_with": [str(r) for r in gen.as_list(deps.get("conflicts_with"))],
            "projection_binding_refs": binding_refs.get(contract_id, []),
            "coexistence": {"allowed": False, "scope_discriminator": None},
        }

    entries = {cid: entry(by_id[cid]) for cid in sorted(by_id)}
    bindings: dict[str, dict[str, Any]] = {}
    drift: list[str] = []
    for binding_id, spec in sorted(specs.items()):
        contract_id = str(spec.get("contract_id"))
        if contract_id not in entries:
            raise gen.GenerationRefused(
                f"PROJECTION-001 target {binding_id} names unregistered {contract_id}"
            )
        instance = binding_gen.build(ctx, spec, entries[contract_id])
        found = parity.problems(ctx, instance, spec, by_id[contract_id], entries[contract_id])
        drift += [f"{binding_id}: {p}" for p in found]
        bindings[binding_gen.output_path(ctx, binding_id)] = instance
    if drift:
        raise gen.GenerationRefused(
            "REGISTRY-009 projection parity fails:\n  " + "\n  ".join(drift)
        )

    # 6. assemble, validate, return
    inputs = ctx.generation_inputs(sources, sorted(external.values()))
    meta_values = metadata if metadata is not None else ctx.head_metadata(inputs)
    output = ctx.section("contract_registry_output")
    all_refs = [r for e in entries.values() for r in e["requires_contracts"] + e["conflicts_with"]]
    statuses = {cid: e["status"] for cid, e in entries.items()}
    registry: dict[str, Any] = {
        "metadata": {
            "registry_id": str(output.get("registry_id")),
            "schema_ref": str(output.get("schema_ref")),
            "generated_at": str(meta_values["generated_at"]),
            "source_commit_sha": str(meta_values["source_commit_sha"]),
        },
        "generation": {
            "generated": True,
            "hand_edit_allowed": False,
            "generator_ref": GENERATED_BY,
            "deterministic": True,
            "binding_ref": ctx.binding_rel,
            "binding_version": str(ctx.section("generation_spec").get("version")),
            "canonicalization": str(gen.canonical.SERIALIZATION_ID),
        },
        "contracts": list(entries.values()),
        "graph": {
            "dependency_graph_acyclic": True,
            "supersession_graph_acyclic": True,
            "unresolved_refs": [],
            "unresolved_conflicts": [],
        },
        "coverage": {
            "active_contract_count": sum(e["status"] == "active" for e in entries.values()),
            "mechanically_enforced_count": sum(
                gen.as_map(by_id[cid].document.get("enforcement")).get("class") == "mechanical"
                for cid in entries
            ),
            "evidence_backed_count": sum(
                bool(gen.as_list(by_id[cid].document.get("evidence_obligations")))
                for cid in entries
            ),
            "unowned_doctrine_count": unowned,
            "projection_drift_count": len(drift),
            "deprecated_contract_reference_count": sum(
                statuses.get(ref) in _INACTIVE for ref in all_refs
            ),
        },
        "reference_resolution": resolution,
        "validation": validation,
        "generation_inputs": inputs,
    }
    _validate_output(ctx, registry, str(output.get("schema_ref")), disposition, schema_root)
    binding_schema = str(ctx.section("projection_binding_generation").get("schema_ref"))
    for instance in bindings.values():
        _validate_output(ctx, instance, binding_schema, disposition, schema_root)
    return Built(registry, bindings, inputs)


def _validate_output(
    ctx: Any, document: dict[str, Any], schema_ref: str, disposition: Any, schema_root: Path
) -> None:
    result = validator.validate(
        document, schema_ref, schema_root=schema_root, disposition=disposition
    )
    if result.status != "VALID":
        raise gen.GenerationRefused(f"generated {schema_ref} instance: {result.as_dict()}")


def render(ctx: Any, built: Built) -> dict[str, str]:
    header = gen.GENERATED_HEADER.format(generator=GENERATED_BY, binding=ctx.binding_rel)
    files = {
        str(ctx.section("contract_registry_output").get("path")): gen.dump_yaml(
            built.registry, header
        )
    }
    for rel, instance in built.bindings.items():
        files[rel] = binding_gen.render(ctx, instance)
    return files


def _committed(ctx: Any) -> dict[str, Any] | None:
    path = ctx.root / str(ctx.section("contract_registry_output").get("path"))
    if not path.is_file():
        return None
    return cast(dict[str, Any], gen.canonical.load_yaml(path.read_text(encoding="utf-8")))


def check(ctx: Any, *, provenance: bool) -> list[str]:
    """Differences between the committed outputs and a regeneration; empty means CURRENT."""
    committed = _committed(ctx)
    if committed is None:
        return ["registry is absent; run `make contract-registry`"]
    metadata = gen.as_map(committed.get("metadata"))
    built = build(
        ctx,
        {
            "generated_at": str(metadata.get("generated_at")),
            "source_commit_sha": str(metadata.get("source_commit_sha")),
        },
        committed,
    )
    found: list[str] = []
    expected = render(ctx, built)
    for rel, text in sorted(expected.items()):
        path = ctx.root / rel
        if not path.is_file():
            found.append(f"{rel} is absent")
        elif path.read_text(encoding="utf-8") != text:
            found.append(f"{rel} differs from regeneration (hand edit or stale input)")
    output_root = ctx.root / str(ctx.section("projection_binding_generation").get("output_root"))
    for path in sorted(output_root.glob("*.yaml")):
        rel = path.relative_to(ctx.root).as_posix()
        if rel not in expected:
            found.append(f"{rel} is not produced by any declared projection target")
    if provenance:
        found += ctx.verify_provenance(metadata, built.inputs)
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=gen.REPO_ROOT)
    parser.add_argument("--binding", type=Path, default=gen.DEFAULT_BINDING)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-provenance", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        ctx = gen.Context.load(root, args.binding)
        if args.check or args.check_provenance:
            found = check(ctx, provenance=args.check_provenance)
            print(
                json.dumps({"status": "DRIFT" if found else "CURRENT", "problems": found}, indent=2)
            )
            return 1 if found else 0
        built = build(ctx, None, _committed(ctx))
        for rel, text in render(ctx, built).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {rel}")
        return 0
    except gen.GenerationBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, indent=2))
        return 3
    except gen.GenerationRefused as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
