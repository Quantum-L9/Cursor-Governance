from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OdooAdapterError(ValueError):
    """Raised when an Odoo repository cannot be adapted safely."""


@dataclass(frozen=True)
class OdooRepositoryContext:
    repository_class: str
    root: str
    addon_roots: tuple[str, ...]
    modules: tuple[str, ...]
    validation_authority: Mapping[str, str]
    protected_paths: tuple[str, ...]
    metadata: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_class": self.repository_class,
            "root": self.root,
            "addon_roots": list(self.addon_roots),
            "modules": list(self.modules),
            "validation_authority": dict(self.validation_authority),
            "protected_paths": list(self.protected_paths),
            "metadata": dict(self.metadata),
        }


class OdooRepositoryAdapter:
    """Interpret generated data for pragmatic local-first Odoo repos."""

    MANIFEST_FILENAME = "__manifest__.py"

    PROTECTED_PATHS = (
        ".env",
        "**/*.pem",
        "**/*.key",
        "**/secrets/**",
        "odoo.conf",
        "filestore/**",
        "data/postgres/**",
    )
    VALIDATION_AUTHORITY = {
        "business_correctness": "odoo_runtime_tests",
        "style_and_lint": "ruff",
        "typing": "pyright_basic_editor_guardrail",
        "integration": "live_odoo_runtime",
    }

    def inspect(
        self,
        repository_root: str | Path,
    ) -> OdooRepositoryContext:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise OdooAdapterError(f"Repository root does not exist: {root}")
        addon_roots = self._discover_addon_roots(root)
        modules = self._discover_modules(
            root,
            addon_roots,
        )
        return OdooRepositoryContext(
            repository_class="odoo",
            root=str(root),
            addon_roots=tuple(addon_roots),
            modules=tuple(modules),
            validation_authority=self.VALIDATION_AUTHORITY,
            protected_paths=self.PROTECTED_PATHS,
            metadata={
                "local_first": True,
                "strict_typing_expected": False,
                "pyright_mode": "basic",
                "runtime_tests_are_authority": True,
                "docker_required": False,
                "module_count": len(modules),
                "conformant": bool(addon_roots),
            },
        )

    def enrich_unit(
        self,
        unit: Mapping[str, Any],
        context: OdooRepositoryContext,
    ) -> dict[str, Any]:
        enriched = dict(unit)
        metadata = dict(enriched.get("adapter_metadata", {}))
        metadata.update(
            {
                "repository_class": "odoo",
                "validation_authority": dict(context.validation_authority),
                "addon_roots": list(context.addon_roots),
                "known_modules": list(context.modules),
                "protected_paths": list(context.protected_paths),
                "typing_policy": {
                    "mode": "basic",
                    "unknown_member_noise_is_not_primary_signal": True,
                    "runtime_correctness_over_type_purity": True,
                },
            }
        )
        primary_class = str(unit.get("primary_class", ""))
        if primary_class in {
            "validation_procedure",
            "regression_candidate",
            "invariant_candidate",
        }:
            metadata["required_validation"] = [
                "ruff",
                "module_install_or_upgrade",
                "odoo_runtime_tests",
                "relevant_live_integration",
            ]
        if primary_class in {
            "architecture_boundary",
            "ownership_finding",
        }:
            metadata["inspect_first"] = [
                self.MANIFEST_FILENAME,
                "models/__init__.py",
                "models/*.py",
                "views/*.xml",
                "security/ir.model.access.csv",
            ]
        enriched["adapter_metadata"] = metadata
        return enriched

    @staticmethod
    def _discover_addon_roots(
        root: Path,
    ) -> list[str]:
        manifest_name = OdooRepositoryAdapter.MANIFEST_FILENAME
        candidates: list[Path] = []
        common = (
            root / "addons",
            root / "custom_addons",
            root / "odoo" / "addons",
        )
        for path in common:
            if path.is_dir():
                candidates.append(path)
        for manifest in root.rglob(manifest_name):
            parent = manifest.parent.parent
            if parent.is_dir():
                candidates.append(parent)
        unique = sorted({str(path.relative_to(root)) for path in candidates if path != root})
        return unique

    @staticmethod
    def _discover_modules(
        root: Path,
        addon_roots: list[str],
    ) -> list[str]:
        manifest_name = OdooRepositoryAdapter.MANIFEST_FILENAME
        modules: set[str] = set()
        for relative_root in addon_roots:
            addon_root = root / relative_root
            if not addon_root.is_dir():
                continue
            for child in addon_root.iterdir():
                if child.is_dir() and (child / manifest_name).is_file():
                    modules.add(str(child.relative_to(root)))
        return sorted(modules)


def main(argv: list[str] | None = None) -> int:
    raise SystemExit("odoo file-path CLI is disabled; use OdooRepositoryAdapter APIs")


if __name__ == "__main__":
    raise SystemExit(main())
