#!/usr/bin/env python3
# pyright: strict
"""Build ``canonical.schema.contract_projection_binding.v1`` instances.

One instance per ``projection_targets`` entry of a generation binding. The contract digest
comes from the registry the same run generates (``projection_binding_generation.contract_digest``
``source: generated_contract_registry``), and ``projected_content_sha256`` is the sha256 of the
target's actual bytes. Nothing is emitted for a target that fails parity
(``validate_projection_parity.problems``): a binding is never generated without it.

This module is driven by ``generate_contract_registry.py``, which owns the write and the
``--check`` comparison, so the registry and its bindings are always produced together.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_GEN = Path(__file__).resolve().parent / "governance_generation.py"


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
GENERATED_BY = "tools/authority/generate_projection_binding.py"


def output_path(ctx: Any, binding_id: str) -> str:
    root = str(ctx.section("projection_binding_generation").get("output_root"))
    return f"{root}/{binding_id}.yaml"


def build(ctx: Any, spec: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """The binding instance for one declared target, pinned to one registry entry."""
    target = gen.as_map(spec.get("target"))
    target_rel = ctx.repo_rel(str(target.get("path")))
    tooling = ctx.section("tooling")
    return {
        "binding": {
            "binding_id": str(spec.get("binding_id")),
            "contract_id": str(entry["contract_id"]),
            "contract_version": str(entry["version"]),
            "contract_digest": str(entry["digest"]),
            "clause_refs": [str(c) for c in gen.as_map(spec.get("clause_anchors"))],
        },
        "target": {
            "type": str(target.get("type")),
            "path": target_rel,
            "projection_mode": str(target.get("projection_mode")),
        },
        "ownership": {"normative_owner": "contract", "target_may_redefine_semantics": False},
        "generation": {
            "mode": "manually_maintained_with_parity_check",
            "generator_ref": None,
            "parity_validator_ref": str(tooling.get("projection_parity_validator_available")),
        },
        "integrity": {
            "projected_content_sha256": gen.canonical.bytes_digest(ctx.read(target_rel)),
            "drift_policy": "fail_closed",
        },
        "provenance": {
            "generated_by": GENERATED_BY,
            "binding_spec": f"{ctx.binding_rel}#projection_targets",
            "contract_path": str(entry["path"]),
            "registry": str(ctx.section("contract_registry_output").get("path")),
        },
    }


def render(ctx: Any, document: dict[str, Any]) -> str:
    header = gen.GENERATED_HEADER.format(generator=GENERATED_BY, binding=ctx.binding_rel)
    return str(gen.dump_yaml(document, header))
