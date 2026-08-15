"""Official Program Execution Blueprint validator adapter (contract §13, Gate D).

Invokes the exact governing validator (core/program-execution-blueprint-template/
scripts/validate_blueprint.py). Never maintains a second approximate validator.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .synthesizer import TEMPLATE_ROOT

VALIDATOR = TEMPLATE_ROOT / "scripts" / "validate_blueprint.py"


@dataclass
class ValidationResult:
    ok: bool
    mode: str
    root: Path
    errors: list[str] = field(default_factory=list)


def validate(blueprint_root: Path, mode: str = "instantiated") -> ValidationResult:
    # sys.executable, not bare `python3` from PATH: the validator needs
    # jsonschema, and PATH/HOME/user-site state varies by shell (2026-08-15
    # factory repair — `python3` under a clean HOME or a venv-prefixed PATH
    # silently lost jsonschema and failed every blueprint validation).
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(blueprint_root), "--mode", mode],
        capture_output=True,
        text=True,
        check=False,
    )
    errors = []
    for line in completed.stdout.splitlines():
        if line.startswith("- "):
            errors.append(line[2:])
    return ValidationResult(
        ok=completed.returncode == 0, mode=mode, root=blueprint_root, errors=errors
    )


def validate_or_repair(
    blueprint_root: Path, mode: str = "instantiated", repair_attempts: int = 1
) -> ValidationResult:
    """PASS -> eligible for Program Lock. FAIL -> bounded autonomous repair.

    Repair is attempted only for deterministic non-authority issues (stale
    manifest digests). It never alters user intent, never invents authority,
    and never widens a ceiling. Beyond the bounded budget the failure is
    escalated as an explicit blocker.
    """
    result = validate(blueprint_root, mode)
    if result.ok:
        return result
    for _ in range(max(0, repair_attempts)):
        if any("manifest" in error.lower() for error in result.errors):
            from .synthesizer import instantiate

            instantiate.write_manifest(blueprint_root)
            result = validate(blueprint_root, mode)
            if result.ok:
                return result
        break
    return result


__all__ = ["ValidationResult", "VALIDATOR", "validate", "validate_or_repair"]
