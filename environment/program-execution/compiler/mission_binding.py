"""Compiler-side Mission Program Binding production (ADR-0026, contract §13).

This is the last design-time step and the one with the strictest ordering::

    Blueprint -> official validation -> blueprint_digest -> Mission Program Binding

Each arrow is load-bearing:

*Validation before identity.* An invalid Blueprint has no admissible identity,
so there is nothing for a binding to pin. The official validator
(``blueprint_validate.validate``) runs first and any failure emits nothing —
not a draft binding, not a partial file.

*Identity before binding.* ``blueprint_digest`` comes from the one shared
implementation, ``core/shared/blueprint_identity.py``, over the exact bytes of
the validated ``MANIFEST.yaml``. It is never computed here a second way.

*Binding outside the digest domain.* The binding names ``blueprint_digest``, so
storing it inside the Blueprint would make the Blueprint's identity depend on a
document that names that identity. The output path is required, explicit, and
checked to be outside the Blueprint root.

Mission identity is not a parameter. It is read off the parsed Mission by the
existing ``mission.binding.bind_mission_to_program``, which this module calls
rather than reimplements — there is one binding authority, not two.

Out of scope by construction: no Program Lock import, no Controller projection,
no campaign wiring, no Mission runtime.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .blueprint_validate import ValidationResult, validate
from .synthesizer import PE_ROOT

CORE_SHARED = PE_ROOT / "core" / "shared"
MISSION_ROOT = PE_ROOT / "mission"

for _path in (CORE_SHARED, MISSION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from binding import (  # noqa: E402 — the one binding authority (contract §17 reuse)
    MissionProgramBinding,
    bind_mission_to_program,
)
from blueprint_identity import compute_blueprint_digest  # noqa: E402
from mission import Mission  # noqa: E402

#: The circular shape ADR-0026 names, kept here so the prohibition is greppable.
FORBIDDEN_IN_BLUEPRINT_FILENAME = "MISSION_BINDING.yaml"


class MissionBindingError(ValueError):
    """A Mission Program Binding could not be produced, so none was written."""


def _is_inside(root: Path, candidate: Path) -> bool:
    """True when ``candidate`` resolves inside ``root``.

    ``realpath`` on both sides, like the template's own ``_write_under``: a
    symlink pointing into the Blueprint is the same circularity as a plain path.
    """
    root_real = os.path.realpath(str(root))
    candidate_real = os.path.realpath(str(candidate))
    return os.path.commonpath([root_real, candidate_real]) == root_real


def produce_binding(
    mission: Mission,
    blueprint_root: Path,
    *,
    program_id: str,
    binding_id: str,
    bound_at: datetime,
    output_path: Path,
    metadata: dict[str, Any] | None = None,
    validation_mode: str = "instantiated",
) -> MissionProgramBinding:
    """Validate, then identify, then bind — or fail closed having written nothing.

    ``output_path`` is explicit and required. There is no default inside the
    Blueprint to fall back to, because a default is exactly how the circular
    shape gets built by accident.
    """
    if not isinstance(mission, Mission):
        raise MissionBindingError("binding requires an already-parsed immutable Mission Revision")

    blueprint_root = Path(blueprint_root)
    if not blueprint_root.is_dir():
        raise MissionBindingError(f"blueprint root is not a directory: {blueprint_root}")

    output_path = Path(output_path)
    if _is_inside(blueprint_root, output_path):
        raise MissionBindingError(
            f"binding output {output_path} is inside the Blueprint whose digest it names; "
            "the final binding must live outside the Blueprint digest domain (ADR-0026)"
        )
    if output_path.exists():
        raise MissionBindingError(
            f"binding output already exists: {output_path}; historical bindings are immutable "
            "and a new Program requires a new binding"
        )

    # 1. Official validation. Not a second approximate validator, and not
    #    validate_or_repair: a repair rewrites MANIFEST.yaml, which would change
    #    the very identity being pinned.
    result = validate(blueprint_root, mode=validation_mode)
    if not result.ok:
        raise MissionBindingError(_validation_message(result))

    # 2. Identity, from the one shared implementation, over validated bytes.
    blueprint_digest = compute_blueprint_digest(blueprint_root)

    # 3. Binding, by the one binding authority. Mission digest comes from the
    #    parsed Mission inside that call, never from this module.
    binding = bind_mission_to_program(
        mission,
        binding_id=binding_id,
        program_id=program_id,
        blueprint_digest=blueprint_digest,
        bound_at=bound_at,
        metadata=metadata,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(binding.as_document(), sort_keys=False, width=110), encoding="utf-8"
    )
    return binding


def _validation_message(result: ValidationResult) -> str:
    detail = "; ".join(result.errors) if result.errors else "validator reported failure"
    return (
        f"Blueprint at {result.root} failed official {result.mode} validation, so it has no "
        f"admissible identity and no binding was written: {detail}"
    )


__all__ = [
    "FORBIDDEN_IN_BLUEPRINT_FILENAME",
    "MissionBindingError",
    "produce_binding",
]
