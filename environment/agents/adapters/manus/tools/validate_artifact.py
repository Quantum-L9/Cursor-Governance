"""``governance_validate_artifact`` — validate one artifact by path.

The repository validators are registry-wide. This tool runs the right validator
and then filters its findings down to the artifact the caller named, so a
targeted check does not require reading a full sweep. If no scoped validator
exists for a prefix, it says so instead of inventing one.
"""

from __future__ import annotations

from typing import Any

from .base import RuntimeContext, ToolInputError, ToolSpec, resolve_within

NAME = "governance_validate_artifact"
DESCRIPTION = (
    "Run the repository validator that governs a single artifact path and report only "
    "findings that reference it. Read-only; refuses paths outside the governance root."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Repository-relative path to the artifact to validate.",
        }
    },
    "required": ["path"],
    "additionalProperties": False,
}

# Ordered: the first matching prefix wins.
VALIDATORS: tuple[tuple[str, str], ...] = (
    (
        "environment/agents/adapters/manus",
        "environment/agents/adapters/manus/validate_manus_adapter.py",
    ),
    ("environment/agents", "environment/agents/tools/validate_agents.py"),
)


def _select(relative: str) -> str | None:
    for prefix, validator in VALIDATORS:
        if relative == prefix or relative.startswith(f"{prefix}/"):
            return validator
    return None


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    relative = arguments.get("path")
    if not isinstance(relative, str) or not relative.strip():
        raise ToolInputError("path must be a non-empty repository-relative path")

    target = resolve_within(context.governance_root, relative)
    if not target.exists():
        raise ToolInputError(f"artifact does not exist: {relative}")
    normalised = target.relative_to(context.governance_root).as_posix()

    validator = _select(normalised)
    if validator is None:
        return {
            "path": normalised,
            "status": "unsupported",
            "reason": (
                "no scoped validator is declared for this prefix; supported prefixes: "
                + ", ".join(prefix for prefix, _ in VALIDATORS)
            ),
            "validators_declared": [item for _, item in VALIDATORS],
        }

    python = context.governance_root / ".venv/bin/python"
    interpreter = str(python) if python.is_file() else "python3"
    command = [interpreter, str(context.governance_root / validator)]
    if validator.endswith("validate_manus_adapter.py"):
        command += ["--repo-root", str(context.governance_root)]

    result = context.run(command, timeout=300)
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    haystack = f"{stdout}\n{stderr}".splitlines()
    needle = normalised.rsplit("/", 1)[-1]
    matched = [line.strip() for line in haystack if normalised in line or needle in line]

    return {
        "path": normalised,
        "validator": validator,
        "exit_code": result.get("exit_code"),
        "status": "passed" if result.get("exit_code") == 0 else "failed",
        "matched_findings": matched[:20],
        "summary": (stderr.strip().splitlines() or ["(no stderr)"])[-1][:400],
        "note": (
            "Validator is registry-wide; matched_findings is filtered to this artifact. "
            "An empty list with exit_code 0 means the artifact contributed no findings."
        ),
    }


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
