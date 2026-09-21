"""Focused tests for closed-world workflow and OpenAPI surface analyzers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


workflow = load("surface_analyzers.workflow", SCRIPTS / "surface_analyzers" / "workflow.py")
openapi = load("surface_analyzers.openapi", SCRIPTS / "surface_analyzers" / "openapi.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_workflow_analyzer_passes_resolved_contract_and_ignores_template(tmp_path: Path):
    workflow_path = tmp_path / ".github" / "workflows" / "ci.yml"
    write(
        workflow_path,
        """name: CI
jobs:
  build:
    runs-on: ubuntu-latest
  test:
    needs: build
    runs-on: ubuntu-latest
""",
    )
    assert workflow.analyze(tmp_path, workflow_path)["status"] == "PASS"

    template = tmp_path / ".github" / "workflows" / "dispatch.yml"
    write(template, "name: Dispatch template\non: workflow_dispatch\n")
    assert workflow.analyze(tmp_path, template)["status"] == "PASS"


def test_workflow_analyzer_handoffs_unresolved_internal_references(tmp_path: Path):
    workflow_path = tmp_path / ".github" / "workflows" / "ci.yml"
    write(
        workflow_path,
        """jobs:
  test:
    needs: build
    uses: ./.github/actions/missing
""",
    )
    result = workflow.analyze(tmp_path, workflow_path)
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert {finding["rule_id"] for finding in result["findings"]} == {
        "workflow.job.needs_resolution",
        "workflow.uses.local_resolution",
    }
    assert {finding["remediation_class"] for finding in result["findings"]} == {"HANDOFF"}


def test_openapi_analyzer_passes_valid_contract_and_handoffs_defects(tmp_path: Path):
    api = tmp_path / "openapi.yaml"
    write(
        api,
        """openapi: 3.1.0
paths:
  /health:
    get:
      responses:
        '200':
          description: healthy
""",
    )
    assert openapi.analyze(tmp_path, api)["status"] == "PASS"

    write(
        api,
        """openapi: 2.0.0
paths:
  health:
    get: {}
""",
    )
    result = openapi.analyze(tmp_path, api)
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert {finding["rule_id"] for finding in result["findings"]} >= {
        "openapi.version.supported",
        "openapi.path.absolute",
        "openapi.operation.responses",
    }
    assert {finding["remediation_class"] for finding in result["findings"]} == {"HANDOFF"}
