#!/usr/bin/env python3
"""Emit the ADR-0031 agent MCP assertion env for ONE principal (no human secret).

Formats written to a 0600 file (never to stdout):
  shell (default) — export KEY='value' lines, consumed by
                    ops/memory/export_agent_assertion_env.sh
  json            — one object, consumed by the sessionStart env merge

stdout is the absolute path of that file, or empty when assertion is skipped.
It is never a log of secrets: the helper refuses a terminal, emits only the
launching principal's signing key and grant entry, and never emits the human
door.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Allow running as a script from anywhere: the repository root is the import
# root for ``ops.memory``. Inserted before the import inside main(), so no
# module-level import has to follow a path mutation.
_ROOT = Path(__file__).resolve().parents[2]

HUMAN_PRINCIPAL = "human"


def _shell_escape(value: str) -> str:
    """Escape a value for use inside single-quoted shell strings."""
    return value.replace("'", "'\"'\"'")


def _default_tokens_map() -> Path:
    return Path(
        os.environ.get(
            "L9_MEMORY_SECRET_MAP",
            str(Path.home() / ".config/l9-memory/agent_tokens.local.json"),
        )
    )


def _default_grants_map() -> Path:
    return Path(
        os.environ.get(
            "L9_MEMORY_GRANTS_MAP",
            str(Path.home() / ".config/l9-memory/agent_grants.json"),
        )
    )


def _runtime_dir() -> str | None:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if runtime and Path(runtime).is_dir() and os.access(runtime, os.W_OK):
        return runtime
    return None


def _write_secret_file(payload: str) -> Path:
    """Write payload to a 0600 tempfile. stdout later gets only this path."""
    fd, name = tempfile.mkstemp(
        prefix="l9-agent-assertion-",
        suffix=".tmp",
        dir=_runtime_dir(),
        text=True,
    )
    try:
        os.fchmod(fd, 0o600)
        data = payload if payload.endswith("\n") else f"{payload}\n"
        os.write(fd, data.encode("utf-8"))
    except Exception:
        os.close(fd)
        Path(name).unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    return Path(name)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a mapping")
    return value


def build_runtime_identity_assertion(
    env: Mapping[str, str] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Resolve this process and build a sealed ``l9.identity-assertion/v1``.

    Actor and surface refs come from ``agent_registry.yaml``. Digests come from
    the canonical identity projection and its receipt. An unresolved actor
    refuses rather than guessing. A surface the binding does not list stays
    ``unknown`` and does not refuse the actor.
    """

    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    import yaml

    from ops.memory.agent_assertion import seal_identity_assertion
    from ops.memory.agent_identity import (
        MEMORY_PRODUCT_REF,
        RUNTIME_RESOLVER_REF,
        IdentityResolutionError,
        actor_ref_from_binding,
        normalized_runtime_evidence,
        resolve_agent_id,
        resolve_surface_id,
        runtime_evidence_digest,
        surface_ref_from_binding,
        unresolved_reason,
    )

    source = os.environ if env is None else env
    repo = _ROOT if root is None else root
    actor_id = resolve_agent_id(source)
    if not actor_id:
        raise IdentityResolutionError(unresolved_reason(source))

    registry = _mapping(
        yaml.safe_load(
            (repo / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
        ),
        "agent registry",
    )
    agents = _mapping(registry.get("agents"), "agent registry agents")
    binding = agents.get(actor_id)
    if not isinstance(binding, dict):
        raise IdentityResolutionError(f"no agent binding for resolved actor {actor_id}")
    actor_ref = actor_ref_from_binding(actor_id, binding)
    surface_id = resolve_surface_id(source)
    surface_ref = surface_ref_from_binding(surface_id, binding)

    projection = _mapping(
        yaml.safe_load(
            (repo / "generated/governance/canonical_identity.yaml").read_text(encoding="utf-8")
        ),
        "canonical identity projection",
    )
    receipt = _mapping(
        yaml.safe_load(
            (repo / "generated/governance/canonical_identity.receipt.yaml").read_text(
                encoding="utf-8"
            )
        ),
        "canonical identity receipt",
    )
    projected_actors = {
        item.get("id") for item in projection.get("actors", []) if isinstance(item, dict)
    }
    if actor_id not in projected_actors:
        raise IdentityResolutionError(
            f"resolved actor {actor_id} is not in the identity projection"
        )
    if surface_ref != "unknown":
        projected_surfaces = {
            item.get("id") for item in projection.get("surfaces", []) if isinstance(item, dict)
        }
        if surface_id not in projected_surfaces:
            raise IdentityResolutionError(
                f"resolved surface {surface_id} is not in the identity projection"
            )

    projection_meta = _mapping(projection.get("projection"), "projection metadata")
    receipt_projection = _mapping(receipt.get("projection"), "receipt projection")
    if projection_meta.get("source_revision") != receipt_projection.get("source_revision"):
        raise IdentityResolutionError(
            "canonical identity projection and receipt disagree on source revision"
        )
    authority = _mapping(registry.get("identity_authority"), "identity authority")
    binding_ref = str(authority["binding_ref"])
    projection_ref = str(authority["projection_ref"])
    bindings_ref = str(registry["artifact_id"])
    sources = _mapping(receipt_projection.get("sources"), "receipt sources")
    output = _mapping(receipt.get("output"), "receipt output")
    evidence = normalized_runtime_evidence(source)
    assertion = {
        "schema": "l9.identity-assertion/v1",
        "subject_ref": actor_ref,
        "product_ref": MEMORY_PRODUCT_REF,
        "resolved_dimensions": {
            "release_identity": "unknown",
            "runtime_identity": "unknown",
            "constellation_identity": "unknown",
            "actor_identity": actor_ref,
            "surface_identity": surface_ref,
        },
        "bindings": [binding_ref, f"{bindings_ref}#{actor_id}"],
        "evidence_refs": [projection_ref, binding_ref, f"{bindings_ref}#{actor_id}"],
        "resolver_ref": RUNTIME_RESOLVER_REF,
        "governing_coordinates": {
            "global_identity_authority_revision": receipt_projection["source_revision"],
            "identity_projection_ref": projection_ref,
            "identity_projection_digest": output["digest"],
            "actor_registry_digest": _mapping(sources.get("actor_registry"), "actor registry")[
                "digest"
            ],
            "surface_registry_digest": _mapping(
                sources.get("surface_registry"), "surface registry"
            )["digest"],
            "identity_binding_ref": binding_ref,
            "agent_bindings_ref": bindings_ref,
        },
        "result": "resolved",
        "provenance": {"runtime_evidence_digest": runtime_evidence_digest(evidence)},
    }
    return seal_identity_assertion(assertion)


def main(argv: list[str] | None = None) -> int:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from ops.memory.agent_assertion import ENV_HUMAN_DOOR_SECRET, env_from_local_secret_map
    from ops.memory.agent_identity import (
        IdentityResolutionError,
        resolve_agent_id,
        unresolved_reason,
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--agent-id",
        default=None,
        help="default: this process's DERIVED actor (ops/memory/agent_identity.py)",
    )
    ap.add_argument(
        "--format",
        choices=("shell", "json"),
        default="shell",
        help="shell export lines (default) or JSON object",
    )
    ap.add_argument(
        "--secret-map",
        dest="tokens_map",
        type=Path,
        default=_default_tokens_map(),
        help="local agent token store (agents door secret + per-agent signing keys)",
    )
    ap.add_argument(
        "--grants-map",
        type=Path,
        default=_default_grants_map(),
        help="registry-rendered grants map (environment/agents/tools/render_principals.py)",
    )
    args = ap.parse_args(argv)
    resolved = resolve_agent_id()
    if not resolved:
        print(
            f"refusing to mint an agent assertion: no memory identity ({unresolved_reason()})",
            file=sys.stderr,
        )
        return 2
    if args.agent_id is None:
        args.agent_id = resolved
    elif args.agent_id != resolved:
        print(
            f"refusing to mint an agent assertion: --agent-id {args.agent_id} "
            f"disagrees with resolved actor {resolved}",
            file=sys.stderr,
        )
        return 2
    try:
        identity_assertion = build_runtime_identity_assertion()
    except (IdentityResolutionError, OSError, ValueError, KeyError) as exc:
        print(f"refusing to mint an agent assertion: {exc}", file=sys.stderr)
        return 2
    if args.agent_id == HUMAN_PRINCIPAL:
        print("refusing to export human private entrance into agent env", file=sys.stderr)
        return 2
    if not args.tokens_map.is_file() or not args.grants_map.is_file():
        if args.format != "json":
            print(
                "# assertion skipped: local agent token store or grants map not found "
                "(memory-blind cold start OK)",
                file=sys.stderr,
            )
        return 0
    if sys.stdout.isatty():
        print(
            "refusing to write assertion env to a terminal: pipe it to a consumer "
            "that reads the emitted path (--format shell or --format json)",
            file=sys.stderr,
        )
        return 2
    env = env_from_local_secret_map(
        args.agent_id, args.tokens_map, args.grants_map, identity_assertion
    )
    # Structural guarantee from the library; kept as a hard refusal here too.
    env.pop(ENV_HUMAN_DOOR_SECRET, None)
    if args.format == "json":
        payload = json.dumps(env, separators=(",", ":"))
    else:
        payload = "\n".join(f"export {key}='{_shell_escape(value)}'" for key, value in env.items())
    path = _write_secret_file(payload)
    print(str(path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
