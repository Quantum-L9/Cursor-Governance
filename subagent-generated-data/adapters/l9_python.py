from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class L9PythonAdapterError(ValueError):
    """Raised when an L9 Python repository cannot be adapted safely."""


@dataclass(frozen=True)
class RepositoryContext:
    repository_class: str
    root: str
    authoritative_files: tuple[str, ...]
    validation_commands: tuple[str, ...]
    architecture_surfaces: tuple[str, ...]
    protected_paths: tuple[str, ...]
    metadata: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_class": self.repository_class,
            "root": self.root,
            "authoritative_files": list(self.authoritative_files),
            "validation_commands": list(self.validation_commands),
            "architecture_surfaces": list(self.architecture_surfaces),
            "protected_paths": list(self.protected_paths),
            "metadata": dict(self.metadata),
        }


class L9PythonRepositoryAdapter:
    """Interpret generated data for strict L9 Python repositories."""

    REQUIRED_FILES = (
        "pyproject.toml",
        "uv.lock",
        "AGENTS.md",
    )
    AUTHORITATIVE_FILES = (
        "AGENTS.md",
        "ARCHITECTURE.md",
        "DEVELOPMENT.md",
        "TESTING.md",
        "OPERATIONS.md",
        "RUNBOOK.md",
        "SECURITY.md",
        "pyproject.toml",
        "uv.lock",
    )
    VALIDATION_COMMANDS = (
        "uv sync --locked",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run pyright",
        "uv run pytest --tb=short -q",
    )
    PROTECTED_PATHS = (
        ".env",
        "**/*.pem",
        "**/*.key",
        "**/secrets/**",
        ".github/workflows/**",
        "AGENTS.md",
        "SECURITY.md",
    )

    def inspect(
        self,
        repository_root: str | Path,
    ) -> RepositoryContext:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise L9PythonAdapterError(f"Repository root does not exist: {root}")
        missing_required = [
            filename for filename in self.REQUIRED_FILES if not (root / filename).is_file()
        ]
        architecture_surfaces = self._discover_surfaces(root)
        return RepositoryContext(
            repository_class="l9_python",
            root=str(root),
            authoritative_files=tuple(
                filename for filename in self.AUTHORITATIVE_FILES if (root / filename).exists()
            ),
            validation_commands=self.VALIDATION_COMMANDS,
            architecture_surfaces=tuple(architecture_surfaces),
            protected_paths=self.PROTECTED_PATHS,
            metadata={
                "strict_typing_expected": True,
                "uv_lock_required": True,
                "py_typed_expected": True,
                "ci_required": True,
                "missing_required_files": missing_required,
                "conformant": not missing_required,
            },
        )

    def enrich_unit(
        self,
        unit: Mapping[str, Any],
        context: RepositoryContext,
    ) -> dict[str, Any]:
        enriched = dict(unit)
        metadata = dict(enriched.get("adapter_metadata", {}))
        metadata.update(
            {
                "repository_class": "l9_python",
                "validation_authority": {
                    "format_and_lint": "ruff",
                    "type_analysis": "pyright_strict",
                    "behavior_validation": "pytest",
                    "dependency_environment": "uv",
                },
                "canonical_validation_commands": list(context.validation_commands),
                "authoritative_files": list(context.authoritative_files),
                "architecture_surfaces": list(context.architecture_surfaces),
                "protected_paths": list(context.protected_paths),
            }
        )
        primary_class = str(unit.get("primary_class", ""))
        if primary_class in {
            "validation_procedure",
            "regression_candidate",
            "invariant_candidate",
        }:
            metadata["required_validation_ladder"] = [
                "format",
                "lint",
                "type",
                "test",
                "ci",
            ]
        if primary_class in {
            "architecture_boundary",
            "ownership_finding",
            "dependency_finding",
        }:
            metadata["architecture_authority_required"] = True
        enriched["adapter_metadata"] = metadata
        return enriched

    @staticmethod
    def _discover_surfaces(
        root: Path,
    ) -> list[str]:
        candidates = (
            "src",
            "tests",
            "evals",
            "prompts",
            "typings",
            ".github/workflows",
            "docs",
        )
        return [candidate for candidate in candidates if (root / candidate).exists()]


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or enrich data for an L9 Python repo.")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--unit")
    args = parser.parse_args()
    adapter = L9PythonRepositoryAdapter()
    context = adapter.inspect(args.repository)
    result: Mapping[str, Any]
    if args.unit:
        unit = load_json(args.unit)
        if not isinstance(unit, Mapping):
            raise SystemExit("Unit root must be an object")
        result = adapter.enrich_unit(unit, context)
    else:
        result = context.to_dict()
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if context.metadata["conformant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
