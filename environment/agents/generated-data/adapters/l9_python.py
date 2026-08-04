from __future__ import annotations

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

    AGENTS_MD = "AGENTS.md"
    REQUIRED_FILES = (
        "pyproject.toml",
        "uv.lock",
        AGENTS_MD,
    )
    AUTHORITATIVE_FILES = (
        AGENTS_MD,
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
        AGENTS_MD,
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


def main(argv: list[str] | None = None) -> int:
    raise SystemExit("l9_python file-path CLI is disabled; use L9PythonRepositoryAdapter APIs")


if __name__ == "__main__":
    raise SystemExit(main())
