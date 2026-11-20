"""The fast controller guard calls the existing validator and does not rewrite digests."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = (
    ROOT / "environment" / "program-execution" / "core" / "program-execution-controller-template"
)
VALIDATOR = TEMPLATE / "scripts" / "validate_controller.py"
LINT = ROOT / ".github" / "workflows" / "l9-lint-test.yml"


def _validator():
    spec = importlib.util.spec_from_file_location("validate_controller_fast_guard", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_consistent_template_passes_without_running_the_suite() -> None:
    errors = _validator().validate(TEMPLATE, "template")
    assert errors == []


def test_digest_mismatch_fails_with_the_path(tmp_path: Path) -> None:
    destination = tmp_path / "template"
    shutil.copytree(
        TEMPLATE,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache"
        ),
    )
    readme = destination / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    errors = _validator().validate(destination, "template")
    assert "manifest digest mismatch: README.md" in errors


def test_lint_job_calls_the_validator_and_does_not_regenerate_the_digest() -> None:
    text = LINT.read_text(encoding="utf-8")
    lint = text.split("name: Lint and Type Check", 1)[1].split("name: Test Suite", 1)[0]
    assert "scripts/validate_controller.py" in lint
    assert "--mode template" in lint
    assert "generate_manifest" not in text
    assert "MANIFEST.yaml" not in lint
